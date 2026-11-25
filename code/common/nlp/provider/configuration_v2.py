
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Version 2 of NLP provider configuration.

Design principles:
- strict Pydantic models;
- frozen configuration objects;
- explicit engine-specific options;
- no implicit model downloads;
- secrets are referenced by environment variable name only;
- runtime settings are declarative hints, not process-global mutations.
"""

from __future__ import annotations

import hashlib
import json
import re

from enum import StrEnum
from pathlib import Path
from typing import Any, Mapping

from pydantic import ConfigDict, Field, field_validator, model_validator

from .immutable import deep_freeze
from ..model.base import NLPModel
from ..model.base import ActorType
from .provenance_configuration import NLPProvenanceConfigV2


class NLPDownloadPolicy(StrEnum):
    """Policy controlling model download behavior."""

    NEVER = "never"
    IF_MISSING = "if_missing"
    ALWAYS = "always"


class NLPExecutionDevice(StrEnum):
    """Supported execution device identifiers."""

    AUTO = "auto"
    CPU = "cpu"


class NLPProviderEngineConfigV2(NLPModel):
    """
    Engine-level configuration.

    Engine-specific parameters belong in `options`.
    Secrets must never be stored directly in this model.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        validate_assignment=True,
        use_enum_values=False,
        str_strip_whitespace=True,
    )

    engine_name: str = Field(min_length=1)

    options: dict[str, Any] = Field(default_factory=dict)

    # Name of an environment variable containing the actual secret.
    # The secret itself must never enter configuration data.
    api_key_env: str | None = None

    @field_validator("engine_name")
    @classmethod
    def validate_engine_name(cls, value: str) -> str:
        if not value:
            raise ValueError("engine_name must not be blank.")
        return value

    @field_validator("api_key_env")
    @classmethod
    def validate_api_key_env(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
            raise ValueError(
                "api_key_env must be a valid environment variable name."
            )

        return value

    @field_validator("options", mode="after")
    @classmethod
    def freeze_options(cls, value: dict[str, Any]) -> dict[str, Any]:
        return deep_freeze(value)


class NLPModelConfigV2(NLPModel):
    """
    Configuration identifying a model and its local installation.

    At least one of model_id or package must be provided.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        validate_assignment=True,
        use_enum_values=False,
        str_strip_whitespace=True,
    )

    model_id: str | None = None

    # Engine/package-specific model identifier.
    # Example: Stanza package "default".
    package: str | None = None

    # Model release, revision, or version.
    version: str | None = None

    language: str | None = None

    # Explicit model directory. No implicit cache-path assumptions.
    model_dir: Path | None = None

    download_policy: NLPDownloadPolicy = NLPDownloadPolicy.NEVER

    @field_validator("model_id", "package", "version", "language")
    @classmethod
    def validate_optional_identifiers(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        if not value:
            raise ValueError("Identifier must not be blank.")

        return value

    @field_validator("model_dir", mode="before")
    @classmethod
    def normalize_model_dir(
        cls,
        value: str | Path | None,
    ) -> Path | None:
        if value is None:
            return None

        if isinstance(value, str) and not value.strip():
            raise ValueError("model_dir must not be blank.")

        return Path(value).expanduser()

    @model_validator(mode="after")
    def validate_model_identity(self) -> "NLPModelConfigV2":
        if self.model_id is None and self.package is None:
            raise ValueError(
                "At least one of model_id or package must be provided."
            )

        return self


class NLPRuntimeConfigV2(NLPModel):
    """
    Declarative runtime configuration.

    memory_limit_mb_hint is advisory. It does not enforce an OS-level
    or engine-level memory limit.

    Thread settings must be coordinated by the runtime/registry layer
    when the underlying engine uses process-global thread configuration.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        validate_assignment=True,
        use_enum_values=False,
        str_strip_whitespace=True,
    )

    device: str = "auto"

    threads: int | None = Field(default=None, gt=0)

    batch_size: int | None = Field(default=None, gt=0)

    memory_limit_mb_hint: int | None = Field(default=None, gt=0)

    allow_device_fallback: bool = True

    @field_validator("device")
    @classmethod
    def validate_device(cls, value: str) -> str:
        normalized = value.casefold()

        if normalized in {"auto", "cpu"}:
            return normalized

        if re.fullmatch(r"cuda:[0-9]+", normalized):
            return normalized

        raise ValueError(
            "device must be 'auto', 'cpu', or 'cuda:N'."
        )


class NLPProviderConfigurationV2(NLPModel):
    """
    Complete configuration for one NLP provider instance.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        validate_assignment=True,
        use_enum_values=False,
        str_strip_whitespace=True,
    )

    provider_id: str = Field(min_length=1)

    engine: NLPProviderEngineConfigV2

    model: NLPModelConfigV2 | None = None

    runtime: NLPRuntimeConfigV2 = Field(
        default_factory=NLPRuntimeConfigV2
    )

    provenance: NLPProvenanceConfigV2 = Field(
        default_factory=NLPProvenanceConfigV2
    )

    @field_validator("provider_id")
    @classmethod
    def validate_provider_id(cls, value: str) -> str:
        if not value:
            raise ValueError("provider_id must not be blank.")
        return value

    @classmethod
    def from_dict(
        cls,
        data: Mapping[str, Any],
    ) -> "NLPProviderConfigurationV2":
        """
        Construct configuration from a Python mapping.

        Pydantic performs strict validation and rejects unknown fields.
        """
        return cls.model_validate(dict(data))

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-compatible configuration data."""
        return self.model_dump(mode="json", exclude_none=False)


    def fingerprint_payload(self) -> dict[str, Any]:
        """
        Return the canonical subset of configuration used for fingerprinting.

        Deployment-specific paths, download policy, credentials references,
        and advisory memory limits are intentionally excluded.
        """

        model_payload = None

        if self.model is not None:
            model_payload = {
                "model_id": self.model.model_id,
                "package": self.model.package,
                "version": self.model.version,
                "language": self.model.language,
            }

        return {
            "fingerprint_schema": "nlp-provider-configuration-v2.1",
            "provider_id": self.provider_id,
            "engine": {
                "engine_name": self.engine.engine_name,
                "options": self.engine.options,
            },
            "model": model_payload,
            "runtime": {
                "device": self.runtime.device,
                "threads": self.runtime.threads,
                "batch_size": self.runtime.batch_size,
                "allow_device_fallback": (
                    self.runtime.allow_device_fallback
                ),
            },
            "provenance": self.provenance.model_dump(
                mode="json",
                exclude_none=False,
            ),
        }

    @property
    def fingerprint_sha256(self) -> str:
        """
        Return a deterministic SHA-256 fingerprint.

        Dictionary insertion order does not affect the result.
        """
        canonical_json = json.dumps(
            self.fingerprint_payload(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )

        return hashlib.sha256(
            canonical_json.encode("utf-8")
        ).hexdigest()


__all__ = [
    "NLPDownloadPolicy",
    "NLPExecutionDevice",
    "NLPProviderEngineConfigV2",
    "NLPModelConfigV2",
    "NLPRuntimeConfigV2",
    "NLPProviderConfigurationV2",
    "NLPProvenanceConfigV2",
]


