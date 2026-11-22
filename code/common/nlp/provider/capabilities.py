
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Capabilities declared by an NLP provider."""

from typing import Any

from pydantic import Field, field_validator

from ..model.base import NLPModel
from ..model.analysis import AnalysisLayer


class ProviderCapabilities(NLPModel):
    """Machine-readable description of an NLP provider's capabilities."""

    provider_id: str = Field(min_length=1)
    provider_version: str = Field(min_length=1)

    supported_language_codes: list[str] = Field(default_factory=list)
    supported_layers: list[AnalysisLayer] = Field(min_length=1)

    supports_diachronic: bool = False
    supports_batch: bool = False
    supports_streaming: bool = False

    max_input_characters: int | None = Field(default=None, gt=0)

    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("provider_id", "provider_version")
    @classmethod
    def validate_nonblank_identifier(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Value must not be blank.")
        return value

    @field_validator("supported_language_codes")
    @classmethod
    def validate_language_codes(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value]

        if any(not item for item in normalized):
            raise ValueError("Language codes must not be blank.")

        lowered = [item.casefold() for item in normalized]

        if len(lowered) != len(set(lowered)):
            raise ValueError("Language codes must be unique.")

        return normalized

    @field_validator("supported_layers")
    @classmethod
    def validate_supported_layers(
        cls,
        value: list[AnalysisLayer],
    ) -> list[AnalysisLayer]:
        if len(value) != len(set(value)):
            raise ValueError("Supported layers must be unique.")

        return value

