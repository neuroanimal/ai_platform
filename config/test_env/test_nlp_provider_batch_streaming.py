
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Contract tests for NLP provider batch and streaming extensions."""

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
    NLPProviderBatch,
    NLPProviderBatchRequest,
    NLPProviderBatchItemError,
    NLPProviderBatchItemResult,
    NLPProviderBatchResponse,
    NLPProviderBatchConformanceReport,
    NLPProviderStreaming,
    NLPProviderStreamEventType,
    NLPProviderStreamError,
    NLPProviderStreamEvent,
    NLPProviderStreamConformanceReport,
    NLPProviderRequest,
    NLPProviderResponse,
    ProviderCapabilities,
    validate_provider_batch_response,
    validate_provider_stream_events,
)


PROVIDER_ID = "test-provider"
PROVIDER_VERSION = "1.0.0"
TEXT_VERSION_ID = "version-001"


def build_request(request_id: str) -> NLPProviderRequest:
    document = NLPDocument(
        document_id=f"document-{request_id}",
        source=SourceDescriptor.model_construct(
            source_id=f"source-{request_id}",
            source_type="text",
        ),
        text_versions=[
            TextVersion.model_construct(
                text_version_id=TEXT_VERSION_ID,
                representation="plain_text",
                text="Ala ma kota.",
            )
        ],
        primary_text_version_id=TEXT_VERSION_ID,
    )

    return NLPProviderRequest(
        request_id=request_id,
        document=document,
        text_version_id=TEXT_VERSION_ID,
        requested_layers=[AnalysisLayer.SEGMENTATION],
    )


def build_response(request: NLPProviderRequest) -> NLPProviderResponse:
    analysis = NLPAnalysis(
        analysis_id=f"analysis-{request.request_id}",
        document_id=request.document.document_id,
        text_version_id=request.text_version_id,
        provider=ProviderMetadata(
            provider_id=PROVIDER_ID,
            provider_version=PROVIDER_VERSION,
            language_code="pl",
        ),
        completed_layers=[AnalysisLayer.SEGMENTATION],
    )

    return NLPProviderResponse(
        request_id=request.request_id,
        provider_id=PROVIDER_ID,
        analysis=analysis,
    )


def build_capabilities() -> ProviderCapabilities:
    return ProviderCapabilities(
        provider_id=PROVIDER_ID,
        provider_version=PROVIDER_VERSION,
        supported_language_codes=["pl"],
        supported_layers=[AnalysisLayer.SEGMENTATION],
        supports_batch=True,
        supports_streaming=True,
    )


class FakeBatchProvider:
    async def analyze_batch(
        self,
        request: NLPProviderBatchRequest,
    ) -> NLPProviderBatchResponse:
        return NLPProviderBatchResponse(
            batch_id=request.batch_id,
            provider_id=PROVIDER_ID,
            results=[
                NLPProviderBatchItemResult(
                    request_id=item.request_id,
                    response=build_response(item),
                )
                for item in request.requests
            ],
        )


class FakeStreamingProvider:
    def analyze_stream(
        self,
        request: NLPProviderRequest,
        *,
        stream_id: str,
    ):
        async def generate():
            yield NLPProviderStreamEvent(
                stream_id=stream_id,
                request_id=request.request_id,
                sequence=0,
                event_type=NLPProviderStreamEventType.STARTED,
            )
            yield NLPProviderStreamEvent(
                stream_id=stream_id,
                request_id=request.request_id,
                sequence=1,
                event_type=NLPProviderStreamEventType.PROGRESS,
                progress=0.5,
                layer=AnalysisLayer.SEGMENTATION,
            )
            yield NLPProviderStreamEvent(
                stream_id=stream_id,
                request_id=request.request_id,
                sequence=2,
                event_type=NLPProviderStreamEventType.RESULT,
                response=build_response(request),
            )
            yield NLPProviderStreamEvent(
                stream_id=stream_id,
                request_id=request.request_id,
                sequence=3,
                event_type=NLPProviderStreamEventType.COMPLETED,
            )

        return generate()


class TestNLPProviderBatchStreaming(unittest.TestCase):

    def test_01_batch_request_creation(self) -> None:
        request = NLPProviderBatchRequest(
            batch_id="batch-001",
            requests=[
                build_request("request-001"),
                build_request("request-002"),
            ],
        )

        self.assertEqual(request.batch_id, "batch-001")
        self.assertEqual(len(request.requests), 2)
        self.assertFalse(request.fail_fast)

        print("BATCH REQUEST CREATION: OK")

    def test_02_batch_rejects_empty_requests(self) -> None:
        with self.assertRaises(ValidationError):
            NLPProviderBatchRequest(
                batch_id="batch-001",
                requests=[],
            )

        print("EMPTY BATCH REJECTION: OK")

    def test_03_batch_rejects_duplicate_request_ids(self) -> None:
        with self.assertRaises(ValidationError):
            NLPProviderBatchRequest(
                batch_id="batch-001",
                requests=[
                    build_request("duplicate"),
                    build_request("duplicate"),
                ],
            )

        print("DUPLICATE BATCH REQUEST IDS: OK")

    def test_04_batch_item_requires_exactly_one_outcome(self) -> None:
        with self.assertRaises(ValidationError):
            NLPProviderBatchItemResult(
                request_id="request-001",
            )

        with self.assertRaises(ValidationError):
            NLPProviderBatchItemResult(
                request_id="request-001",
                response=build_response(build_request("request-001")),
                error=NLPProviderBatchItemError(
                    code="failure",
                    message="Failure.",
                ),
            )

        print("BATCH ITEM OUTCOME VALIDATION: OK")

    def test_05_batch_item_rejects_response_id_mismatch(self) -> None:
        with self.assertRaises(ValidationError):
            NLPProviderBatchItemResult(
                request_id="request-001",
                response=build_response(build_request("request-002")),
            )

        print("BATCH ITEM REQUEST ID MATCH: OK")

    def test_06_batch_response_counts(self) -> None:
        response = NLPProviderBatchResponse(
            batch_id="batch-001",
            provider_id=PROVIDER_ID,
            results=[
                NLPProviderBatchItemResult(
                    request_id="request-001",
                    response=build_response(build_request("request-001")),
                ),
                NLPProviderBatchItemResult(
                    request_id="request-002",
                    error=NLPProviderBatchItemError(
                        code="provider_execution_error",
                        message="Temporary failure.",
                        retryable=True,
                    ),
                ),
            ],
        )

        self.assertEqual(response.succeeded_count, 1)
        self.assertEqual(response.failed_count, 1)
        self.assertFalse(response.is_successful)

        print("BATCH RESPONSE COUNTS: OK")

    def test_07_batch_response_rejects_duplicate_ids(self) -> None:
        item = NLPProviderBatchItemResult(
            request_id="request-001",
            response=build_response(build_request("request-001")),
        )

        with self.assertRaises(ValidationError):
            NLPProviderBatchResponse(
                batch_id="batch-001",
                provider_id=PROVIDER_ID,
                results=[item, item],
            )

        print("BATCH RESPONSE DUPLICATE IDS: OK")

    def test_08_batch_response_rejects_provider_mismatch(self) -> None:
        with self.assertRaises(ValidationError):
            NLPProviderBatchResponse(
                batch_id="batch-001",
                provider_id="different-provider",
                results=[
                    NLPProviderBatchItemResult(
                        request_id="request-001",
                        response=build_response(
                            build_request("request-001")
                        ),
                    )
                ],
            )

        print("BATCH RESPONSE PROVIDER MATCH: OK")

    def test_09_batch_conformance(self) -> None:
        request = NLPProviderBatchRequest(
            batch_id="batch-001",
            requests=[
                build_request("request-001"),
                build_request("request-002"),
            ],
        )

        response = NLPProviderBatchResponse(
            batch_id="batch-001",
            provider_id=PROVIDER_ID,
            results=[
                NLPProviderBatchItemResult(
                    request_id=item.request_id,
                    response=build_response(item),
                )
                for item in request.requests
            ],
        )

        report = validate_provider_batch_response(
            request,
            build_capabilities(),
            response,
        )

        self.assertIsInstance(report, NLPProviderBatchConformanceReport)
        self.assertTrue(report.is_valid)
        self.assertEqual(report.issues, [])

        print("BATCH CONFORMANCE: OK")

    def test_10_batch_conformance_detects_missing_item(self) -> None:
        request = NLPProviderBatchRequest(
            batch_id="batch-001",
            requests=[
                build_request("request-001"),
                build_request("request-002"),
            ],
        )

        response = NLPProviderBatchResponse(
            batch_id="batch-001",
            provider_id=PROVIDER_ID,
            results=[
                NLPProviderBatchItemResult(
                    request_id="request-001",
                    response=build_response(
                        build_request("request-001")
                    ),
                )
            ],
        )

        report = validate_provider_batch_response(
            request,
            build_capabilities(),
            response,
        )

        self.assertFalse(report.is_valid)
        self.assertIn(
            "missing_batch_items",
            [issue.code for issue in report.issues],
        )

        print("BATCH MISSING ITEM DETECTION: OK")

    def test_11_batch_protocol(self) -> None:
        provider = FakeBatchProvider()
        self.assertIsInstance(provider, NLPProviderBatch)

        print("BATCH RUNTIME PROTOCOL: OK")

    def test_12_async_batch_execution(self) -> None:
        provider = FakeBatchProvider()

        request = NLPProviderBatchRequest(
            batch_id="batch-001",
            requests=[
                build_request("request-001"),
                build_request("request-002"),
            ],
        )

        response = asyncio.run(provider.analyze_batch(request))

        self.assertEqual(response.batch_id, request.batch_id)
        self.assertEqual(response.succeeded_count, 2)
        self.assertEqual(response.failed_count, 0)

        print("ASYNC BATCH EXECUTION: OK")

    def test_13_stream_event_validation(self) -> None:
        event = NLPProviderStreamEvent(
            stream_id="stream-001",
            request_id="request-001",
            sequence=0,
            event_type=NLPProviderStreamEventType.STARTED,
        )

        self.assertEqual(event.sequence, 0)
        self.assertEqual(
            event.event_type,
            NLPProviderStreamEventType.STARTED,
        )

        print("STREAM EVENT CREATION: OK")

    def test_14_progress_event_requires_progress(self) -> None:
        with self.assertRaises(ValidationError):
            NLPProviderStreamEvent(
                stream_id="stream-001",
                request_id="request-001",
                sequence=1,
                event_type=NLPProviderStreamEventType.PROGRESS,
            )

        print("STREAM PROGRESS VALIDATION: OK")

    def test_15_result_event_requires_response(self) -> None:
        with self.assertRaises(ValidationError):
            NLPProviderStreamEvent(
                stream_id="stream-001",
                request_id="request-001",
                sequence=1,
                event_type=NLPProviderStreamEventType.RESULT,
            )

        print("STREAM RESULT VALIDATION: OK")

    def test_16_failed_event_requires_error(self) -> None:
        with self.assertRaises(ValidationError):
            NLPProviderStreamEvent(
                stream_id="stream-001",
                request_id="request-001",
                sequence=1,
                event_type=NLPProviderStreamEventType.FAILED,
            )

        print("STREAM FAILURE VALIDATION: OK")

    def test_17_stream_sequence_conformance(self) -> None:
        events = [
            NLPProviderStreamEvent(
                stream_id="stream-001",
                request_id="request-001",
                sequence=0,
                event_type=NLPProviderStreamEventType.STARTED,
            ),
            NLPProviderStreamEvent(
                stream_id="stream-001",
                request_id="request-001",
                sequence=1,
                event_type=NLPProviderStreamEventType.PROGRESS,
                progress=0.5,
            ),
            NLPProviderStreamEvent(
                stream_id="stream-001",
                request_id="request-001",
                sequence=2,
                event_type=NLPProviderStreamEventType.COMPLETED,
            ),
        ]

        report = validate_provider_stream_events(
            events,
            stream_id="stream-001",
            request_id="request-001",
        )

        self.assertIsInstance(report, NLPProviderStreamConformanceReport)
        self.assertTrue(report.is_valid)

        print("STREAM SEQUENCE CONFORMANCE: OK")

    def test_18_stream_detects_invalid_sequence(self) -> None:
        events = [
            NLPProviderStreamEvent(
                stream_id="stream-001",
                request_id="request-001",
                sequence=0,
                event_type=NLPProviderStreamEventType.STARTED,
            ),
            NLPProviderStreamEvent(
                stream_id="stream-001",
                request_id="request-001",
                sequence=4,
                event_type=NLPProviderStreamEventType.COMPLETED,
            ),
        ]

        report = validate_provider_stream_events(
            events,
            stream_id="stream-001",
            request_id="request-001",
        )

        self.assertFalse(report.is_valid)
        self.assertIn(
            "invalid_sequence",
            [issue.code for issue in report.issues],
        )

        print("STREAM INVALID SEQUENCE DETECTION: OK")

    def test_19_stream_detects_events_after_terminal(self) -> None:
        events = [
            NLPProviderStreamEvent(
                stream_id="stream-001",
                request_id="request-001",
                sequence=0,
                event_type=NLPProviderStreamEventType.STARTED,
            ),
            NLPProviderStreamEvent(
                stream_id="stream-001",
                request_id="request-001",
                sequence=1,
                event_type=NLPProviderStreamEventType.COMPLETED,
            ),
            NLPProviderStreamEvent(
                stream_id="stream-001",
                request_id="request-001",
                sequence=2,
                event_type=NLPProviderStreamEventType.PROGRESS,
                progress=1.0,
            ),
        ]

        report = validate_provider_stream_events(
            events,
            stream_id="stream-001",
            request_id="request-001",
        )

        self.assertFalse(report.is_valid)
        self.assertIn(
            "events_after_terminal",
            [issue.code for issue in report.issues],
        )

        print("STREAM TERMINAL EVENT ENFORCEMENT: OK")

    def test_20_stream_protocol(self) -> None:
        provider = FakeStreamingProvider()
        self.assertIsInstance(provider, NLPProviderStreaming)

        print("STREAMING RUNTIME PROTOCOL: OK")

    def test_21_async_stream_execution(self) -> None:
        provider = FakeStreamingProvider()
        request = build_request("request-001")

        async def collect():
            return [
                event
                async for event in provider.analyze_stream(
                    request,
                    stream_id="stream-001",
                )
            ]

        events = asyncio.run(collect())

        self.assertEqual(len(events), 4)
        self.assertEqual(
            events[-1].event_type,
            NLPProviderStreamEventType.COMPLETED,
        )

        report = validate_provider_stream_events(
            events,
            stream_id="stream-001",
            request_id=request.request_id,
        )

        self.assertTrue(report.is_valid)

        print("ASYNC STREAM EXECUTION: OK")

    def test_23_successful_is_not_complete(self) -> None:
        """is_successful: no returned item failed - it does not prove every item came back."""
        request = NLPProviderBatchRequest(
            batch_id="batch-001",
            requests=[build_request("request-001"), build_request("request-002")],
        )
        response = NLPProviderBatchResponse(
            batch_id="batch-001",
            provider_id=PROVIDER_ID,
            results=[NLPProviderBatchItemResult(
                request_id="request-001",
                response=build_response(build_request("request-001")))],
        )
        self.assertTrue(response.is_successful)
        report = validate_provider_batch_response(request, build_capabilities(), response)
        self.assertIn("missing_batch_items", [issue.code for issue in report.issues])
        print("SUCCESSFUL IS NOT COMPLETE: OK")

    def test_24_stream_without_terminal_or_events(self) -> None:
        def event(sequence, event_type, **kwargs):
            return NLPProviderStreamEvent(stream_id="stream-001", request_id="request-001",
                                          sequence=sequence, event_type=event_type, **kwargs)

        unfinished = [event(0, NLPProviderStreamEventType.STARTED),
                      event(1, NLPProviderStreamEventType.PROGRESS, progress=0.5)]
        codes = [issue.code for issue in validate_provider_stream_events(
            unfinished, stream_id="stream-001", request_id="request-001").issues]
        self.assertEqual(codes, ["missing_terminal_event"])
        empty = validate_provider_stream_events([], stream_id="stream-001",
                                                request_id="request-001")
        self.assertIn("empty_stream", [issue.code for issue in empty.issues])
        print("STREAM WITHOUT TERMINAL EVENT / EMPTY STREAM: OK")

    def test_25_stream_result_checked_against_request(self) -> None:
        request = build_request("request-001")
        result = build_response(request)
        events = [
            NLPProviderStreamEvent(stream_id="stream-001", request_id="request-001",
                                   sequence=0, event_type=NLPProviderStreamEventType.STARTED),
            NLPProviderStreamEvent(stream_id="stream-001", request_id="request-001",
                                   sequence=1, event_type=NLPProviderStreamEventType.RESULT,
                                   response=result),
            NLPProviderStreamEvent(stream_id="stream-001", request_id="request-001",
                                   sequence=2, event_type=NLPProviderStreamEventType.COMPLETED),
        ]
        good = validate_provider_stream_events(events, stream_id="stream-001",
                                               request_id="request-001", request=request,
                                               capabilities=build_capabilities())
        self.assertTrue(good.is_valid, [issue.code for issue in good.issues])
        other = ProviderCapabilities(provider_id="someone-else", provider_version="1",
                                     supported_language_codes=["pl"],
                                     supported_layers=list(build_capabilities().supported_layers))
        bad = validate_provider_stream_events(events, stream_id="stream-001",
                                              request_id="request-001", request=request,
                                              capabilities=other)
        self.assertTrue(any(issue.code.startswith("result_") for issue in bad.issues))
        print("STREAM RESULT CONFORMANCE: OK")

    def test_22_public_exports(self) -> None:
        from ai_platform.common.nlp.provider import __all__

        expected = {
            "NLPProviderBatchRequest",
            "NLPProviderBatchResponse",
            "NLPProviderBatch",
            "NLPProviderStreamEvent",
            "NLPProviderStreaming",
            "validate_provider_batch_response",
            "validate_provider_stream_events",
        }

        self.assertTrue(expected.issubset(set(__all__)))

        print("BATCH / STREAM PUBLIC EXPORTS: OK")


def main() -> None:
    print("=" * 60)
    print("NLP PROVIDER BATCH AND STREAMING CONTRACT TESTS")
    print("=" * 60)

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        TestNLPProviderBatchStreaming
    )

    result = unittest.TextTestRunner(verbosity=0).run(suite)

    if not result.wasSuccessful():
        raise SystemExit(1)

    print()
    print(
        "ALL BATCH / STREAMING CONTRACT TESTS PASSED: "
        f"{result.testsRun}/{result.testsRun}"
    )


if __name__ == "__main__":
    main()

