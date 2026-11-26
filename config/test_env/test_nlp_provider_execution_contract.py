#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for stage 8C: NLPProviderLifecycle under the runtime execution contract."""

import asyncio
import time
import unittest

from ai_platform.common.core.execution import (
    CancellationToken,
    ExecutionCancelledError,
    ExecutionContext,
    ExecutionOutcome,
    ExecutionTimeoutError,
    RuntimePolicy,
)
from ai_platform.common.core.registry.plugin_registry import PluginRegistry
from ai_platform.common.nlp.model.analysis import AnalysisLayer, NLPAnalysis
from ai_platform.common.nlp.model.document import (
    NLPDocument,
    SourceDescriptor,
    TextRepresentation,
    TextVersion,
)
from ai_platform.common.nlp.provider import (
    NLPProviderError,
    NLPProviderInputError,
    NLPProviderRequest,
    NLPProviderResponse,
    ProviderCapabilities,
)
from ai_platform.common.nlp.provider.errors import (
    NLPProviderCancelledError,
    NLPProviderTimeoutError,
)
from ai_platform.common.nlp.provider.lifecycle import (
    NLPProviderLifecycle,
    NLPProviderLifecycleState,
)


def build_request(request_id: str = "8c-request") -> NLPProviderRequest:
    document = NLPDocument(
        document_id="8c-document",
        source=SourceDescriptor(source_id="8c-source", source_type="text"),
        text_versions=[
            TextVersion(
                text_version_id="8c-version",
                representation=TextRepresentation.DIPLOMATIC,
                text="Ala ma kota.",
            )
        ],
        primary_text_version_id="8c-version",
    )
    return NLPProviderRequest(
        request_id=request_id,
        document=document,
        text_version_id="8c-version",
        requested_layers=[AnalysisLayer.SEGMENTATION],
        allow_partial=False,
    )


def build_response(provider_id: str, request: NLPProviderRequest) -> NLPProviderResponse:
    return NLPProviderResponse(
        request_id=request.request_id,
        provider_id=provider_id,
        analysis=NLPAnalysis(
            analysis_id="8c-analysis",
            document_id=request.document.document_id,
            text_version_id=request.text_version_id,
            completed_layers=[AnalysisLayer.SEGMENTATION],
        ),
    )


class LegacyProvider:
    """Provider with only analyze(request); ``delay`` seconds per analysis."""

    def __init__(self, provider_id: str = "legacy", delay: float = 0.0,
                 error: Exception | None = None) -> None:
        self._capabilities = ProviderCapabilities(
            provider_id=provider_id, provider_version="1.0.0",
            supported_language_codes=["pl"], supported_layers=[AnalysisLayer.SEGMENTATION])
        self.delay, self.error = delay, error
        self.running = 0
        self.max_running = 0
        self.finished = 0

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    async def analyze(self, request: NLPProviderRequest) -> NLPProviderResponse:
        self.running += 1
        self.max_running = max(self.max_running, self.running)
        try:
            await asyncio.sleep(self.delay)
            if self.error is not None:
                raise self.error
            return build_response(self._capabilities.provider_id, request)
        finally:
            self.running -= 1
            self.finished += 1


class ContextAwareProvider(LegacyProvider):
    """Provider implementing analyze_in_context: checks the context, records facts."""

    def __init__(self, provider_id: str = "aware", steps: int = 1) -> None:
        super().__init__(provider_id)
        self.steps = steps
        self.seen_context = None

    async def analyze_in_context(self, request, context, recorder):
        self.seen_context = context
        recorder.record_engine("fake-engine", "2.0")
        recorder.record_device("cpu", threads=context.policy.max_threads)
        for step in range(self.steps):
            context.check(f"step {step}")
            await asyncio.sleep(0.02)
        recorder.note("steps", self.steps)
        return build_response(self._capabilities.provider_id, request)


