"""
Runtime policy: where and how an engine may run.

A policy is declarative and frozen. It says what is allowed; the engine
adapter applies what it can and reports in ``ExecutionMetadata`` what it
actually used. Which limits an engine can really enforce differs, so the
policy marks the difference instead of hiding it:

- ``timeout_seconds``: enforced by the executor for the caller (the caller
  gets ``ExecutionTimeoutError`` at the deadline); stopping the engine itself
  needs cooperation (see ``cancellation``);
- ``max_concurrency``: enforced by ``ResourceManager.slot``; ``queue_timeout_seconds``
  bounds the wait for a slot;
- ``device``: checked against the devices the engine reports; without
  ``allow_device_fallback`` a missing device is a ``PolicyViolationError``.
  The boundary is deliberate: the ENGINE CONFIGURATION chooses the device
  (a loaded model sits on one device); the policy only RESTRICTS it - it can
  reject an execution, not move a model to another device;
- ``max_threads``: applied by the adapter; process-global thread settings go
  through ``ResourceManager.claim_setting`` so two engines cannot silently
  overwrite each other;
- ``memory_limit_mb``: a hint unless ``memory_limit_enforced`` - Python cannot
  cap the memory of a library inside the same process.

``narrow`` combines a provider's policy with a request's: the stricter value
of every limit wins, so a request can tighten but never loosen a policy.
``from_runtime_config`` reads an existing runtime section (e.g. the NLP
``NLPRuntimeConfigV2``: device, threads, batch_size, memory_limit_mb_hint).
"""

import math
import re
from dataclasses import dataclass, replace
from typing import Any, Mapping, Optional, Sequence

from ai_platform.common.core.execution.errors import PolicyViolationError

_DEVICE = re.compile(r"^(auto|cpu|cuda:\d+|mps)$")


def _smaller(left: Optional[float], right: Optional[float]) -> Optional[float]:
    if left is None:
        return right
    if right is None:
        return left
    return min(left, right)


@dataclass(frozen=True)
class RuntimePolicy:  # pylint: disable=too-many-instance-attributes
    """What an execution may use. None = no limit from this policy."""

    device: str = "auto"
    allow_device_fallback: bool = True
    max_threads: Optional[int] = None
    batch_size: Optional[int] = None
    max_concurrency: Optional[int] = None
    timeout_seconds: Optional[float] = None
    queue_timeout_seconds: Optional[float] = None
    memory_limit_mb: Optional[int] = None
    memory_limit_enforced: bool = False

    def __post_init__(self) -> None:
        device = str(self.device).strip().lower()
        if not _DEVICE.match(device):
            raise PolicyViolationError(f"device must be auto, cpu, cuda:N or mps, got {device!r}",
                                       stage="policy")
        object.__setattr__(self, "device", device)
        for name in ("max_threads", "batch_size", "max_concurrency", "memory_limit_mb"):
            value = getattr(self, name)
            # bool is a subclass of int in Python: True must not pass as 1.
            if value is not None and (isinstance(value, bool) or not isinstance(value, int)
                                      or value <= 0):
                raise PolicyViolationError(f"{name} must be a positive integer, got {value!r}",
                                           stage="policy")
        for name in ("timeout_seconds", "queue_timeout_seconds"):
            value = getattr(self, name)
            if value is not None and (isinstance(value, bool)
                                      or not isinstance(value, (int, float))
                                      or not math.isfinite(value) or value <= 0):
                raise PolicyViolationError(f"{name} must be a finite positive number, got "
                                           f"{value!r}", stage="policy")
        for name in ("allow_device_fallback", "memory_limit_enforced"):
            if not isinstance(getattr(self, name), bool):
                raise PolicyViolationError(f"{name} must be a bool", stage="policy")

    def narrow(self, other: Optional["RuntimePolicy"]) -> "RuntimePolicy":
        """The stricter combination of two policies (a request cannot loosen a provider)."""
        if other is None:
            return self
        device = self.device if other.device == "auto" else other.device
        if self.device not in ("auto", device):
            raise PolicyViolationError(f"device {other.device!r} conflicts with the provider's "
                                       f"{self.device!r}", stage="policy")
        return replace(
            self, device=device,
            allow_device_fallback=self.allow_device_fallback and other.allow_device_fallback,
            max_threads=_smaller(self.max_threads, other.max_threads),
            batch_size=_smaller(self.batch_size, other.batch_size),
            max_concurrency=_smaller(self.max_concurrency, other.max_concurrency),
            timeout_seconds=_smaller(self.timeout_seconds, other.timeout_seconds),
            queue_timeout_seconds=_smaller(self.queue_timeout_seconds,
                                           other.queue_timeout_seconds),
            memory_limit_mb=_smaller(self.memory_limit_mb, other.memory_limit_mb),
            memory_limit_enforced=self.memory_limit_enforced or other.memory_limit_enforced)

    def resolve_device(self, available: Sequence[str]) -> str:
        """The device to use, given the devices the engine can use (e.g. ["cpu"])."""
        devices = [str(d).lower() for d in available]
        if not devices:
            raise PolicyViolationError("the engine reports no usable device", stage="device")
        if self.device == "auto":
            return next((d for d in devices if d != "cpu"), devices[0])
        if self.device in devices:
            return self.device
        if self.allow_device_fallback:
            return "cpu" if "cpu" in devices else devices[0]
        raise PolicyViolationError(f"device {self.device!r} is not available (available: "
                                   f"{devices}) and fallback is not allowed", stage="device",
                                   details={"requested": self.device, "available": devices})

    @classmethod
    def from_runtime_config(cls, runtime: Any, **overrides: Any) -> "RuntimePolicy":
        """Policy from a runtime section (object or mapping with device/threads/...)."""
        def read(name: str) -> Any:
            if isinstance(runtime, Mapping):
                return runtime.get(name)
            return getattr(runtime, name, None)

        values = {"device": read("device") or "auto", "max_threads": read("threads"),
                  "batch_size": read("batch_size"),
                  "memory_limit_mb": read("memory_limit_mb_hint")}
        fallback = read("allow_device_fallback")
        if fallback is not None:
            values["allow_device_fallback"] = bool(fallback)
        values.update(overrides)
        return cls(**values)
