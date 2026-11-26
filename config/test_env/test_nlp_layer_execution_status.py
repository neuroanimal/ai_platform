#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for NLP per-layer execution status contract."""

import unittest
from datetime import datetime, timedelta, timezone

from pydantic import ValidationError

from ai_platform.common.nlp.model import (
    AnalysisLayer,
    AnalysisLayerExecution,
    AnalysisLayerExecutionStatus,
    NLPAnalysis,
    ProviderMetadata,
)
from ai_platform.common.nlp.model.analysis import AnalysisStatus
from ai_platform.common.nlp.provider import (
    NLPProviderRequest,
    NLPProviderResponse,
    ProviderCapabilities,
)
from ai_platform.common.nlp.provider.validation import (
    validate_provider_response,
)


def build_request() -> NLPProviderRequest:
    from ai_platform.common.nlp.model.document import (
        NLPDocument,
        SourceDescriptor,
        TextRepresentation,
        TextVersion,
    )

    document = NLPDocument(
        document_id="layer-document",
        source=SourceDescriptor(
            source_id="layer-source",
            source_type="text",
        ),
        text_versions=[
            TextVersion(
                text_version_id="layer-version",
                representation=TextRepresentation.DIPLOMATIC,
                text="Ala ma kota.",
            )
        ],
        primary_text_version_id="layer-version",
    )

    return NLPProviderRequest(
        request_id="layer-request",
        document=document,
        text_version_id="layer-version",
        requested_layers=[
            AnalysisLayer.SEGMENTATION,
            AnalysisLayer.MORPHOLOGY,
        ],
        allow_partial=True,
    )


def build_capabilities() -> ProviderCapabilities:
    return ProviderCapabilities(
        provider_id="layer-provider",
        provider_version="1.0.0",
        supported_language_codes=["pl"],
        supported_layers=[
            AnalysisLayer.SEGMENTATION,
            AnalysisLayer.MORPHOLOGY,
        ],
    )


def build_response(
    *,
    layer_executions: list[AnalysisLayerExecution],
    completed_layers: list[AnalysisLayer] | None = None,
    unavailable_layers: list[AnalysisLayer] | None = None,
) -> NLPProviderResponse:
    request = build_request()

    return NLPProviderResponse(
        request_id=request.request_id,
        provider_id="layer-provider",
        analysis=NLPAnalysis(
            analysis_id="layer-analysis",
            document_id=request.document.document_id,
            text_version_id=request.text_version_id,
            status=AnalysisStatus.PARTIAL,
            provider=ProviderMetadata(
                provider_id="layer-provider",
                provider_version="1.0.0",
            ),
            completed_layers=completed_layers or [],
            unavailable_layers=unavailable_layers or [],
            layer_executions=layer_executions,
        ),
    )


class TestLayerExecutionModel(unittest.TestCase):

    def test_all_statuses_are_available(self) -> None:
        expected = {
            "not_started",
            "running",
            "completed",
            "failed",
            "skipped",
            "unavailable",
            "cancelled",
        }

        actual = {
            item.value
            for item in AnalysisLayerExecutionStatus
        }

        self.assertEqual(actual, expected)
        print("LAYER EXECUTION STATUS ENUM: OK")

    def test_not_started_has_no_timestamps(self) -> None:
        item = AnalysisLayerExecution(
            layer=AnalysisLayer.MORPHOLOGY,
            status=AnalysisLayerExecutionStatus.NOT_STARTED,
        )

        self.assertIsNone(item.started_at)
        self.assertIsNone(item.finished_at)
        print("NOT STARTED STATUS: OK")

    def test_running_cannot_have_finished_at(self) -> None:
        with self.assertRaises(ValidationError):
            AnalysisLayerExecution(
                layer=AnalysisLayer.MORPHOLOGY,
                status=AnalysisLayerExecutionStatus.RUNNING,
                started_at=datetime.now(timezone.utc),
                finished_at=datetime.now(timezone.utc),
            )

        print("RUNNING STATUS VALIDATION: OK")

    def test_finished_before_started_rejected(self) -> None:
        now = datetime.now(timezone.utc)

        with self.assertRaises(ValidationError):
            AnalysisLayerExecution(
                layer=AnalysisLayer.MORPHOLOGY,
                status=AnalysisLayerExecutionStatus.COMPLETED,
                started_at=now,
                finished_at=now - timedelta(seconds=1),
            )

        print("EXECUTION TIMESTAMP ORDER: OK")

    def test_duration_must_be_nonnegative(self) -> None:
        with self.assertRaises(ValidationError):
            AnalysisLayerExecution(
                layer=AnalysisLayer.MORPHOLOGY,
                status=AnalysisLayerExecutionStatus.FAILED,
                duration_seconds=-1,
            )

        print("EXECUTION DURATION VALIDATION: OK")


