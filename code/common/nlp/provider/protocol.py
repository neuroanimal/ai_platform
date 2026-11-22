
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Structural protocol implemented by NLP providers."""

from typing import Protocol, runtime_checkable

from .capabilities import ProviderCapabilities
from .request import NLPProviderRequest
from .response import NLPProviderResponse


@runtime_checkable
class NLPProvider(Protocol):
    """Minimal asynchronous NLP provider interface."""

    @property
    def capabilities(self) -> ProviderCapabilities:
        ...

    async def analyze(
        self,
        request: NLPProviderRequest,
    ) -> NLPProviderResponse:
        ...

