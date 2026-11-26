"""
Shared resources of engines: loaded models, concurrency slots, process-global settings.

Three things every engine adapter needs and should not invent again:

- ``lease(key, factory, closer)``: one shared object per key (a loaded Stanza
  pipeline, an OCR model), created on first use, reference-counted, closed by
  ``release`` of the last user or by ``close_all``. Creation of the same key
  happens once even when several threads ask at the same moment.
- ``slot(key, limit, context)``: at most ``limit`` executions of one engine at
  a time (``RuntimePolicy.max_concurrency``). Waiting honours the context's
  cancellation and deadline and ``queue_timeout_seconds``; the time waited is
  returned for ``ExecutionMetadata.queue_seconds``.
- ``claim_setting(name, value, owner)``: process-global settings (e.g.
  ``torch.set_num_threads``) are claimed before they are applied. Every owner
  that relies on the value is recorded; a different value is a
  ``ResourceConflictError`` while any OTHER owner holds a claim, instead of a
  silent overwrite that changes another engine's behaviour. ``release_settings``
  drops only that owner's claims - the setting stays protected while anyone
  else still relies on it.

Synchronization uses threading primitives, so the manager works from
worker threads and from asyncio code (where blocking waits are run in a
thread by the executor).
"""

import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterator, Optional, Tuple

from ai_platform.common.core.execution.errors import (
    ResourceConflictError,
    ResourceUnavailableError,
)

#: How often a waiting slot request re-checks cancellation and the deadline.
POLL_SECONDS = 0.05


@dataclass
class _Shared:
    value: Any
    closer: Optional[Callable[[Any], None]]
    users: int = 0


@dataclass
class _Slots:
    limit: int
    semaphore: threading.Semaphore = field(init=False)
    in_use: int = 0
    waiting: int = 0

    def __post_init__(self) -> None:
        self.semaphore = threading.Semaphore(self.limit)


class ResourceManager:
    """Leases of shared objects, concurrency slots and process-global setting claims."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._shared: Dict[str, _Shared] = {}
        self._creating: Dict[str, threading.Lock] = {}
        self._slots: Dict[str, _Slots] = {}
        # setting name -> (value, owners that rely on it)
        self._settings: Dict[str, Tuple[Any, set]] = {}

    # -- shared objects -------------------------------------------------------

    def acquire(self, key: str, factory: Callable[[], Any],
                closer: Optional[Callable[[Any], None]] = None) -> Any:
        """The shared object for ``key`` (created by ``factory`` once); counts one user."""
        with self._lock:
            create_lock = self._creating.setdefault(key, threading.Lock())
        with create_lock:
            with self._lock:
                shared = self._shared.get(key)
            if shared is None:
                shared = _Shared(factory(), closer)
                with self._lock:
                    self._shared[key] = shared
            with self._lock:
                shared.users += 1
                return shared.value

    def release(self, key: str, close_when_unused: bool = False) -> None:
        """One user fewer; with ``close_when_unused`` the last user closes the object."""
        with self._lock:
            shared = self._shared.get(key)
            if shared is None:
                return
            shared.users = max(0, shared.users - 1)
            if not (close_when_unused and shared.users == 0):
                return
            del self._shared[key]
        self._close(shared)

    @contextmanager
    def lease(self, key: str, factory: Callable[[], Any],
              closer: Optional[Callable[[Any], None]] = None,
              close_when_unused: bool = False) -> Iterator[Any]:
        """``with manager.lease(key, factory) as obj:`` - acquire and release."""
        value = self.acquire(key, factory, closer)
        try:
            yield value
        finally:
            self.release(key, close_when_unused)

    def users(self, key: str) -> int:
        """Current users of a shared object (0 when not created)."""
        with self._lock:
            shared = self._shared.get(key)
            return shared.users if shared else 0

    def close_all(self) -> Dict[str, str]:
        """Close every shared object; returns {key: error} for closers that failed."""
        with self._lock:
            shared, self._shared = self._shared, {}
        errors = {}
        for key, item in shared.items():
            try:
                self._close(item)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                errors[key] = f"{type(exc).__name__}: {exc}"
        return errors

    @staticmethod
    def _close(shared: _Shared) -> None:
        if shared.closer is not None:
            shared.closer(shared.value)
        elif hasattr(shared.value, "close"):
            shared.value.close()

    # -- concurrency slots ----------------------------------------------------

    @contextmanager
    def slot(self, key: str, limit: int, context=None,
             queue_timeout_seconds: Optional[float] = None) -> Iterator[float]:
        """Hold one of ``limit`` slots of ``key``; yields the seconds waited for it."""
        with self._lock:
            slots = self._slots.get(key)
            if slots is None or slots.limit != limit:
                if slots is not None and (slots.in_use or slots.waiting):
                    # Replacing the semaphore would strand the holders/waiters of the old one.
                    raise ResourceConflictError(
                        f"slot limit of {key!r} changed from {slots.limit} to {limit} while "
                        f"{slots.in_use} hold and {slots.waiting} wait for a slot", stage="slot")
                slots = self._slots[key] = _Slots(limit)
            slots.waiting += 1
        start = time.monotonic()
        try:
            while not slots.semaphore.acquire(timeout=POLL_SECONDS):
                waited = time.monotonic() - start
                if context is not None:
                    context.check(f"waiting for a slot of {key}")
                if queue_timeout_seconds is not None and waited >= queue_timeout_seconds:
                    raise ResourceUnavailableError(
                        f"no free slot of {key!r} within {queue_timeout_seconds} s",
                        stage="slot", details={"key": key, "limit": limit,
                                               "waited_seconds": round(waited, 3)})
        finally:
            with self._lock:
                slots.waiting -= 1
        with self._lock:
            slots.in_use += 1
        try:
            yield time.monotonic() - start
        finally:
            with self._lock:
                slots.in_use -= 1
            slots.semaphore.release()

    def slots_in_use(self, key: str) -> int:
        """Slots of ``key`` held now."""
        with self._lock:
            slots = self._slots.get(key)
            return slots.in_use if slots else 0

    # -- process-global settings ----------------------------------------------

    def claim_setting(self, name: str, value: Any, owner: str) -> bool:
        """Claim a process-global setting; True when this owner must apply it now.

        The same value claimed again adds the owner to those relying on it and
        returns False. A different value is allowed only when no other owner
        holds a claim (then this owner becomes the only one and must apply
        it); otherwise it is a ResourceConflictError and nothing changes.
        """
        with self._lock:
            current = self._settings.get(name)
            if current is None:
                self._settings[name] = (value, {owner})
                return True
            current_value, owners = current
            if current_value == value:
                owners.add(owner)
                return False
            others = owners - {owner}
            if not others:
                self._settings[name] = (value, {owner})
                return True
            raise ResourceConflictError(
                f"{name}={value!r} requested by {owner!r}, but {sorted(others)} rely on "
                f"{current_value!r} for the whole process", stage="setting",
                details={"setting": name, "requested": value, "current": current_value,
                         "owners": sorted(others)})

    def release_settings(self, owner: str) -> None:
        """Drop the claims of ``owner``; a setting stays claimed while others rely on it."""
        with self._lock:
            for name in list(self._settings):
                owners = self._settings[name][1]
                owners.discard(owner)
                if not owners:
                    del self._settings[name]

    def setting(self, name: str) -> Optional[Tuple[Any, frozenset]]:
        """(value, owners relying on it) of a claimed setting, or None."""
        with self._lock:
            current = self._settings.get(name)
            return (current[0], frozenset(current[1])) if current else None
