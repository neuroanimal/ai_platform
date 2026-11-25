#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Integration tests for NLP provider configuration and lifecycle."""

import asyncio
import unittest

from ai_platform.common.core.registry.plugin_registry import (
    PluginRegistry,
)
from ai_platform.common.nlp.model.analysis import AnalysisLayer
from ai_platform.common.nlp.provider import (
    NLPConfigurationLoadError,
    NLPProviderConfigurationError,
    NLPProviderConfigurationRuntime,
    NLPProviderConfigurationService,
    NLPProviderLifecycle,
    NLPProviderLifecycleState,
    NLPProviderRequest,
    NLPProviderResponse,
    NLPProviderUnavailableError,
    ProviderCapabilities,
)


PROVIDER_ID = "configuration-runtime-test"
REGISTRY_KEY = f"nlp:{PROVIDER_ID}"


def configuration_data(
    *,
    provider_id: str = PROVIDER_ID,
    language: str = "pl",
) -> dict:
    return {
        "provider_id": provider_id,
        "engine": {
            "engine_name": "test-engine",
            "options": {
                "processors": "tokenize,pos,lemma",
            },
        },
        "model": {
            "model_id": "test-model",
            "language": language,
        },
        "runtime": {
            "device": "cpu",
            "batch_size": 1,
        },
    }


class FakeConfigurableProvider:
    """Provider with observable lifecycle and analysis calls."""

    def __init__(self) -> None:
        self._capabilities = ProviderCapabilities(
            provider_id=PROVIDER_ID,
            provider_version="1.0.0",
            supported_language_codes=["pl"],
            supported_layers=[
                AnalysisLayer.SEGMENTATION,
            ],
        )

        self.initialize_calls = 0
        self.analysis_calls = 0
        self.close_calls = 0

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    def initialize(self) -> None:
        self.initialize_calls += 1

    def close(self) -> None:
        self.close_calls += 1

    async def analyze(
        self,
        request: NLPProviderRequest,
    ) -> NLPProviderResponse:
        self.analysis_calls += 1
        raise AssertionError(
            "Configuration runtime must not execute analysis."
        )


