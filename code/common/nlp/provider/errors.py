
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Exception hierarchy for NLP providers."""

from typing import Any


class NLPProviderError(Exception):
    """Base exception for NLP provider failures."""

    default_code = "nlp_provider_error"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        provider_id: str | None = None,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)

        self.code = code or self.default_code
        self.provider_id = provider_id
        self.retryable = retryable
        self.details = details or {}


class NLPProviderConfigurationError(NLPProviderError):
    default_code = "provider_configuration_error"


class NLPProviderCapabilityError(NLPProviderError):
    default_code = "provider_capability_error"


class NLPProviderInputError(NLPProviderError):
    default_code = "provider_input_error"


class NLPProviderExecutionError(NLPProviderError):
    default_code = "provider_execution_error"


class NLPProviderOutputError(NLPProviderError):
    default_code = "provider_output_error"


class NLPProviderUnavailableError(NLPProviderError):
    default_code = "provider_unavailable"


class NLPProviderFactoryError(NLPProviderError):
    """Raised when an NLP provider factory operation fails."""

    default_code = "provider_factory_error"




# Stage 8C: errors decided by the runtime execution contract
# (ai_platform.common.core.execution) when an NLP analysis runs out of time or
# is cancelled. They belong to BOTH hierarchies, so a caller catching
# NLPProviderError and a caller catching ExecutionTimeoutError /
# ExecutionCancelledError both see them.
from ai_platform.common.core.execution.errors import (  # noqa: E402  pylint: disable=wrong-import-position
    ExecutionCancelledError,
    ExecutionTimeoutError,
)


class _NLPExecutionContractError(NLPProviderExecutionError):
    """Shared constructor: NLP fields plus the execution contract's ``stage``."""

    default_retryable = False

    def __init__(  # pylint: disable=too-many-arguments
        self,
        message: str,
        *,
        code: str | None = None,
        provider_id: str | None = None,
        retryable: bool | None = None,
        stage: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code=code,
            provider_id=provider_id,
            retryable=self.default_retryable if retryable is None else retryable,
            details=details,
        )
        self.stage = stage


class NLPProviderTimeoutError(_NLPExecutionContractError, ExecutionTimeoutError):
    """The analysis did not finish before the deadline (retrying may succeed)."""

    default_code = "provider_timeout"
    default_retryable = True


class NLPProviderCancelledError(_NLPExecutionContractError, ExecutionCancelledError):
    """The caller cancelled the analysis."""

    default_code = "provider_cancelled"
