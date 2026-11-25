
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Regression tests for NLP provider configuration resolver."""

import unittest
from dataclasses import FrozenInstanceError

from ai_platform.common.core.registry.plugin_registry import PluginRegistry
from ai_platform.common.nlp.model.analysis import AnalysisLayer
from ai_platform.common.nlp.provider import (
    NLPProvider,
    NLPProviderConfigurationError,
    NLPProviderConfigurationResolver,
    NLPProviderConfigurationV2,
    NLPProviderRequest,
    NLPProviderResolution,
    NLPProviderResponse,
    NLPProviderUnavailableError,
    ProviderCapabilities,
)


PROVIDER_ID = "resolver-test-provider"
PROVIDER_VERSION = "1.0.0"
REGISTRY_KEY = f"nlp:{PROVIDER_ID}"


class FakeNLPProvider:
    """Minimal provider with observable runtime side effects."""

    def __init__(
        self,
        *,
        provider_id: str = PROVIDER_ID,
        languages: list[str] | None = None,
        supports_batch: bool = False,
    ) -> None:
        if languages is None:
            languages = ["pl"]

        self._capabilities = ProviderCapabilities(
            provider_id=provider_id,
            provider_version=PROVIDER_VERSION,
            supported_language_codes=languages,
            supported_layers=[
                AnalysisLayer.SEGMENTATION,
            ],
            supports_batch=supports_batch,
        )

        self.initialize_calls = 0
        self.analyze_calls = 0

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    async def analyze(
        self,
        request: NLPProviderRequest,
    ) -> NLPProviderResponse:
        self.analyze_calls += 1
        raise AssertionError(
            "Resolver must not execute provider analysis."
        )

    def initialize(self) -> None:
        self.initialize_calls += 1


class InvalidCapabilitiesProvider:
    """Structurally valid provider with invalid capabilities type."""

    @property
    def capabilities(self) -> dict:
        return {
            "provider_id": PROVIDER_ID,
        }

    async def analyze(
        self,
        request: NLPProviderRequest,
    ) -> NLPProviderResponse:
        raise AssertionError("Analysis must not be called.")


def build_configuration(
    *,
    provider_id: str = PROVIDER_ID,
    language: str | None = None,
    batch_size: int | None = None,
) -> NLPProviderConfigurationV2:
    model = None

    if language is not None:
        model = {
            "model_id": "resolver-test-model",
            "language": language,
        }

    return NLPProviderConfigurationV2.from_dict(
        {
            "provider_id": provider_id,
            "engine": {
                "engine_name": "resolver-test-engine",
            },
            "model": model,
            "runtime": {
                "batch_size": batch_size,
            },
        }
    )


class TestNLPProviderConfigurationResolver(unittest.TestCase):

    def setUp(self) -> None:
        self.registry = PluginRegistry()
        self.resolver = NLPProviderConfigurationResolver(
            self.registry
        )

    def test_01_constructor_requires_registry_contract(self) -> None:
        with self.assertRaises(TypeError):
            NLPProviderConfigurationResolver(object())

        print("REGISTRY CONTRACT REQUIRED: OK")

    def test_02_resolve_returns_resolution_object(self) -> None:
        provider = FakeNLPProvider()
        self.registry.register(REGISTRY_KEY, provider)

        result = self.resolver.resolve(
            build_configuration(language="pl")
        )

        self.assertIsInstance(result, NLPProviderResolution)

        print("RESOLUTION OBJECT: OK")

    def test_03_resolved_provider_identity(self) -> None:
        provider = FakeNLPProvider()
        self.registry.register(REGISTRY_KEY, provider)

        result = self.resolver.resolve(
            build_configuration(language="pl")
        )

        self.assertEqual(result.provider_id, PROVIDER_ID)
        self.assertEqual(result.registry_key, REGISTRY_KEY)
        self.assertIs(result.provider, provider)

        print("RESOLVED PROVIDER IDENTITY: OK")

    def test_04_resolved_configuration_is_preserved(self) -> None:
        provider = FakeNLPProvider()
        self.registry.register(REGISTRY_KEY, provider)

        configuration = build_configuration(language="pl")
        result = self.resolver.resolve(configuration)

        self.assertIs(result.configuration, configuration)

        print("RESOLVED CONFIGURATION PRESERVED: OK")

    def test_05_resolved_capabilities_are_preserved(self) -> None:
        provider = FakeNLPProvider()
        self.registry.register(REGISTRY_KEY, provider)

        result = self.resolver.resolve(
            build_configuration(language="pl")
        )

        self.assertIs(
            result.capabilities,
            provider.capabilities,
        )

        print("RESOLVED CAPABILITIES PRESERVED: OK")

    def test_06_configuration_fingerprint_is_preserved(self) -> None:
        provider = FakeNLPProvider()
        self.registry.register(REGISTRY_KEY, provider)

        configuration = build_configuration(language="pl")
        result = self.resolver.resolve(configuration)

        self.assertEqual(
            result.configuration_fingerprint,
            configuration.fingerprint_sha256,
        )

        print("CONFIGURATION FINGERPRINT: OK")

    def test_07_unknown_provider_is_rejected(self) -> None:
        with self.assertRaises(NLPProviderUnavailableError) as context:
            self.resolver.resolve(
                build_configuration(language="pl")
            )

        self.assertEqual(
            context.exception.provider_id,
            PROVIDER_ID,
        )
        self.assertEqual(
            context.exception.details["registry_key"],
            REGISTRY_KEY,
        )
        self.assertEqual(
            context.exception.details["state"],
            "unregistered",
        )

        print("UNKNOWN PROVIDER REJECTION: OK")

    def test_08_invalid_registered_object_is_rejected(self) -> None:
        self.registry.register(REGISTRY_KEY, object())

        with self.assertRaises(
            NLPProviderConfigurationError
        ) as context:
            self.resolver.resolve(
                build_configuration(language="pl")
            )

        self.assertIn(
            "registered_type",
            context.exception.details,
        )

        print("INVALID REGISTERED OBJECT: OK")

    def test_09_invalid_capabilities_type_is_rejected(self) -> None:
        self.registry.register(
            REGISTRY_KEY,
            InvalidCapabilitiesProvider(),
        )

        with self.assertRaises(
            NLPProviderConfigurationError
        ) as context:
            self.resolver.resolve(
                build_configuration(language="pl")
            )

        self.assertIn(
            "capabilities_type",
            context.exception.details,
        )

        print("INVALID CAPABILITIES TYPE: OK")

    def test_10_provider_id_mismatch_is_rejected(self) -> None:
        provider = FakeNLPProvider(
            provider_id="different-provider"
        )

        # Deliberately place the provider under the requested key.
        self.registry.register(REGISTRY_KEY, provider)

        with self.assertRaises(
            NLPProviderConfigurationError
        ) as context:
            self.resolver.resolve(
                build_configuration(language="pl")
            )

        issues = context.exception.details["validation_issues"]

        self.assertIn(
            "provider_id_mismatch",
            [issue["code"] for issue in issues],
        )

        print("PROVIDER ID MISMATCH: OK")

    def test_11_unsupported_language_is_rejected(self) -> None:
        provider = FakeNLPProvider(languages=["pl"])
        self.registry.register(REGISTRY_KEY, provider)

        with self.assertRaises(
            NLPProviderConfigurationError
        ) as context:
            self.resolver.resolve(
                build_configuration(language="de")
            )

        issues = context.exception.details["validation_issues"]

        self.assertIn(
            "unsupported_model_language",
            [issue["code"] for issue in issues],
        )

        print("UNSUPPORTED LANGUAGE REJECTION: OK")

    def test_12_unsupported_batch_size_is_rejected(self) -> None:
        provider = FakeNLPProvider(supports_batch=False)
        self.registry.register(REGISTRY_KEY, provider)

        with self.assertRaises(
            NLPProviderConfigurationError
        ) as context:
            self.resolver.resolve(
                build_configuration(batch_size=8)
            )

        issues = context.exception.details["validation_issues"]

        self.assertIn(
            "batch_not_supported",
            [issue["code"] for issue in issues],
        )

        print("UNSUPPORTED BATCH SIZE REJECTION: OK")

    def test_13_multiple_validation_issues_are_preserved(self) -> None:
        provider = FakeNLPProvider(languages=["pl"])
        self.registry.register(REGISTRY_KEY, provider)

        with self.assertRaises(
            NLPProviderConfigurationError
        ) as context:
            self.resolver.resolve(
                build_configuration(
                    language="de",
                    batch_size=8,
                )
            )

        issues = context.exception.details["validation_issues"]
        codes = [issue["code"] for issue in issues]

        self.assertEqual(
            codes,
            [
                "unsupported_model_language",
                "batch_not_supported",
            ],
        )

        print("MULTIPLE VALIDATION ISSUES: OK")

    def test_14_resolver_does_not_initialize_provider(self) -> None:
        provider = FakeNLPProvider()
        self.registry.register(REGISTRY_KEY, provider)

        self.resolver.resolve(
            build_configuration(language="pl")
        )

        self.assertEqual(provider.initialize_calls, 0)

        print("NO PROVIDER INITIALIZATION: OK")

    def test_15_resolver_does_not_execute_analysis(self) -> None:
        provider = FakeNLPProvider()
        self.registry.register(REGISTRY_KEY, provider)

        self.resolver.resolve(
            build_configuration(language="pl")
        )

        self.assertEqual(provider.analyze_calls, 0)

        print("NO ANALYSIS EXECUTION: OK")

    def test_16_resolver_does_not_register_providers(self) -> None:
        provider = FakeNLPProvider()

        resolver = NLPProviderConfigurationResolver(
            self.registry
        )

        self.assertEqual(self.registry.list(), {})

        with self.assertRaises(NLPProviderUnavailableError):
            resolver.resolve(
                build_configuration(language="pl")
            )

        self.assertEqual(self.registry.list(), {})

        # Registration remains an explicit operation.
        self.registry.register(REGISTRY_KEY, provider)

        self.assertIs(
            self.registry.get(REGISTRY_KEY),
            provider,
        )

        print("NO IMPLICIT REGISTRATION: OK")

    def test_17_registry_is_not_modified_by_resolution(self) -> None:
        provider = FakeNLPProvider()
        self.registry.register(REGISTRY_KEY, provider)

        before = self.registry.list()

        self.resolver.resolve(
            build_configuration(language="pl")
        )

        after = self.registry.list()

        self.assertEqual(before, after)
        self.assertIs(after[REGISTRY_KEY], provider)

        print("REGISTRY UNCHANGED: OK")

    def test_18_resolution_result_is_frozen(self) -> None:
        provider = FakeNLPProvider()
        self.registry.register(REGISTRY_KEY, provider)

        result = self.resolver.resolve(
            build_configuration(language="pl")
        )

        with self.assertRaises(FrozenInstanceError):
            result.provider_id = "changed"

        print("FROZEN RESOLUTION RESULT: OK")

    def test_19_invalid_configuration_type_is_rejected(self) -> None:
        provider = FakeNLPProvider()
        self.registry.register(REGISTRY_KEY, provider)

        with self.assertRaises(TypeError):
            self.resolver.resolve({})

        print("INVALID CONFIGURATION TYPE: OK")

    def test_20_configuration_is_not_mutated(self) -> None:
        provider = FakeNLPProvider()
        self.registry.register(REGISTRY_KEY, provider)

        configuration = build_configuration(
            language="pl",
            batch_size=1,
        )

        before = configuration.to_dict()

        self.resolver.resolve(configuration)

        self.assertEqual(configuration.to_dict(), before)

        print("CONFIGURATION IMMUTABILITY: OK")

    def test_21_public_resolver_exports(self) -> None:
        from ai_platform.common.nlp.provider import __all__

        expected = {
            "NLPProviderResolution",
            "NLPProviderConfigurationResolver",
        }

        self.assertTrue(expected.issubset(set(__all__)))

        print("PUBLIC RESOLVER EXPORTS: OK")


def main() -> None:
    print("=" * 60)
    print("NLP PROVIDER CONFIGURATION RESOLVER TESTS")
    print("=" * 60)

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        TestNLPProviderConfigurationResolver
    )

    result = unittest.TextTestRunner(verbosity=0).run(suite)

    if not result.wasSuccessful():
        raise SystemExit(1)

    print()
    print(
        "ALL NLP PROVIDER CONFIGURATION RESOLVER TESTS PASSED: "
        "21/21"
    )


if __name__ == "__main__":
    main()

