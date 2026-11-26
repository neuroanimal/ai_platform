#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for stage 8D: the Stanza provider under the runtime execution contract."""

import asyncio
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_nlp_stanza_provider import (  # noqa: E402  pylint: disable=wrong-import-position
    build_request,
    make_standard_pipeline,
)

from ai_platform.common.core.execution import (  # noqa: E402  pylint: disable=wrong-import-position
    PolicyViolationError,
    ResourceConflictError,
    ResourceManager,
    RuntimePolicy,
)
from ai_platform.common.core.registry.plugin_registry import (  # noqa: E402  pylint: disable=wrong-import-position
    PluginRegistry,
)
from ai_platform.common.nlp.provider import (  # noqa: E402  pylint: disable=wrong-import-position
    NLPProviderLifecycle,
    NLPProviderTimeoutError,
    StanzaPolishProvider,
)
from ai_platform.common.nlp.provider.stanza_provider import (  # noqa: E402  pylint: disable=wrong-import-position
    PROVIDER_ID,
)


class StagedPipeline:
    """Fake Stanza pipeline with processors and process(doc, processors=[...]).

    The first stage returns the standard fake document, later stages pass
    it on, so the provider's mapping sees a real-looking result.
    """

    def __init__(self, delay: float = 0.0) -> None:
        self.processors = {name: object() for name in
                           ("tokenize", "mwt", "pos", "lemma", "depparse")}
        self.document = make_standard_pipeline().stanza_document
        self.delay = delay
        self.calls: list[list[str]] = []

    def process(self, document, processors=None):
        self.calls.append(list(processors))
        time.sleep(self.delay)
        return self.document if isinstance(document, str) else document

    def __call__(self, text: str):
        raise AssertionError("the staged path must not call the whole pipeline")


def make_lifecycle(pipeline, policy=None, resources=None):
    lifecycle = NLPProviderLifecycle(PluginRegistry(), resources=resources)
    provider = StanzaPolishProvider(pipeline=pipeline, provider_version="test")
    lifecycle.register(provider, policy=policy)
    return lifecycle, provider


class TestStanzaExecutionContract(unittest.IsolatedAsyncioTestCase):

    async def test_01_processors_run_one_by_one(self) -> None:
        pipeline = StagedPipeline()
        lifecycle, _ = make_lifecycle(pipeline)
        result = await lifecycle.analyze_with_context(PROVIDER_ID, build_request("Ala ma kota."))
        self.assertEqual(pipeline.calls, [["tokenize"], ["pos"], ["lemma"], ["depparse"]])
        meta = result.metadata
        self.assertEqual((meta.engine, meta.engine_version, meta.device_used),
                         ("stanza", "test", "cpu"))
        self.assertEqual(list(meta.extra["stage_seconds"]),
                         ["tokenize+mwt", "pos", "lemma", "depparse"])
        self.assertTrue(result.response.analysis.tokens)
        print("PROCESSORS ONE BY ONE, METADATA: OK")

    async def test_02_timeout_stops_at_processor_boundary(self) -> None:
        pipeline = StagedPipeline(delay=0.1)
        lifecycle, _ = make_lifecycle(pipeline)
        with self.assertRaises(NLPProviderTimeoutError) as caught:
            await lifecycle.analyze_with_context(PROVIDER_ID, build_request("Ala ma kota."),
                                                 timeout_seconds=0.15)
        await asyncio.sleep(0.3)  # let the worker reach its next check
        self.assertLess(len(pipeline.calls), 4)
        self.assertFalse(caught.exception.execution_metadata.abandoned)
        print("TIMEOUT AT PROCESSOR BOUNDARY: OK")

    async def test_03_callable_only_pipeline_still_works(self) -> None:
        lifecycle, _ = make_lifecycle(make_standard_pipeline())
        result = await lifecycle.analyze_with_context(PROVIDER_ID, build_request("Ala ma kota."))
        self.assertEqual(list(result.metadata.extra["stage_seconds"]), ["pipeline"])
        print("CALLABLE-ONLY PIPELINE: OK")

    async def test_04_device_policy(self) -> None:
        lifecycle, _ = make_lifecycle(StagedPipeline(), policy=RuntimePolicy(
            device="cuda:0", allow_device_fallback=False))
        with self.assertRaises(PolicyViolationError):
            await lifecycle.analyze_with_context(PROVIDER_ID, build_request("Ala ma kota."))
        lifecycle, _ = make_lifecycle(StagedPipeline(), policy=RuntimePolicy(device="cuda:0"))
        result = await lifecycle.analyze_with_context(PROVIDER_ID, build_request("Ala ma kota."))
        self.assertEqual((result.metadata.device_requested, result.metadata.device_used),
                         ("cuda:0", "cpu"))
        print("DEVICE POLICY AND FALLBACK: OK")

    async def test_05_thread_setting_is_claimed(self) -> None:
        import torch  # pylint: disable=import-outside-toplevel
        current = torch.get_num_threads()
        resources = ResourceManager()
        resources.claim_setting("torch.num_threads", current + 1, "another-engine")
        lifecycle, _ = make_lifecycle(StagedPipeline(), policy=RuntimePolicy(
            max_threads=current), resources=resources)
        with self.assertRaises(ResourceConflictError):
            await lifecycle.analyze_with_context(PROVIDER_ID, build_request("Ala ma kota."))
        self.assertEqual(torch.get_num_threads(), current)  # nothing was changed
        resources.release_settings("another-engine")
        result = await lifecycle.analyze_with_context(PROVIDER_ID, build_request("Ala ma kota."))
        self.assertEqual(result.metadata.threads, current)
        self.assertEqual(resources.setting("torch.num_threads"), (current, PROVIDER_ID))
        print("PROCESS-GLOBAL THREAD SETTING CLAIMED: OK")

    async def test_06_pipeline_shared_between_instances(self) -> None:
        resources = ResourceManager()
        built = []

        def build(self):
            built.append(1)
            return StagedPipeline()

        original = StanzaPolishProvider._initialize_pipeline
        StanzaPolishProvider._initialize_pipeline = build
        try:
            first = StanzaPolishProvider(provider_version="test")
            second = StanzaPolishProvider(provider_version="test")
            for provider in (first, second):
                provider.bind_execution_resources(resources)
                provider.initialize()
        finally:
            StanzaPolishProvider._initialize_pipeline = original
        self.assertEqual(built, [1])
        self.assertIs(first._pipeline, second._pipeline)  # pylint: disable=protected-access
        key = first._shared_pipeline_key()  # pylint: disable=protected-access
        self.assertEqual(resources.users(key), 2)
        first.close()
        second.close()
        self.assertEqual(resources.users(key), 0)
        print("PIPELINE SHARED BETWEEN INSTANCES: OK")


def main() -> None:
    print("=" * 60)
    print("STANZA EXECUTION CONTRACT TESTS (8D)")
    print("=" * 60)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestStanzaExecutionContract)
    result = unittest.TextTestRunner(verbosity=0).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)
    print()
    print(f"ALL STANZA EXECUTION CONTRACT TESTS PASSED: {result.testsRun}/{result.testsRun}")


if __name__ == "__main__":
    main()