class TestLayerExecutionConformance(unittest.TestCase):

    def setUp(self) -> None:
        self.request = build_request()
        self.capabilities = build_capabilities()

    def validate(self, response: NLPProviderResponse):
        return validate_provider_response(
            self.request,
            self.capabilities,
            response,
        )

    def test_completed_status_matches_completed_layers(self) -> None:
        response = build_response(
            layer_executions=[
                AnalysisLayerExecution(
                    layer=AnalysisLayer.SEGMENTATION,
                    status=AnalysisLayerExecutionStatus.COMPLETED,
                    duration_seconds=0.02,
                ),
                AnalysisLayerExecution(
                    layer=AnalysisLayer.MORPHOLOGY,
                    status=AnalysisLayerExecutionStatus.COMPLETED,
                    duration_seconds=0.04,
                ),
            ],
            completed_layers=[
                AnalysisLayer.SEGMENTATION,
                AnalysisLayer.MORPHOLOGY,
            ],
        )

        self.assertTrue(self.validate(response).is_valid)
        print("COMPLETED LAYERS CONSISTENCY: OK")

    def test_unavailable_status_matches_unavailable_layers(self) -> None:
        response = build_response(
            layer_executions=[
                AnalysisLayerExecution(
                    layer=AnalysisLayer.SEGMENTATION,
                    status=AnalysisLayerExecutionStatus.COMPLETED,
                ),
                AnalysisLayerExecution(
                    layer=AnalysisLayer.MORPHOLOGY,
                    status=AnalysisLayerExecutionStatus.UNAVAILABLE,
                ),
            ],
            completed_layers=[AnalysisLayer.SEGMENTATION],
            unavailable_layers=[AnalysisLayer.MORPHOLOGY],
        )

        self.assertTrue(self.validate(response).is_valid)
        print("UNAVAILABLE LAYERS CONSISTENCY: OK")

    def test_failed_layer_is_not_completed(self) -> None:
        response = build_response(
            layer_executions=[
                AnalysisLayerExecution(
                    layer=AnalysisLayer.SEGMENTATION,
                    status=AnalysisLayerExecutionStatus.COMPLETED,
                ),
                AnalysisLayerExecution(
                    layer=AnalysisLayer.MORPHOLOGY,
                    status=AnalysisLayerExecutionStatus.FAILED,
                    error_code="engine_error",
                    message="Morphology engine failed.",
                ),
            ],
            completed_layers=[AnalysisLayer.SEGMENTATION],
        )

        self.assertTrue(self.validate(response).is_valid)
        print("FAILED LAYER REPRESENTATION: OK")

    def test_missing_requested_layer_is_rejected(self) -> None:
        response = build_response(
            layer_executions=[
                AnalysisLayerExecution(
                    layer=AnalysisLayer.SEGMENTATION,
                    status=AnalysisLayerExecutionStatus.COMPLETED,
                ),
            ],
            completed_layers=[AnalysisLayer.SEGMENTATION],
        )

        report = self.validate(response)

        self.assertFalse(report.is_valid)
        self.assertIn(
            "missing_layer_executions",
            {issue.code for issue in report.issues},
        )
        print("MISSING LAYER EXECUTION REJECTED: OK")

    def test_duplicate_layer_execution_is_rejected(self) -> None:
        response = build_response(
            layer_executions=[
                AnalysisLayerExecution(
                    layer=AnalysisLayer.SEGMENTATION,
                    status=AnalysisLayerExecutionStatus.COMPLETED,
                ),
                AnalysisLayerExecution(
                    layer=AnalysisLayer.SEGMENTATION,
                    status=AnalysisLayerExecutionStatus.FAILED,
                ),
                AnalysisLayerExecution(
                    layer=AnalysisLayer.MORPHOLOGY,
                    status=AnalysisLayerExecutionStatus.NOT_STARTED,
                ),
            ],
            completed_layers=[AnalysisLayer.SEGMENTATION],
        )

        report = self.validate(response)

        self.assertFalse(report.is_valid)
        self.assertIn(
            "duplicate_layer_executions",
            {issue.code for issue in report.issues},
        )
        print("DUPLICATE LAYER EXECUTION REJECTED: OK")

    def test_status_mismatch_is_rejected(self) -> None:
        response = build_response(
            layer_executions=[
                AnalysisLayerExecution(
                    layer=AnalysisLayer.SEGMENTATION,
                    status=AnalysisLayerExecutionStatus.COMPLETED,
                ),
                AnalysisLayerExecution(
                    layer=AnalysisLayer.MORPHOLOGY,
                    status=AnalysisLayerExecutionStatus.SKIPPED,
                ),
            ],
            completed_layers=[],
        )

        report = self.validate(response)

        self.assertFalse(report.is_valid)
        self.assertIn(
            "completed_layer_execution_mismatch",
            {issue.code for issue in report.issues},
        )
        print("LAYER STATUS MISMATCH REJECTED: OK")

    def test_legacy_response_without_layer_executions_remains_valid(self) -> None:
        response = build_response(
            layer_executions=[],
            completed_layers=[AnalysisLayer.SEGMENTATION],
            unavailable_layers=[AnalysisLayer.MORPHOLOGY],
        )

        self.assertTrue(self.validate(response).is_valid)
        print("LEGACY RESPONSE COMPATIBILITY: OK")


def main() -> None:
    print("=" * 60)
    print("NLP LAYER EXECUTION STATUS TESTS (8E.1)")
    print("=" * 60)

    suite = unittest.TestSuite()

    suite.addTests(
        unittest.defaultTestLoader.loadTestsFromTestCase(
            TestLayerExecutionModel
        )
    )

    suite.addTests(
        unittest.defaultTestLoader.loadTestsFromTestCase(
            TestLayerExecutionConformance
        )
    )

    result = unittest.TextTestRunner(verbosity=0).run(suite)

    if not result.wasSuccessful():
        raise SystemExit(1)

    print()
    print(
        "ALL NLP LAYER EXECUTION STATUS TESTS PASSED: "
        f"{result.testsRun}/{result.testsRun}"
    )


if __name__ == "__main__":
    main()

