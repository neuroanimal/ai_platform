
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Contract tests for the NLP provider interface."""

import asyncio
import unittest

from pydantic import ValidationError

from ai_platform.common.nlp.model.analysis import (
    AnalysisLayer,
    NLPAnalysis,
    ProviderMetadata,
)
from ai_platform.common.nlp.model.document import (
    NLPDocument,
    SourceDescriptor,
    TextVersion,
)

from ai_platform.common.nlp.provider import (
    NLPProvider,
    NLPProviderRequest,
    NLPProviderResponse,
    ProviderCapabilities,
    ProviderDiagnostic,
    ProviderDiagnosticSeverity,
    NLPProviderExecutionError,
    validate_provider_request,
    validate_provider_response,
)


PROVIDER_ID = "test-nlp-provider"
PROVIDER_VERSION = "1.0.0"
REQUEST_ID = "request-001"
DOCUMENT_ID = "document-001"
TEXT_VERSION_ID = "text-version-001"


def build_document() -> NLPDocument:
    source = SourceDescriptor.model_construct(
        source_id="source-001",
        source_type="text",
    )

    text_version = TextVersion.model_construct(
        text_version_id=TEXT_VERSION_ID,
        representation="plain_text",
        text="Ala ma kota.",
    )

    return NLPDocument(
        document_id=DOCUMENT_ID,
        source=source,
        text_versions=[text_version],
        primary_text_version_id=TEXT_VERSION_ID,
    )


def build_capabilities() -> ProviderCapabilities:
    return ProviderCapabilities(
        provider_id=PROVIDER_ID,
        provider_version=PROVIDER_VERSION,
        supported_language_codes=["pl"],
        supported_layers=[
            AnalysisLayer.SEGMENTATION,
            AnalysisLayer.MORPHOLOGY,
        ],
        max_input_characters=1000,
    )


def build_request(
    *,
    allow_partial: bool = True,
    requested_layers: list[AnalysisLayer] | None = None,
) -> NLPProviderRequest:
    if requested_layers is None:
        requested_layers = [AnalysisLayer.SEGMENTATION]

    return NLPProviderRequest(
        request_id=REQUEST_ID,
        document=build_document(),
        text_version_id=TEXT_VERSION_ID,
        requested_layers=requested_layers,
        allow_partial=allow_partial,
    )


def build_analysis(
    *,
    document_id: str = DOCUMENT_ID,
    text_version_id: str = TEXT_VERSION_ID,
    provider_id: str = PROVIDER_ID,
    provider_version: str = PROVIDER_VERSION,
    completed_layers: list[AnalysisLayer] | None = None,
    unavailable_layers: list[AnalysisLayer] | None = None,
) -> NLPAnalysis:
    if completed_layers is None:
        completed_layers = [AnalysisLayer.SEGMENTATION]

    if unavailable_layers is None:
        unavailable_layers = []

    return NLPAnalysis(
        analysis_id="analysis-001",
        document_id=document_id,
        text_version_id=text_version_id,
        provider=ProviderMetadata(
            provider_id=provider_id,
            provider_version=provider_version,
            language_code="pl",
        ),
        completed_layers=completed_layers,
        unavailable_layers=unavailable_layers,
    )


def build_response(
    *,
    request_id: str = REQUEST_ID,
    provider_id: str = PROVIDER_ID,
    analysis: NLPAnalysis | None = None,
) -> NLPProviderResponse:
    if analysis is None:
        analysis = build_analysis()

    return NLPProviderResponse(
        request_id=request_id,
        provider_id=provider_id,
        analysis=analysis,
        diagnostics=[
            ProviderDiagnostic(
                code="test_info",
                message="Test diagnostic.",
                severity=ProviderDiagnosticSeverity.INFO,
            )
        ],
    )


class FakeNLPProvider:
    @property
    def capabilities(self) -> ProviderCapabilities:
        return build_capabilities()

    async def analyze(
        self,
        request: NLPProviderRequest,
    ) -> NLPProviderResponse:
        return NLPProviderResponse(
            request_id=request.request_id,
            provider_id=self.capabilities.provider_id,
            analysis=build_analysis(
                document_id=request.document.document_id,
                text_version_id=request.text_version_id,
            ),
        )


class TestNLPProviderContract(unittest.TestCase):

    def test_01_capabilities_creation(self) -> None:
        capabilities = build_capabilities()

        self.assertEqual(capabilities.provider_id, PROVIDER_ID)
        self.assertEqual(capabilities.provider_version, PROVIDER_VERSION)
        self.assertIn(
            AnalysisLayer.SEGMENTATION,
            capabilities.supported_layers,
        )

        print("CAPABILITIES CREATION: OK")

    def test_02_capabilities_reject_duplicate_layers(self) -> None:
        with self.assertRaises(ValidationError):
            ProviderCapabilities(
                provider_id=PROVIDER_ID,
                provider_version=PROVIDER_VERSION,
                supported_layers=[
                    AnalysisLayer.SEGMENTATION,
                    AnalysisLayer.SEGMENTATION,
                ],
            )

        print("CAPABILITIES DUPLICATE LAYERS: OK")

    def test_03_request_creation(self) -> None:
        request = build_request()

        self.assertEqual(request.request_id, REQUEST_ID)
        self.assertEqual(request.document.document_id, DOCUMENT_ID)
        self.assertEqual(request.text_version_id, TEXT_VERSION_ID)

        print("REQUEST CREATION: OK")

    def test_04_request_rejects_unknown_text_version(self) -> None:
        with self.assertRaises(ValidationError):
            NLPProviderRequest(
                request_id=REQUEST_ID,
                document=build_document(),
                text_version_id="unknown-version",
                requested_layers=[AnalysisLayer.SEGMENTATION],
            )

        print("REQUEST UNKNOWN TEXT VERSION: OK")

    def test_05_request_rejects_duplicate_layers(self) -> None:
        with self.assertRaises(ValidationError):
            NLPProviderRequest(
                request_id=REQUEST_ID,
                document=build_document(),
                text_version_id=TEXT_VERSION_ID,
                requested_layers=[
                    AnalysisLayer.SEGMENTATION,
                    AnalysisLayer.SEGMENTATION,
                ],
            )

        print("REQUEST DUPLICATE LAYERS: OK")

    def test_06_request_capability_validation(self) -> None:
        request = build_request(
            requested_layers=[
                AnalysisLayer.SEGMENTATION,
                AnalysisLayer.MORPHOLOGY,
            ]
        )

        report = validate_provider_request(
            request,
            build_capabilities(),
        )

        self.assertTrue(report.is_valid)
        self.assertEqual(report.issues, [])

        unsupported_request = build_request(
            requested_layers=[
                AnalysisLayer.SEGMENTATION,
                AnalysisLayer.DISCOURSE,
            ]
        )

        unsupported_report = validate_provider_request(
            unsupported_request,
            build_capabilities(),
        )

        self.assertFalse(unsupported_report.is_valid)
        self.assertIn(
            "unsupported_requested_layers",
            [issue.code for issue in unsupported_report.issues],
        )

        print("REQUEST CAPABILITY VALIDATION: OK")

    def test_07_input_limit_validation(self) -> None:
        request = build_request()

        capabilities = ProviderCapabilities(
            provider_id=PROVIDER_ID,
            provider_version=PROVIDER_VERSION,
            supported_layers=[AnalysisLayer.SEGMENTATION],
            max_input_characters=3,
        )

        report = validate_provider_request(request, capabilities)

        self.assertFalse(report.is_valid)
        self.assertIn(
            "input_exceeds_provider_limit",
            [issue.code for issue in report.issues],
        )

        print("INPUT LIMIT VALIDATION: OK")

    def test_08_valid_response_conformance(self) -> None:
        request = build_request()
        capabilities = build_capabilities()
        response = build_response()

        report = validate_provider_response(
            request,
            capabilities,
            response,
        )

        self.assertTrue(report.is_valid)
        self.assertEqual(report.issues, [])

        print("VALID RESPONSE CONFORMANCE: OK")

    def test_09_response_request_id_mismatch(self) -> None:
        request = build_request()
        capabilities = build_capabilities()

        response = build_response(request_id="different-request")

        report = validate_provider_response(
            request,
            capabilities,
            response,
        )

        self.assertFalse(report.is_valid)
        self.assertIn(
            "request_id_mismatch",
            [issue.code for issue in report.issues],
        )

        print("RESPONSE REQUEST ID MISMATCH: OK")

    def test_10_response_document_mismatch(self) -> None:
        request = build_request()
        capabilities = build_capabilities()

        analysis = build_analysis(document_id="different-document")
        response = build_response(analysis=analysis)

        report = validate_provider_response(
            request,
            capabilities,
            response,
        )

        self.assertFalse(report.is_valid)
        self.assertIn(
            "document_id_mismatch",
            [issue.code for issue in report.issues],
        )

        print("RESPONSE DOCUMENT MISMATCH: OK")

    def test_11_response_text_version_mismatch(self) -> None:
        request = build_request()
        capabilities = build_capabilities()

        analysis = build_analysis(
            text_version_id="different-version"
        )
        response = build_response(analysis=analysis)

        report = validate_provider_response(
            request,
            capabilities,
            response,
        )

        self.assertFalse(report.is_valid)
        self.assertIn(
            "text_version_id_mismatch",
            [issue.code for issue in report.issues],
        )

        print("RESPONSE TEXT VERSION MISMATCH: OK")

    def test_12_response_provider_mismatch(self) -> None:
        request = build_request()
        capabilities = build_capabilities()

        analysis = build_analysis(provider_id="different-provider")
        response = build_response(analysis=analysis)

        report = validate_provider_response(
            request,
            capabilities,
            response,
        )

        self.assertFalse(report.is_valid)
        self.assertIn(
            "analysis_provider_id_mismatch",
            [issue.code for issue in report.issues],
        )

        print("RESPONSE PROVIDER MISMATCH: OK")

    def test_13_completed_unavailable_overlap(self) -> None:
        request = build_request()
        capabilities = build_capabilities()

        analysis = build_analysis(
            completed_layers=[AnalysisLayer.SEGMENTATION],
            unavailable_layers=[AnalysisLayer.SEGMENTATION],
        )
        response = build_response(analysis=analysis)

        report = validate_provider_response(
            request,
            capabilities,
            response,
        )

        self.assertFalse(report.is_valid)
        self.assertIn(
            "completed_unavailable_overlap",
            [issue.code for issue in report.issues],
        )

        print("COMPLETED / UNAVAILABLE OVERLAP: OK")

    def test_14_unrequested_layer_reported(self) -> None:
        request = build_request(
            requested_layers=[AnalysisLayer.SEGMENTATION]
        )
        capabilities = build_capabilities()

        analysis = build_analysis(
            completed_layers=[
                AnalysisLayer.SEGMENTATION,
                AnalysisLayer.MORPHOLOGY,
            ]
        )
        response = build_response(analysis=analysis)

        report = validate_provider_response(
            request,
            capabilities,
            response,
        )

        self.assertFalse(report.is_valid)
        self.assertIn(
            "unrequested_layers_reported",
            [issue.code for issue in report.issues],
        )

        print("UNREQUESTED LAYER REPORTED: OK")

    def test_15_partial_result_policy(self) -> None:
        request = build_request(
            allow_partial=False,
            requested_layers=[
                AnalysisLayer.SEGMENTATION,
                AnalysisLayer.MORPHOLOGY,
            ],
        )
        capabilities = build_capabilities()

        analysis = build_analysis(
            completed_layers=[AnalysisLayer.SEGMENTATION]
        )
        response = build_response(analysis=analysis)

        report = validate_provider_response(
            request,
            capabilities,
            response,
        )

        self.assertFalse(report.is_valid)
        self.assertIn(
            "incomplete_analysis",
            [issue.code for issue in report.issues],
        )

        print("PARTIAL RESULT POLICY: OK")

    def test_16_provider_protocol(self) -> None:
        provider = FakeNLPProvider()

        self.assertIsInstance(provider, NLPProvider)

        print("RUNTIME PROVIDER PROTOCOL: OK")

    def test_17_async_provider_execution(self) -> None:
        provider = FakeNLPProvider()
        request = build_request()

        response = asyncio.run(provider.analyze(request))

        self.assertEqual(response.request_id, request.request_id)
        self.assertEqual(response.provider_id, PROVIDER_ID)

        report = validate_provider_response(
            request,
            provider.capabilities,
            response,
        )

        self.assertTrue(report.is_valid)

        print("ASYNC PROVIDER EXECUTION: OK")

    def test_18_error_hierarchy(self) -> None:
        error = NLPProviderExecutionError(
            "Temporary execution failure.",
            provider_id=PROVIDER_ID,
            retryable=True,
            details={"attempt": 1},
        )

        self.assertEqual(error.code, "provider_execution_error")
        self.assertEqual(error.provider_id, PROVIDER_ID)
        self.assertTrue(error.retryable)
        self.assertEqual(error.details["attempt"], 1)

        print("ERROR HIERARCHY: OK")

    def test_19_json_schema_generation(self) -> None:
        capabilities_schema = ProviderCapabilities.model_json_schema()
        request_schema = NLPProviderRequest.model_json_schema()
        response_schema = NLPProviderResponse.model_json_schema()

        self.assertIn("properties", capabilities_schema)
        self.assertIn("properties", request_schema)
        self.assertIn("properties", response_schema)

        self.assertIn(
            "provider_id",
            capabilities_schema["properties"],
        )
        self.assertIn(
            "requested_layers",
            request_schema["properties"],
        )
        self.assertIn(
            "analysis",
            response_schema["properties"],
        )

        print("PROVIDER JSON SCHEMAS: OK")

    def test_20_public_exports(self) -> None:
        from ai_platform.common.nlp.provider import __all__

        expected = {
            "ProviderCapabilities",
            "NLPProviderRequest",
            "NLPProviderResponse",
            "NLPProvider",
            "validate_provider_request",
            "validate_provider_response",
        }

        self.assertTrue(expected.issubset(set(__all__)))

        print(
            f"PUBLIC EXPORTS: OK ({len(__all__)} names)"
        )


def main() -> None:
    print("=" * 60)
    print("NLP PROVIDER CONTRACT TESTS")
    print("=" * 60)

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        TestNLPProviderContract
    )

    result = unittest.TextTestRunner(verbosity=0).run(suite)

    if not result.wasSuccessful():
        raise SystemExit(1)

    print()
    print("ALL NLP PROVIDER CONTRACT TESTS PASSED: 20/20")


if __name__ == "__main__":
    main()