class TestNLPProviderConfigurationRuntime(
    unittest.IsolatedAsyncioTestCase
):

    def setUp(self) -> None:
        self.registry = PluginRegistry()
        self.lifecycle = NLPProviderLifecycle(self.registry)
        self.configuration_service = (
            NLPProviderConfigurationService(self.registry)
        )
        self.runtime = NLPProviderConfigurationRuntime(
            self.configuration_service,
            self.lifecycle,
        )

        self.provider = FakeConfigurableProvider()

    def register_provider(self) -> None:
        self.lifecycle.register(self.provider)

    async def test_01_configuration_service_loads_mapping(self) -> None:
        configuration = self.configuration_service.load(
            configuration_data(),
            environ={},
        )

        self.assertEqual(configuration.provider_id, PROVIDER_ID)
        self.assertEqual(configuration.engine.engine_name, "test-engine")

        print("CONFIGURATION SERVICE LOAD: OK")

    async def test_02_configuration_service_resolves_provider(self) -> None:
        self.register_provider()

        resolution = self.configuration_service.load_and_resolve(
            configuration_data(),
            environ={},
        )

        self.assertIs(resolution.provider, self.provider)
        self.assertEqual(resolution.provider_id, PROVIDER_ID)

        self.assertEqual(self.provider.initialize_calls, 0)

        print("CONFIGURATION SERVICE RESOLUTION: OK")

    async def test_03_environment_override_reaches_resolution(self) -> None:
        from ai_platform.common.nlp.provider.configuration_loader import (
            ENV_PREFIX,
        )

        self.register_provider()

        data = configuration_data()
        data["runtime"]["device"] = "auto"

        resolution = self.configuration_service.load_and_resolve(
            data,
            environ={
                f"{ENV_PREFIX}RUNTIME__DEVICE": "cpu",
            },
        )

        self.assertEqual(
            resolution.configuration.runtime.device,
            "cpu",
        )

        print("ENVIRONMENT OVERRIDE IN INTEGRATION FLOW: OK")

    async def test_04_loader_error_is_not_flattened(self) -> None:
        with self.assertRaises(NLPConfigurationLoadError):
            self.configuration_service.load_and_resolve(
                {"invalid": "configuration"},
                environ={},
            )

        print("LOADER ERROR BOUNDARY: OK")

    async def test_05_unregistered_provider_error_is_preserved(self) -> None:
        with self.assertRaises(NLPProviderUnavailableError):
            self.configuration_service.load_and_resolve(
                configuration_data(),
                environ={},
            )

        print("UNREGISTERED PROVIDER ERROR BOUNDARY: OK")

    async def test_06_incompatible_configuration_error_is_preserved(self) -> None:
        self.register_provider()

        with self.assertRaises(NLPProviderConfigurationError):
            self.configuration_service.load_and_resolve(
                configuration_data(language="de"),
                environ={},
            )

        print("CONFIGURATION COMPATIBILITY ERROR BOUNDARY: OK")

    async def test_07_resolution_does_not_initialize_provider(self) -> None:
        self.register_provider()

        self.configuration_service.load_and_resolve(
            configuration_data(),
            environ={},
        )

        self.assertEqual(self.provider.initialize_calls, 0)
        self.assertEqual(self.provider.analysis_calls, 0)

        self.assertEqual(
            self.lifecycle.get_snapshot(PROVIDER_ID).state,
            NLPProviderLifecycleState.REGISTERED,
        )

        print("RESOLUTION DOES NOT INITIALIZE PROVIDER: OK")

    async def test_08_runtime_initializes_resolved_provider(self) -> None:
        self.register_provider()

        result = await self.runtime.initialize_from_configuration(
            configuration_data(),
            environ={},
        )

        self.assertEqual(result.provider_id, PROVIDER_ID)

        self.assertEqual(
            result.lifecycle_snapshot.state,
            NLPProviderLifecycleState.READY,
        )

        self.assertEqual(self.provider.initialize_calls, 1)
        self.assertEqual(self.provider.analysis_calls, 0)

        print("RUNTIME INITIALIZATION: OK")

    async def test_09_runtime_preserves_configuration_fingerprint(self) -> None:
        self.register_provider()

        result = await self.runtime.initialize_from_configuration(
            configuration_data(),
            environ={},
        )

        self.assertEqual(
            result.configuration_fingerprint,
            result.resolution.configuration.fingerprint_sha256,
        )

        print("RUNTIME CONFIGURATION FINGERPRINT: OK")

    async def test_10_runtime_does_not_register_provider_again(self) -> None:
        self.register_provider()

        before = self.registry.list()

        await self.runtime.initialize_from_configuration(
            configuration_data(),
            environ={},
        )

        after = self.registry.list()

        self.assertEqual(set(before), set(after))
        self.assertIs(after[REGISTRY_KEY], self.provider)

        print("NO DUPLICATE REGISTRATION: OK")

    async def test_11_runtime_rejects_provider_not_managed_by_lifecycle(self) -> None:
        self.register_provider()

        other_registry = PluginRegistry()
        other_provider = FakeConfigurableProvider()

        other_registry.register(
            REGISTRY_KEY,
            other_provider,
        )

        other_service = NLPProviderConfigurationService(
            other_registry
        )

        other_runtime = NLPProviderConfigurationRuntime(
            other_service,
            self.lifecycle,
        )

        with self.assertRaises(NLPProviderUnavailableError):
            await other_runtime.initialize_from_configuration(
                configuration_data(),
                environ={},
            )

        print("LIFECYCLE PROVIDER IDENTITY CHECK: OK")

    async def test_12_runtime_initialization_is_idempotent(self) -> None:
        self.register_provider()

        first = await self.runtime.initialize_from_configuration(
            configuration_data(),
            environ={},
        )

        second = await self.runtime.initialize_from_configuration(
            configuration_data(),
            environ={},
        )

        self.assertEqual(
            first.lifecycle_snapshot.state,
            NLPProviderLifecycleState.READY,
        )

        self.assertEqual(
            second.lifecycle_snapshot.state,
            NLPProviderLifecycleState.READY,
        )

        self.assertEqual(self.provider.initialize_calls, 1)

        print("RUNTIME INITIALIZATION IDEMPOTENCY: OK")

    async def test_13_runtime_does_not_execute_analysis(self) -> None:
        self.register_provider()

        await self.runtime.initialize_from_configuration(
            configuration_data(),
            environ={},
        )

        self.assertEqual(self.provider.analysis_calls, 0)

        print("NO ANALYSIS EXECUTION: OK")

    async def test_14_runtime_public_exports(self) -> None:
        from ai_platform.common.nlp.provider import __all__

        expected = {
            "NLPProviderConfigurationService",
            "NLPProviderConfiguredRuntime",
            "NLPProviderConfigurationRuntime",
        }

        self.assertTrue(expected.issubset(set(__all__)))

        print("PUBLIC RUNTIME EXPORTS: OK")


def main() -> None:
    print("=" * 60)
    print("NLP PROVIDER CONFIGURATION RUNTIME TESTS")
    print("=" * 60)

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        TestNLPProviderConfigurationRuntime
    )

    result = unittest.TextTestRunner(verbosity=0).run(suite)

    if not result.wasSuccessful():
        raise SystemExit(1)

    print()
    print(
        "ALL NLP PROVIDER CONFIGURATION RUNTIME TESTS PASSED: "
        "14/14"
    )


if __name__ == "__main__":
    main()

