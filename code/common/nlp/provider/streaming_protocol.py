
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Optional asynchronous streaming protocol for NLP providers."""

from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from .request import NLPProviderRequest
from .streaming import NLPProviderStreamEvent


@runtime_checkable
class NLPProviderStreaming(Protocol):
    """Optional interface for providers supporting streaming analysis."""

    def analyze_stream(
        self,
        request: NLPProviderRequest,
        *,
        stream_id: str,
    ) -> AsyncIterator[NLPProviderStreamEvent]:
        """Return an asynchronous stream of ordered analysis events."""
        ...


__all__ = [
    "NLPProviderStreaming",
]

