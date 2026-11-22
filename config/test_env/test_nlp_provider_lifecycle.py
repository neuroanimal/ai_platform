
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for NLPProviderLifecycle."""

import asyncio
import unittest

from ai_platform.common.core.registry.plugin_registry import PluginRegistry

from ai_platform.common.nlp.model.analysis import (
    AnalysisLayer,
    NLPAnalysis,
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
    NLPProviderUnavailableError,
    ProviderCapabilities,
)
from ai_platform.common.nlp.provider.lifecycle import (
    NLPProviderLifecycle,
    NLPProviderLifecycleState,
)


class FakeProvider:
    """Provider without optional lifecycle hooks."""

    def __init__(
        self,
        provider_id: str = "fake-provider",
        entered: asyncio.Event | None = None,
        release: asyncio.Event | None = None,
    ) -> None:
        self._capabilities = ProviderCapabilities(
            provider_id=provider_id,
            provider_version="1.0.0",
            supported_language_codes=["pl"],
            supported_layers=[
                AnalysisLayer.SEGMENTATION,
            ],
        )

        self.entered = entered
        self.release = release
        self.analysis_calls = 0

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    async def analyze(
        self,
        request: NLPProviderRequest,
    ) -> NLPProviderResponse:
        self.analysis_calls += 1

        if self.entered is not None:
            self.entered.set()

        if self.release is not None:
            await self.release.wait()

        analysis = NLPAnalysis(
            analysis_id="lifecycle-test-analysis",
            document_id=request.document.document_id,
            text_version_id=request.text_version_id,
            completed_layers=[
                AnalysisLayer.SEGMENTATION,
            ],
        )

        return NLPProviderResponse(
            request_id=request.request_id,
            provider_id=self.capabilities.provider_id,
            analysis=analysis,
        )


class SyncLifecycleProvider(FakeProvider):
    """Provider with synchronous lifecycle hooks."""

    def __init__(self, provider_id: str = "sync-provider") -> None:
        super().__init__(provider_id)

        self.initialize_calls = 0
        self.health_calls = 0
        self.close_calls = 0
        self.healthy = True

    def initialize(self) -> None:
        self.initialize_calls += 1

    def health_check(self) -> bool:
        self.health_calls += 1
        return self.healthy

    def close(self) -> None:
        self.close_calls += 1


class AsyncLifecycleProvider(FakeProvider):
    """Provider with asynchronous lifecycle hooks."""

    def __init__(self) -> None:
        super().__init__("async-provider")

        self.initialize_calls = 0
        self.health_calls = 0
        self.close_calls = 0

    async def initialize(self) -> None:
        self.initialize_calls += 1

    async def health_check(self) -> bool:
        self.health_calls += 1
        return True

    async def close(self) -> None:
        self.close_calls += 1


def build_request() -> NLPProviderRequest:
    document = NLPDocument(
        document_id="lifecycle-document",
        source=SourceDescriptor(
            source_id="lifecycle-source",
            source_type="text",
        ),
        text_versions=[
            TextVersion(
                text_version_id="lifecycle-version",
                representation=TextRepresentation.DIPLOMATIC,
                text="Ala ma kota.",
            )
        ],
        primary_text_version_id="lifecycle-version",
    )

    return NLPProviderRequest(
        request_id="lifecycle-request",
        document=document,
        text_version_id="lifecycle-version",
        requested_layers=[
            AnalysisLayer.SEGMENTATION,
        ],
        allow_partial=False,
    )


class TestNLPProviderLifecycle(unittest.IsolatedAsyncioTestCase):

    def setUp(self) -> None:
        self.registry = PluginRegistry()
        self.lifecycle = NLPProviderLifecycle(self.registry)

    async def test_01_registration_state(self) -> None:
        provider = FakeProvider()

        snapshot = self.lifecycle.register(provider)

        self.assertEqual(
            snapshot.state,
            NLPProviderLifecycleState.REGISTERED,
        )

        self.assertIs(
            self.registry.get("nlp:fake-provider"),
            provider,
        )

        with self.assertRaises(NLPProviderUnavailableError):
            self.lifecycle.get_provider("fake-provider")

        print("EXPLICIT REGISTRATION STATE: OK")

    async def test_02_provider_without_hooks(self) -> None:
        provider = FakeProvider()
        self.lifecycle.register(provider)

        snapshot = await self.lifecycle.initialize(
            "fake-provider"
        )

        self.assertEqual(
            snapshot.state,
            NLPProviderLifecycleState.READY,
        )

        self.assertIs(
            self.lifecycle.get_provider("fake-provider"),
            provider,
        )

        print("PROVIDER WITHOUT LIFECYCLE HOOKS: OK")

    async def test_03_sync_lifecycle_hooks(self) -> None:
        provider = SyncLifecycleProvider()
        self.lifecycle.register(provider)

        await self.lifecycle.initialize("sync-provider")
        await self.lifecycle.initialize("sync-provider")

        self.assertEqual(provider.initialize_calls, 1)
        self.assertEqual(provider.health_calls, 1)

        await self.lifecycle.close("sync-provider")

        self.assertEqual(provider.close_calls, 1)

        print("SYNCHRONOUS LIFECYCLE HOOKS: OK")

    async def test_04_async_lifecycle_hooks(self) -> None:
        provider = AsyncLifecycleProvider()
        self.lifecycle.register(provider)

        await self.lifecycle.initialize("async-provider")

        self.assertEqual(provider.initialize_calls, 1)
        self.assertEqual(provider.health_calls, 1)

        await self.lifecycle.close("async-provider")

        self.assertEqual(provider.close_calls, 1)

        print("ASYNCHRONOUS LIFECYCLE HOOKS: OK")

    async def test_05_automatic_initialization_on_analysis(self) -> None:
        provider = SyncLifecycleProvider()
        self.lifecycle.register(provider)

        response = await self.lifecycle.analyze(
            "sync-provider",
            build_request(),
        )

        self.assertEqual(
            response.request_id,
            "lifecycle-request",
        )

        self.assertEqual(provider.initialize_calls, 1)
        self.assertEqual(provider.analysis_calls, 1)

        self.assertEqual(
            self.lifecycle.get_snapshot(
                "sync-provider"
            ).state,
            NLPProviderLifecycleState.READY,
        )

        print("AUTOMATIC INITIALIZATION ON ANALYSIS: OK")

    async def test_06_close_waits_for_active_analysis(self) -> None:
        entered = asyncio.Event()
        release = asyncio.Event()

        provider = FakeProvider(
            provider_id="slow-provider",
            entered=entered,
            release=release,
        )

        self.lifecycle.register(provider)

        analysis_task = asyncio.create_task(
            self.lifecycle.analyze(
                "slow-provider",
                build_request(),
            )
        )

        await entered.wait()

        close_task = asyncio.create_task(
            self.lifecycle.close("slow-provider")
        )

        while (
            self.lifecycle.get_snapshot(
                "slow-provider"
            ).state != NLPProviderLifecycleState.CLOSING
        ):
            await asyncio.sleep(0)

        self.assertFalse(close_task.done())

        release.set()

        response = await analysis_task
        snapshot = await close_task

        self.assertEqual(
            response.request_id,
            "lifecycle-request",
        )

        self.assertEqual(
            snapshot.state,
            NLPProviderLifecycleState.CLOSED,
        )

        print("GRACEFUL SHUTDOWN DURING ACTIVE ANALYSIS: OK")

    async def test_07_failed_health_check(self) -> None:
        provider = SyncLifecycleProvider()
        provider.healthy = False

        self.lifecycle.register(provider)

        with self.assertRaises(NLPProviderUnavailableError):
            await self.lifecycle.initialize("sync-provider")

        snapshot = self.lifecycle.get_snapshot("sync-provider")

        self.assertEqual(
            snapshot.state,
            NLPProviderLifecycleState.FAILED,
        )

        self.assertIsNotNone(snapshot.last_error)

        print("FAILED HEALTH CHECK STATE: OK")

    async def test_08_close_before_initialization(self) -> None:
        provider = SyncLifecycleProvider()
        self.lifecycle.register(provider)

        snapshot = await self.lifecycle.close("sync-provider")

        self.assertEqual(
            snapshot.state,
            NLPProviderLifecycleState.CLOSED,
        )

        self.assertEqual(provider.close_calls, 0)
        self.assertEqual(provider.initialize_calls, 0)

        print("CLOSE BEFORE INITIALIZATION: OK")

    async def test_09_close_is_idempotent(self) -> None:
        provider = SyncLifecycleProvider()
        self.lifecycle.register(provider)

        await self.lifecycle.initialize("sync-provider")

        first = await self.lifecycle.close("sync-provider")
        second = await self.lifecycle.close("sync-provider")

        self.assertEqual(
            first.state,
            NLPProviderLifecycleState.CLOSED,
        )

        self.assertEqual(
            second.state,
            NLPProviderLifecycleState.CLOSED,
        )

        self.assertEqual(provider.close_calls, 1)

        print("IDEMPOTENT SHUTDOWN: OK")

    async def test_10_closed_provider_rejects_analysis(self) -> None:
        provider = FakeProvider()
        self.lifecycle.register(provider)

        await self.lifecycle.initialize("fake-provider")
        await self.lifecycle.close("fake-provider")

        with self.assertRaises(NLPProviderUnavailableError):
            await self.lifecycle.analyze(
                "fake-provider",
                build_request(),
            )

        self.assertEqual(provider.analysis_calls, 0)

        print("CLOSED PROVIDER ANALYSIS REJECTION: OK")

    async def test_11_initialize_and_close_all(self) -> None:
        first = FakeProvider("first-provider")
        second = FakeProvider("second-provider")

        self.lifecycle.register(first)
        self.lifecycle.register(second)

        initialized = await self.lifecycle.initialize_all()

        self.assertEqual(
            initialized["first-provider"].state,
            NLPProviderLifecycleState.READY,
        )

        self.assertEqual(
            initialized["second-provider"].state,
            NLPProviderLifecycleState.READY,
        )

        closed = await self.lifecycle.close_all()

        self.assertEqual(
            closed["first-provider"].state,
            NLPProviderLifecycleState.CLOSED,
        )

        self.assertEqual(
            closed["second-provider"].state,
            NLPProviderLifecycleState.CLOSED,
        )

        print("BULK INITIALIZATION AND SHUTDOWN: OK")

    async def test_12_unknown_provider(self) -> None:
        with self.assertRaises(NLPProviderUnavailableError):
            self.lifecycle.get_snapshot("unknown-provider")

        with self.assertRaises(NLPProviderUnavailableError):
            await self.lifecycle.initialize("unknown-provider")

        print("UNKNOWN PROVIDER REJECTION: OK")


def main() -> None:
    print("=" * 60)
    print("NLP PROVIDER LIFECYCLE TESTS")
    print("=" * 60)

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        TestNLPProviderLifecycle
    )

    result = unittest.TextTestRunner(verbosity=0).run(suite)

    if not result.wasSuccessful():
        raise SystemExit(1)

    print()
    print("ALL NLP PROVIDER LIFECYCLE TESTS PASSED: 12/12")


if __name__ == "__main__":
    main()


