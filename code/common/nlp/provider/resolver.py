
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NLP provider configuration resolver.

Responsibilities:
- resolve a configured provider from the central registry;
- verify the registered object implements NLPProvider;
- obtain and validate provider capabilities;
- validate configuration/capability compatibility;
- return an explicit resolved provider binding.

Non-responsibilities:
- provider registration;
- provider initialization or readiness;
- model downloads;
- engine initialization;
- analysis execution;
- lifecycle management.
"""

from __future__ import annotations

from dataclasses import dataclass

from ai_platform.common.core.registry.registry_contract import (
    RegistryContract,
)
from ai_platform.common.core.registry.registry_exception import (
    PluginNotFoundError,
)

from .capabilities import ProviderCapabilities
from .configuration_v2 import NLPProviderConfigurationV2
from .errors import (
    NLPProviderConfigurationError,
    NLPProviderUnavailableError,
)
from .plugin import NLPProviderPlugin
from .protocol import NLPProvider
from .validation.configuration import validate_provider_configuration


@dataclass(frozen=True)
class NLPProviderResolution:
    """
    Result of resolving a provider configuration.

    The object represents a validated binding between:
    - one immutable configuration;
    - one registered provider;
    - the provider capabilities used during validation.
    """

    provider_id: str
    registry_key: str
    provider: NLPProvider
    capabilities: ProviderCapabilities
    configuration: NLPProviderConfigurationV2
    configuration_fingerprint: str


class NLPProviderConfigurationResolver:
    """
    Resolve NLP provider configurations through RegistryContract.

    The resolver reads from the registry but never registers providers
    or changes their lifecycle state.
    """

    def __init__(
        self,
        registry: RegistryContract,
    ) -> None:
        if not isinstance(registry, RegistryContract):
            raise TypeError(
                "registry must implement RegistryContract."
            )

        self._registry = registry

    def resolve(
        self,
        configuration: NLPProviderConfigurationV2,
    ) -> NLPProviderResolution:
        """
        Resolve and validate one provider configuration.

        Raises:
            TypeError:
                If configuration is not NLPProviderConfigurationV2.

            NLPProviderUnavailableError:
                If no provider is registered under the expected key.

            NLPProviderConfigurationError:
                If the registered object or its capabilities are invalid,
                or if configuration is incompatible with capabilities.
        """
        if not isinstance(
            configuration,
            NLPProviderConfigurationV2,
        ):
            raise TypeError(
                "configuration must be NLPProviderConfigurationV2."
            )

        provider_id = configuration.provider_id

        registry_key = (
            f"{NLPProviderPlugin.KEY_PREFIX}{provider_id}"
        )

        try:
            provider = self._registry.get(registry_key)
        except PluginNotFoundError as error:
            raise NLPProviderUnavailableError(
                f"No NLP provider is registered for '{provider_id}'.",
                provider_id=provider_id,
                details={
                    "registry_key": registry_key,
                    "state": "unregistered",
                },
            ) from error

        if not isinstance(provider, NLPProvider):
            raise NLPProviderConfigurationError(
                "Registered object does not implement NLPProvider.",
                provider_id=provider_id,
                details={
                    "registry_key": registry_key,
                    "registered_type": type(provider).__name__,
                },
            )

        capabilities = provider.capabilities

        if not isinstance(capabilities, ProviderCapabilities):
            raise NLPProviderConfigurationError(
                "Provider capabilities must be ProviderCapabilities.",
                provider_id=provider_id,
                details={
                    "registry_key": registry_key,
                    "capabilities_type": type(capabilities).__name__,
                },
            )

        validation = validate_provider_configuration(
            configuration,
            capabilities,
        )

        if not validation.is_valid:
            raise NLPProviderConfigurationError(
                "Provider configuration is incompatible "
                "with the registered provider capabilities.",
                provider_id=provider_id,
                details={
                    "registry_key": registry_key,
                    "validation_issues": [
                        issue.model_dump(mode="json")
                        for issue in validation.issues
                    ],
                },
            )

        return NLPProviderResolution(
            provider_id=provider_id,
            registry_key=registry_key,
            provider=provider,
            capabilities=capabilities,
            configuration=configuration,
            configuration_fingerprint=(
                configuration.fingerprint_sha256
            ),
        )


__all__ = [
    "NLPProviderResolution",
    "NLPProviderConfigurationResolver",
]

