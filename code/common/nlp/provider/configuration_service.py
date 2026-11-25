#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Application-facing NLP provider configuration service.

Responsibilities:
- load and validate provider configuration;
- resolve the configured provider through the central registry;
- expose one controlled load-and-resolve entry point.

This service does not:
- register providers;
- initialize providers or models;
- execute NLP analysis;
- manage provider lifecycle.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ai_platform.common.core.registry.registry_contract import (
    RegistryContract,
)

from .configuration_loader import (
    NLPProviderConfigurationLoader,
)
from .configuration_v2 import NLPProviderConfigurationV2
from .resolver import (
    NLPProviderConfigurationResolver,
    NLPProviderResolution,
)


class NLPProviderConfigurationService:
    """Application-facing facade for configuration loading and resolution."""

    def __init__(
        self,
        registry: RegistryContract,
    ) -> None:
        self._loader = NLPProviderConfigurationLoader
        self._resolver = NLPProviderConfigurationResolver(registry)

    def load(
        self,
        source: Mapping[str, Any] | str | Path,
        *,
        environ: Mapping[str, str] | None = None,
    ) -> NLPProviderConfigurationV2:
        """
        Load configuration from a mapping or YAML path.

        NLPConfigurationLoadError is propagated unchanged.
        """
        return self._loader.load(
            source,
            environ=environ,
        )

    def resolve(
        self,
        configuration: NLPProviderConfigurationV2,
    ) -> NLPProviderResolution:
        """
        Resolve a previously loaded configuration.

        Resolver exceptions are propagated unchanged.
        """
        return self._resolver.resolve(configuration)

    def load_and_resolve(
        self,
        source: Mapping[str, Any] | str | Path,
        *,
        environ: Mapping[str, str] | None = None,
    ) -> NLPProviderResolution:
        """
        Execute the complete configuration loading and resolution flow.

        Error boundaries remain explicit:
        - NLPConfigurationLoadError: loading or configuration validation;
        - NLPProviderUnavailableError: provider not registered;
        - NLPProviderConfigurationError: provider/configuration incompatibility.
        """
        configuration = self.load(
            source,
            environ=environ,
        )

        return self.resolve(configuration)


__all__ = [
    "NLPProviderConfigurationService",
]
