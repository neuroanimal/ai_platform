
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Live integration test for the real Polish Stanza model."""

import asyncio

from ai_platform.common.core.registry.plugin_registry import PluginRegistry
from ai_platform.common.nlp.model import (
    AnalysisLayer,
    NLPDocument,
    SourceDescriptor,
    TextRepresentation,
    TextVersion,
)
from ai_platform.common.nlp.provider import NLPProviderRequest
from ai_platform.common.nlp.provider.plugin import NLPProviderPlugin
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


TEXT = (
    "Ala ma kota. "
    "Kot śpi na kanapie. "
    "Czy Ala lubi swojego kota?"
)


def build_document() -> NLPDocument:
    return NLPDocument(
        document_id="stanza-live-document-001",
        source=SourceDescriptor(
            source_id="stanza-live-source-001",
            source_type="text",
            title="Stanza Polish live test",
        ),
        text_versions=[
            TextVersion(
                text_version_id="stanza-live-version-001",
                representation=TextRepresentation.DIPLOMATIC,
                text=TEXT,
            )
        ],
        primary_text_version_id="stanza-live-version-001",
        document_language=None,
    )


async def main() -> None:
    print("=" * 60)
    print("STANZA POLISH LIVE INTEGRATION TEST")
    print("=" * 60)

    provider = StanzaPolishProvider(
        use_gpu=False,
    )

    print(f"PROVIDER: {provider.capabilities.provider_id}")
    print(f"VERSION: {provider.capabilities.provider_version}")
    print(f"LAYERS: {[x.value for x in provider.capabilities.supported_layers]}")

    # Explicit registration in the central plugin registry.
    registry = PluginRegistry()
    plugin = NLPProviderPlugin(provider)
    plugin.register(registry)

    registered_provider = registry.get(
        f"nlp:{PROVIDER_ID}"
    )

    assert registered_provider is provider

    print("CENTRAL REGISTRY INTEGRATION: OK")

    document = build_document()

    request = NLPProviderRequest(
        request_id="stanza-live-request-001",
        document=document,
        text_version_id="stanza-live-version-001",
        requested_layers=[
            AnalysisLayer.SEGMENTATION,
            AnalysisLayer.MORPHOLOGY,
            AnalysisLayer.DEPENDENCY_SYNTAX,
        ],
        allow_partial=False,
        include_provider_native=True,
    )

    # Since the provider factory (78d22f1) real pipelines are created only by
    # initialize() - normally called by NLPProviderLifecycle; this test calls
    # the provider directly, so it initializes it explicitly.
    provider.initialize()

    response = await provider.analyze(request)
    analysis = response.analysis

    assert response.provider_id == PROVIDER_ID
    assert response.request_id == request.request_id

    assert analysis.document_id == document.document_id
    assert analysis.text_version_id == request.text_version_id

    assert set(analysis.completed_layers) == set(
        request.requested_layers
    )

    assert not analysis.unavailable_layers

    print("REAL MODEL INFERENCE: OK")
    print(f"SENTENCES: {len(analysis.sentences)}")
    print(f"TOKENS: {len(analysis.tokens)}")
    print(f"DEPENDENCIES: {len(analysis.dependencies)}")

    structural = validate_document_analysis(
        document,
        analysis,
    )

    graph = validate_graph_consistency(
        analysis,
    )

    print(
        "STRUCTURAL VALIDATION:",
        "OK" if structural.is_valid else "FAILED",
    )

    print(
        "GRAPH VALIDATION:",
        "OK" if graph.is_valid else "FAILED",
    )

    if not structural.is_valid:
        print(structural.to_dict())
        raise SystemExit(1)

    if not graph.is_valid:
        print(graph.to_dict())
        raise SystemExit(1)

    print()
    print("SAMPLE ANNOTATIONS:")

    for token in analysis.tokens[:20]:
        print(
            f"{token.text!r:16} "
            f"lemma={str(token.lemma):12} "
            f"upos={str(token.upos):16} "
            f"xpos={str(token.xpos):16}"
        )

    print()
    print("SAMPLE DEPENDENCIES:")

    token_by_id = {
        token.token_id: token
        for token in analysis.tokens
    }

    for relation in analysis.dependencies[:20]:
        head = token_by_id[relation.head_token_id]
        dependent = token_by_id[relation.dependent_token_id]

        print(
            f"{head.text!r:12} "
            f"--{relation.relation}--> "
            f"{dependent.text!r}"
        )

    print()
    print("ALL STANZA LIVE INTEGRATION CHECKS PASSED")


if __name__ == "__main__":
    asyncio.run(main())

