
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Compatibility validation between NLP provider capabilities
and NLP provider configuration.

This module:
- validates provider identity;
- validates configured model language against declared languages;
- validates batch-size settings against batch support;
- returns structured validation reports;
- does not initialize providers or models;
- does not perform downloads or runtime operations;
- does not mutate configuration or capabilities.
"""

from __future__ import annotations

from ...model.base import NLPModel
from ..capabilities import ProviderCapabilities
from ..configuration_v2 import NLPProviderConfigurationV2


class ProviderConfigurationIssue(NLPModel):
    """One configuration/capability compatibility issue."""

    code: str
    field: str
    message: str


class ProviderConfigurationReport(NLPModel):
    """Result of provider configuration compatibility validation."""

    is_valid: bool
    issues: list[ProviderConfigurationIssue]


def _add_issue(
    issues: list[ProviderConfigurationIssue],
    *,
    code: str,
    field: str,
    message: str,
) -> None:
    issues.append(
        ProviderConfigurationIssue(
            code=code,
            field=field,
            message=message,
        )
    )


def _normalize_language_code(value: str) -> str:
    """
    Normalize language-code spelling for comparison.

    Matching remains exact after normalization:
    - case is ignored;
    - underscores are treated as hyphens;
    - regional subtags are not implicitly removed.
    """
    return value.strip().replace("_", "-").casefold()


def validate_provider_configuration(
    configuration: NLPProviderConfigurationV2,
    capabilities: ProviderCapabilities,
) -> ProviderConfigurationReport:
    """
    Validate configuration against provider-declared capabilities.

    The function checks only constraints represented explicitly
    in the current configuration and capability contracts.
    """
    issues: list[ProviderConfigurationIssue] = []

    # Provider identity
    if configuration.provider_id != capabilities.provider_id:
        _add_issue(
            issues,
            code="provider_id_mismatch",
            field="provider_id",
            message=(
                "Configuration provider_id does not match "
                "the provider capabilities provider_id."
            ),
        )

    # Model language compatibility
    model = configuration.model

    if model is not None and model.language is not None:
        configured_language = _normalize_language_code(
            model.language
        )

        declared_languages = {
            _normalize_language_code(language)
            for language in capabilities.supported_language_codes
        }

        if not declared_languages:
            _add_issue(
                issues,
                code="language_support_not_declared",
                field="model.language",
                message=(
                    "A model language is configured, but the provider "
                    "does not declare supported language codes."
                ),
            )
        elif configured_language not in declared_languages:
            _add_issue(
                issues,
                code="unsupported_model_language",
                field="model.language",
                message=(
                    "Configured model language is not declared "
                    "as supported by the provider."
                ),
            )

    # Batch execution compatibility
    batch_size = configuration.runtime.batch_size

    if (
        batch_size is not None
        and batch_size > 1
        and not capabilities.supports_batch
    ):
        _add_issue(
            issues,
            code="batch_not_supported",
            field="runtime.batch_size",
            message=(
                "Configured batch_size is greater than 1, "
                "but the provider does not declare batch support."
            ),
        )

    return ProviderConfigurationReport(
        is_valid=not issues,
        issues=issues,
    )


__all__ = [
    "ProviderConfigurationIssue",
    "ProviderConfigurationReport",
    "validate_provider_configuration",
]

