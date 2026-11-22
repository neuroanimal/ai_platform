
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Unit and contract tests for the Stanza Polish provider."""

import unittest
from types import SimpleNamespace

from ai_platform.common.nlp.model import (
    AnalysisLayer,
    NLPAnalysis,
    NLPDocument,
    SourceDescriptor,
    TextRepresentation,
    TextVersion,
)
from ai_platform.common.nlp.provider import NLPProviderRequest
from ai_platform.common.nlp.provider.errors import (
    NLPProviderCapabilityError,
    NLPProviderConfigurationError,
)
from ai_platform.common.nlp.provider.stanza_provider import (
    PROVIDER_ID,
    StanzaPolishProvider,
)
from ai_platform.common.nlp.validation.graph_validator import (
    validate_graph_consistency,
)
from ai_platform.common.nlp.validation.structural_validator import (
    validate_document_analysis,
)


def build_document(text: str) -> NLPDocument:
    return NLPDocument(
        document_id="document-001",
        source=SourceDescriptor(
            source_id="source-001",
            source_type="text",
        ),
        text_versions=[
            TextVersion(
                text_version_id="version-001",
                representation=TextRepresentation.DIPLOMATIC,
                text=text,
            )
        ],
        primary_text_version_id="version-001",
    )


def build_request(
    text: str,
    *,
    layers: list[AnalysisLayer] | None = None,
    allow_partial: bool = True,
    include_provider_native: bool = True,
    configuration: dict | None = None,
) -> NLPProviderRequest:
    return NLPProviderRequest(
        request_id="request-001",
        document=build_document(text),
        text_version_id="version-001",
        requested_layers=layers or [
            AnalysisLayer.SEGMENTATION,
            AnalysisLayer.MORPHOLOGY,
            AnalysisLayer.DEPENDENCY_SYNTAX,
        ],
        allow_partial=allow_partial,
        include_provider_native=include_provider_native,
        configuration=configuration or {},
    )


class FakeWord:

    def __init__(
        self,
        *,
        word_id: int,
        text: str,
        upos: str,
        head: int,
        deprel: str,
        lemma: str | None = None,
        xpos: str | None = None,
        feats: str | None = None,
        start_char: int | None = None,
        end_char: int | None = None,
    ) -> None:
        self.id = word_id
        self.text = text
        self.upos = upos
        self.head = head
        self.deprel = deprel
        self.lemma = lemma
        self.xpos = xpos
        self.feats = feats
        self.misc = None
        self.start_char = start_char
        self.end_char = end_char
        self.parent = None


class FakeToken:

    def __init__(
        self,
        *,
        token_id: tuple[int, ...],
        text: str,
        start_char: int,
        end_char: int,
        words: list[FakeWord],
    ) -> None:
        self.id = token_id
        self.text = text
        self.start_char = start_char
        self.end_char = end_char
        self.words = words

        for word in words:
            word.parent = self


class FakePipeline:

    def __init__(self, stanza_document) -> None:
        self.stanza_document = stanza_document
        self.calls = 0

    def __call__(self, text: str):
        self.calls += 1
        return self.stanza_document


def make_standard_pipeline() -> FakePipeline:
    text = "Ala ma kota."

    specifications = [
        {
            "surface": "Ala",
            "start": 0,
            "end": 3,
            "words": [
                FakeWord(
                    word_id=1,
                    text="Ala",
                    lemma="Ala",
                    upos="PROPN",
                    xpos="subst:sg:nom:f",
                    feats="Case=Nom|Gender=Fem|Number=Sing",
                    head=2,
                    deprel="nsubj",
                    start_char=0,
                    end_char=3,
                )
            ],
        },
        {
            "surface": "ma",
            "start": 4,
            "end": 6,
            "words": [
                FakeWord(
                    word_id=2,
                    text="ma",
                    lemma="mieć",
                    upos="VERB",
                    xpos="fin:sg:ter:imperf",
                    feats="Aspect=Imp|Mood=Ind|Person=3|Tense=Pres",
                    head=0,
                    deprel="root",
                    start_char=4,
                    end_char=6,
                )
            ],
        },
        {
            "surface": "kota",
            "start": 7,
            "end": 11,
            "words": [
                FakeWord(
                    word_id=3,
                    text="kota",
                    lemma="kot",
                    upos="NOUN",
                    xpos="subst:sg:acc:m2",
                    feats="Case=Acc|Gender=Masc|Number=Sing",
                    head=2,
                    deprel="obj",
                    start_char=7,
                    end_char=11,
                )
            ],
        },
        {
            "surface": ".",
            "start": 11,
            "end": 12,
            "words": [
                FakeWord(
                    word_id=4,
                    text=".",
                    lemma=".",
                    upos="PUNCT",
                    head=2,
                    deprel="punct",
                    start_char=11,
                    end_char=12,
                )
            ],
        },
    ]

    tokens = [
        FakeToken(
            token_id=(index,),
            text=item["surface"],
            start_char=item["start"],
            end_char=item["end"],
            words=item["words"],
        )
        for index, item in enumerate(specifications, start=1)
    ]

    words = [
        word
        for token in tokens
        for word in token.words
    ]

    sentence = SimpleNamespace(
        tokens=tokens,
        words=words,
    )

    return FakePipeline(
        SimpleNamespace(sentences=[sentence])
    )


def make_mwt_pipeline() -> FakePipeline:
    text = "nań."

    mwt_words = [
        FakeWord(
            word_id=1,
            text="na",
            lemma="na",
            upos="ADP",
            head=2,
            deprel="case",
        ),
        FakeWord(
            word_id=2,
            text="ń",
            lemma="on",
            upos="PRON",
            feats="Case=Acc|Gender=Masc|Number=Sing",
            head=0,
            deprel="root",
        ),
    ]

    punctuation_word = FakeWord(
        word_id=3,
        text=".",
        lemma=".",
        upos="PUNCT",
        head=2,
        deprel="punct",
        start_char=3,
        end_char=4,
    )

    tokens = [
        FakeToken(
            token_id=(1, 2),
            text="nań",
            start_char=0,
            end_char=3,
            words=mwt_words,
        ),
        FakeToken(
            token_id=(3,),
            text=".",
            start_char=3,
            end_char=4,
            words=[punctuation_word],
        ),
    ]

    sentence = SimpleNamespace(
        tokens=tokens,
        words=mwt_words + [punctuation_word],
    )

    return FakePipeline(
        SimpleNamespace(sentences=[sentence])
    )


class TestStanzaPolishProvider(unittest.IsolatedAsyncioTestCase):

    async def test_01_provider_capabilities(self) -> None:
        provider = StanzaPolishProvider(
            pipeline=make_standard_pipeline(),
            provider_version="test",
        )

        self.assertEqual(provider.capabilities.provider_id, PROVIDER_ID)
        self.assertIn("pl", provider.capabilities.supported_language_codes)

        self.assertEqual(
            set(provider.capabilities.supported_layers),
            {
                AnalysisLayer.SEGMENTATION,
                AnalysisLayer.MORPHOLOGY,
                AnalysisLayer.DEPENDENCY_SYNTAX,
            },
        )

        print("PROVIDER CAPABILITIES: OK")

    async def test_02_standard_mapping(self) -> None:
        pipeline = make_standard_pipeline()

        provider = StanzaPolishProvider(
            pipeline=pipeline,
            provider_version="test",
        )

        request = build_request("Ala ma kota.")
        response = await provider.analyze(request)

        analysis = response.analysis

        self.assertEqual(response.provider_id, PROVIDER_ID)
        self.assertEqual(response.request_id, request.request_id)

        self.assertEqual(len(analysis.sentences), 1)
        self.assertEqual(len(analysis.tokens), 4)
        self.assertEqual(len(analysis.dependencies), 3)

        self.assertEqual(
            analysis.completed_layers,
            [
                AnalysisLayer.SEGMENTATION,
                AnalysisLayer.MORPHOLOGY,
                AnalysisLayer.DEPENDENCY_SYNTAX,
            ],
        )

        self.assertEqual(analysis.tokens[0].text, "Ala")
        self.assertEqual(analysis.tokens[0].lemma, "Ala")
        self.assertEqual(analysis.tokens[0].upos.value, "proper_noun")

        self.assertEqual(
            analysis.tokens[0].morphology[0].category,
            "Case",
        )

        self.assertEqual(
            analysis.tokens[0].morphology[0].value,
            "Nom",
        )

        self.assertEqual(
            analysis.sentences[0].text,
            "Ala ma kota.",
        )

        self.assertEqual(pipeline.calls, 1)

        print("STANDARD STANZA MAPPING: OK")

    async def test_03_dependency_root_preservation(self) -> None:
        provider = StanzaPolishProvider(
            pipeline=make_standard_pipeline(),
            provider_version="test",
        )

        response = await provider.analyze(
            build_request("Ala ma kota.")
        )

        analysis = response.analysis
        roots = analysis.metadata["dependency_roots"]

        self.assertEqual(len(roots), 1)
        self.assertEqual(roots[0]["relation"], "root")

        self.assertFalse(
            any(
                relation.head_token_id == "0"
                for relation in analysis.dependencies
            )
        )

        print("DEPENDENCY ROOT PRESERVATION: OK")

    async def test_04_mwt_surface_and_word_forms(self) -> None:
        provider = StanzaPolishProvider(
            pipeline=make_mwt_pipeline(),
            provider_version="test",
        )

        response = await provider.analyze(
            build_request("nań.")
        )

        analysis = response.analysis

        self.assertEqual(len(analysis.tokens), 3)

        first, second, punctuation = analysis.tokens

        self.assertEqual(first.text, "nań")
        self.assertEqual(second.text, "nań")

        self.assertEqual(first.normalized_form, "na")
        self.assertEqual(second.normalized_form, "ń")

        self.assertEqual(
            first.multiword_token_id,
            second.multiword_token_id,
        )

        self.assertEqual(
            first.anchor.span,
            second.anchor.span,
        )

        self.assertEqual(
            first.anchor.quoted_text,
            "nań",
        )

        self.assertEqual(punctuation.text, ".")

        print("MULTI-WORD TOKEN PRESERVATION: OK")

    async def test_05_structural_and_graph_validation(self) -> None:
        document = build_document("Ala ma kota.")

        provider = StanzaPolishProvider(
            pipeline=make_standard_pipeline(),
            provider_version="test",
        )

        response = await provider.analyze(
            build_request("Ala ma kota.")
        )

        structural = validate_document_analysis(
            document,
            response.analysis,
        )

        graph = validate_graph_consistency(
            response.analysis,
        )

        self.assertTrue(
            structural.is_valid,
            structural.to_dict(),
        )

        self.assertTrue(
            graph.is_valid,
            graph.to_dict(),
        )

        print("STRUCTURAL VALIDATION: OK")
        print("GRAPH VALIDATION: OK")

    async def test_06_partial_unsupported_layer(self) -> None:
        pipeline = make_standard_pipeline()

        provider = StanzaPolishProvider(
            pipeline=pipeline,
            provider_version="test",
        )

        request = build_request(
            "Ala ma kota.",
            layers=[
                AnalysisLayer.SEGMENTATION,
                AnalysisLayer.SEMANTICS,
            ],
            allow_partial=True,
        )

        response = await provider.analyze(request)

        self.assertEqual(
            response.analysis.completed_layers,
            [AnalysisLayer.SEGMENTATION],
        )

        self.assertEqual(
            response.analysis.unavailable_layers,
            [AnalysisLayer.SEMANTICS],
        )

        self.assertEqual(
            response.diagnostics[0].code,
            "layer_not_supported",
        )

        print("PARTIAL UNSUPPORTED LAYER: OK")

    async def test_07_unsupported_layer_rejected(self) -> None:
        provider = StanzaPolishProvider(
            pipeline=make_standard_pipeline(),
            provider_version="test",
        )

        request = build_request(
            "Ala ma kota.",
            layers=[
                AnalysisLayer.SEGMENTATION,
                AnalysisLayer.SEMANTICS,
            ],
            allow_partial=False,
        )

        with self.assertRaises(NLPProviderCapabilityError):
            await provider.analyze(request)

        print("UNSUPPORTED LAYER REJECTION: OK")

    async def test_08_request_configuration_rejected(self) -> None:
        provider = StanzaPolishProvider(
            pipeline=make_standard_pipeline(),
            provider_version="test",
        )

        request = build_request(
            "Ala ma kota.",
            configuration={"unknown_option": True},
        )

        with self.assertRaises(NLPProviderConfigurationError):
            await provider.analyze(request)

        print("UNSUPPORTED CONFIGURATION REJECTION: OK")

    async def test_09_provider_native_can_be_omitted(self) -> None:
        provider = StanzaPolishProvider(
            pipeline=make_standard_pipeline(),
            provider_version="test",
        )

        request = build_request(
            "Ala ma kota.",
            include_provider_native=False,
        )

        response = await provider.analyze(request)

        self.assertTrue(
            all(
                not token.provider_native
                for token in response.analysis.tokens
            )
        )

        print("OPTIONAL PROVIDER NATIVE DATA: OK")

    async def test_10_partial_without_supported_layers(self) -> None:
        pipeline = make_standard_pipeline()

        provider = StanzaPolishProvider(
            pipeline=pipeline,
            provider_version="test",
        )

        request = build_request(
            "Ala ma kota.",
            layers=[AnalysisLayer.SEMANTICS],
            allow_partial=True,
        )

        response = await provider.analyze(request)

        self.assertEqual(pipeline.calls, 0)
        self.assertEqual(response.analysis.tokens, [])
        self.assertEqual(response.analysis.sentences, [])
        self.assertEqual(
            response.analysis.unavailable_layers,
            [AnalysisLayer.SEMANTICS],
        )

        print("NO-OP FOR UNSUPPORTED-ONLY REQUEST: OK")


def main() -> None:
    print("=" * 60)
    print("STANZA POLISH PROVIDER TESTS")
    print("=" * 60)

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        TestStanzaPolishProvider
    )

    result = unittest.TextTestRunner(verbosity=0).run(suite)

    if not result.wasSuccessful():
        raise SystemExit(1)

    print()
    print("ALL STANZA PROVIDER TESTS PASSED: 10/10")


if __name__ == "__main__":
    main()

