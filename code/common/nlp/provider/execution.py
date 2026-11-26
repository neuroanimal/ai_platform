#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Stage 8C: NLP analysis under the platform's runtime execution contract.

``NLPProviderLifecycle.analyze_with_context`` runs a provider through
``ai_platform.common.core.execution.execute``. This module holds what the
lifecycle needs for that and nothing engine-specific:

- ``ContextAwareNLPProvider``: the optional richer provider protocol.
  A provider that implements ``analyze_in_context(request, context, recorder)``
  checks the context between its own steps (so it can really stop) and
  records what it used (device, threads, engine version). Providers with only
  ``analyze(request)`` keep working unchanged.
- ``NLPExecutionResult``: the response together with its ``ExecutionMetadata``.
- ``as_nlp_error``: the execution contract's timeout / cancellation turned
  into ``NLPProviderTimeoutError`` / ``NLPProviderCancelledError`` - types that
  belong to both hierarchies - keeping the original as ``__cause__`` and the
  metadata attached.

Provider errors (``NLPProviderInputError`` and the rest) are never translated:
they reach the caller with their own type and with ``execution_metadata``.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol, runtime_checkable

from ai_platform.common.core.execution import (
    ExecutionCancelledError,
    ExecutionContext,
    ExecutionMetadata,
    ExecutionRecorder,
    ExecutionTimeoutError,
)

from .errors import (
    NLPProviderCancelledError,
    NLPProviderError,
    NLPProviderTimeoutError,
)
from .request import NLPProviderRequest
from .response import NLPProviderResponse

#: Operation name of NLP analyses in ExecutionContext / ExecutionMetadata.
ANALYZE_OPERATION = "nlp.analyze"


@runtime_checkable
class ContextAwareNLPProvider(Protocol):  # pylint: disable=too-few-public-methods
    """Provider that runs inside an ExecutionContext (checks it, records facts)."""

    async def analyze_in_context(
        self,
        request: NLPProviderRequest,
        context: ExecutionContext,
        recorder: ExecutionRecorder,
    ) -> NLPProviderResponse:
        """Analyze; call ``context.check()`` between steps, record device/engine."""


@dataclass(frozen=True)
class NLPExecutionResult:
    """Response of one analysis and the facts of its execution."""

    response: NLPProviderResponse
    metadata: ExecutionMetadata


def mark_abandoned(exc: BaseException) -> None:
    """Set ``abandoned`` in the metadata of ``exc`` (work still running after the error)."""
    metadata = getattr(exc, "execution_metadata", None)
    if metadata is not None and not metadata.abandoned:
        exc.execution_metadata = replace(metadata, abandoned=True)


def as_nlp_error(exc: BaseException, provider_id: str) -> BaseException:
    """Timeout / cancellation of the contract as NLP errors; anything else unchanged."""
    if isinstance(exc, NLPProviderError):
        return exc
    if isinstance(exc, (ExecutionTimeoutError, ExecutionCancelledError)):
        kind = NLPProviderTimeoutError if isinstance(exc, ExecutionTimeoutError) \
            else NLPProviderCancelledError
        translated = kind(
            f"Provider '{provider_id}': {exc}",
            provider_id=provider_id,
            stage=getattr(exc, "stage", None),
            details=dict(getattr(exc, "details", {}) or {}),
        )
        translated.__cause__ = exc
        metadata = getattr(exc, "execution_metadata", None)
        if metadata is not None:
            translated.execution_metadata = metadata
        return translated
    return exc


__all__ = [
    "ANALYZE_OPERATION",
    "ContextAwareNLPProvider",
    "NLPExecutionResult",
    "as_nlp_error",
    "mark_abandoned",
]
