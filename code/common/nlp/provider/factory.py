
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Explicit NLP provider factory and engine-adapter contracts.

Responsibilities:
- register engine adapters explicitly;
- select an adapter by configuration.engine.engine_name;
- apply engine-specific configuration through the adapter;
- validate the created NLP provider;
- return a factory result without registering or initializing it.

The factory layer does not:
- register NLP providers;
- initialize models or engines;
- execute NLP analysis;
- download model resources.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Protocol, runtime_checkable

from .capabilities import ProviderCapabilities
from .configuration_v2 import NLPProviderConfigurationV2
from .errors import (
    NLPProviderConfigurationError,
    NLPProviderFactoryError,
    NLPProviderUnavailableError,
)
from .protocol import NLPProvider


@runtime_checkable
class NLPProviderEngineAdapter(Protocol):
    """
    Engine-specific provider construction contract.

    Implementations translate the canonical configuration into
    engine-specific constructor arguments and return an uninitialized
    NLPProvider instance.
    """

    @property
    def engine_name(self) -> str:
        """Return the canonical engine identifier."""
        ...

    def create_provider(
        self,
        configuration: NLPProviderConfigurationV2,
    ) -> NLPProvider:
        """
        Construct an NLP provider from validated configuration.

        Implementations must not register or initialize the provider.
        """
        ...


class NLPProviderFactoryRegistry:
    """
    Explicit registry of engine-specific adapters.

    Registration is deterministic:
    - no automatic imports;
    - no auto-discovery;
    - no replacement of existing adapters;
    - no provider construction during registration.
    """

    def __init__(self) -> None:
        self._adapters: dict[str, NLPProviderEngineAdapter] = {}

    def register(
        self,
        adapter: NLPProviderEngineAdapter,
    ) -> None:
        """Explicitly register one engine adapter."""

        if not isinstance(adapter, NLPProviderEngineAdapter):
            raise TypeError(
                "adapter must implement NLPProviderEngineAdapter."
            )

        engine_name = adapter.engine_name

        if not isinstance(engine_name, str) or not engine_name.strip():
            raise ValueError(
                "adapter.engine_name must be a non-empty string."
            )

        normalized_name = engine_name.strip().casefold()

        if normalized_name in self._adapters:
            raise ValueError(
                f"Engine adapter '{normalized_name}' is already registered."
            )

        self._adapters[normalized_name] = adapter

    def get(
        self,
        engine_name: str,
    ) -> NLPProviderEngineAdapter:
        """Retrieve an explicitly registered engine adapter."""

        if not isinstance(engine_name, str) or not engine_name.strip():
            raise ValueError(
                "engine_name must be a non-empty string."
            )

        normalized_name = engine_name.strip().casefold()
        adapter = self._adapters.get(normalized_name)

        if adapter is None:
            raise NLPProviderUnavailableError(
                f"No NLP provider engine adapter is registered "
                f"for '{normalized_name}'.",
                details={
                    "engine_name": normalized_name,
                    "reason": "engine_adapter_not_registered",
                },
            )

        return adapter

    def list(self) -> Mapping[str, NLPProviderEngineAdapter]:
        """Return a read-only snapshot of registered adapters."""

        return MappingProxyType(dict(self._adapters))


@dataclass(frozen=True)
class NLPProviderFactoryResult:
    """Immutable description of a provider created by the factory."""

    provider: NLPProvider
    provider_id: str
    engine_name: str
    configuration_fingerprint: str


class NLPProviderFactoryService:
    """
    Create NLP providers using explicitly registered engine adapters.

    The returned provider is not registered and is not initialized.
    """

    def __init__(
        self,
        registry: NLPProviderFactoryRegistry,
    ) -> None:
        if not isinstance(registry, NLPProviderFactoryRegistry):
            raise TypeError(
                "registry must be NLPProviderFactoryRegistry."
            )

        self._registry = registry

    def create(
        self,
        configuration: NLPProviderConfigurationV2,
    ) -> NLPProviderFactoryResult:
        """
        Create and validate one provider.

        Adapter configuration errors are propagated unchanged.
        Unexpected adapter errors are wrapped in NLPProviderFactoryError.
        """

        if not isinstance(
            configuration,
            NLPProviderConfigurationV2,
        ):
            raise TypeError(
                "configuration must be NLPProviderConfigurationV2."
            )

        engine_name = configuration.engine.engine_name.casefold()
        adapter = self._registry.get(engine_name)

        try:
            provider = adapter.create_provider(configuration)

        except (
            NLPProviderConfigurationError,
            NLPProviderFactoryError,
            NLPProviderUnavailableError,
        ):
            raise

        except Exception as error:
            raise NLPProviderFactoryError(
                "Engine adapter failed to create the NLP provider.",
                provider_id=configuration.provider_id,
                details={
                    "engine_name": engine_name,
                    "error_type": type(error).__name__,
                },
            ) from error

        if not isinstance(provider, NLPProvider):
            raise NLPProviderFactoryError(
                "Engine adapter returned an object "
                "that does not implement NLPProvider.",
                provider_id=configuration.provider_id,
                details={
                    "engine_name": engine_name,
                    "returned_type": type(provider).__name__,
                },
            )

        capabilities = provider.capabilities

        if not isinstance(capabilities, ProviderCapabilities):
            raise NLPProviderFactoryError(
                "Created provider does not expose valid "
                "ProviderCapabilities.",
                provider_id=configuration.provider_id,
                details={
                    "engine_name": engine_name,
                    "capabilities_type": type(capabilities).__name__,
                },
            )

        if capabilities.provider_id != configuration.provider_id:
            raise NLPProviderConfigurationError(
                "Created provider identity does not match "
                "configuration.provider_id.",
                provider_id=configuration.provider_id,
                details={
                    "actual_provider_id": capabilities.provider_id,
                    "engine_name": engine_name,
                },
            )

        return NLPProviderFactoryResult(
            provider=provider,
            provider_id=configuration.provider_id,
            engine_name=engine_name,
            configuration_fingerprint=(
                configuration.fingerprint_sha256
            ),
        )


__all__ = [
    "NLPProviderEngineAdapter",
    "NLPProviderFactoryRegistry",
    "NLPProviderFactoryResult",
    "NLPProviderFactoryService",
]