class TestNLPExecutionContract(unittest.IsolatedAsyncioTestCase):

    def setUp(self) -> None:
        self.lifecycle = NLPProviderLifecycle(PluginRegistry())

    async def test_01_old_analyze_unchanged(self) -> None:
        self.lifecycle.register(LegacyProvider())
        response = await self.lifecycle.analyze("legacy", build_request())
        self.assertEqual(response.provider_id, "legacy")
        print("OLD analyze() RESULT UNCHANGED: OK")

    async def test_02_metadata_of_legacy_provider(self) -> None:
        self.lifecycle.register(LegacyProvider(), policy=RuntimePolicy(device="cpu"))
        result = await self.lifecycle.analyze_with_context("legacy", build_request("r-2"))
        meta = result.metadata
        self.assertEqual(meta.outcome, ExecutionOutcome.SUCCEEDED)
        self.assertEqual((meta.provider_id, meta.request_id, meta.operation),
                         ("legacy", "r-2", "nlp.analyze"))
        self.assertEqual(meta.device_requested, "cpu")
        self.assertFalse(meta.extra["context_aware"])
        print("EXECUTION METADATA (LEGACY PROVIDER): OK")

    async def test_03_context_aware_provider_gets_context(self) -> None:
        provider = ContextAwareProvider(steps=3)
        self.lifecycle.register(provider, policy=RuntimePolicy(max_threads=4))
        result = await self.lifecycle.analyze_with_context(
            "aware", build_request(), policy=RuntimePolicy(max_threads=2))
        meta = result.metadata
        self.assertEqual(provider.seen_context.policy.max_threads, 2)  # narrowed
        self.assertEqual((meta.engine, meta.engine_version, meta.device_used, meta.threads,
                          meta.extra["steps"]), ("fake-engine", "2.0", "cpu", 2, 3))
        print("CONTEXT-AWARE PROVIDER: OK")

    async def test_04_timeout_cooperative(self) -> None:
        self.lifecycle.register(ContextAwareProvider(steps=100))
        with self.assertRaises(NLPProviderTimeoutError) as caught:
            await self.lifecycle.analyze_with_context("aware", build_request(),
                                                      timeout_seconds=0.1)
        error = caught.exception
        self.assertIsInstance(error, NLPProviderError)
        self.assertIsInstance(error, ExecutionTimeoutError)
        self.assertTrue(error.retryable)
        self.assertEqual(error.execution_metadata.outcome, ExecutionOutcome.TIMED_OUT)
        self.assertFalse(error.execution_metadata.abandoned)
        print("TIMEOUT (COOPERATIVE): OK")

    async def test_05_timeout_legacy_is_abandoned_and_close_waits(self) -> None:
        provider = LegacyProvider(delay=0.4)
        self.lifecycle.register(provider)
        start = time.monotonic()
        with self.assertRaises(NLPProviderTimeoutError) as caught:
            await self.lifecycle.analyze_with_context("legacy", build_request(),
                                                      timeout_seconds=0.05)
        self.assertLess(time.monotonic() - start, 0.35)
        self.assertTrue(caught.exception.execution_metadata.abandoned)
        self.assertEqual(provider.finished, 0)  # still running
        snapshot = await self.lifecycle.close("legacy")  # waits for the real end
        self.assertEqual(snapshot.state, NLPProviderLifecycleState.CLOSED)
        self.assertEqual(provider.finished, 1)
        print("TIMEOUT (LEGACY, ABANDONED, CLOSE WAITS): OK")

    async def test_06_cancellation(self) -> None:
        self.lifecycle.register(ContextAwareProvider(steps=100))
        token = CancellationToken()
        asyncio.get_running_loop().call_later(0.05, token.cancel, "user pressed stop")
        with self.assertRaises(NLPProviderCancelledError) as caught:
            await self.lifecycle.analyze_with_context("aware", build_request(),
                                                      cancellation=token)
        self.assertIsInstance(caught.exception, ExecutionCancelledError)
        self.assertEqual(caught.exception.execution_metadata.outcome,
                         ExecutionOutcome.CANCELLED)
        print("CANCELLATION: OK")

    async def test_07_provider_error_keeps_type(self) -> None:
        self.lifecycle.register(LegacyProvider(error=NLPProviderInputError(
            "empty text", provider_id="legacy")))
        with self.assertRaises(NLPProviderInputError) as caught:
            await self.lifecycle.analyze_with_context("legacy", build_request())
        meta = caught.exception.execution_metadata
        self.assertEqual(meta.outcome, ExecutionOutcome.FAILED)
        self.assertEqual(meta.error.code, "provider_input_error")
        print("PROVIDER ERROR TYPE KEPT: OK")

    async def test_08_concurrency_limit(self) -> None:
        provider = LegacyProvider(delay=0.05)
        self.lifecycle.register(provider, policy=RuntimePolicy(max_concurrency=1))
        await asyncio.gather(*(self.lifecycle.analyze("legacy", build_request(f"r{n}"))
                               for n in range(4)))
        self.assertEqual(provider.max_running, 1)
        print("CONCURRENCY LIMIT: OK")

    async def test_09_caller_context_is_parent(self) -> None:
        self.lifecycle.register(ContextAwareProvider())
        parent = ExecutionContext.create("pipeline.run", timeout_seconds=30)
        result = await self.lifecycle.analyze_with_context("aware", build_request(),
                                                           context=parent)
        self.assertEqual(result.metadata.parent_id, parent.execution_id)
        print("CALLER CONTEXT AS PARENT: OK")


