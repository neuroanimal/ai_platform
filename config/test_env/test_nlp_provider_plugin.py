
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Integration tests for NLPProviderPlugin and PluginRegistry."""

import unittest

from ai_platform.common.core.interface.plugin_contract import PluginContract
from ai_platform.common.core.registry.plugin_registry import PluginRegistry
from ai_platform.common.core.registry.registry_exception import (
    PluginAlreadyRegisteredError,
    PluginNotFoundError,
)

from ai_platform.common.nlp.model.analysis import (
    AnalysisLayer,
    NLPAnalysis,
)
from ai_platform.common.nlp.provider import (
    NLPProvider,
    NLPProviderRequest,
    NLPProviderResponse,
    ProviderCapabilities,
)
from ai_platform.common.nlp.provider.plugin import NLPProviderPlugin


PROVIDER_ID = "test-provider"
PROVIDER_VERSION = "1.0.0"
REGISTRY_KEY = f"nlp:{PROVIDER_ID}"


class FakeNLPProvider:

    def __init__(self) -> None:
        self._capabilities = ProviderCapabilities(
            provider_id=PROVIDER_ID,
            provider_version=PROVIDER_VERSION,
            supported_language_codes=["pl"],
            supported_layers=[
                AnalysisLayer.SEGMENTATION,
            ],
        )

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    async def analyze(
        self,
        request: NLPProviderRequest,
    ) -> NLPProviderResponse:
        analysis = NLPAnalysis(
            analysis_id="test-analysis",
            document_id=request.document.document_id,
            text_version_id=request.text_version_id,
            completed_layers=[
                AnalysisLayer.SEGMENTATION,
            ],
        )

        return NLPProviderResponse(
            request_id=request.request_id,
            provider_id=PROVIDER_ID,
            analysis=analysis,
        )


class InvalidProvider:
    """Object intentionally not implementing NLPProvider."""


class InvalidCapabilitiesProvider:

    @property
    def capabilities(self) -> dict:
        return {
            "provider_id": PROVIDER_ID,
        }

    async def analyze(
        self,
        request: NLPProviderRequest,
    ) -> NLPProviderResponse:
        raise NotImplementedError


class TestNLPProviderPlugin(unittest.TestCase):

    def test_01_plugin_implements_plugin_contract(self) -> None:
        provider = FakeNLPProvider()
        plugin = NLPProviderPlugin(provider)

        self.assertIsInstance(plugin, PluginContract)
        self.assertIsInstance(provider, NLPProvider)

        print("PLUGIN CONTRACT IMPLEMENTATION: OK")

    def test_02_registry_key_generation(self) -> None:
        provider = FakeNLPProvider()
        plugin = NLPProviderPlugin(provider)

        self.assertEqual(plugin.provider_id, PROVIDER_ID)
        self.assertEqual(plugin.registry_key, REGISTRY_KEY)

        print("REGISTRY KEY GENERATION: OK")

    def test_03_no_implicit_registration(self) -> None:
        registry = PluginRegistry()
        provider = FakeNLPProvider()
        plugin = NLPProviderPlugin(provider)

        self.assertEqual(registry.list(), {})

        # Construction of the adapter must not register anything.
        self.assertEqual(registry.list(), {})

        self.assertIs(plugin.provider, provider)

        print("NO IMPLICIT REGISTRATION: OK")

    def test_04_explicit_registration(self) -> None:
        registry = PluginRegistry()
        provider = FakeNLPProvider()
        plugin = NLPProviderPlugin(provider)

        plugin.register(registry)

        self.assertIn(REGISTRY_KEY, registry.list())
        self.assertIs(registry.get(REGISTRY_KEY), provider)

        print("EXPLICIT REGISTRATION: OK")

    def test_05_registered_provider_protocol(self) -> None:
        registry = PluginRegistry()
        provider = FakeNLPProvider()
        plugin = NLPProviderPlugin(provider)

        plugin.register(registry)

        registered_provider = registry.get(REGISTRY_KEY)

        self.assertIsInstance(registered_provider, NLPProvider)
        self.assertIs(
            registered_provider.capabilities,
            provider.capabilities,
        )
        self.assertTrue(callable(registered_provider.analyze))

        print("REGISTERED PROVIDER PROTOCOL: OK")

    def test_06_duplicate_registration(self) -> None:
        registry = PluginRegistry()

        first_provider = FakeNLPProvider()
        second_provider = FakeNLPProvider()

        first_plugin = NLPProviderPlugin(first_provider)
        second_plugin = NLPProviderPlugin(second_provider)

        first_plugin.register(registry)

        with self.assertRaises(PluginAlreadyRegisteredError):
            second_plugin.register(registry)

        # The original provider must remain registered.
        self.assertIs(
            registry.get(REGISTRY_KEY),
            first_provider,
        )

        print("DUPLICATE REGISTRATION: OK")

    def test_07_unknown_registry_key(self) -> None:
        registry = PluginRegistry()

        with self.assertRaises(PluginNotFoundError):
            registry.get(REGISTRY_KEY)

        print("UNKNOWN REGISTRY KEY: OK")

    def test_08_invalid_provider_rejected(self) -> None:
        with self.assertRaises(TypeError):
            NLPProviderPlugin(InvalidProvider())

        print("INVALID PROVIDER REJECTION: OK")

    def test_09_invalid_capabilities_rejected(self) -> None:
        with self.assertRaises(TypeError):
            NLPProviderPlugin(InvalidCapabilitiesProvider())

        print("INVALID CAPABILITIES REJECTION: OK")

    def test_10_invalid_registry_rejected(self) -> None:
        plugin = NLPProviderPlugin(FakeNLPProvider())

        with self.assertRaises(TypeError):
            plugin.register({})

        print("INVALID REGISTRY REJECTION: OK")

    def test_11_registry_isolation(self) -> None:
        first_registry = PluginRegistry()
        second_registry = PluginRegistry()

        provider = FakeNLPProvider()
        plugin = NLPProviderPlugin(provider)

        plugin.register(first_registry)

        self.assertIs(
            first_registry.get(REGISTRY_KEY),
            provider,
        )

        self.assertEqual(second_registry.list(), {})

        print("REGISTRY ISOLATION: OK")


def main() -> None:
    print("=" * 60)
    print("NLP PROVIDER PLUGIN INTEGRATION TESTS")
    print("=" * 60)

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        TestNLPProviderPlugin
    )

    result = unittest.TextTestRunner(verbosity=0).run(suite)

    if not result.wasSuccessful():
        raise SystemExit(1)

    print()
    print("ALL NLP PROVIDER PLUGIN TESTS PASSED: 11/11")


if __name__ == "__main__":
    main()


