#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Stanza provider for Polish NLP.

The provider maps Stanza annotations into the canonical NLP model.

Supported canonical layers:
    - SEGMENTATION
    - MORPHOLOGY
    - DEPENDENCY_SYNTAX

Important MWT policy:
    Stanza distinguishes surface Tokens from syntactic Words.
    Canonical Token.text always contains text actually present in the
    source document, so that its TextAnchor remains verifiable.

    For expanded MWT words, the original surface form is stored in
    Token.text and the syntactic word form in Token.normalized_form
    and provider_native.

    Multiple syntactic words originating from one surface token share
    the same source span and multiword_token_id.

Root dependencies:
    Stanza uses head=0 for the artificial dependency root.
    The canonical DependencyRelation requires a real head token.
    Root information is therefore retained in provider_native and
    analysis.metadata; no artificial token or fake edge is created.

No automatic model download is performed.
"""

# pylint: disable=too-many-lines  # one engine adapter: mapping + 8D execution contract

from __future__ import annotations

import asyncio
import importlib.metadata
import threading
import time
import unicodedata
from pathlib import Path
from typing import Any

from ai_platform.common.core.execution.errors import ExecutionError

from ..model.analysis import (
    AnalysisLayer,
    AnalysisStatus,
    NLPAnalysis,
    ProviderMetadata,
)
from ..model.base import (
    ActorType,
    OffsetUnit,
    Provenance,
    TextAnchor,
    TextSpan,
)
from ..model.document import NLPDocument
from ..model.linguistic import (
    DependencyLayer,
    DependencyRelation,
    MorphologicalFeature,
    PartOfSpeech,
    Token,
)
from ..model.segmentation import Sentence
from .capabilities import ProviderCapabilities
from .errors import (
    NLPProviderCapabilityError,
    NLPProviderConfigurationError,
    NLPProviderExecutionError,
    NLPProviderInputError,
    NLPProviderOutputError,
)
from .protocol import NLPProvider
from .request import NLPProviderRequest
from .response import (
    NLPProviderResponse,
    ProviderDiagnostic,
    ProviderDiagnosticSeverity,
)
from .validation.conformance import (
    validate_provider_request,
    validate_provider_response,
)
from .provenance_configuration import NLPProvenanceConfigV2


PROVIDER_ID = "stanza-pl"

SUPPORTED_LAYERS = [
    AnalysisLayer.SEGMENTATION,
    AnalysisLayer.MORPHOLOGY,
    AnalysisLayer.DEPENDENCY_SYNTAX,
]

PROCESSORS = "tokenize,mwt,pos,lemma,depparse"

UPOS_MAPPING = {
    "NOUN": PartOfSpeech.NOUN,
    "PROPN": PartOfSpeech.PROPER_NOUN,
    "VERB": PartOfSpeech.VERB,
    "AUX": PartOfSpeech.AUXILIARY,
    "ADJ": PartOfSpeech.ADJECTIVE,
    "ADV": PartOfSpeech.ADVERB,
    "PRON": PartOfSpeech.PRONOUN,
    "DET": PartOfSpeech.DETERMINER,
    "NUM": PartOfSpeech.NUMERAL,
    "ADP": PartOfSpeech.ADPOSITION,
    "CCONJ": PartOfSpeech.CONJUNCTION,
    "SCONJ": PartOfSpeech.CONJUNCTION,
    "PART": PartOfSpeech.PARTICLE,
    "INTJ": PartOfSpeech.INTERJECTION,
    "PUNCT": PartOfSpeech.OTHER,
    "SYM": PartOfSpeech.OTHER,
    "X": PartOfSpeech.OTHER,
}


class StanzaPolishProvider(NLPProvider):
    """Polish NLP provider backed by the Stanza neural pipeline."""

    def __init__(
        self,
        *,
        model_dir: str | Path | None = None,
        package: str = "default",
        use_gpu: bool | None = False,
        pipeline: Any | None = None,
        provider_version: str | None = None,
        provenance: NLPProvenanceConfigV2 | None = None,
        processors: str = PROCESSORS,
        tokenize_batch_size: int = 32,
        device: str | None = None,
    ) -> None:
        """
        Initialize the provider.

        Args:
            model_dir:
                Optional Stanza resources directory.
            package:
                Package to use, otherwise 'default'.
            use_gpu:
                Whether Stanza should use a GPU.
            pipeline:
                Optional injected pipeline, primarily for tests.
                When omitted, the real Stanza pipeline is initialized.
            provider_version:
                Optional explicit version override.
        """
        self._model_dir = (
            Path(model_dir).expanduser()
            if model_dir is not None
            else None
        )
        if not isinstance(package, str) or not package.strip():
            raise ValueError("package must be a non-empty string.")

        if use_gpu is not None and not isinstance(use_gpu, bool):
            raise TypeError("use_gpu must be bool or None.")

        if not isinstance(processors, str) or not processors.strip():
            raise ValueError(
                "processors must be a non-empty string."
            )

        if (
            isinstance(tokenize_batch_size, bool)
            or not isinstance(tokenize_batch_size, int)
            or tokenize_batch_size <= 0
        ):
            raise ValueError(
                "tokenize_batch_size must be a positive integer."
            )

        self._package = package
        self._use_gpu = use_gpu
        self._processors = processors
        self._tokenize_batch_size = tokenize_batch_size

        self._device = (
            device
            if device is not None
            else (
                "auto"
                if use_gpu is None
                else ("cuda" if use_gpu else "cpu")
            )
        )

        self._lock = threading.Lock()

        # Stage 8D: shared ResourceManager (bind_execution_resources) and the
        # key of the shared pipeline leased from it.
        self._resources: Any = None
        self._pipeline_key: str | None = None

        # Initialization and inference use separate locks.
        self._initialization_lock = threading.Lock()

        self._provider_version = (
            provider_version or self._detect_stanza_version()
        )

        # Injected pipelines remain immediately usable in tests
        # and explicit embedding scenarios.
        ### if pipeline is not None:
        ###     self._pipeline = pipeline
        ### else:
        ###     self._pipeline = self._initialize_pipeline()
        # Real pipelines are initialized only by Lifecycle.initialize().
        self._pipeline = pipeline

        self._model_id = f"pl-{self._package}-pdb"

        self._provenance_config = (
            provenance
            if provenance is not None
            else NLPProvenanceConfigV2()
        )

        if not isinstance(
            self._provenance_config,
            NLPProvenanceConfigV2,
        ):
            raise TypeError(
                "provenance must be NLPProvenanceConfigV2."
            )

        self._capabilities = ProviderCapabilities(
            provider_id=PROVIDER_ID,
            provider_version=self._provider_version,
            supported_language_codes=["pl"],
            supported_layers=SUPPORTED_LAYERS,
            supports_diachronic=False,
            supports_batch=False,
            supports_streaming=False,
            metadata={
                "engine": "Stanza",
                "language": "Polish",
                "model_package": self._package,
                "treebank": "PDB",
                "processors": self._processors,
                "tokenize_batch_size": self._tokenize_batch_size,
                "use_gpu": self._use_gpu,
                "device": self._device,
            },
        )

    @staticmethod
    def _detect_stanza_version() -> str:
        try:
            return importlib.metadata.version("stanza")
        except importlib.metadata.PackageNotFoundError:
            return "unknown"

    def initialize(self) -> None:
        """
        Initialize the Stanza pipeline exactly once.

        This hook is invoked by NLPProviderLifecycle.
        It never downloads model resources.
        """

        with self._initialization_lock:
            if self._pipeline is not None:
                return

            resources = getattr(self, "_resources", None)
            if resources is None:
                self._pipeline = self._initialize_pipeline()
                return
            # Stage 8D: one pipeline per configuration, shared by every
            # provider instance of this lifecycle (loaded models are large).
            self._pipeline_key = self._shared_pipeline_key()
            self._pipeline = resources.acquire(
                self._pipeline_key,
                self._initialize_pipeline,
                closer=lambda pipeline: None,
            )

    def _initialize_pipeline(self) -> Any:
        try:
            import stanza
        except ImportError as exc:
            raise NLPProviderConfigurationError(
                "Stanza is not installed. Install it with "
                "'pip install -r requirements-nlp-stanza.txt'.",
                provider_id=PROVIDER_ID,
            ) from exc

        kwargs: dict[str, Any] = {
            "lang": "pl",
            "package": self._package,
            "processors": self._processors,
            "tokenize_batch_size": self._tokenize_batch_size,
            "use_gpu": self._use_gpu,
            "download_method": None,
        }

        if self._model_dir is not None:
            kwargs["dir"] = str(self._model_dir)

        try:
            return stanza.Pipeline(**kwargs)
        except Exception as exc:
            raise NLPProviderConfigurationError(
                "Could not initialize the Polish Stanza pipeline. "
                "Check whether the Polish models are installed. "
                "Use stanza.download('pl') explicitly to download them.",
                provider_id=PROVIDER_ID,
                details={
                    "model_dir": (
                        str(self._model_dir)
                        if self._model_dir is not None
                        else None
                    ),
                    "processors": self._processors,
                    "tokenize_batch_size": self._tokenize_batch_size,
                    "device": self._device,
                    "original_error": str(exc),
                },
            ) from exc

    async def _run_whole_pipeline(self, text: str) -> Any:
        """The whole pipeline in one call, in a worker thread (no execution context)."""
        def run_pipeline() -> Any:
            with self._lock:
                return self._pipeline(text)

        return await asyncio.to_thread(run_pipeline)

    def _pipeline_stages(self) -> list[list[str]]:
        """Processor groups in pipeline order; mwt runs together with tokenize.

        (Stanza adds mwt whenever tokenize is requested, so running mwt again
        as its own stage would apply it twice.)
        """
        try:
            from stanza.pipeline.core import PIPELINE_NAMES  # pylint: disable=import-outside-toplevel
        except ImportError:  # injected test pipelines without Stanza
            PIPELINE_NAMES = (  # pylint: disable=invalid-name
                "tokenize", "mwt", "pos", "lemma", "depparse",
                "ner", "sentiment", "constituency",
            )
        active = getattr(self._pipeline, "processors", None) or {
            name.strip(): True for name in self._processors.split(",")
        }
        stages: list[list[str]] = []
        for name in PIPELINE_NAMES:
            if name not in active:
                continue
            if name == "mwt" and stages and stages[-1] == ["tokenize"]:
                stages[-1].append("mwt")
            else:
                stages.append([name])
        return stages

    def _run_staged_pipeline(
        self,
        text: str,
        context: Any,
        recorder: Any,
    ) -> Any:
        """Run the processors one group at a time, checking the context before each."""
        seconds: dict[str, float] = {}
        with self._lock:
            if not hasattr(self._pipeline, "process"):
                # An injected pipeline that is only callable (tests, embedding):
                # one call, with the context checked before and after it.
                context.check("stanza:pipeline")
                started = time.perf_counter()
                document = self._pipeline(text)
                seconds["pipeline"] = round(time.perf_counter() - started, 4)
                context.check("stanza:mapping")
                recorder.note("stage_seconds", seconds)
                return document
            document: Any = text
            for stage in self._pipeline_stages():
                name = "+".join(stage)
                context.check(f"stanza:{name}")
                started = time.perf_counter()
                document = self._pipeline.process(document, processors=[stage[0]])
                seconds[name] = round(time.perf_counter() - started, 4)
            context.check("stanza:mapping")
        recorder.note("stage_seconds", seconds)
        return document

    def _actual_device(self) -> str:
        """Device the pipeline really runs on ("cpu" or "cuda:0")."""
        if not self._use_gpu:
            return "cpu"
        try:
            import torch  # pylint: disable=import-outside-toplevel
        except ImportError:
            return "cpu"
        return "cuda:0" if torch.cuda.is_available() else "cpu"

    def bind_execution_resources(self, resources: Any) -> None:
        """Called by NLPProviderLifecycle.register (stage 8D): the shared ResourceManager."""
        self._resources = resources

    def _apply_thread_policy(self, max_threads: int | None) -> int | None:
        """Apply ``max_threads`` to PyTorch's process-global thread pool.

        The setting is claimed in the shared ResourceManager first: if another
        engine already set a different value for the whole process, this is a
        ResourceConflictError instead of a silent change of its behaviour.
        Returns the thread count in effect (None when torch is absent).
        """
        try:
            import torch  # pylint: disable=import-outside-toplevel
        except ImportError:
            return None
        if max_threads is not None:
            resources = getattr(self, "_resources", None)
            must_apply = (
                resources.claim_setting("torch.num_threads", max_threads, PROVIDER_ID)
                if resources is not None
                else True
            )
            if must_apply:
                torch.set_num_threads(max_threads)
        return torch.get_num_threads()

    def close(self) -> None:
        """Release the shared pipeline (stage 8D); invoked by NLPProviderLifecycle.close."""
        resources = getattr(self, "_resources", None)
        key = getattr(self, "_pipeline_key", None)
        if resources is not None and key is not None:
            resources.release(key, close_when_unused=True)
            resources.release_settings(PROVIDER_ID)
            self._pipeline = None

    def _shared_pipeline_key(self) -> str:
        """Key under which identical pipelines are shared between provider instances."""
        return (
            f"stanza:pl:{self._package}:{self._processors}:"
            f"{self._tokenize_batch_size}:{self._use_gpu}:{self._model_dir}"
        )

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    @staticmethod
    def _get_text(request: NLPProviderRequest) -> str:
        for version in request.document.text_versions:
            if version.text_version_id == request.text_version_id:
                return version.text

        raise NLPProviderInputError(
            "Requested text version does not exist.",
            provider_id=PROVIDER_ID,
        )

    @staticmethod
    def _parse_morphology(
        feats: str | None,
    ) -> list[MorphologicalFeature]:
        if not feats:
            return []

        result: list[MorphologicalFeature] = []

        for item in feats.split("|"):
            if "=" not in item:
                continue

            category, value = item.split("=", 1)

            if not category or not value:
                continue

            result.append(
                MorphologicalFeature(
                    category=category,
                    value=value,
                    language_specific=False,
                    scheme="UD",
                )
            )

        return result

    @staticmethod
    def _is_punctuation(text: str, upos: str | None) -> bool:
        if upos == "PUNCT":
            return True

        visible = [char for char in text if not char.isspace()]

        return bool(visible) and all(
            unicodedata.category(char).startswith("P")
            for char in visible
        )

    @staticmethod
    def _get_surface_span(
        text: str,
        stanza_token: Any,
    ) -> tuple[int, int, str]:
        start = getattr(stanza_token, "start_char", None)
        end = getattr(stanza_token, "end_char", None)

        if not isinstance(start, int) or not isinstance(end, int):
            raise NLPProviderOutputError(
                "Stanza token does not contain usable character offsets.",
                provider_id=PROVIDER_ID,
                details={
                    "token_text": getattr(stanza_token, "text", None),
                },
            )

        if start < 0 or end < start or end > len(text):
            raise NLPProviderOutputError(
                "Stanza returned token offsets outside the source text.",
                provider_id=PROVIDER_ID,
                details={
                    "start": start,
                    "end": end,
                    "text_length": len(text),
                },
            )

        surface = text[start:end]

        if not surface:
            raise NLPProviderOutputError(
                "Stanza returned an empty source span for a token.",
                provider_id=PROVIDER_ID,
            )

        return start, end, surface

    @staticmethod
    def _get_word_span(
        text: str,
        stanza_word: Any,
        parent_start: int,
        parent_end: int,
        parent_surface: str,
    ) -> tuple[int, int, str]:
        """
        Return a source-verifiable span for a syntactic word.

        Stanza may not assign individual source offsets to words
        expanded from an MWT. In that case, use the parent surface
        token span instead of inventing character positions.
        """
        start = getattr(stanza_word, "start_char", None)
        end = getattr(stanza_word, "end_char", None)
        word_text = getattr(stanza_word, "text", None)

        if isinstance(start, int) and isinstance(end, int):
            if (
                0 <= start <= end <= len(text)
                and text[start:end] == word_text
            ):
                return start, end, text[start:end]

        return parent_start, parent_end, parent_surface

    def _make_provenance(
        self,
        provider_version: str,
        configuration: dict[str, Any],
    ) -> Provenance:
        provenance_config = self._provenance_config

        return Provenance(
            actor_type=provenance_config.actor_type,
            actor_id=provenance_config.actor_id,
            provider_id=PROVIDER_ID,
            provider_version=provider_version,
            model_id=self._model_id,
            method=provenance_config.method,
            notes=provenance_config.notes,
            configuration=configuration,
        )

    def _map_document(
        self,
        *,
        document: NLPDocument,
        text_version_id: str,
        text: str,
        stanza_document: Any,
        requested_layers: set[AnalysisLayer],
        include_provider_native: bool,
        runtime_seconds: float,
    ) -> NLPAnalysis:
        sentences: list[Sentence] = []
        tokens: list[Token] = []
        dependencies: list[DependencyRelation] = []
        roots: list[dict[str, Any]] = []

        want_morphology = AnalysisLayer.MORPHOLOGY in requested_layers
        want_dependencies = (
            AnalysisLayer.DEPENDENCY_SYNTAX in requested_layers
        )

        configuration = {
            "language": "pl",
            "processors": self._processors,
            "tokenize_batch_size": self._tokenize_batch_size,
            "use_gpu": self._use_gpu,
            "device": self._device,
            "model_package": self._package,
            "model_id": self._model_id,
            "model_dir": (
                str(self._model_dir)
                if self._model_dir is not None
                else None
            ),
        }

        provenance = self._make_provenance(
            self._provider_version,
            configuration,
        )

        for sentence_index, stanza_sentence in enumerate(
            stanza_document.sentences,
            start=1,
        ):
            sentence_prefix = f"{PROVIDER_ID}:s{sentence_index}"

            stanza_tokens = list(stanza_sentence.tokens)
            stanza_words = list(stanza_sentence.words)

            if not stanza_tokens:
                continue

            surface_spans = [
                self._get_surface_span(text, stanza_token)
                for stanza_token in stanza_tokens
            ]

            sentence_start = min(span[0] for span in surface_spans)
            sentence_end = max(span[1] for span in surface_spans)

            sentence_text = text[sentence_start:sentence_end]

            word_id_map: dict[int, str] = {}
            word_records: list[tuple[Any, Any, str, str]] = []

            for stanza_token_index, stanza_token in enumerate(
                stanza_tokens,
                start=1,
            ):
                parent_start, parent_end, parent_surface = (
                    surface_spans[stanza_token_index - 1]
                )

                parent_words = list(stanza_token.words)
                is_mwt = len(parent_words) > 1

                parent_id = getattr(stanza_token, "id", stanza_token_index)

                mwt_id = (
                    f"{sentence_prefix}:mwt:{parent_id}"
                    if is_mwt
                    else None
                )

                for word in parent_words:
                    word_id = getattr(word, "id", None)

                    if not isinstance(word_id, int):
                        raise NLPProviderOutputError(
                            "Stanza returned a word without an integer ID.",
                            provider_id=PROVIDER_ID,
                        )

                    token_id = f"{sentence_prefix}:w{word_id}"

                    if word_id in word_id_map:
                        raise NLPProviderOutputError(
                            "Stanza returned duplicate word IDs "
                            "within a sentence.",
                            provider_id=PROVIDER_ID,
                        )

                    word_id_map[word_id] = token_id

                    word_start, word_end, word_surface = (
                        self._get_word_span(
                            text,
                            word,
                            parent_start,
                            parent_end,
                            parent_surface,
                        )
                    )

                    word_records.append(
                        (
                            word,
                            stanza_token,
                            token_id,
                            mwt_id,
                        )
                    )

                    upos_value = getattr(word, "upos", None)
                    word_form = getattr(word, "text", None) or word_surface

                    morphology = (
                        self._parse_morphology(
                            getattr(word, "feats", None)
                        )
                        if want_morphology
                        else []
                    )

                    provider_native: dict[str, Any] = {}

                    if include_provider_native:
                        provider_native = {
                            "engine": "stanza",
                            "sentence_index": sentence_index,
                            "word_id": word_id,
                            "word_text": word_form,
                            "surface_token_text": parent_surface,
                            "surface_token_id": str(parent_id),
                            "upos": upos_value,
                            "xpos": getattr(word, "xpos", None),
                            "feats": getattr(word, "feats", None),
                            "head": getattr(word, "head", None),
                            "deprel": getattr(word, "deprel", None),
                            "misc": getattr(word, "misc", None),
                            "word_surface_matches_syntactic_form": (
                                word_surface == word_form
                            ),
                        }

                    token = Token(
                        token_id=token_id,
                        anchor=TextAnchor(
                            text_version_id=text_version_id,
                            span=TextSpan(
                                start=word_start,
                                end=word_end,
                                offset_unit=OffsetUnit.CODEPOINT,
                            ),
                            quoted_text=word_surface,
                        ),
                        text=word_surface,
                        normalized_form=(
                            word_form
                            if word_form != word_surface
                            else None
                        ),
                        lemma=(
                            getattr(word, "lemma", None)
                            if want_morphology
                            else None
                        ),
                        upos=(
                            UPOS_MAPPING.get(
                                upos_value,
                                PartOfSpeech.UNKNOWN,
                            )
                            if want_morphology and upos_value
                            else None
                        ),
                        xpos=(
                            getattr(word, "xpos", None)
                            if want_morphology
                            else None
                        ),
                        pos_scheme="UD" if want_morphology else None,
                        morphology=morphology,
                        is_punctuation=self._is_punctuation(
                            word_surface,
                            upos_value,
                        ),
                        sentence_id=f"{sentence_prefix}",
                        multiword_token_id=mwt_id,
                        provenance=provenance,
                        provider_native=provider_native,
                    )

                    tokens.append(token)

            sentence_token_ids = [
                record[2]
                for record in word_records
            ]

            sentences.append(
                Sentence(
                    sentence_id=sentence_prefix,
                    anchor=TextAnchor(
                        text_version_id=text_version_id,
                        span=TextSpan(
                            start=sentence_start,
                            end=sentence_end,
                            offset_unit=OffsetUnit.CODEPOINT,
                        ),
                        quoted_text=sentence_text,
                    ),
                    text=sentence_text,
                    sequence_number=sentence_index - 1,
                    language_code="pl",
                    token_ids=sentence_token_ids,
                    provenance=provenance,
                )
            )

            if want_dependencies:
                for word, _parent, dependent_id, _mwt_id in word_records:
                    head = getattr(word, "head", None)
                    deprel = getattr(word, "deprel", None)

                    if not isinstance(head, int) or not deprel:
                        raise NLPProviderOutputError(
                            "Stanza returned an incomplete dependency "
                            "annotation.",
                            provider_id=PROVIDER_ID,
                            details={
                                "word_id": getattr(word, "id", None),
                                "head": head,
                                "deprel": deprel,
                            },
                        )

                    if head == 0:
                        roots.append({
                            "sentence_id": sentence_prefix,
                            "token_id": dependent_id,
                            "relation": deprel,
                        })
                        continue

                    head_id = word_id_map.get(head)

                    if head_id is None:
                        raise NLPProviderOutputError(
                            "Stanza dependency references an unknown head.",
                            provider_id=PROVIDER_ID,
                            details={
                                "dependent_id": dependent_id,
                                "head": head,
                            },
                        )

                    relation_parts = deprel.split(":", 1)

                    dependencies.append(
                        DependencyRelation(
                            relation_id=(
                                f"{sentence_prefix}:dep:"
                                f"{dependent_id.rsplit(':', 1)[-1]}"
                            ),
                            head_token_id=head_id,
                            dependent_token_id=dependent_id,
                            relation=deprel,
                            layer=DependencyLayer.UNIVERSAL_DEPENDENCIES,
                            subtype=(
                                relation_parts[1]
                                if len(relation_parts) == 2
                                else None
                            ),
                            scheme="UD",
                            provenance=provenance,
                        )
                    )

        completed_layers = [
            layer
            for layer in SUPPORTED_LAYERS
            if layer in requested_layers
        ]

        return NLPAnalysis(
            analysis_id=f"{PROVIDER_ID}:{time.time_ns()}",
            document_id=document.document_id,
            text_version_id=text_version_id,
            status=AnalysisStatus.COMPLETED,
            provider=ProviderMetadata(
                provider_id=PROVIDER_ID,
                provider_version=self._provider_version,
                model_id=self._model_id,
                language_code="pl",
                configuration=configuration,
                runtime_seconds=runtime_seconds,
                hardware={
                    "device": self._device,
                },
            ),
            sentences=sentences,
            tokens=tokens,
            dependencies=dependencies,
            completed_layers=completed_layers,
            metadata={
                "engine": "stanza",
                "language": "pl",
                "model_package": self._package,
                "treebank": "PDB",
                "processors": self._processors,
                "tokenize_batch_size": self._tokenize_batch_size,
                "device": self._device,
                "dependency_roots": roots,
                "mwt_policy": (
                    "surface-verifiable spans; syntactic word forms "
                    "preserved separately"
                ),
            },
        )

    async def analyze(
        self,
        request: NLPProviderRequest,
    ) -> NLPProviderResponse:
        """Analyze one canonical document request."""
        return await self._analyze(request, self._run_whole_pipeline)

    async def analyze_in_context(
        self,
        request: NLPProviderRequest,
        context: Any,
        recorder: Any,
    ) -> NLPProviderResponse:
        """
        Analyze under the runtime execution contract (stage 8D).

        The Stanza processors run one after another (tokenize+mwt, pos,
        lemma, depparse, ...) and the context is checked before each of
        them, so a timeout or a cancellation stops the analysis at the
        next processor boundary instead of after the whole pipeline.
        A single processor over a long text still runs to its end - that
        is the finest granularity Stanza offers. The recorder gets the
        engine, its version, the device, the threads and the seconds of
        every processor.
        """
        recorder.record_engine("stanza", self._provider_version)
        device = context.policy.resolve_device([self._actual_device()])
        threads = self._apply_thread_policy(context.policy.max_threads)
        recorder.record_device(device, threads=threads)
        recorder.note("processors", self._processors)

        async def run(text: str) -> Any:
            return await asyncio.to_thread(
                self._run_staged_pipeline, text, context, recorder
            )

        return await self._analyze(request, run)

    async def _analyze(
        self,
        request: NLPProviderRequest,
        run_pipeline_fn: Any,
    ) -> NLPProviderResponse:
        """Shared body of analyze / analyze_in_context; ``run_pipeline_fn(text)`` runs Stanza."""

        if request.configuration:
            raise NLPProviderConfigurationError(
                "Per-request Stanza configuration is not supported yet. "
                "Configure the pipeline when constructing the provider.",
                provider_id=PROVIDER_ID,
                details={
                    "received_configuration": request.configuration,
                },
            )

        text = self._get_text(request)

        if (
            self.capabilities.max_input_characters is not None
            and len(text) > self.capabilities.max_input_characters
        ):
            raise NLPProviderInputError(
                "Input exceeds the provider character limit.",
                provider_id=PROVIDER_ID,
                details={
                    "input_characters": len(text),
                    "limit": self.capabilities.max_input_characters,
                },
            )

        request_report = validate_provider_request(
            request,
            self.capabilities,
        )

        unsupported_layers = [
            issue
            for issue in request_report.issues
            if issue.code == "unsupported_requested_layers"
        ]

        other_issues = [
            issue
            for issue in request_report.issues
            if issue.code != "unsupported_requested_layers"
        ]

        if other_issues:
            raise NLPProviderInputError(
                "Provider request validation failed.",
                provider_id=PROVIDER_ID,
                details={
                    "issues": [
                        issue.model_dump()
                        for issue in other_issues
                    ],
                },
            )

        if unsupported_layers and not request.allow_partial:
            raise NLPProviderCapabilityError(
                "The request contains layers not supported by Stanza.",
                provider_id=PROVIDER_ID,
                details={
                    "issues": [
                        issue.model_dump()
                        for issue in unsupported_layers
                    ],
                },
            )

        supported_requested = (
            set(request.requested_layers)
            & set(self.capabilities.supported_layers)
        )

        unavailable_layers = (
            set(request.requested_layers)
            - set(self.capabilities.supported_layers)
        )

        if supported_requested and self._pipeline is None:
            raise NLPProviderConfigurationError(
                "Stanza pipeline has not been initialized. "
                "Initialize the provider through NLPProviderLifecycle.",
                provider_id=PROVIDER_ID,
            )

        diagnostics: list[ProviderDiagnostic] = []

        for layer in sorted(
            unavailable_layers,
            key=lambda item: item.value,
        ):
            diagnostics.append(
                ProviderDiagnostic(
                    code="layer_not_supported",
                    message=(
                        f"Stanza provider does not support "
                        f"the requested layer '{layer.value}'."
                    ),
                    severity=ProviderDiagnosticSeverity.WARNING,
                    layer=layer,
                )
            )

        runtime_seconds = 0.0

        if supported_requested:
            started = time.perf_counter()

            try:
                # Stanza is synchronous: the runner executes inference
                # outside the event loop and serializes pipeline access.
                stanza_document = await run_pipeline_fn(text)

            except ExecutionError:
                # Timeout / cancellation of the execution contract (8D):
                # not a Stanza failure, propagated with its own type.
                raise
            except Exception as exc:
                raise NLPProviderExecutionError(
                    "Stanza inference failed.",
                    provider_id=PROVIDER_ID,
                    retryable=False,
                    details={
                        "original_error": str(exc),
                    },
                ) from exc

            runtime_seconds = time.perf_counter() - started

            analysis = self._map_document(
                document=request.document,
                text_version_id=request.text_version_id,
                text=text,
                stanza_document=stanza_document,
                requested_layers=supported_requested,
                include_provider_native=request.include_provider_native,
                runtime_seconds=runtime_seconds,
            )
        else:
            analysis = NLPAnalysis(
                analysis_id=f"{PROVIDER_ID}:{time.time_ns()}",
                document_id=request.document.document_id,
                text_version_id=request.text_version_id,
                status=AnalysisStatus.PARTIAL,
                provider=ProviderMetadata(
                    provider_id=PROVIDER_ID,
                    provider_version=self._provider_version,
                    model_id=self._model_id,
                    language_code="pl",
                ),
            )

        analysis.unavailable_layers = sorted(
            unavailable_layers,
            key=lambda item: item.value,
        )

        if unavailable_layers:
            analysis.status = AnalysisStatus.PARTIAL

        response = NLPProviderResponse(
            request_id=request.request_id,
            provider_id=PROVIDER_ID,
            analysis=analysis,
            diagnostics=diagnostics,
        )

        conformance = validate_provider_response(
            request,
            self.capabilities,
            response,
        )

        if not conformance.is_valid:
            raise NLPProviderOutputError(
                "Stanza output does not conform to the provider contract.",
                provider_id=PROVIDER_ID,
                details={
                    "issues": [
                        issue.model_dump()
                        for issue in conformance.issues
                    ],
                },
            )

        return response


