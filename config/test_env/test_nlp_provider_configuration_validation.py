
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Regression tests for NLP provider configuration validation."""

import unittest

from ai_platform.common.nlp.model import AnalysisLayer
from ai_platform.common.nlp.provider import (
    NLPProviderConfigurationV2,
    ProviderCapabilities,
    ProviderConfigurationIssue,
    ProviderConfigurationReport,
    validate_provider_configuration,
)


PROVIDER_ID = "test-provider"
PROVIDER_VERSION = "1.0.0"


def build_configuration(
    *,
    provider_id: str = PROVIDER_ID,
    language: str | None = None,
    batch_size: int | None = None,
) -> NLPProviderConfigurationV2:
    model = None

    if language is not None:
        model = {
            "model_id": "test-model",
            "language": language,
        }

    return NLPProviderConfigurationV2.from_dict(
        {
            "provider_id": provider_id,
            "engine": {
                "engine_name": "test-engine",
            },
            "model": model,
            "runtime": {
                "batch_size": batch_size,
            },
        }
    )


def build_capabilities(
    *,
    provider_id: str = PROVIDER_ID,
    languages: list[str] | None = None,
    supports_batch: bool = False,
) -> ProviderCapabilities:
    if languages is None:
        languages = ["pl"]

    return ProviderCapabilities(
        provider_id=provider_id,
        provider_version=PROVIDER_VERSION,
        supported_language_codes=languages,
        supported_layers=[
            AnalysisLayer.SEGMENTATION,
        ],
        supports_batch=supports_batch,
    )


class TestNLPProviderConfigurationValidation(unittest.TestCase):

    def test_01_valid_configuration(self) -> None:
        report = validate_provider_configuration(
            build_configuration(language="pl"),
            build_capabilities(),
        )

        self.assertTrue(report.is_valid)
        self.assertEqual(report.issues, [])

        print("VALID CONFIGURATION: OK")

    def test_02_provider_id_mismatch(self) -> None:
        report = validate_provider_configuration(
            build_configuration(provider_id="other-provider"),
            build_capabilities(),
        )

        self.assertFalse(report.is_valid)
        self.assertIn(
            "provider_id_mismatch",
            [issue.code for issue in report.issues],
        )
        self.assertEqual(
            report.issues[0].field,
            "provider_id",
        )

        print("PROVIDER ID MISMATCH: OK")

    def test_03_supported_model_language(self) -> None:
        report = validate_provider_configuration(
            build_configuration(language="pl"),
            build_capabilities(languages=["pl", "en"]),
        )

        self.assertTrue(report.is_valid)

        print("SUPPORTED MODEL LANGUAGE: OK")

    def test_04_language_comparison_is_case_insensitive(self) -> None:
        report = validate_provider_configuration(
            build_configuration(language="PL"),
            build_capabilities(languages=["pl"]),
        )

        self.assertTrue(report.is_valid)

        print("CASE-INSENSITIVE LANGUAGE MATCH: OK")

    def test_05_language_separator_normalization(self) -> None:
        report = validate_provider_configuration(
            build_configuration(language="zh_Hans"),
            build_capabilities(languages=["zh-Hans"]),
        )

        self.assertTrue(report.is_valid)

        print("LANGUAGE SEPARATOR NORMALIZATION: OK")

    def test_06_unsupported_model_language(self) -> None:
        report = validate_provider_configuration(
            build_configuration(language="de"),
            build_capabilities(languages=["pl", "en"]),
        )

        self.assertFalse(report.is_valid)
        self.assertIn(
            "unsupported_model_language",
            [issue.code for issue in report.issues],
        )
        self.assertEqual(
            report.issues[0].field,
            "model.language",
        )

        print("UNSUPPORTED MODEL LANGUAGE: OK")

    def test_07_language_support_not_declared(self) -> None:
        report = validate_provider_configuration(
            build_configuration(language="pl"),
            build_capabilities(languages=[]),
        )

        self.assertFalse(report.is_valid)
        self.assertIn(
            "language_support_not_declared",
            [issue.code for issue in report.issues],
        )

        print("UNDECLARED LANGUAGE SUPPORT: OK")

    def test_08_missing_model_is_allowed(self) -> None:
        report = validate_provider_configuration(
            build_configuration(),
            build_capabilities(languages=[]),
        )

        self.assertTrue(report.is_valid)

        print("OPTIONAL MODEL: OK")

    def test_09_missing_model_language_is_allowed(self) -> None:
        configuration = NLPProviderConfigurationV2.from_dict(
            {
                "provider_id": PROVIDER_ID,
                "engine": {
                    "engine_name": "test-engine",
                },
                "model": {
                    "model_id": "test-model",
                },
            }
        )

        report = validate_provider_configuration(
            configuration,
            build_capabilities(languages=[]),
        )

        self.assertTrue(report.is_valid)

        print("OPTIONAL MODEL LANGUAGE: OK")

    def test_10_batch_not_supported(self) -> None:
        report = validate_provider_configuration(
            build_configuration(batch_size=8),
            build_capabilities(supports_batch=False),
        )

        self.assertFalse(report.is_valid)
        self.assertIn(
            "batch_not_supported",
            [issue.code for issue in report.issues],
        )
        self.assertEqual(
            report.issues[0].field,
            "runtime.batch_size",
        )

        print("UNSUPPORTED BATCH SIZE: OK")

    def test_11_single_item_batch_without_batch_support(self) -> None:
        report = validate_provider_configuration(
            build_configuration(batch_size=1),
            build_capabilities(supports_batch=False),
        )

        self.assertTrue(report.is_valid)

        print("SINGLE ITEM WITHOUT BATCH SUPPORT: OK")

    def test_12_batch_supported(self) -> None:
        report = validate_provider_configuration(
            build_configuration(batch_size=8),
            build_capabilities(supports_batch=True),
        )

        self.assertTrue(report.is_valid)

        print("SUPPORTED BATCH SIZE: OK")

    def test_13_multiple_issues_are_aggregated(self) -> None:
        report = validate_provider_configuration(
            build_configuration(
                provider_id="other-provider",
                language="de",
                batch_size=8,
            ),
            build_capabilities(
                languages=["pl"],
                supports_batch=False,
            ),
        )

        self.assertFalse(report.is_valid)

        codes = [issue.code for issue in report.issues]

        self.assertEqual(
            codes,
            [
                "provider_id_mismatch",
                "unsupported_model_language",
                "batch_not_supported",
            ],
        )

        print("MULTIPLE ISSUES AGGREGATION: OK")

    def test_14_report_contains_structured_issues(self) -> None:
        report = validate_provider_configuration(
            build_configuration(language="de"),
            build_capabilities(languages=["pl"]),
        )

        self.assertIsInstance(report, ProviderConfigurationReport)
        self.assertTrue(
            all(
                isinstance(issue, ProviderConfigurationIssue)
                for issue in report.issues
            )
        )

        print("STRUCTURED VALIDATION REPORT: OK")

    def test_15_validation_does_not_mutate_inputs(self) -> None:
        configuration = build_configuration(
            language="pl",
            batch_size=1,
        )
        capabilities = build_capabilities(
            languages=["pl"],
            supports_batch=False,
        )

        configuration_before = configuration.to_dict()
        capabilities_before = capabilities.model_dump(mode="json")

        validate_provider_configuration(
            configuration,
            capabilities,
        )

        self.assertEqual(
            configuration.to_dict(),
            configuration_before,
        )
        self.assertEqual(
            capabilities.model_dump(mode="json"),
            capabilities_before,
        )

        print("INPUT IMMUTABILITY: OK")

    def test_16_public_validation_exports(self) -> None:
        from ai_platform.common.nlp.provider.validation import (
            ProviderConfigurationIssue as ValidationIssue,
            ProviderConfigurationReport as ValidationReport,
            validate_provider_configuration as validation_function,
        )

        self.assertIs(ValidationIssue, ProviderConfigurationIssue)
        self.assertIs(ValidationReport, ProviderConfigurationReport)
        self.assertIs(
            validation_function,
            validate_provider_configuration,
        )

        print("PUBLIC VALIDATION EXPORTS: OK")

    def test_17_public_provider_exports(self) -> None:
        from ai_platform.common.nlp.provider import __all__

        expected = {
            "ProviderConfigurationIssue",
            "ProviderConfigurationReport",
            "validate_provider_configuration",
        }

        self.assertTrue(expected.issubset(set(__all__)))

        print("PUBLIC PROVIDER EXPORTS: OK")


def main() -> None:
    print("=" * 60)
    print("NLP PROVIDER CONFIGURATION VALIDATION TESTS")
    print("=" * 60)

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        TestNLPProviderConfigurationValidation
    )

    result = unittest.TextTestRunner(verbosity=0).run(suite)

    if not result.wasSuccessful():
        raise SystemExit(1)

    print()
    print(
        "ALL NLP PROVIDER CONFIGURATION VALIDATION TESTS PASSED: "
        "17/17"
    )


if __name__ == "__main__":
    main()

