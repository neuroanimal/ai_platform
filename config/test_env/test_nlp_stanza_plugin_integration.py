
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""End-to-end integration test: Stanza provider and PluginRegistry."""

import asyncio
import unittest
from types import SimpleNamespace

from ai_platform.common.core.registry.plugin_registry import PluginRegistry
from ai_platform.common.nlp.model.analysis import AnalysisLayer
from ai_platform.common.nlp.model.document import (
    NLPDocument,
    SourceDescriptor,
    TextRepresentation,
    TextVersion,
)
from ai_platform.common.nlp.provider import (
    NLPProvider,
    NLPProviderRequest,
    StanzaPolishProvider,
)
from ai_platform.common.nlp.provider.plugin import NLPProviderPlugin


class FakeWord:

    def __init__(
        self,
        word_id: int,
        text: str,
        upos: str,
        lemma: str,
        head: int,
        deprel: str,
        start: int,
        end: int,
    ) -> None:
        self.id = word_id
        self.text = text
        self.upos = upos
        self.xpos = None
        self.lemma = lemma
        self.feats = None
        self.head = head
        self.deprel = deprel
        self.misc = None
        self.start_char = start
        self.end_char = end


class FakeToken:

    def __init__(
        self,
        token_id: int,
        text: str,
        start: int,
        end: int,
        word: FakeWord,
    ) -> None:
        self.id = (token_id,)
        self.text = text
        self.start_char = start
        self.end_char = end
        self.words = [word]


class FakePipeline:

    def __init__(self) -> None:
        specifications = [
            (1, "Ala", "PROPN", "Ala", 2, "nsubj", 0, 3),
            (2, "ma", "VERB", "mieć", 0, "root", 4, 6),
            (3, "kota", "NOUN", "kot", 2, "obj", 7, 11),
            (4, ".", "PUNCT", ".", 2, "punct", 11, 12),
        ]

        tokens = []

        for item in specifications:
            word = FakeWord(*item)

            tokens.append(
                FakeToken(
                    token_id=item[0],
                    text=item[1],
                    start=item[6],
                    end=item[7],
                    word=word,
                )
            )

        words = [
            token.words[0]
            for token in tokens
        ]

        sentence = SimpleNamespace(
            tokens=tokens,
            words=words,
        )

        self.document = SimpleNamespace(
            sentences=[sentence],
        )

        self.calls = 0

    def __call__(self, text: str):
        self.calls += 1

        if text != "Ala ma kota.":
            raise ValueError("Unexpected test input.")

        return self.document


def build_request() -> NLPProviderRequest:
    document = NLPDocument(
        document_id="stanza-registry-document",
        source=SourceDescriptor(
            source_id="stanza-registry-source",
            source_type="text",
        ),
        text_versions=[
            TextVersion(
                text_version_id="stanza-registry-version",
                representation=TextRepresentation.DIPLOMATIC,
                text="Ala ma kota.",
            )
        ],
        primary_text_version_id="stanza-registry-version",
    )

    return NLPProviderRequest(
        request_id="stanza-registry-request",
        document=document,
        text_version_id="stanza-registry-version",
        requested_layers=[
            AnalysisLayer.SEGMENTATION,
            AnalysisLayer.MORPHOLOGY,
            AnalysisLayer.DEPENDENCY_SYNTAX,
        ],
        allow_partial=False,
        include_provider_native=True,
    )


class TestStanzaPluginIntegration(unittest.IsolatedAsyncioTestCase):

    async def test_01_registered_provider_executes_analysis(self) -> None:
        pipeline = FakePipeline()

        provider = StanzaPolishProvider(
            pipeline=pipeline,
            provider_version="integration-test",
        )

        self.assertIsInstance(provider, NLPProvider)

        plugin = NLPProviderPlugin(provider)

        registry = PluginRegistry()

        self.assertEqual(registry.list(), {})

        plugin.register(registry)

        registry_key = "nlp:stanza-pl"

        self.assertIn(registry_key, registry.list())

        registered_provider = registry.get(registry_key)

        self.assertIs(registered_provider, provider)
        self.assertIsInstance(registered_provider, NLPProvider)

        request = build_request()

        response = await registered_provider.analyze(request)

        self.assertEqual(
            response.request_id,
            request.request_id,
        )

        self.assertEqual(
            response.provider_id,
            "stanza-pl",
        )

        self.assertEqual(
            response.analysis.document_id,
            request.document.document_id,
        )

        self.assertEqual(
            len(response.analysis.sentences),
            1,
        )

        self.assertEqual(
            len(response.analysis.tokens),
            4,
        )

        self.assertEqual(
            len(response.analysis.dependencies),
            3,
        )

        self.assertEqual(
            set(response.analysis.completed_layers),
            set(request.requested_layers),
        )

        self.assertEqual(
            response.analysis.unavailable_layers,
            [],
        )

        self.assertEqual(pipeline.calls, 1)

        print("STANZA PROVIDER REGISTRATION: OK")
        print("PROVIDER RETRIEVAL FROM REGISTRY: OK")
        print("ANALYSIS THROUGH REGISTERED PROVIDER: OK")
        print("CANONICAL NLP RESPONSE: OK")


def main() -> None:
    print("=" * 60)
    print("STANZA PLUGIN END-TO-END INTEGRATION TEST")
    print("=" * 60)

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        TestStanzaPluginIntegration
    )

    result = unittest.TextTestRunner(verbosity=0).run(suite)

    if not result.wasSuccessful():
        raise SystemExit(1)

    print()
    print("ALL STANZA PLUGIN INTEGRATION TESTS PASSED: 1/1")


if __name__ == "__main__":
    main()

