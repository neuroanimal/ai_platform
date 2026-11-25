
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for configurable NLP provenance."""

import unittest

from pydantic import ValidationError

from ai_platform.common.nlp.model.base import (
    ActorType,
)
from ai_platform.common.nlp.provider import (
    NLPProvenanceConfigV2,
    NLPProviderConfigurationLoader,
    StanzaPolishEngineAdapter,
    StanzaPolishProvider,
)
from ai_platform.common.nlp.provider.configuration_loader import (
    ENV_PREFIX,
)


def base_configuration() -> dict:
    return {
        "provider_id": "stanza-pl",
        "engine": {
            "engine_name": "stanza",
        },
        "model": {
            "package": "default",
            "language": "pl",
        },
        "runtime": {
            "device": "cpu",
        },
    }


class TestProvenanceConfiguration(unittest.TestCase):

    def test_01_default_provenance(self) -> None:
        config = NLPProvenanceConfigV2()

        self.assertEqual(
            config.actor_type,
            ActorType.MODEL,
        )
        self.assertIsNone(config.actor_id)
        self.assertIsNone(config.method)
        self.assertIsNone(config.notes)

        print("PROVENANCE DEFAULTS: OK")

    def test_02_configurable_provenance(self) -> None:
        config = NLPProvenanceConfigV2(
            actor_type=ActorType.RULE,
            actor_id="rule-engine-01",
            method="Rule-based morphological analysis",
            notes="Experimental configuration",
        )

        self.assertEqual(config.actor_type, ActorType.RULE)
        self.assertEqual(config.actor_id, "rule-engine-01")
        self.assertEqual(
            config.method,
            "Rule-based morphological analysis",
        )
        self.assertEqual(
            config.notes,
            "Experimental configuration",
        )

        print("CONFIGURABLE PROVENANCE: OK")

    def test_03_blank_method_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            NLPProvenanceConfigV2(method="   ")

        print("BLANK PROVENANCE METHOD REJECTED: OK")

    def test_04_blank_actor_id_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            NLPProvenanceConfigV2(actor_id="   ")

        print("BLANK ACTOR ID REJECTED: OK")

    def test_05_configuration_is_frozen(self) -> None:
        config = NLPProvenanceConfigV2(
            method="Configured method",
        )

        with self.assertRaises(ValidationError):
            config.method = "Changed method"

        print("PROVENANCE CONFIGURATION IMMUTABILITY: OK")

    def test_06_main_configuration_has_provenance(self) -> None:
        config = NLPProviderConfigurationLoader.load(
            base_configuration(),
            environ={},
        )

        self.assertIsInstance(
            config.provenance,
            NLPProvenanceConfigV2,
        )

        self.assertIsNone(config.provenance.method)

        print("MAIN CONFIGURATION PROVENANCE: OK")

    def test_07_provenance_env_override(self) -> None:
        config = NLPProviderConfigurationLoader.load(
            base_configuration(),
            environ={
                f"{ENV_PREFIX}PROVENANCE__ACTOR_TYPE": "rule",
                f"{ENV_PREFIX}PROVENANCE__ACTOR_ID": "rules-01",
                f"{ENV_PREFIX}PROVENANCE__METHOD": "Rule analysis",
                f"{ENV_PREFIX}PROVENANCE__NOTES": "Local rules",
            },
        )

        self.assertEqual(
            config.provenance.actor_type,
            ActorType.RULE,
        )
        self.assertEqual(
            config.provenance.actor_id,
            "rules-01",
        )
        self.assertEqual(
            config.provenance.method,
            "Rule analysis",
        )
        self.assertEqual(
            config.provenance.notes,
            "Local rules",
        )

        print("PROVENANCE ENV OVERRIDES: OK")

    def test_08_provenance_fingerprint_changes(self) -> None:
        first_data = base_configuration()

        second_data = base_configuration()
        second_data["provenance"] = {
            "method": "Method A",
        }

        third_data = base_configuration()
        third_data["provenance"] = {
            "method": "Method B",
        }

        first = NLPProviderConfigurationLoader.load(
            first_data,
            environ={},
        )
        second = NLPProviderConfigurationLoader.load(
            second_data,
            environ={},
        )
        third = NLPProviderConfigurationLoader.load(
            third_data,
            environ={},
        )

        self.assertNotEqual(
            first.fingerprint_sha256,
            second.fingerprint_sha256,
        )
        self.assertNotEqual(
            second.fingerprint_sha256,
            third.fingerprint_sha256,
        )

        print("PROVENANCE FINGERPRINT SENSITIVITY: OK")

    def test_09_provenance_fingerprint_is_deterministic(
        self,
    ) -> None:
        data = base_configuration()
        data["provenance"] = {
            "actor_type": "model",
            "actor_id": "model-01",
            "method": "Configured method",
            "notes": "Test",
        }

        first = NLPProviderConfigurationLoader.load(
            data,
            environ={},
        )
        second = NLPProviderConfigurationLoader.load(
            data,
            environ={},
        )

        self.assertEqual(
            first.fingerprint_sha256,
            second.fingerprint_sha256,
        )

        print("PROVENANCE FINGERPRINT DETERMINISM: OK")

    def test_10_provenance_is_serialized(self) -> None:
        data = base_configuration()
        data["provenance"] = {
            "actor_type": "model",
            "actor_id": "stanza-model-01",
            "method": "Configured Stanza method",
        }

        config = NLPProviderConfigurationLoader.load(
            data,
            environ={},
        )

        serialized = config.to_dict()

        self.assertEqual(
            serialized["provenance"]["actor_type"],
            "model",
        )
        self.assertEqual(
            serialized["provenance"]["actor_id"],
            "stanza-model-01",
        )
        self.assertEqual(
            serialized["provenance"]["method"],
            "Configured Stanza method",
        )

        print("PROVENANCE SERIALIZATION: OK")


class TestStanzaProvenanceIntegration(unittest.TestCase):

    def test_11_factory_passes_provenance(self) -> None:
        data = base_configuration()
        data["provenance"] = {
            "actor_type": "model",
            "actor_id": "stanza-polish-01",
            "method": "Configured Stanza method",
            "notes": "Configured notes",
        }

        configuration = NLPProviderConfigurationLoader.load(
            data,
            environ={},
        )

        provider = StanzaPolishEngineAdapter().create_provider(
            configuration
        )

        self.assertIsInstance(
            provider,
            StanzaPolishProvider,
        )

        self.assertEqual(
            provider._provenance_config.actor_id,
            "stanza-polish-01",
        )

        self.assertEqual(
            provider._provenance_config.method,
            "Configured Stanza method",
        )

        print("FACTORY PROVENANCE MAPPING: OK")

    def test_12_provider_builds_canonical_provenance(
        self,
    ) -> None:
        provenance_config = NLPProvenanceConfigV2(
            actor_type=ActorType.MODEL,
            actor_id="stanza-polish-01",
            method="Configured Stanza method",
            notes="Configured notes",
        )

        provider = StanzaPolishProvider(
            provider_version="test",
            provenance=provenance_config,
        )

        provenance = provider._make_provenance(
            "test",
            {"language": "pl"},
        )

        self.assertEqual(
            provenance.actor_type,
            ActorType.MODEL,
        )
        self.assertEqual(
            provenance.actor_id,
            "stanza-polish-01",
        )
        self.assertEqual(
            provenance.provider_id,
            "stanza-pl",
        )
        self.assertEqual(
            provenance.method,
            "Configured Stanza method",
        )
        self.assertEqual(
            provenance.notes,
            "Configured notes",
        )

        print("CANONICAL PROVENANCE MAPPING: OK")

    def test_13_method_is_not_hardcoded(self) -> None:
        provider = StanzaPolishProvider(
            provider_version="test",
        )

        provenance = provider._make_provenance(
            "test",
            {},
        )

        self.assertIsNone(provenance.method)
        self.assertIsNone(provenance.actor_id)

        print("NO HARDCODED PROVENANCE METHOD: OK")


def main() -> None:
    print("=" * 60)
    print("NLP PROVIDER PROVENANCE CONFIGURATION TESTS")
    print("=" * 60)

    suite = unittest.TestSuite()

    for test_case in (
        TestProvenanceConfiguration,
        TestStanzaProvenanceIntegration,
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
    print("ALL PROVENANCE TESTS PASSED: 13/13")


if __name__ == "__main__":
    main()

