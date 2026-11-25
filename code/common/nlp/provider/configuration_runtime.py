#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Configuration-driven NLP provider runtime entry point.

Responsibilities:
- load and resolve provider configuration;
- initialize the resolved provider through NLPProviderLifecycle;
- return an immutable execution-preparation result.

Provider registration remains explicit and external.
Engine-specific configuration application is not performed here.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .configuration_service import (
    NLPProviderConfigurationService,
)
from .lifecycle import (
    NLPProviderLifecycle,
    NLPProviderLifecycleSnapshot,
)
from .resolver import NLPProviderResolution


@dataclass(frozen=True)
class NLPProviderConfiguredRuntime:
    """Result of configuration resolution and lifecycle initialization."""

    resolution: NLPProviderResolution
    lifecycle_snapshot: NLPProviderLifecycleSnapshot

    @property
    def provider_id(self) -> str:
        return self.resolution.provider_id

    @property
    def configuration_fingerprint(self) -> str:
        return self.resolution.configuration_fingerprint


class NLPProviderConfigurationRuntime:
    """
    Coordinate configuration resolution with provider lifecycle.

    The provider must already be explicitly registered through
    the same NLPProviderLifecycle instance.
    """

    def __init__(
        self,
        configuration_service: NLPProviderConfigurationService,
        lifecycle: NLPProviderLifecycle,
    ) -> None:
        if not isinstance(
            configuration_service,
            NLPProviderConfigurationService,
        ):
            raise TypeError(
                "configuration_service must be "
                "NLPProviderConfigurationService."
            )

        if not isinstance(lifecycle, NLPProviderLifecycle):
            raise TypeError(
                "lifecycle must be NLPProviderLifecycle."
            )

        self._configuration_service = configuration_service
        self._lifecycle = lifecycle

    async def initialize_from_configuration(
        self,
        source: Mapping[str, Any] | str | Path,
        *,
        environ: Mapping[str, str] | None = None,
    ) -> NLPProviderConfiguredRuntime:
        """
        Load, resolve and initialize a previously registered provider.

        Original loader, resolver and lifecycle exceptions are
        deliberately propagated without flattening their types.
        """
        resolution = (
            self._configuration_service.load_and_resolve(
                source,
                environ=environ,
            )
        )

        snapshot = await self._lifecycle.initialize_resolution(
            resolution
        )

        return NLPProviderConfiguredRuntime(
            resolution=resolution,
            lifecycle_snapshot=snapshot,
        )


__all__ = [
    "NLPProviderConfiguredRuntime",
    "NLPProviderConfigurationRuntime",
]
