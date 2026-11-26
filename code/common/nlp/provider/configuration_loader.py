
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
YAML and environment configuration loader for NLP providers.

Responsibilities:
- load configuration from YAML or Python mappings;
- apply explicit environment variable overrides;
- reject unknown NLP environment variables;
- validate the final configuration through NLPProviderConfigurationV2;
- avoid exposing configuration values in loader errors;
- never resolve secrets or initialize/download provider models.
"""

from __future__ import annotations

import copy
import math
import os
import re

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .configuration_v2 import NLPProviderConfigurationV2


ENV_PREFIX = "AI_PLATFORM_NLP__"


class NLPConfigurationLoadError(ValueError):
    """Raised when NLP provider configuration cannot be loaded."""

    def __init__(self, source: str, detail: str) -> None:
        self.source = source
        self.detail = detail
        super().__init__(f"{source}: {detail}")


# Each entry maps an environment variable suffix to:
# (configuration path, parser).
#
# Parsers deliberately accept only unambiguous representations.
def _parse_string(value: str) -> str:
    return value


def _parse_integer(value: str) -> int:
    normalized = value.strip()

    if not re.fullmatch(r"[+-]?[0-9]+", normalized):
        raise ValueError("expected an integer")

    return int(normalized)


def _parse_float(value: str) -> float:
    normalized = value.strip()

    try:
        parsed = float(normalized)
    except ValueError as error:
        raise ValueError("expected a number") from error

    if not math.isfinite(parsed):
        raise ValueError("expected a finite number")

    return parsed


def _parse_boolean(value: str) -> bool:
    normalized = value.strip().casefold()

    if normalized == "true":
        return True

    if normalized == "false":
        return False

    raise ValueError("expected 'true' or 'false'")


_ENVIRONMENT_FIELDS = {
    "PROVIDER_ID": (("provider_id",), _parse_string),

    "ENGINE__ENGINE_NAME": (
        ("engine", "engine_name"),
        _parse_string,
    ),
    "ENGINE__API_KEY_ENV": (
        ("engine", "api_key_env"),
        _parse_string,
    ),

    "MODEL__MODEL_ID": (
        ("model", "model_id"),
        _parse_string,
    ),
    "MODEL__PACKAGE": (
        ("model", "package"),
        _parse_string,
    ),
    "MODEL__VERSION": (
        ("model", "version"),
        _parse_string,
    ),
    "MODEL__LANGUAGE": (
        ("model", "language"),
        _parse_string,
    ),
    "MODEL__MODEL_DIR": (
        ("model", "model_dir"),
        _parse_string,
    ),
    "MODEL__DOWNLOAD_POLICY": (
        ("model", "download_policy"),
        _parse_string,
    ),

    "RUNTIME__DEVICE": (
        ("runtime", "device"),
        _parse_string,
    ),
    "RUNTIME__THREADS": (
        ("runtime", "threads"),
        _parse_integer,
    ),
    "RUNTIME__BATCH_SIZE": (
        ("runtime", "batch_size"),
        _parse_integer,
    ),
    "RUNTIME__MAX_CONCURRENCY": (
        ("runtime", "max_concurrency"),
        _parse_integer,
    ),
    "RUNTIME__TIMEOUT_SECONDS": (
        ("runtime", "timeout_seconds"),
        _parse_float,
    ),
    "RUNTIME__QUEUE_TIMEOUT_SECONDS": (
        ("runtime", "queue_timeout_seconds"),
        _parse_float,
    ),
    "RUNTIME__MEMORY_LIMIT_MB_HINT": (
        ("runtime", "memory_limit_mb_hint"),
        _parse_integer,
    ),
    "RUNTIME__ALLOW_DEVICE_FALLBACK": (
        ("runtime", "allow_device_fallback"),
        _parse_boolean,
    ),
    "PROVENANCE__ACTOR_TYPE": (
        ("provenance", "actor_type"),
        _parse_string,
    ),
    "PROVENANCE__ACTOR_ID": (
        ("provenance", "actor_id"),
        _parse_string,
    ),
    "PROVENANCE__METHOD": (
        ("provenance", "method"),
        _parse_string,
    ),
    "PROVENANCE__NOTES": (
        ("provenance", "notes"),
        _parse_string,
    ),
}
# Sample values:
# AI_PLATFORM_NLP__PROVENANCE__ACTOR_TYPE=model
# AI_PLATFORM_NLP__PROVENANCE__ACTOR_ID=nlp-engine-01
# AI_PLATFORM_NLP__PROVENANCE__METHOD=Stanza neural pipeline, Polish PDB
# AI_PLATFORM_NLP__PROVENANCE__NOTES=Local model installation


def _validation_error_detail(error: ValidationError) -> str:
    """Build a validation message without including rejected input values."""

    details: list[str] = []

    for item in error.errors(include_input=False):
        location = ".".join(str(part) for part in item["loc"])
        message = item["msg"]

        if location:
            details.append(f"{location}: {message}")
        else:
            details.append(message)

    return "; ".join(details) or "configuration validation failed"


def _set_nested_value(
    data: dict[str, Any],
    path: tuple[str, ...],
    value: Any,
) -> None:
    """Set a nested configuration value, creating missing mappings."""

    current = data

    for key in path[:-1]:
        existing = current.get(key)

        if existing is None:
            existing = {}
            current[key] = existing

        if not isinstance(existing, dict):
            raise ValueError(
                f"configuration path '{'.'.join(path)}' "
                "has a non-mapping parent"
            )

        current = existing

    current[path[-1]] = value


class NLPProviderConfigurationLoader:
    """Load and validate NLP provider configuration."""

    @staticmethod
    def apply_env_overrides(
        data: Mapping[str, Any],
        *,
        environ: Mapping[str, str] | None = None,
        source: str = "<mapping>",
    ) -> dict[str, Any]:
        """
        Apply explicitly supported environment overrides.

        Only variables beginning with ENV_PREFIX are considered.
        Unknown variables using that prefix are rejected.
        """

        environment = os.environ if environ is None else environ

        try:
            result = copy.deepcopy(dict(data))
        except Exception as error:
            raise NLPConfigurationLoadError(
                source,
                "configuration mapping could not be copied",
            ) from error

        if not isinstance(result, dict):
            raise NLPConfigurationLoadError(
                source,
                "configuration root must be a mapping",
            )

        for variable_name, raw_value in environment.items():
            if not variable_name.startswith(ENV_PREFIX):
                continue

            suffix = variable_name[len(ENV_PREFIX):]

            if suffix not in _ENVIRONMENT_FIELDS:
                raise NLPConfigurationLoadError(
                    source,
                    f"unsupported environment variable: {variable_name}",
                )

            path, parser = _ENVIRONMENT_FIELDS[suffix]

            try:
                parsed_value = parser(raw_value)
                _set_nested_value(result, path, parsed_value)
            except (TypeError, ValueError) as error:
                raise NLPConfigurationLoadError(
                    source,
                    f"invalid value for environment variable "
                    f"{variable_name}: {error}",
                ) from error

        return result

    @classmethod
    def from_dict(
        cls,
        data: Mapping[str, Any],
        *,
        environ: Mapping[str, str] | None = None,
        source: str = "<mapping>",
    ) -> NLPProviderConfigurationV2:
        """Load configuration from a Python mapping."""

        if not isinstance(data, Mapping):
            raise NLPConfigurationLoadError(
                source,
                "configuration root must be a mapping",
            )

        merged = cls.apply_env_overrides(
            data,
            environ=environ,
            source=source,
        )

        try:
            return NLPProviderConfigurationV2.from_dict(merged)
        except ValidationError as error:
            raise NLPConfigurationLoadError(
                source,
                _validation_error_detail(error),
            ) from error

    @classmethod
    def from_yaml(
        cls,
        path: str | Path,
        *,
        environ: Mapping[str, str] | None = None,
    ) -> NLPProviderConfigurationV2:
        """Load configuration from a YAML file."""

        config_path = Path(path).expanduser()
        source = str(config_path)

        try:
            import yaml
        except ImportError as error:
            raise NLPConfigurationLoadError(
                source,
                "PyYAML is required for YAML configuration loading",
            ) from error

        try:
            with config_path.open("r", encoding="utf-8") as file:
                data = yaml.safe_load(file)
        except FileNotFoundError as error:
            raise NLPConfigurationLoadError(
                source,
                "configuration file does not exist",
            ) from error
        except PermissionError as error:
            raise NLPConfigurationLoadError(
                source,
                "configuration file cannot be read",
            ) from error
        except OSError as error:
            raise NLPConfigurationLoadError(
                source,
                "configuration file read failed",
            ) from error
        except yaml.YAMLError as error:
            raise NLPConfigurationLoadError(
                source,
                "invalid YAML syntax",
            ) from error

        if data is None:
            raise NLPConfigurationLoadError(
                source,
                "configuration file is empty",
            )

        if not isinstance(data, Mapping):
            raise NLPConfigurationLoadError(
                source,
                "YAML root must be a mapping",
            )

        return cls.from_dict(
            data,
            environ=environ,
            source=source,
        )

    @classmethod
    def load(
        cls,
        source: Mapping[str, Any] | str | Path,
        *,
        environ: Mapping[str, str] | None = None,
    ) -> NLPProviderConfigurationV2:
        """
        Load configuration from either a mapping or a YAML file path.

        Strings and Path objects are interpreted as YAML file paths.
        """

        if isinstance(source, Mapping):
            return cls.from_dict(
                source,
                environ=environ,
            )

        if isinstance(source, (str, Path)):
            return cls.from_yaml(
                source,
                environ=environ,
            )

        raise NLPConfigurationLoadError(
            "<unknown>",
            "source must be a mapping, string path, or Path object",
        )


__all__ = [
    "ENV_PREFIX",
    "NLPConfigurationLoadError",
    "NLPProviderConfigurationLoader",
]

