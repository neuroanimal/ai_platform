"""
Cooperative cancellation shared by async code and worker threads.

A ``CancellationToken`` is set once, with the first reason given; later calls
change nothing. Engines that run in a worker thread (Stanza, OCR, llama.cpp
bindings) cannot be interrupted from outside - Python has no safe way to kill
a thread - so cancellation is cooperative: the work calls
``raise_if_cancelled`` (or ``ExecutionContext.check``) between its steps, and
an engine that offers its own stop hook registers it with ``add_callback``.
Work that never checks keeps running after cancellation; the executor then
reports it as abandoned rather than pretending it stopped.

Child tokens are cancelled together with their parent, not the other way
round - a step can be stopped without stopping the whole run.
"""

import threading
from typing import Callable, List, Optional

from ai_platform.common.core.execution.errors import ExecutionCancelledError


class CancellationToken:
    """Thread-safe, set-once cancellation flag with callbacks."""

    def __init__(self) -> None:
        self._event = threading.Event()
        self._lock = threading.Lock()
        self._reason: Optional[str] = None
        self._callbacks: List[Callable[[str], None]] = []

    @property
    def cancelled(self) -> bool:
        """True once ``cancel`` was called."""
        return self._event.is_set()

    @property
    def reason(self) -> Optional[str]:
        """The reason given to the first ``cancel`` call."""
        return self._reason

    def cancel(self, reason: str = "cancelled by the caller") -> bool:
        """Cancel; returns False when it was already cancelled (the first reason stays)."""
        with self._lock:
            if self._event.is_set():
                return False
            self._reason = reason
            self._event.set()
            callbacks, self._callbacks = self._callbacks, []
        for callback in callbacks:
            callback(reason)
        return True

    def add_callback(self, callback: Callable[[str], None]) -> None:
        """Call ``callback(reason)`` on cancellation (at once if already cancelled)."""
        with self._lock:
            if not self._event.is_set():
                self._callbacks.append(callback)
                return
        callback(self._reason or "cancelled")

    def raise_if_cancelled(self, stage: Optional[str] = None) -> None:
        """Raise ``ExecutionCancelledError`` when cancelled."""
        if self._event.is_set():
            raise ExecutionCancelledError(f"execution cancelled: {self._reason}", stage=stage,
                                          details={"reason": self._reason})

    def wait(self, timeout: Optional[float] = None) -> bool:
        """Block until cancelled or ``timeout`` seconds; True when cancelled."""
        return self._event.wait(timeout)

    def child(self) -> "CancellationToken":
        """A token cancelled together with this one (and cancellable on its own)."""
        token = CancellationToken()
        self.add_callback(lambda reason: token.cancel(f"parent cancelled: {reason}"))
        return token
