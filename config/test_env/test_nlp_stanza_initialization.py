
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for actual Stanza provider initialization."""

import sys
import unittest

from types import ModuleType
from unittest.mock import patch

from ai_platform.common.nlp.provider.stanza_provider import (
    StanzaPolishProvider,
)


class TestStanzaInitialization(unittest.TestCase):

    def test_01_initialization_is_lazy(self) -> None:
        provider = StanzaPolishProvider(
            provider_version="test",
        )

        self.assertIsNone(provider._pipeline)

        print("LAZY INITIALIZATION BEFORE LIFECYCLE: OK")

    def test_02_initialization_is_idempotent(self) -> None:
        provider = StanzaPolishProvider(
            provider_version="test",
        )

        pipeline = object()

        with patch.object(
            provider,
            "_initialize_pipeline",
            return_value=pipeline,
        ) as initialize_pipeline:

            provider.initialize()
            provider.initialize()

        self.assertIs(provider._pipeline, pipeline)
        initialize_pipeline.assert_called_once()

        print("INITIALIZATION IDEMPOTENCY: OK")

    def test_03_injected_pipeline_is_preserved(self) -> None:
        pipeline = object()

        provider = StanzaPolishProvider(
            pipeline=pipeline,
            provider_version="test",
        )

        with patch.object(
            provider,
            "_initialize_pipeline",
        ) as initialize_pipeline:

            provider.initialize()

        self.assertIs(provider._pipeline, pipeline)
        initialize_pipeline.assert_not_called()

        print("INJECTED PIPELINE PRESERVATION: OK")

    def test_04_pipeline_initialization_disables_downloads(
        self,
    ) -> None:
        captured: dict = {}

        def fake_pipeline(**kwargs):
            captured.update(kwargs)
            return object()

        stanza_module = ModuleType("stanza")
        stanza_module.Pipeline = fake_pipeline

        provider = StanzaPolishProvider(
            model_dir="/tmp/stanza-test-resources",
            package="default",
            use_gpu=False,
            provider_version="test",
        )

        with patch.dict(
            sys.modules,
            {"stanza": stanza_module},
        ):
            provider.initialize()

        self.assertIsNotNone(provider._pipeline)

        self.assertEqual(captured["lang"], "pl")
        self.assertEqual(captured["package"], "default")
        self.assertEqual(
            captured["processors"],
            "tokenize,mwt,pos,lemma,depparse",
        )
        self.assertFalse(captured["use_gpu"])
        self.assertIsNone(captured["download_method"])
        self.assertEqual(
            captured["dir"],
            "/tmp/stanza-test-resources",
        )

        print("EXPLICIT NO-DOWNLOAD INITIALIZATION: OK")

    def test_05_initialization_and_inference_locks_are_separate(
        self,
    ) -> None:
        provider = StanzaPolishProvider(
            provider_version="test",
        )

        self.assertIsNot(
            provider._lock,
            provider._initialization_lock,
        )

        print("SEPARATE INITIALIZATION AND INFERENCE LOCKS: OK")


def main() -> None:
    print("=" * 60)
    print("STANZA INITIALIZATION TESTS")
    print("=" * 60)

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        TestStanzaInitialization
    )

    result = unittest.TextTestRunner(verbosity=0).run(suite)

    if not result.wasSuccessful():
        raise SystemExit(1)

    print()
    print("ALL STANZA INITIALIZATION TESTS PASSED: 5/5")


if __name__ == "__main__":
    main()

