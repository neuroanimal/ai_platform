
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


