
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for NLP provider factories and engine configuration adapters."""

import unittest
from pathlib import Path

from ai_platform.common.core.registry.plugin_registry import (
    PluginRegistry,
)
from ai_platform.common.nlp.model.analysis import AnalysisLayer
from ai_platform.common.nlp.provider import (
    NLPConfigurationLoadError,
    NLPProvider,
    NLPProviderConfigurationError,
    NLPProviderConfigurationLoader,
    NLPProviderFactoryError,
    NLPProviderFactoryRegistry,
    NLPProviderFactoryService,
    NLPProviderLifecycle,
    NLPProviderLifecycleState,
    NLPProviderRequest,
    NLPProviderResponse,
    NLPProviderUnavailableError,
    ProviderCapabilities,
    StanzaPolishEngineAdapter,
    StanzaPolishProvider,
)


def test_configuration(
    *,
    provider_id: str = "factory-test",
    engine_name: str = "test-engine",
) -> dict:
    return {
        "provider_id": provider_id,
        "engine": {
            "engine_name": engine_name,
            "options": {},
        },
        "model": {
            "model_id": "test-model",
            "language": "pl",
        },
        "runtime": {
            "device": "cpu",
            "batch_size": 1,
        },
    }


def stanza_configuration(
    *,
    download_policy: str = "never",
    options: dict | None = None,
) -> dict:
    return {
        "provider_id": "stanza-pl",
        "engine": {
            "engine_name": "stanza",
            "options": options or {},
        },
        "model": {
            "package": "default",
            "language": "pl",
            "model_dir": "/tmp/stanza-resources",
            "download_policy": download_policy,
        },
        "runtime": {
            "device": "cpu",
        },
    }


class FakeProvider:
    """Minimal provider with observable lifecycle calls."""

    def __init__(
        self,
        provider_id: str = "factory-test",
    ) -> None:
        self._capabilities = ProviderCapabilities(
            provider_id=provider_id,
            provider_version="1.0.0",
            supported_language_codes=["pl"],
            supported_layers=[
                AnalysisLayer.SEGMENTATION,
            ],
        )
        self.initialize_calls = 0
        self.analysis_calls = 0

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    def initialize(self) -> None:
        self.initialize_calls += 1

    async def analyze(
        self,
        request: NLPProviderRequest,
    ) -> NLPProviderResponse:
        self.analysis_calls += 1
        raise NotImplementedError


class FakeEngineAdapter:
    """Test engine adapter."""

    engine_name = "test-engine"

    def __init__(
        self,
        provider: FakeProvider | None = None,
    ) -> None:
        self.provider = provider or FakeProvider()
        self.calls = 0
        self.received_configuration = None

    def create_provider(self, configuration):
        self.calls += 1
        self.received_configuration = configuration
        return self.provider


class InvalidEngineAdapter:
    """Adapter returning an object outside the provider contract."""

    engine_name = "invalid-engine"

    def create_provider(self, configuration):
        return object()


class TestNLPProviderFactory(unittest.TestCase):

    def setUp(self) -> None:
        self.registry = NLPProviderFactoryRegistry()
        self.adapter = FakeEngineAdapter()
        self.registry.register(self.adapter)

        self.service = NLPProviderFactoryService(
            self.registry
        )

    def test_01_explicit_adapter_registration(self) -> None:
        self.assertIn(
            "test-engine",
            self.registry.list(),
        )

        self.assertIs(
            self.registry.get("test-engine"),
            self.adapter,
        )

        print("EXPLICIT ENGINE ADAPTER REGISTRATION: OK")

    def test_02_duplicate_adapter_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.registry.register(self.adapter)

        print("DUPLICATE ENGINE ADAPTER REJECTION: OK")

    def test_03_unknown_adapter_rejected(self) -> None:
        with self.assertRaises(NLPProviderUnavailableError):
            self.registry.get("unknown-engine")

        print("UNKNOWN ENGINE ADAPTER ERROR: OK")

    def test_04_registry_snapshot_is_immutable(self) -> None:
        snapshot = self.registry.list()

        with self.assertRaises(TypeError):
            snapshot["another-engine"] = self.adapter

        print("READ-ONLY FACTORY REGISTRY SNAPSHOT: OK")

    def test_05_factory_creates_provider(self) -> None:
        configuration = NLPProviderConfigurationLoader.load(
            test_configuration(),
            environ={},
        )

        result = self.service.create(configuration)

        self.assertIs(result.provider, self.adapter.provider)
        self.assertEqual(result.provider_id, "factory-test")
        self.assertEqual(result.engine_name, "test-engine")

        self.assertEqual(self.adapter.calls, 1)
        self.assertIs(
            self.adapter.received_configuration,
            configuration,
        )

        print("FACTORY PROVIDER CREATION: OK")

    def test_06_factory_does_not_initialize_provider(self) -> None:
        configuration = NLPProviderConfigurationLoader.load(
            test_configuration(),
            environ={},
        )

        result = self.service.create(configuration)

        self.assertEqual(result.provider.initialize_calls, 0)
        self.assertEqual(result.provider.analysis_calls, 0)

        print("FACTORY DOES NOT INITIALIZE PROVIDER: OK")

    def test_07_factory_preserves_configuration_fingerprint(self) -> None:
        configuration = NLPProviderConfigurationLoader.load(
            test_configuration(),
            environ={},
        )

        result = self.service.create(configuration)

        self.assertEqual(
            result.configuration_fingerprint,
            configuration.fingerprint_sha256,
        )

        print("FACTORY CONFIGURATION FINGERPRINT: OK")

    def test_08_provider_identity_mismatch_rejected(self) -> None:
        wrong_provider = FakeProvider("different-provider")
        adapter = FakeEngineAdapter(wrong_provider)

        registry = NLPProviderFactoryRegistry()
        registry.register(adapter)

        service = NLPProviderFactoryService(registry)

        configuration = NLPProviderConfigurationLoader.load(
            test_configuration(),
            environ={},
        )

        with self.assertRaises(NLPProviderConfigurationError):
            service.create(configuration)

        print("FACTORY PROVIDER IDENTITY VALIDATION: OK")

    def test_09_invalid_provider_contract_rejected(self) -> None:
        registry = NLPProviderFactoryRegistry()
        registry.register(InvalidEngineAdapter())

        service = NLPProviderFactoryService(registry)

        configuration = NLPProviderConfigurationLoader.load(
            {
                **test_configuration(),
                "engine": {
                    "engine_name": "invalid-engine",
                    "options": {},
                },
            },
            environ={},
        )

        with self.assertRaises(NLPProviderFactoryError):
            service.create(configuration)

        print("INVALID FACTORY PROVIDER REJECTION: OK")

    def test_10_factory_error_boundary(self) -> None:
        class FailingAdapter:
            engine_name = "test-engine"

            def create_provider(self, configuration):
                raise RuntimeError("synthetic factory failure")

        registry = NLPProviderFactoryRegistry()
        registry.register(FailingAdapter())

        service = NLPProviderFactoryService(registry)

        configuration = NLPProviderConfigurationLoader.load(
            test_configuration(),
            environ={},
        )

        with self.assertRaises(NLPProviderFactoryError):
            service.create(configuration)

        print("FACTORY ERROR BOUNDARY: OK")

    def test_11_adapter_registry_does_not_create_providers(self) -> None:
        self.assertEqual(self.adapter.calls, 0)

        self.registry.get("test-engine")

        self.assertEqual(self.adapter.calls, 0)

        print("REGISTRY DOES NOT CREATE PROVIDERS: OK")

    def test_12_factory_service_requires_correct_registry(self) -> None:
        with self.assertRaises(TypeError):
            NLPProviderFactoryService(object())

        print("FACTORY REGISTRY CONTRACT: OK")


class TestStanzaEngineAdapter(unittest.TestCase):

    def setUp(self) -> None:
        self.adapter = StanzaPolishEngineAdapter()

    def test_13_stanza_engine_identity(self) -> None:
        self.assertEqual(self.adapter.engine_name, "stanza")

        print("STANZA ENGINE IDENTITY: OK")

    def test_14_stanza_configuration_mapping(self) -> None:
        configuration = NLPProviderConfigurationLoader.load(
            stanza_configuration(),
            environ={},
        )

        provider = self.adapter.create_provider(configuration)

        self.assertIsInstance(provider, StanzaPolishProvider)
        self.assertEqual(provider.capabilities.provider_id, "stanza-pl")
        self.assertEqual(provider._package, "default")
        self.assertEqual(
            provider._model_dir,
            Path("/tmp/stanza-resources"),
        )

        print("STANZA CONFIGURATION MAPPING: OK")

    def test_15_stanza_provider_is_lazy(self) -> None:
        configuration = NLPProviderConfigurationLoader.load(
            stanza_configuration(),
            environ={},
        )

        provider = self.adapter.create_provider(configuration)

        self.assertIsNone(provider._pipeline)

        print("STANZA PIPELINE LAZY INITIALIZATION: OK")

    def test_16_stanza_engine_options_rejected(self) -> None:
        configuration = NLPProviderConfigurationLoader.load(
            stanza_configuration(
                options={"unknown_option": True},
            ),
            environ={},
        )

        with self.assertRaises(NLPProviderConfigurationError):
            self.adapter.create_provider(configuration)

        print("UNSUPPORTED STANZA ENGINE OPTIONS REJECTED: OK")

    def test_17_stanza_download_policy_enforced(self) -> None:
        configuration = NLPProviderConfigurationLoader.load(
            stanza_configuration(
                download_policy="if_missing",
            ),
            environ={},
        )

        with self.assertRaises(NLPProviderConfigurationError):
            self.adapter.create_provider(configuration)

        print("STANZA EXPLICIT DOWNLOAD POLICY: OK")

    def test_18_stanza_device_constraints(self) -> None:
        data = stanza_configuration()
        data["runtime"]["device"] = "cuda:0"

        configuration = NLPProviderConfigurationLoader.load(
            data,
            environ={},
        )

        with self.assertRaises(NLPProviderConfigurationError):
            self.adapter.create_provider(configuration)

        print("STANZA DEVICE CONSTRAINTS: OK")

    def test_19_stanza_threads_constraint(self) -> None:
        data = stanza_configuration()
        data["runtime"]["threads"] = 2

        configuration = NLPProviderConfigurationLoader.load(
            data,
            environ={},
        )

        with self.assertRaises(NLPProviderConfigurationError):
            self.adapter.create_provider(configuration)

        print("STANZA THREAD CONFIGURATION CONSTRAINT: OK")

    def test_20_stanza_language_constraint(self) -> None:
        data = stanza_configuration()
        data["model"]["language"] = "de"

        configuration = NLPProviderConfigurationLoader.load(
            data,
            environ={},
        )

        with self.assertRaises(NLPProviderConfigurationError):
            self.adapter.create_provider(configuration)

        print("STANZA LANGUAGE CONSTRAINT: OK")


class TestFactoryLifecycleIntegration(
    unittest.IsolatedAsyncioTestCase
):

    async def test_21_factory_then_explicit_lifecycle_registration(
        self,
    ) -> None:
        provider = FakeProvider()

        adapter = FakeEngineAdapter(provider)

        factory_registry = NLPProviderFactoryRegistry()
        factory_registry.register(adapter)

        factory_service = NLPProviderFactoryService(
            factory_registry
        )

        configuration = NLPProviderConfigurationLoader.load(
            test_configuration(),
            environ={},
        )

        result = factory_service.create(configuration)

        self.assertEqual(provider.initialize_calls, 0)

        plugin_registry = PluginRegistry()
        lifecycle = NLPProviderLifecycle(plugin_registry)

        lifecycle.register(result.provider)

        self.assertEqual(
            lifecycle.get_snapshot("factory-test").state,
            NLPProviderLifecycleState.REGISTERED,
        )

        self.assertIs(
            plugin_registry.get("nlp:factory-test"),
            provider,
        )

        from ai_platform.common.nlp.provider import (
            NLPProviderConfigurationResolver,
        )

        resolution = NLPProviderConfigurationResolver(
            plugin_registry
        ).resolve(configuration)

        snapshot = await lifecycle.initialize_resolution(
            resolution
        )

        self.assertEqual(
            snapshot.state,
            NLPProviderLifecycleState.READY,
        )

        self.assertEqual(provider.initialize_calls, 1)
        self.assertEqual(provider.analysis_calls, 0)

        print("FACTORY TO EXPLICIT LIFECYCLE INTEGRATION: OK")


def main() -> None:
    print("=" * 60)
    print("NLP PROVIDER FACTORY TESTS")
    print("=" * 60)

    suite = unittest.TestSuite()

    for test_case in (
        TestNLPProviderFactory,
        TestStanzaEngineAdapter,
        TestFactoryLifecycleIntegration,
    ):
        suite.addTests(
            unittest.defaultTestLoader.loadTestsFromTestCase(
                test_case
            )
        )

    result = unittest.TextTestRunner(verbosity=0).run(suite)

    if not result.wasSuccessful():
        raise SystemExit(1)

    print()
    print("ALL NLP PROVIDER FACTORY TESTS PASSED: 21/21")


if __name__ == "__main__":
    main()

