"""
Execution metadata: what an execution actually did, recorded as data.

The configuration says what was asked for; the metadata says what happened:
the device really used (after fallback), the threads, the engine and its
version, the time waited for a slot, the time spent, the outcome and the
error. Benchmarks, reports and the layer above read this instead of guessing
from the configuration.

``ExecutionRecorder`` is the mutable builder the engine adapter fills while
it runs (``record_device``, ``record_engine``, ``note``); the executor
finishes it into a frozen ``ExecutionMetadata``.

``abandoned`` is True when the caller stopped waiting (timeout or
cancellation) but the work could not be stopped - a worker thread that never
checked its context. It is reported, not hidden: the engine is still busy
and its slot is held until the thread ends.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from ai_platform.common.core.execution.errors import ErrorInfo


class ExecutionOutcome(str, Enum):
    """How an execution ended."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


@dataclass(frozen=True)
class ExecutionMetadata:  # pylint: disable=too-many-instance-attributes
    """Facts of one finished execution."""

    execution_id: str
    operation: str
    outcome: ExecutionOutcome
    started_utc: str
    finished_utc: str
    elapsed_seconds: float
    queue_seconds: float = 0.0
    provider_id: Optional[str] = None
    request_id: Optional[str] = None
    parent_id: Optional[str] = None
    device_requested: Optional[str] = None
    device_used: Optional[str] = None
    threads: Optional[int] = None
    engine: Optional[str] = None
    engine_version: Optional[str] = None
    configuration_fingerprint: Optional[str] = None
    resources: tuple = ()
    abandoned: bool = False
    error: Optional[ErrorInfo] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """JSON-compatible form."""
        data = dict(self.__dict__)
        data["outcome"] = self.outcome.value
        data["resources"] = list(self.resources)
        data["error"] = self.error.to_dict() if self.error else None
        return data


class ExecutionRecorder:  # pylint: disable=too-many-instance-attributes
    """Collects facts during an execution; ``finish`` freezes them."""

    def __init__(self, context, configuration_fingerprint: Optional[str] = None) -> None:
        self.context = context
        self.configuration_fingerprint = configuration_fingerprint
        self.started_utc = _utc()
        self._started = context.clock()
        self.queue_seconds = 0.0
        self.device_used: Optional[str] = None
        self.threads: Optional[int] = None
        self.engine: Optional[str] = None
        self.engine_version: Optional[str] = None
        self.resources: List[str] = []
        self.extra: Dict[str, Any] = {}

    def record_device(self, device: str, threads: Optional[int] = None) -> None:
        """The device (and threads) the engine really uses."""
        self.device_used = device
        if threads is not None:
            self.threads = threads

    def record_engine(self, name: str, version: Optional[str] = None) -> None:
        """Engine name and version."""
        self.engine, self.engine_version = name, version

    def record_resource(self, key: str) -> None:
        """A shared resource the execution used."""
        if key not in self.resources:
            self.resources.append(key)

    def note(self, key: str, value: Any) -> None:
        """Any other fact worth keeping (e.g. number of tokens, pages, batches)."""
        self.extra[key] = value

    def finish(self, outcome: ExecutionOutcome, error: Optional[BaseException] = None,
               abandoned: bool = False) -> ExecutionMetadata:
        """Frozen metadata of the execution."""
        context = self.context
        return ExecutionMetadata(
            execution_id=context.execution_id, operation=context.operation, outcome=outcome,
            started_utc=self.started_utc, finished_utc=_utc(),
            elapsed_seconds=round(context.clock() - self._started, 6),
            queue_seconds=round(self.queue_seconds, 6), provider_id=context.provider_id,
            request_id=context.request_id, parent_id=context.parent_id,
            device_requested=context.policy.device, device_used=self.device_used,
            threads=self.threads if self.threads is not None else context.policy.max_threads,
            engine=self.engine, engine_version=self.engine_version,
            configuration_fingerprint=self.configuration_fingerprint,
            resources=tuple(self.resources), abandoned=abandoned,
            error=ErrorInfo.from_exception(error) if error is not None else None,
            extra=dict(self.extra))
