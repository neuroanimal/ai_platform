"""
Runtime execution contract shared by every engine of the platform (NLP, OCR/HTR,
speech, LLM): execution context, runtime policy, shared resources, execution
metadata, cancellation and timeouts, and the rule for propagating errors.
See README.md in this directory.
"""

from ai_platform.common.core.execution.cancellation import CancellationToken
from ai_platform.common.core.execution.context import ExecutionContext
from ai_platform.common.core.execution.errors import (
    ErrorInfo,
    ExecutionCancelledError,
    ExecutionError,
    ExecutionTimeoutError,
    PolicyViolationError,
    ResourceConflictError,
    ResourceUnavailableError,
)
from ai_platform.common.core.execution.executor import (
    ExecutionResult,
    execute,
    execute_blocking,
)
from ai_platform.common.core.execution.metadata import (
    ExecutionMetadata,
    ExecutionOutcome,
    ExecutionRecorder,
)
from ai_platform.common.core.execution.policy import RuntimePolicy
from ai_platform.common.core.execution.resources import ResourceManager

__all__ = [
    "CancellationToken", "ErrorInfo", "ExecutionCancelledError", "ExecutionContext",
    "ExecutionError", "ExecutionMetadata", "ExecutionOutcome", "ExecutionRecorder",
    "ExecutionResult", "ExecutionTimeoutError", "PolicyViolationError", "ResourceConflictError",
    "ResourceManager", "ResourceUnavailableError", "RuntimePolicy", "execute",
    "execute_blocking",
]
