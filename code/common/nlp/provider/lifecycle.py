
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

Stage 8C - runtime execution contract (ai_platform.common.core.execution):
- every analysis runs through ``execute()`` in an ExecutionContext with a
  deadline, a cancellation token and the provider's RuntimePolicy (from the
  configuration's runtime section, or given at registration), narrowed by
  the caller's policy;
- ``max_concurrency`` of the policy is enforced with a slot per provider in a
  ResourceManager shared by this lifecycle;
- ``analyze_with_context`` returns the response with ExecutionMetadata;
  ``analyze`` keeps its old signature and result;
- providers implementing ``analyze_in_context`` are given the context and a
  recorder; others are awaited as before, and on a timeout their call keeps
  running (shielded) until it really ends - ``close()`` waits for it and the
  metadata says ``abandoned``;
- timeouts and cancellations reach the caller as NLPProviderTimeoutError /
  NLPProviderCancelledError, provider errors with their own types; all of
  them carry ``execution_metadata``.

The central PluginRegistry remains responsible only for storage
and retrieval. This module does not modify its behavior.
"""

from __future__ import annotations

import asyncio
import inspect

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Callable

from ai_platform.common.core.execution import (
    CancellationToken,
    ExecutionContext,
    ExecutionRecorder,
    ResourceManager,
    RuntimePolicy,
    execute,
)
from ai_platform.common.core.registry.registry_contract import (
    RegistryContract,
)

from .errors import NLPProviderUnavailableError
from .execution import (
    ANALYZE_OPERATION,
    ContextAwareNLPProvider,
    NLPExecutionResult,
    as_nlp_error,
    mark_abandoned,
)
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
class _ProviderRecord:  # pylint: disable=too-many-instance-attributes
    """Internal mutable lifecycle record."""

    provider_id: str
    provider: NLPProvider
    state: NLPProviderLifecycleState
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    shutdown_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    drained: asyncio.Event = field(default_factory=asyncio.Event)
    active_analyses: int = 0
    last_error: str | None = None
    # Stage 8C: execution policy and configuration identity of the provider.
    policy: RuntimePolicy = field(default_factory=RuntimePolicy)
    configuration_fingerprint: str | None = None

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
        resources: ResourceManager | None = None,
    ) -> None:
        if not isinstance(registry, RegistryContract):
            raise TypeError(
                "registry must implement RegistryContract."
            )

        self._registry = registry
        self._records: dict[str, _ProviderRecord] = {}
        # Shared by every provider of this lifecycle: concurrency slots,
        # shared engine objects, process-global setting claims.
        self.resources = resources or ResourceManager()

    def register(
        self,
        provider: NLPProvider,
        policy: RuntimePolicy | None = None,
    ) -> NLPProviderLifecycleSnapshot:
        """
        Explicitly register a provider.

        The underlying provider is stored in PluginRegistry
        through NLPProviderPlugin. ``policy`` is the provider's execution
        policy (stage 8C); a configuration resolved later narrows it.
        """

        plugin = NLPProviderPlugin(provider)
        provider_id = plugin.provider_id

        if provider_id in self._records:
            raise ValueError(
                f"Provider '{provider_id}' is already managed."
            )

        plugin.register(self._registry)

        # Stage 8D: providers that share engine resources get the manager.
        bind = getattr(provider, "bind_execution_resources", None)
        if callable(bind):
            bind(self.resources)

        record = _ProviderRecord(
            provider_id=provider_id,
            provider=provider,
            state=NLPProviderLifecycleState.REGISTERED,
            lock=asyncio.Lock(),
            policy=policy or RuntimePolicy(),
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

    async def initialize_resolution(
        self,
        resolution: Any,
    ) -> NLPProviderLifecycleSnapshot:
        """
        Initialize a provider represented by a validated resolution.

        The provider must already be explicitly managed by this
        lifecycle instance. The method never registers providers.

        The resolution must refer to the exact provider object managed
        by this lifecycle and registered in its central registry.

        Configuration is validated and retained as resolution metadata.
        Engine-specific configuration application is not performed here.
        """
        from .resolver import NLPProviderResolution
        from .errors import NLPProviderConfigurationError

        if not isinstance(resolution, NLPProviderResolution):
            raise TypeError(
                "resolution must be NLPProviderResolution."
            )

        expected_key = (
            f"{NLPProviderPlugin.KEY_PREFIX}{resolution.provider_id}"
        )

        if resolution.registry_key != expected_key:
            raise NLPProviderConfigurationError(
                "Resolution contains an invalid registry key.",
                provider_id=resolution.provider_id,
                details={
                    "expected_registry_key": expected_key,
                    "actual_registry_key": resolution.registry_key,
                },
            )

        if (
            resolution.configuration.provider_id
            != resolution.provider_id
        ):
            raise NLPProviderConfigurationError(
                "Resolution configuration provider_id mismatch.",
                provider_id=resolution.provider_id,
            )

        if (
            resolution.configuration_fingerprint
            != resolution.configuration.fingerprint_sha256
        ):
            raise NLPProviderConfigurationError(
                "Resolution configuration fingerprint mismatch.",
                provider_id=resolution.provider_id,
            )

        record = self._get_record(resolution.provider_id)

        if record.provider is not resolution.provider:
            raise NLPProviderUnavailableError(
                "Resolved provider is not the provider managed "
                "by this lifecycle instance.",
                provider_id=resolution.provider_id,
                details={
                    "state": record.state.value,
                    "reason": "provider_identity_mismatch",
                },
            )

        # Stage 8C: the configuration's runtime section becomes the policy.
        record.policy = record.policy.narrow(
            RuntimePolicy.from_runtime_config(
                resolution.configuration.runtime
            )
        )
        record.configuration_fingerprint = (
            resolution.configuration_fingerprint
        )

        registered_provider = self._registry.get(expected_key)

        if registered_provider is not resolution.provider:
            raise NLPProviderUnavailableError(
                "Resolved provider does not match the object "
                "currently stored in the central registry.",
                provider_id=resolution.provider_id,
                details={
                    "registry_key": expected_key,
                    "reason": "registry_identity_mismatch",
                },
            )

        return await self.initialize(resolution.provider_id)

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
        Runs under the execution contract with the provider's policy;
        use ``analyze_with_context`` to also get the execution metadata.
        """
        result = await self.analyze_with_context(provider_id, request)
        return result.response

    async def analyze_with_context(  # pylint: disable=too-many-arguments
        self,
        provider_id: str,
        request: NLPProviderRequest,
        *,
        context: ExecutionContext | None = None,
        timeout_seconds: float | None = None,
        policy: RuntimePolicy | None = None,
        cancellation: CancellationToken | None = None,
    ) -> NLPExecutionResult:
        """
        Execute analysis under the runtime execution contract (stage 8C).

        Without ``context`` one is created: the provider's policy narrowed
        by ``policy``, the deadline from ``timeout_seconds`` (else the
        policy's timeout), and ``cancellation`` if given. With ``context``
        its policy is narrowed by the provider's (a caller cannot loosen it).
        """
        await self.initialize(provider_id)
        record = self._get_record(provider_id)
        if context is None:
            context = ExecutionContext.create(
                ANALYZE_OPERATION,
                timeout_seconds=timeout_seconds,
                policy=record.policy.narrow(policy),
                cancellation=cancellation,
                provider_id=provider_id,
                request_id=request.request_id,
            )
        else:
            context = context.child(
                ANALYZE_OPERATION,
                timeout_seconds=timeout_seconds,
                policy=record.policy.narrow(policy),
            )

        provider = self._registry.get(
            f"{NLPProviderPlugin.KEY_PREFIX}{provider_id}"
        )

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

        inner: list[asyncio.Future] = []

        async def work(ctx: ExecutionContext, recorder: ExecutionRecorder):
            if isinstance(provider, ContextAwareNLPProvider):
                return await provider.analyze_in_context(request, ctx, recorder)
            recorder.note("context_aware", False)
            # Shielded: on a timeout the provider's call keeps running and
            # is still counted as active until it really ends.
            call = asyncio.ensure_future(provider.analyze(request))
            inner.append(call)
            return await asyncio.shield(call)

        try:
            result = await execute(
                context,
                work,
                resources=self.resources,
                slot_key=f"nlp:{provider_id}",
                configuration_fingerprint=record.configuration_fingerprint,
            )
        except BaseException as exc:
            if inner and not inner[0].done():
                mark_abandoned(exc)
                inner[0].add_done_callback(
                    lambda call: self._finish_abandoned(record, call)
                )
            else:
                await self._finish_analysis(record)
            translated = as_nlp_error(exc, provider_id)
            if translated is exc:
                raise
            raise translated from exc
        await self._finish_analysis(record)
        return NLPExecutionResult(result.value, result.metadata)

    async def _finish_analysis(self, record: _ProviderRecord) -> None:
        """One analysis fewer; the last one lets close() continue."""
        async with record.lock:
            record.active_analyses -= 1
            if record.active_analyses == 0:
                record.drained.set()

    def _finish_abandoned(
        self,
        record: _ProviderRecord,
        call: asyncio.Future,
    ) -> None:
        """Done-callback of a provider call that outlived its deadline."""
        if not call.cancelled():
            call.exception()  # retrieved: the late result is dropped on purpose
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