class TestCancellationWithContext(unittest.IsolatedAsyncioTestCase):

    async def test_11_separate_token_works_together_with_a_context(self) -> None:
        lifecycle = NLPProviderLifecycle(PluginRegistry())
        lifecycle.register(ContextAwareProvider(steps=100))
        parent = ExecutionContext.create("pipeline.run", timeout_seconds=30)
        token = CancellationToken()
        asyncio.get_running_loop().call_later(0.05, token.cancel, "stop button")
        with self.assertRaises(NLPProviderCancelledError):
            await lifecycle.analyze_with_context("aware", build_request(), context=parent,
                                                 cancellation=token)
        self.assertFalse(parent.cancellation.cancelled)  # only this analysis stopped
        print("SEPARATE TOKEN + CALLER CONTEXT: OK")


class TestPolicyFromConfiguration(unittest.IsolatedAsyncioTestCase):

    async def test_10_runtime_section_becomes_policy(self) -> None:
        from ai_platform.common.nlp.provider import (  # pylint: disable=import-outside-toplevel
            NLPProviderConfigurationRuntime,
            NLPProviderConfigurationService,
        )
        registry = PluginRegistry()
        lifecycle = NLPProviderLifecycle(registry)
        provider = LegacyProvider("configured")
        lifecycle.register(provider, policy=RuntimePolicy(max_threads=8,
                                                          timeout_seconds=60))
        runtime = NLPProviderConfigurationRuntime(
            NLPProviderConfigurationService(registry), lifecycle)
        configured = await runtime.initialize_from_configuration({
            "provider_id": "configured",
            "engine": {"engine_name": "test-engine"},
            "model": {"model_id": "m", "language": "pl"},
            "runtime": {"device": "cpu", "threads": 2},
        }, environ={})
        result = await lifecycle.analyze_with_context("configured", build_request())
        meta = result.metadata
        self.assertEqual((meta.device_requested, meta.threads), ("cpu", 2))  # narrowed
        self.assertEqual(meta.configuration_fingerprint,
                         configured.configuration_fingerprint)
        print("POLICY AND FINGERPRINT FROM CONFIGURATION: OK")


def main() -> None:
    print("=" * 60)
    print("NLP PROVIDER EXECUTION CONTRACT TESTS (8C)")
    print("=" * 60)
    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite([loader.loadTestsFromTestCase(TestNLPExecutionContract),
                                loader.loadTestsFromTestCase(TestCancellationWithContext),
                                loader.loadTestsFromTestCase(TestPolicyFromConfiguration)])
    result = unittest.TextTestRunner(verbosity=0).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)
    print()
    print(f"ALL NLP PROVIDER EXECUTION CONTRACT TESTS PASSED: "
          f"{result.testsRun}/{result.testsRun}")


if __name__ == "__main__":
    main()
