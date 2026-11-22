
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Regression tests for partial NLP provider response conformance."""

import unittest

from ai_platform.common.nlp.model.analysis import (
    AnalysisLayer,
    AnalysisStatus,
    NLPAnalysis,
    ProviderMetadata,
)
from ai_platform.common.nlp.model.document import (
    NLPDocument,
    SourceDescriptor,
    TextRepresentation,
    TextVersion,
)
from ai_platform.common.nlp.provider import (
    NLPProviderRequest,
    NLPProviderResponse,
    ProviderCapabilities,
    validate_provider_response,
)


PROVIDER_ID = "test-partial-provider"


def build_request(
    layers: list[AnalysisLayer],
) -> NLPProviderRequest:
    document = NLPDocument(
        document_id="document-partial-001",
        source=SourceDescriptor(
            source_id="source-partial-001",
            source_type="text",
        ),
        text_versions=[
            TextVersion(
                text_version_id="version-partial-001",
                representation=TextRepresentation.DIPLOMATIC,
                text="Ala ma kota.",
            )
        ],
        primary_text_version_id="version-partial-001",
    )

    return NLPProviderRequest(
        request_id="request-partial-001",
        document=document,
        text_version_id="version-partial-001",
        requested_layers=layers,
        allow_partial=True,
    )


def build_capabilities() -> ProviderCapabilities:
    return ProviderCapabilities(
        provider_id=PROVIDER_ID,
        provider_version="1.0.0",
        supported_language_codes=["pl"],
        supported_layers=[
            AnalysisLayer.SEGMENTATION,
        ],
    )


def build_response(
    request: NLPProviderRequest,
    *,
    completed: list[AnalysisLayer],
    unavailable: list[AnalysisLayer],
) -> NLPProviderResponse:
    analysis = NLPAnalysis(
        analysis_id="analysis-partial-001",
        document_id=request.document.document_id,
        text_version_id=request.text_version_id,
        status=(
            AnalysisStatus.PARTIAL
            if unavailable
            else AnalysisStatus.COMPLETED
        ),
        provider=ProviderMetadata(
            provider_id=PROVIDER_ID,
            provider_version="1.0.0",
            model_id="test-model",
            language_code="pl",
        ),
        completed_layers=completed,
        unavailable_layers=unavailable,
    )

    return NLPProviderResponse(
        request_id=request.request_id,
        provider_id=PROVIDER_ID,
        analysis=analysis,
    )


class TestPartialProviderConformance(unittest.TestCase):

    def test_01_unsupported_layer_may_be_unavailable(self) -> None:
        request = build_request([
            AnalysisLayer.SEGMENTATION,
            AnalysisLayer.SEMANTICS,
        ])

        response = build_response(
            request,
            completed=[AnalysisLayer.SEGMENTATION],
            unavailable=[AnalysisLayer.SEMANTICS],
        )

        report = validate_provider_response(
            request,
            build_capabilities(),
            response,
        )

        self.assertTrue(
            report.is_valid,
            [issue.model_dump() for issue in report.issues],
        )

        print("UNSUPPORTED LAYER AS UNAVAILABLE: OK")

    def test_02_unsupported_layer_cannot_be_completed(self) -> None:
        request = build_request([
            AnalysisLayer.SEMANTICS,
        ])

        response = build_response(
            request,
            completed=[AnalysisLayer.SEMANTICS],
            unavailable=[],
        )

        report = validate_provider_response(
            request,
            build_capabilities(),
            response,
        )

        self.assertFalse(report.is_valid)

        self.assertIn(
            "unsupported_completed_layers",
            [issue.code for issue in report.issues],
        )

        print("UNSUPPORTED LAYER AS COMPLETED: REJECTED")

    def test_03_unrequested_layer_cannot_be_reported(self) -> None:
        request = build_request([
            AnalysisLayer.SEGMENTATION,
        ])

        response = build_response(
            request,
            completed=[AnalysisLayer.SEGMENTATION],
            unavailable=[AnalysisLayer.SEMANTICS],
        )

        report = validate_provider_response(
            request,
            build_capabilities(),
            response,
        )

        self.assertFalse(report.is_valid)

        self.assertIn(
            "unrequested_layers_reported",
            [issue.code for issue in report.issues],
        )

        print("UNREQUESTED LAYER REPORTING: REJECTED")


def main() -> None:
    print("=" * 60)
    print("PARTIAL PROVIDER CONFORMANCE REGRESSION TESTS")
    print("=" * 60)

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        TestPartialProviderConformance
    )

    result = unittest.TextTestRunner(verbosity=0).run(suite)

    if not result.wasSuccessful():
        raise SystemExit(1)

    print()
    print("ALL PARTIAL CONFORMANCE TESTS PASSED: 3/3")


if __name__ == "__main__":
    main()


