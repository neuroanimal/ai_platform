
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Optional batch execution protocol for NLP providers."""

from typing import Protocol, runtime_checkable

from .batch import (
    NLPProviderBatchRequest,
    NLPProviderBatchResponse,
)


@runtime_checkable
class NLPProviderBatch(Protocol):
    """Optional interface for providers supporting batch processing."""

    async def analyze_batch(
        self,
        request: NLPProviderBatchRequest,
    ) -> NLPProviderBatchResponse:
        """Analyze a batch and return one outcome per processed request."""
        ...


__all__ = [
    "NLPProviderBatch",
]

