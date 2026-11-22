
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Integration of NLP providers with the central plugin registry."""

from typing import Any

from ai_platform.common.core.interface.plugin_contract import PluginContract
from ai_platform.common.core.registry.registry_contract import RegistryContract

from .capabilities import ProviderCapabilities
from .protocol import NLPProvider


class NLPProviderPlugin(PluginContract):
    """
    Explicit registration adapter for an NLP provider.

    The adapter implements PluginContract, while the registry stores
    the underlying NLPProvider instance.

    Registration key:
        nlp:{provider_id}

    No auto-discovery, imports or registration side effects are performed.
    """

    KEY_PREFIX = "nlp:"

    def __init__(self, provider: NLPProvider) -> None:
        if not isinstance(provider, NLPProvider):
            raise TypeError(
                "provider must implement the NLPProvider protocol."
            )

        capabilities = provider.capabilities

        if not isinstance(capabilities, ProviderCapabilities):
            raise TypeError(
                "provider.capabilities must return ProviderCapabilities."
            )

        provider_id = capabilities.provider_id

        if not provider_id or not provider_id.strip():
            raise ValueError("Provider ID must not be blank.")

        self._provider = provider
        self._provider_id = provider_id

    @property
    def provider(self) -> NLPProvider:
        """Return the wrapped NLP provider."""
        return self._provider

    @property
    def provider_id(self) -> str:
        """Return the provider identifier."""
        return self._provider_id

    @property
    def registry_key(self) -> str:
        """Return the deterministic registry key."""
        return f"{self.KEY_PREFIX}{self.provider_id}"

    def register(self, registry: RegistryContract) -> None:
        """
        Explicitly register the NLP provider.

        Existing registry collision behavior is preserved.
        Registry exceptions are intentionally propagated unchanged.
        """
        if not isinstance(registry, RegistryContract):
            raise TypeError(
                "registry must implement RegistryContract."
            )

        registry.register(
            self.registry_key,
            self.provider,
        )

