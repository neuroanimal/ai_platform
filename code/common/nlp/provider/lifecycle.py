
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Lifecycle management for NLP providers.

Responsibilities:
- explicit provider registration;
- initialization and readiness;
- health checks;
- analysis execution;
- graceful shutdown.

The central PluginRegistry remains responsible only for storage
and retrieval. This module does not modify its behavior.
"""

from __future__ import annotations

import asyncio
import inspect

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Callable

from ai_platform.common.core.registry.registry_contract import (
    RegistryContract,
)

from .errors import NLPProviderUnavailableError
from .plugin import NLPProviderPlugin
from .protocol import NLPProvider
from .request import NLPProviderRequest
from .response import NLPProviderResponse


class NLPProviderLifecycleState(StrEnum):
    """Runtime state of a registered NLP provider."""

    REGISTERED = "registered"
    INITIALIZING = "initializing"
    READY = "ready"
    FAILED = "failed"
    CLOSING = "closing"
    CLOSED = "closed"


@dataclass(frozen=True)
class NLPProviderLifecycleSnapshot:
    """Read-only public view of a provider lifecycle state."""

    provider_id: str
    state: NLPProviderLifecycleState
    last_error: str | None = None

@dataclass
class _ProviderRecord:
    """Internal mutable lifecycle record."""

    provider_id: str
    provider: NLPProvider
    state: NLPProviderLifecycleState
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    shutdown_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    drained: asyncio.Event = field(default_factory=asyncio.Event)
    active_analyses: int = 0
    last_error: str | None = None

class NLPProviderLifecycle:
    """
    Manage NLP provider lifecycle through the central registry.

    Optional provider hooks:
        initialize() -> None
        health_check() -> bool
        close() -> None

    Each hook may be synchronous or asynchronous.

    Providers without lifecycle hooks are supported.
    Such providers become READY after explicit initialization.
    """

    def __init__(
        self,
        registry: RegistryContract,
    ) -> None:
        if not isinstance(registry, RegistryContract):
            raise TypeError(
                "registry must implement RegistryContract."
            )

        self._registry = registry
        self._records: dict[str, _ProviderRecord] = {}

    def register(
        self,
        provider: NLPProvider,
    ) -> NLPProviderLifecycleSnapshot:
        """
        Explicitly register a provider.

        The underlying provider is stored in PluginRegistry
        through NLPProviderPlugin.
        """

        plugin = NLPProviderPlugin(provider)
        provider_id = plugin.provider_id

        if provider_id in self._records:
            raise ValueError(
                f"Provider '{provider_id}' is already managed."
            )

        plugin.register(self._registry)

        record = _ProviderRecord(
            provider_id=provider_id,
            provider=provider,
            state=NLPProviderLifecycleState.REGISTERED,
            lock=asyncio.Lock(),
        )
        record.drained.set()
        self._records[provider_id] = record

        return self._snapshot(record)

    def get_snapshot(
        self,
        provider_id: str,
    ) -> NLPProviderLifecycleSnapshot:
        """Return an immutable lifecycle state snapshot."""

        record = self._get_record(provider_id)
        return self._snapshot(record)

    def list_states(
        self,
    ) -> dict[str, NLPProviderLifecycleSnapshot]:
        """Return snapshots for all managed providers."""

        return {
            provider_id: self._snapshot(record)
            for provider_id, record in self._records.items()
        }

    def get_provider(
        self,
        provider_id: str,
    ) -> NLPProvider:
        """
        Retrieve a provider only when its lifecycle state is READY.
        """

        record = self._get_record(provider_id)

        if record.state != NLPProviderLifecycleState.READY:
            raise NLPProviderUnavailableError(
                (
                    f"Provider '{provider_id}' is not ready. "
                    f"Current state: '{record.state.value}'."
                ),
                provider_id=provider_id,
                details={
                    "state": record.state.value,
                    "last_error": record.last_error,
                },
            )

        # Registry remains the source of registered provider objects.
        return self._registry.get(
            f"{NLPProviderPlugin.KEY_PREFIX}{provider_id}"
        )

    async def initialize(
        self,
        provider_id: str,
    ) -> NLPProviderLifecycleSnapshot:
        """Initialize one provider and verify its readiness."""

        record = self._get_record(provider_id)

        async with record.lock:
            if record.state == NLPProviderLifecycleState.READY:
                return self._snapshot(record)

            if record.state in {
                NLPProviderLifecycleState.CLOSING,
                NLPProviderLifecycleState.CLOSED,
            }:
                raise NLPProviderUnavailableError(
                    f"Provider '{provider_id}' cannot be initialized "
                    f"from state '{record.state.value}'.",
                    provider_id=provider_id,
                    details={
                        "state": record.state.value,
                    },
                )

            record.state = NLPProviderLifecycleState.INITIALIZING
            record.last_error = None

            try:
                await self._invoke_optional_hook(
                    record.provider,
                    "initialize",
                )

                healthy = await self._run_health_check(record)

                if not healthy:
                    raise RuntimeError(
                        "Provider health check returned False."
                    )

                record.state = NLPProviderLifecycleState.READY

            except Exception as exc:
                record.state = NLPProviderLifecycleState.FAILED
                record.last_error = (
                    f"{type(exc).__name__}: {exc}"
                )

                raise NLPProviderUnavailableError(
                    f"Provider '{provider_id}' initialization failed.",
                    provider_id=provider_id,
                    details={
                        "stage": "initialize",
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    },
                ) from exc

            return self._snapshot(record)

    async def initialize_all(
        self,
    ) -> dict[str, NLPProviderLifecycleSnapshot]:
        """Initialize all registered providers sequentially."""

        for provider_id in self._records:
            await self.initialize(provider_id)

        return self.list_states()

    async def check_health(
        self,
        provider_id: str,
    ) -> bool:
        """Execute a provider health check."""

        record = self._get_record(provider_id)

        async with record.lock:
            if record.state != NLPProviderLifecycleState.READY:
                raise NLPProviderUnavailableError(
                    f"Provider '{provider_id}' is not ready.",
                    provider_id=provider_id,
                    details={
                        "state": record.state.value,
                    },
                )

            try:
                healthy = await self._run_health_check(record)

                if not healthy:
                    raise RuntimeError(
                        "Provider health check returned False."
                    )

                return True

            except Exception as exc:
                record.state = NLPProviderLifecycleState.FAILED
                record.last_error = (
                    f"{type(exc).__name__}: {exc}"
                )

                raise NLPProviderUnavailableError(
                    f"Provider '{provider_id}' health check failed.",
                    provider_id=provider_id,
                    details={
                        "stage": "health_check",
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    },
                ) from exc

    async def analyze(
        self,
        provider_id: str,
        request: NLPProviderRequest,
    ) -> NLPProviderResponse:
        """
        Execute analysis through a READY provider.

        Initialization is automatic on first use.
        Shutdown waits for all active analyses to finish.
        """

        await self.initialize(provider_id)

        record = self._get_record(provider_id)

        async with record.lock:
            if record.state != NLPProviderLifecycleState.READY:
                raise NLPProviderUnavailableError(
                    f"Provider '{provider_id}' is not ready.",
                    provider_id=provider_id,
                    details={
                        "state": record.state.value,
                    },
                )

            record.active_analyses += 1
            record.drained.clear()

        try:
            provider = self._registry.get(
                f"{NLPProviderPlugin.KEY_PREFIX}{provider_id}"
            )

            return await provider.analyze(request)

        finally:
            async with record.lock:
                record.active_analyses -= 1

                if record.active_analyses == 0:
                    record.drained.set()

    async def close(
        self,
        provider_id: str,
    ) -> NLPProviderLifecycleSnapshot:
        """Gracefully close one provider after active analyses finish."""

        record = self._get_record(provider_id)

        async with record.shutdown_lock:

            async with record.lock:
                if record.state == NLPProviderLifecycleState.CLOSED:
                    return self._snapshot(record)

                previous_state = record.state

                if previous_state == NLPProviderLifecycleState.CLOSING:
                    raise NLPProviderUnavailableError(
                        f"Provider '{provider_id}' is already closing.",
                        provider_id=provider_id,
                    )

                record.state = NLPProviderLifecycleState.CLOSING

            try:
                # Wait until all active analyze() calls have finished.
                await record.drained.wait()

                if previous_state != NLPProviderLifecycleState.REGISTERED:
                    await self._invoke_optional_hook(
                        record.provider,
                        "close",
                    )

                async with record.lock:
                    record.state = NLPProviderLifecycleState.CLOSED
                    record.last_error = None

                    return self._snapshot(record)

            except Exception as exc:
                async with record.lock:
                    record.state = NLPProviderLifecycleState.FAILED
                    record.last_error = (
                        f"{type(exc).__name__}: {exc}"
                    )

                raise NLPProviderUnavailableError(
                    f"Provider '{provider_id}' shutdown failed.",
                    provider_id=provider_id,
                    details={
                        "stage": "close",
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    },
                ) from exc

    async def close_all(
        self,
    ) -> dict[str, NLPProviderLifecycleSnapshot]:
        """
        Close all providers in reverse registration order.

        A failure in one provider does not prevent attempts to
        close the remaining providers.
        """

        errors: dict[str, str] = {}

        for provider_id in reversed(list(self._records)):
            try:
                await self.close(provider_id)
            except NLPProviderUnavailableError as exc:
                errors[provider_id] = str(exc)

        if errors:
            raise NLPProviderUnavailableError(
                "One or more NLP providers could not be closed.",
                details={
                    "provider_errors": errors,
                },
            )

        return self.list_states()

    async def _run_health_check(
        self,
        record: _ProviderRecord,
    ) -> bool:
        """Run optional provider health check."""

        hook = getattr(
            record.provider,
            "health_check",
            None,
        )

        if not callable(hook):
            return True

        result = await self._invoke_hook(hook)

        return result is not False

    async def _invoke_optional_hook(
        self,
        provider: NLPProvider,
        hook_name: str,
    ) -> Any:
        """Invoke an optional lifecycle hook."""

        hook = getattr(provider, hook_name, None)

        if not callable(hook):
            return None

        return await self._invoke_hook(hook)

    @staticmethod
    async def _invoke_hook(
        hook: Callable[..., Any],
    ) -> Any:
        """
        Invoke a synchronous or asynchronous hook.

        Synchronous hooks run in a worker thread to avoid blocking
        the event loop.
        """

        if inspect.iscoroutinefunction(hook):
            return await hook()

        result = await asyncio.to_thread(hook)

        if inspect.isawaitable(result):
            return await result

        return result

    def _get_record(
        self,
        provider_id: str,
    ) -> _ProviderRecord:
        """Resolve an internal provider record."""

        record = self._records.get(provider_id)

        if record is None:
            raise NLPProviderUnavailableError(
                f"Provider '{provider_id}' is not managed.",
                provider_id=provider_id,
                details={
                    "state": "unregistered",
                },
            )

        return record

    @staticmethod
    def _snapshot(
        record: _ProviderRecord,
    ) -> NLPProviderLifecycleSnapshot:
        """Create an immutable public state snapshot."""

        return NLPProviderLifecycleSnapshot(
            provider_id=record.provider_id,
            state=record.state,
            last_error=record.last_error,
        )


