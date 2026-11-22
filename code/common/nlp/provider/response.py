
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Canonical response returned by an NLP provider."""

from enum import StrEnum
from typing import Any

from pydantic import Field

from ..model.base import NLPModel
from ..model.analysis import AnalysisLayer, NLPAnalysis


class ProviderDiagnosticSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ProviderDiagnostic(NLPModel):
    """Diagnostic message produced during provider execution."""

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)

    severity: ProviderDiagnosticSeverity = ProviderDiagnosticSeverity.INFO

    layer: AnalysisLayer | None = None
    object_id: str | None = None

    details: dict[str, Any] = Field(default_factory=dict)


class NLPProviderResponse(NLPModel):
    """Response envelope for an NLP provider."""

    request_id: str = Field(min_length=1)
    provider_id: str = Field(min_length=1)

    analysis: NLPAnalysis

    diagnostics: list[ProviderDiagnostic] = Field(default_factory=list)

