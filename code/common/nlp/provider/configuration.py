#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Typed configuration models for NLP providers.

Configuration is separated into three independent concerns:

1. Provider engine configuration:
   engine name and engine-specific parameters.

2. Model configuration:
   model identifier, package, revision and language.

3. Runtime configuration:
   execution device, thread count and memory constraints.

NLPProviderConfiguration combines these concerns into one
serializable configuration object.

This module defines configuration contracts only. It does not
initialize providers, load models or modify provider instances.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import Field, field_validator

from ..model.base import NLPModel


class NLPExecutionDevice(StrEnum):
    """Supported execution device identifiers."""

    CPU = "cpu"
    CUDA = "cuda"
    MPS = "mps"
    AUTO = "auto"


class NLPProviderEngineConfig(NLPModel):
    """Configuration specific to a provider engine."""

    engine_name: str = Field(min_length=1)

    parameters: dict[str, Any] = Field(default_factory=dict)

    @field_validator("engine_name")
    @classmethod
    def validate_engine_name(cls, value: str) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError("engine_name must not be blank.")

        return normalized


class NLPModelConfig(NLPModel):
    """Identity and selection settings for an NLP model."""

    model_id: str = Field(min_length=1)

    package: str | None = None
    revision: str | None = None
    language_code: str | None = None

    parameters: dict[str, Any] = Field(default_factory=dict)

    @field_validator("model_id")
    @classmethod
    def validate_model_id(cls, value: str) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError("model_id must not be blank.")

        return normalized

    @field_validator("package", "revision", "language_code")
    @classmethod
    def validate_optional_identifiers(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                "Optional model identifiers must not be blank."
            )

        return normalized


class NLPRuntimeConfig(NLPModel):
    """Runtime and resource constraints for NLP execution."""

    device: NLPExecutionDevice = NLPExecutionDevice.CPU

    threads: int | None = Field(default=None, gt=0)

    memory_limit_mb: int | None = Field(default=None, gt=0)

    allow_device_fallback: bool = False


class NLPProviderConfiguration(NLPModel):
    """
    Complete configuration for one NLP provider.

    The provider_id identifies the target provider. The nested
    configurations remain independent so that engine, model and
    runtime settings can be validated and serialized separately.
    """

    provider_id: str = Field(min_length=1)

    engine: NLPProviderEngineConfig

    model: NLPModelConfig | None = None

    runtime: NLPRuntimeConfig = Field(
        default_factory=NLPRuntimeConfig
    )

    @field_validator("provider_id")
    @classmethod
    def validate_provider_id(cls, value: str) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError("provider_id must not be blank.")

        return normalized

    def to_dict(self) -> dict[str, Any]:
        """
        Return a JSON-compatible representation.

        Enum values are serialized as strings. None-valued optional
        fields are omitted.
        """
        return self.model_dump(
            mode="json",
            exclude_none=True,
        )

