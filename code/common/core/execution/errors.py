"""
Errors of the execution contract, and a serializable view of any error.

Rule of propagation (the same for every engine - NLP, OCR/HTR, speech, LLM):

1. Errors raised by the engine or the provider keep their type. A provider
   error such as ``NLPProviderInputError`` reaches the caller as itself; the
   executor never flattens it into a generic error.
2. Errors the execution layer itself decides are of the types below:
   cancellation, timeout, policy violation, resource unavailable or in
   conflict. Their ``__cause__`` is the engine error, if there was one.
3. Every error that leaves ``execute`` carries ``execution_metadata`` (an
   ``ExecutionMetadata``) as an attribute, so the layer above can log what
   was attempted, where and for how long, whatever the error type.
4. ``ErrorInfo.from_exception`` turns any exception into data (code,
   retryable, stage, details, chained cause). It reads ``code``,
   ``retryable`` and ``details`` when the exception has them, so provider
   error hierarchies need no dependency on this module to be described.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional

MAX_CAUSE_DEPTH = 5


class ExecutionError(Exception):
    """Base of the errors decided by the execution layer."""

    default_code = "execution_error"
    default_retryable = False

    def __init__(self, message: str, *, code: Optional[str] = None,
                 retryable: Optional[bool] = None, stage: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.code = code or self.default_code
        self.retryable = self.default_retryable if retryable is None else retryable
        self.stage = stage
        self.details = dict(details or {})


class ExecutionCancelledError(ExecutionError):
    """The caller cancelled the execution (``CancellationToken.cancel``)."""

    default_code = "execution_cancelled"


class ExecutionTimeoutError(ExecutionError):
    """The deadline passed before the work finished. Retrying may succeed."""

    default_code = "execution_timeout"
    default_retryable = True


class PolicyViolationError(ExecutionError):
    """The request cannot be run under the runtime policy (e.g. device not available)."""

    default_code = "policy_violation"


class ResourceUnavailableError(ExecutionError):
    """A shared resource or a concurrency slot was not obtained in time."""

    default_code = "resource_unavailable"
    default_retryable = True


class ResourceConflictError(ExecutionError):
    """Two users need incompatible process-global settings (e.g. thread counts)."""

    default_code = "resource_conflict"


@dataclass(frozen=True)
class ErrorInfo:
    """Serializable description of an exception and its causes."""

    type: str
    code: str
    message: str
    retryable: bool = False
    stage: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    cause: Optional["ErrorInfo"] = None

    def __post_init__(self) -> None:
        # Deferred import: freeze has no dependencies, errors is imported everywhere.
        from ai_platform.common.core.execution.freeze import (  # pylint: disable=import-outside-toplevel
            deep_freeze,
        )
        object.__setattr__(self, "details", deep_freeze(dict(self.details)))

    @classmethod
    def from_exception(cls, exc: BaseException, stage: Optional[str] = None,
                       _depth: int = 0) -> "ErrorInfo":
        """Describe ``exc`` (duck-typed ``code``/``retryable``/``details``/``stage``)."""
        cause = exc.__cause__ or (None if exc.__suppress_context__ else exc.__context__)
        details = getattr(exc, "details", None)
        return cls(
            type=type(exc).__name__,
            code=str(getattr(exc, "code", None) or type(exc).__name__),
            message=str(exc),
            retryable=bool(getattr(exc, "retryable", False)),
            stage=getattr(exc, "stage", None) or stage,
            details=dict(details) if isinstance(details, Mapping) else {},
            cause=cls.from_exception(cause, _depth=_depth + 1)
            if cause is not None and _depth < MAX_CAUSE_DEPTH else None)

    def to_dict(self) -> Dict[str, Any]:
        """JSON-compatible form."""
        from ai_platform.common.core.execution.freeze import thaw  # pylint: disable=import-outside-toplevel
        return {"type": self.type, "code": self.code, "message": self.message,
                "retryable": self.retryable, "stage": self.stage, "details": thaw(self.details),
                "cause": self.cause.to_dict() if self.cause else None}
