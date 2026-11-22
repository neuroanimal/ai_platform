#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for typed NLP provider configuration models."""

import json
import unittest

from pydantic import ValidationError

from ai_platform.common.nlp.provider.configuration import (
    NLPExecutionDevice,
    NLPModelConfig,
    NLPProviderConfiguration,
    NLPProviderEngineConfig,
    NLPRuntimeConfig,
)


PROVIDER_ID = "stanza-pl"


def build_configuration() -> NLPProviderConfiguration:
    return NLPProviderConfiguration(
        provider_id=PROVIDER_ID,
        engine=NLPProviderEngineConfig(
            engine_name="stanza",
            parameters={
                "processors": "tokenize,mwt,pos,lemma,depparse",
                "download_method": None,
            },
        ),
        model=NLPModelConfig(
            model_id="pl-default-pdb",
            package="default",
            revision="pdb",
            language_code="pl",
        ),
        runtime=NLPRuntimeConfig(
            device=NLPExecutionDevice.CPU,
            threads=4,
            memory_limit_mb=4096,
        ),
    )


class TestNLPProviderConfiguration(unittest.TestCase):

    def test_01_engine_configuration_creation(self) -> None:
        engine = NLPProviderEngineConfig(
            engine_name="stanza",
            parameters={"processors": "tokenize,pos"},
        )

        self.assertEqual(engine.engine_name, "stanza")
        self.assertEqual(
            engine.parameters["processors"],
            "tokenize,pos",
        )

        print("ENGINE CONFIGURATION CREATION: OK")

    def test_02_engine_name_must_not_be_blank(self) -> None:
        with self.assertRaises(ValidationError):
            NLPProviderEngineConfig(engine_name="   ")

        print("ENGINE NAME VALIDATION: OK")

    def test_03_engine_parameters_default(self) -> None:
        engine = NLPProviderEngineConfig(
            engine_name="test-engine"
        )

        self.assertEqual(engine.parameters, {})

        print("ENGINE PARAMETERS DEFAULT: OK")

    def test_04_model_configuration_creation(self) -> None:
        model = NLPModelConfig(
            model_id="pl-default-pdb",
            package="default",
            revision="pdb",
            language_code="pl",
        )

        self.assertEqual(model.model_id, "pl-default-pdb")
        self.assertEqual(model.package, "default")
        self.assertEqual(model.revision, "pdb")
        self.assertEqual(model.language_code, "pl")

        print("MODEL CONFIGURATION CREATION: OK")

    def test_05_model_id_must_not_be_blank(self) -> None:
        with self.assertRaises(ValidationError):
            NLPModelConfig(model_id=" ")

        print("MODEL ID VALIDATION: OK")

    def test_06_optional_model_fields(self) -> None:
        model = NLPModelConfig(model_id="generic-model")

        self.assertIsNone(model.package)
        self.assertIsNone(model.revision)
        self.assertIsNone(model.language_code)
        self.assertEqual(model.parameters, {})

        print("OPTIONAL MODEL FIELDS: OK")

    def test_07_optional_model_identifiers_must_not_be_blank(
        self,
    ) -> None:
        invalid_values = [
            {"package": " "},
            {"revision": " "},
            {"language_code": " "},
        ]

        for values in invalid_values:
            with self.subTest(values=values):
                with self.assertRaises(ValidationError):
                    NLPModelConfig(
                        model_id="generic-model",
                        **values,
                    )

        print("OPTIONAL MODEL IDENTIFIER VALIDATION: OK")

    def test_08_runtime_configuration_defaults(self) -> None:
        runtime = NLPRuntimeConfig()

        self.assertEqual(runtime.device, NLPExecutionDevice.CPU)
        self.assertIsNone(runtime.threads)
        self.assertIsNone(runtime.memory_limit_mb)
        self.assertFalse(runtime.allow_device_fallback)

        print("RUNTIME CONFIGURATION DEFAULTS: OK")

    def test_09_runtime_device_selection(self) -> None:
        for device in NLPExecutionDevice:
            with self.subTest(device=device):
                runtime = NLPRuntimeConfig(device=device)
                self.assertEqual(runtime.device, device)

        print("RUNTIME DEVICE SELECTION: OK")

    def test_10_runtime_resource_limits(self) -> None:
        runtime = NLPRuntimeConfig(
            device=NLPExecutionDevice.CUDA,
            threads=8,
            memory_limit_mb=8192,
            allow_device_fallback=True,
        )

        self.assertEqual(runtime.threads, 8)
        self.assertEqual(runtime.memory_limit_mb, 8192)
        self.assertTrue(runtime.allow_device_fallback)

        print("RUNTIME RESOURCE LIMITS: OK")

    def test_11_runtime_rejects_invalid_resource_limits(self) -> None:
        invalid_values = [
            {"threads": 0},
            {"threads": -1},
            {"memory_limit_mb": 0},
            {"memory_limit_mb": -1024},
        ]

        for values in invalid_values:
            with self.subTest(values=values):
                with self.assertRaises(ValidationError):
                    NLPRuntimeConfig(**values)

        print("RUNTIME RESOURCE VALIDATION: OK")

    def test_12_complete_configuration_creation(self) -> None:
        configuration = build_configuration()

        self.assertEqual(configuration.provider_id, PROVIDER_ID)
        self.assertEqual(configuration.engine.engine_name, "stanza")
        self.assertEqual(configuration.model.model_id, "pl-default-pdb")
        self.assertEqual(
            configuration.runtime.device,
            NLPExecutionDevice.CPU,
        )

        print("COMPLETE CONFIGURATION CREATION: OK")

    def test_13_model_configuration_is_optional(self) -> None:
        configuration = NLPProviderConfiguration(
            provider_id="rule-based-pl",
            engine=NLPProviderEngineConfig(
                engine_name="native-rules"
            ),
        )

        self.assertIsNone(configuration.model)
        self.assertEqual(
            configuration.runtime.device,
            NLPExecutionDevice.CPU,
        )

        print("OPTIONAL MODEL CONFIGURATION: OK")

    def test_14_provider_id_must_not_be_blank(self) -> None:
        with self.assertRaises(ValidationError):
            NLPProviderConfiguration(
                provider_id=" ",
                engine=NLPProviderEngineConfig(
                    engine_name="test-engine"
                ),
            )

        print("PROVIDER ID VALIDATION: OK")

    def test_15_json_compatible_serialization(self) -> None:
        configuration = build_configuration()

        serialized = configuration.to_dict()

        self.assertEqual(serialized["provider_id"], PROVIDER_ID)
        self.assertEqual(
            serialized["runtime"]["device"],
            "cpu",
        )
        self.assertEqual(
            serialized["engine"]["engine_name"],
            "stanza",
        )
        self.assertEqual(
            serialized["model"]["language_code"],
            "pl",
        )

        # The result must be directly JSON serializable.
        json_text = json.dumps(serialized)
        restored = json.loads(json_text)

        self.assertEqual(restored, serialized)

        print("JSON-COMPATIBLE SERIALIZATION: OK")

    def test_16_optional_fields_are_omitted(self) -> None:
        configuration = NLPProviderConfiguration(
            provider_id="rule-based-pl",
            engine=NLPProviderEngineConfig(
                engine_name="native-rules"
            ),
        )

        serialized = configuration.to_dict()

        self.assertNotIn("model", serialized)
        self.assertNotIn("threads", serialized["runtime"])
        self.assertNotIn(
            "memory_limit_mb",
            serialized["runtime"],
        )

        print("OPTIONAL FIELD SERIALIZATION: OK")

    def test_17_configuration_round_trip(self) -> None:
        original = build_configuration()

        serialized = original.to_dict()

        restored = NLPProviderConfiguration.model_validate(
            serialized
        )

        self.assertEqual(
            restored.model_dump(),
            original.model_dump(),
        )

        print("CONFIGURATION ROUND-TRIP: OK")

    def test_18_unknown_fields_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            NLPProviderEngineConfig(
                engine_name="stanza",
                unknown_setting=True,
            )

        print("STRICT CONFIGURATION SCHEMA: OK")

    def test_19_json_schema_generation(self) -> None:
        schema = NLPProviderConfiguration.model_json_schema()

        self.assertIn("properties", schema)

        properties = schema["properties"]

        self.assertIn("provider_id", properties)
        self.assertIn("engine", properties)
        self.assertIn("model", properties)
        self.assertIn("runtime", properties)

        print("CONFIGURATION JSON SCHEMA: OK")

    def test_20_public_types_are_distinct(self) -> None:
        self.assertIsNot(
            NLPProviderEngineConfig,
            NLPModelConfig,
        )
        self.assertIsNot(
            NLPModelConfig,
            NLPRuntimeConfig,
        )

        print("CONFIGURATION LAYER SEPARATION: OK")


def main() -> None:
    print("=" * 60)
    print("NLP PROVIDER CONFIGURATION TESTS")
    print("=" * 60)

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        TestNLPProviderConfiguration
    )

    result = unittest.TextTestRunner(verbosity=0).run(suite)

    if not result.wasSuccessful():
        raise SystemExit(1)

    print()
    print(
        "ALL NLP PROVIDER CONFIGURATION TESTS PASSED: 20/20"
    )


if __name__ == "__main__":
    main()

