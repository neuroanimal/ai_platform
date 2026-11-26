
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for actual Stanza provider configuration application."""

import sys
import unittest

from types import SimpleNamespace
from unittest.mock import patch

from ai_platform.common.nlp.provider import (
    NLPProviderConfigurationLoader,
    NLPProviderFactoryRegistry,
    NLPProviderFactoryService,
    StanzaPolishEngineAdapter,
    StanzaPolishProvider,
)
from ai_platform.common.nlp.provider.errors import (
    NLPProviderConfigurationError,
)
from ai_platform.common.nlp.provider.stanza_provider import (
    PROCESSORS,
)


def stanza_configuration(
    *,
    options: dict | None = None,
    model_updates: dict | None = None,
    runtime_updates: dict | None = None,
) -> dict:
    model = {
        "package": "default",
        "language": "pl",
        "model_dir": "/tmp/stanza-resources",
        "download_policy": "never",
    }

    runtime = {
        "device": "cpu",
    }

    if model_updates:
        model.update(model_updates)

    if runtime_updates:
        runtime.update(runtime_updates)

    return {
        "provider_id": "stanza-pl",
        "engine": {
            "engine_name": "stanza",
            "options": options or {},
        },
        "model": model,
        "runtime": runtime,
    }


def load_configuration(**kwargs):
    return NLPProviderConfigurationLoader.load(
        stanza_configuration(**kwargs),
        environ={},
    )


class TestStanzaEngineConfigurationApplication(
    unittest.TestCase
):

    def setUp(self) -> None:
        self.adapter = StanzaPolishEngineAdapter()

    def test_01_default_engine_configuration(self) -> None:
        configuration = load_configuration()

        provider = self.adapter.create_provider(configuration)

        self.assertEqual(provider._processors, PROCESSORS)
        self.assertEqual(provider._tokenize_batch_size, 32)

        print("DEFAULT ENGINE CONFIGURATION: OK")

    def test_02_custom_processors_applied(self) -> None:
        processors = "tokenize,mwt,pos,lemma,depparse"

        configuration = load_configuration(
            options={
                "processors": processors,
            }
        )

        provider = self.adapter.create_provider(configuration)

        self.assertEqual(provider._processors, processors)

        print("CUSTOM PROCESSORS APPLIED: OK")

    def test_03_processors_sequence_applied(self) -> None:
        processors = (
            "tokenize",
            "mwt",
            "pos",
            "lemma",
            "depparse",
        )

        configuration = load_configuration(
            options={
                "processors": list(processors),
            }
        )

        provider = self.adapter.create_provider(configuration)

        self.assertEqual(
            provider._processors,
            ",".join(processors),
        )

        print("PROCESSOR SEQUENCE APPLIED: OK")

    def test_04_tokenize_batch_size_applied(self) -> None:
        configuration = load_configuration(
            options={
                "tokenize_batch_size": 64,
            }
        )

        provider = self.adapter.create_provider(configuration)

        self.assertEqual(
            provider._tokenize_batch_size,
            64,
        )

        print("TOKENIZE BATCH SIZE APPLIED: OK")

    def test_05_missing_required_processor_rejected(self) -> None:
        configuration = load_configuration(
            options={
                "processors": "tokenize,pos,lemma",
            }
        )

        with self.assertRaises(NLPProviderConfigurationError):
            self.adapter.create_provider(configuration)

        print("MISSING REQUIRED PROCESSOR REJECTED: OK")

    def test_06_duplicate_processors_rejected(self) -> None:
        configuration = load_configuration(
            options={
                "processors": (
                    "tokenize,mwt,pos,lemma,depparse,pos"
                ),
            }
        )

        with self.assertRaises(NLPProviderConfigurationError):
            self.adapter.create_provider(configuration)

        print("DUPLICATE PROCESSORS REJECTED: OK")

    def test_07_invalid_tokenize_batch_size_rejected(self) -> None:
        for value in (0, -1, True, "32"):
            with self.subTest(value=value):
                configuration = load_configuration(
                    options={
                        "tokenize_batch_size": value,
                    }
                )

                with self.assertRaises(
                    NLPProviderConfigurationError
                ):
                    self.adapter.create_provider(configuration)

        print("INVALID TOKENIZE BATCH SIZE REJECTED: OK")

    def test_08_unknown_engine_option_rejected(self) -> None:
        configuration = load_configuration(
            options={
                "unknown_option": True,
            }
        )

        with self.assertRaises(NLPProviderConfigurationError):
            self.adapter.create_provider(configuration)

        print("UNKNOWN ENGINE OPTION REJECTED: OK")

    def test_09_model_package_applied(self) -> None:
        configuration = load_configuration(
            model_updates={
                "package": "default",
            }
        )

        provider = self.adapter.create_provider(configuration)

        self.assertEqual(provider._package, "default")
        self.assertEqual(provider._model_id, "pl-default-pdb")

        print("MODEL PACKAGE APPLIED: OK")

    def test_10_model_directory_applied(self) -> None:
        configuration = load_configuration(
            model_updates={
                "model_dir": "/opt/nlp/stanza",
            }
        )

        provider = self.adapter.create_provider(configuration)

        self.assertEqual(
            str(provider._model_dir),
            "/opt/nlp/stanza",
        )

        print("MODEL DIRECTORY APPLIED: OK")

    def test_11_model_id_consistency_enforced(self) -> None:
        configuration = load_configuration(
            model_updates={
                "package": "default",
                "model_id": "pl-other-pdb",
            }
        )

        with self.assertRaises(NLPProviderConfigurationError):
            self.adapter.create_provider(configuration)

        print("MODEL ID CONSISTENCY ENFORCED: OK")

    def test_12_model_version_rejected(self) -> None:
        configuration = load_configuration(
            model_updates={
                "version": "1.0",
            }
        )

        with self.assertRaises(NLPProviderConfigurationError):
            self.adapter.create_provider(configuration)

        print("UNSUPPORTED MODEL VERSION REJECTED: OK")

    def test_13_cpu_device_applied(self) -> None:
        configuration = load_configuration(
            runtime_updates={
                "device": "cpu",
            }
        )

        provider = self.adapter.create_provider(configuration)

        self.assertIs(provider._use_gpu, False)
        self.assertEqual(provider._device, "cpu")

        print("CPU DEVICE APPLIED: OK")

    def test_14_auto_device_applied(self) -> None:
        configuration = load_configuration(
            runtime_updates={
                "device": "auto",
            }
        )

        provider = self.adapter.create_provider(configuration)

        self.assertIsNone(provider._use_gpu)
        self.assertEqual(provider._device, "auto")

        print("AUTOMATIC DEVICE SELECTION APPLIED: OK")

    def test_15_unsupported_runtime_settings_rejected(self) -> None:
        cases = [
            {"threads": 2},
            {"batch_size": 8},
            {"device": "cuda:0"},
            {
                "device": "auto",
                "allow_device_fallback": False,
            },
        ]

        for runtime_updates in cases:
            with self.subTest(runtime_updates=runtime_updates):
                configuration = load_configuration(
                    runtime_updates=runtime_updates,
                )

                with self.assertRaises(
                    NLPProviderConfigurationError
                ):
                    self.adapter.create_provider(configuration)

        print("UNSUPPORTED RUNTIME SETTINGS REJECTED: OK")

    def test_16_provider_creation_remains_lazy(self) -> None:
        configuration = load_configuration()

        provider = self.adapter.create_provider(configuration)

        self.assertIsNone(provider._pipeline)

        print("PROVIDER CREATION REMAINS LAZY: OK")


class TestStanzaPipelineConfigurationApplication(
    unittest.TestCase
):

    def test_17_pipeline_receives_applied_configuration(self) -> None:
        configuration = load_configuration(
            options={
                "processors": (
                    "tokenize,mwt,pos,lemma,depparse"
                ),
                "tokenize_batch_size": 64,
            },
            model_updates={
                "package": "default",
                "model_dir": "/tmp/stanza-test",
            },
            runtime_updates={
                "device": "auto",
            },
        )

        provider = StanzaPolishEngineAdapter().create_provider(
            configuration
        )

        captured: dict = {}

        def fake_pipeline(**kwargs):
            captured.update(kwargs)
            return object()

        fake_stanza = SimpleNamespace(
            Pipeline=fake_pipeline,
        )

        with patch.dict(
            sys.modules,
            {"stanza": fake_stanza},
        ):
            result = provider._initialize_pipeline()

        self.assertIsNotNone(result)

        self.assertEqual(captured["lang"], "pl")
        self.assertEqual(captured["package"], "default")
        self.assertEqual(
            captured["processors"],
            "tokenize,mwt,pos,lemma,depparse",
        )
        self.assertEqual(
            captured["tokenize_batch_size"],
            64,
        )
        self.assertIsNone(captured["use_gpu"])
        self.assertIsNone(captured["download_method"])
        self.assertEqual(
            captured["dir"],
            "/tmp/stanza-test",
        )

        print("STANZA PIPELINE RECEIVES CONFIGURATION: OK")

    def test_18_pipeline_does_not_download_models(self) -> None:
        configuration = load_configuration()

        provider = StanzaPolishEngineAdapter().create_provider(
            configuration
        )

        captured: dict = {}

        def fake_pipeline(**kwargs):
            captured.update(kwargs)
            return object()

        fake_stanza = SimpleNamespace(
            Pipeline=fake_pipeline,
        )

        with patch.dict(
            sys.modules,
            {"stanza": fake_stanza},
        ):
            provider._initialize_pipeline()

        self.assertIn("download_method", captured)
        self.assertIsNone(captured["download_method"])

        print("PIPELINE DOES NOT DOWNLOAD MODELS: OK")


class TestFactoryConfigurationApplication(
    unittest.TestCase
):

    def test_19_factory_applies_stanza_configuration(self) -> None:
        configuration = load_configuration(
            options={
                "tokenize_batch_size": 48,
            },
        )

        registry = NLPProviderFactoryRegistry()
        registry.register(StanzaPolishEngineAdapter())

        service = NLPProviderFactoryService(registry)

        result = service.create(configuration)

        self.assertIsInstance(
            result.provider,
            StanzaPolishProvider,
        )

        self.assertEqual(
            result.provider._tokenize_batch_size,
            48,
        )

        self.assertEqual(
            result.configuration_fingerprint,
            configuration.fingerprint_sha256,
        )

        self.assertIsNone(result.provider._pipeline)

        print("FACTORY APPLIES STANZA CONFIGURATION: OK")


def main() -> None:
    print("=" * 60)
    print("STANZA CONFIGURATION APPLICATION TESTS")
    print("=" * 60)

    suite = unittest.TestSuite()

    for test_case in (
        TestStanzaEngineConfigurationApplication,
        TestStanzaPipelineConfigurationApplication,
        TestFactoryConfigurationApplication,
    ):
        suite.addTests(
            unittest.defaultTestLoader.loadTestsFromTestCase(
                test_case
            )
        )

    result = unittest.TextTestRunner(verbosity=0).run(suite)

    if not result.wasSuccessful():
        raise SystemExit(1)

    print()
    print("ALL STANZA CONFIGURATION APPLICATION TESTS PASSED: 19/19")


if __name__ == "__main__":
    main()

