"""
Execution context: the explicit frame one execution runs in.

Instead of each engine inventing its own timeout and identity handling, the
caller creates one ``ExecutionContext`` and passes it down: provider, engine
adapter and every step see the same identifiers, the same deadline and the
same cancellation token.

- identity: ``execution_id`` (new per execution), ``operation`` (e.g.
  "nlp.analyze", "ocr.recognize"), ``provider_id``, ``request_id``,
  ``parent_id`` for nested steps;
- time: an absolute monotonic deadline (``timeout_seconds`` from the call,
  else from the policy), ``remaining_seconds`` and ``check``;
- control: the ``CancellationToken`` and the effective ``RuntimePolicy``;
- ``labels``: free key/value pairs for tracing (frozen).

``child`` opens a nested context: its deadline is never later than the
parent's, its token is cancelled with the parent's, and its policy can only
be stricter (``RuntimePolicy.narrow``).
"""

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Callable, Mapping, Optional

from ai_platform.common.core.execution.cancellation import CancellationToken
from ai_platform.common.core.execution.errors import ExecutionTimeoutError
from ai_platform.common.core.execution.policy import RuntimePolicy

Clock = Callable[[], float]


@dataclass(frozen=True)
class ExecutionContext:  # pylint: disable=too-many-instance-attributes
    """Identity, deadline, cancellation and policy of one execution."""

    operation: str
    execution_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    provider_id: Optional[str] = None
    request_id: Optional[str] = None
    parent_id: Optional[str] = None
    policy: RuntimePolicy = field(default_factory=RuntimePolicy)
    cancellation: CancellationToken = field(default_factory=CancellationToken)
    deadline: Optional[float] = None
    created_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(
        timespec="milliseconds"))
    labels: Mapping[str, Any] = field(default_factory=dict)
    clock: Clock = field(default=time.monotonic, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not str(self.operation).strip():
            raise ValueError("operation must not be blank")
        object.__setattr__(self, "labels", MappingProxyType(dict(self.labels)))

    @classmethod
    def create(cls, operation: str, *, timeout_seconds: Optional[float] = None,  # pylint: disable=too-many-arguments
               policy: Optional[RuntimePolicy] = None, clock: Clock = time.monotonic,
               cancellation: Optional[CancellationToken] = None,
               **identity: Any) -> "ExecutionContext":
        """New root context; ``timeout_seconds`` falls back to ``policy.timeout_seconds``."""
        policy = policy or RuntimePolicy()
        timeout = timeout_seconds if timeout_seconds is not None else policy.timeout_seconds
        return cls(operation=operation, policy=policy, clock=clock,
                   cancellation=cancellation or CancellationToken(),
                   deadline=clock() + timeout if timeout is not None else None, **identity)

    def remaining_seconds(self) -> Optional[float]:
        """Seconds until the deadline (0 when passed), None without a deadline."""
        if self.deadline is None:
            return None
        return max(0.0, self.deadline - self.clock())

    @property
    def expired(self) -> bool:
        """True when the deadline has passed."""
        return self.deadline is not None and self.clock() >= self.deadline

    def check(self, stage: Optional[str] = None) -> None:
        """Raise if cancelled or past the deadline. Engines call this between steps."""
        self.cancellation.raise_if_cancelled(stage)
        if self.expired:
            raise ExecutionTimeoutError(f"deadline passed during {stage or self.operation}",
                                        stage=stage, details={"execution_id": self.execution_id})

    def child(self, operation: str, *, timeout_seconds: Optional[float] = None,
              policy: Optional[RuntimePolicy] = None, **labels: Any) -> "ExecutionContext":
        """Nested context: earlier-or-equal deadline, linked token, stricter policy."""
        deadline = self.deadline
        if timeout_seconds is not None:
            own = self.clock() + timeout_seconds
            deadline = own if deadline is None else min(deadline, own)
        return ExecutionContext(
            operation=operation, provider_id=self.provider_id, request_id=self.request_id,
            parent_id=self.execution_id, policy=self.policy.narrow(policy),
            cancellation=self.cancellation.child(), deadline=deadline,
            labels={**self.labels, **labels}, clock=self.clock)
