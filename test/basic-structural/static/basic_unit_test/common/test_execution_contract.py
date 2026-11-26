"""Contract tests of the runtime execution contract (common/core/execution)."""

import asyncio
import threading
import time

import pytest

from ai_platform.common.core.execution import (
    CancellationToken,
    ErrorInfo,
    ExecutionCancelledError,
    ExecutionContext,
    ExecutionOutcome,
    ExecutionTimeoutError,
    PolicyViolationError,
    ResourceConflictError,
    ResourceManager,
    ResourceUnavailableError,
    RuntimePolicy,
    execute,
    execute_blocking,
)
from ai_platform.common.core.execution.conformance import check_execution_conformance


class ProviderInputError(Exception):
    """Stands for a provider's own error type (e.g. NLPProviderInputError)."""

    code = "provider_input_error"
    retryable = False

    def __init__(self, message):
        super().__init__(message)
        self.details = {"field": "text"}


# -- policy -------------------------------------------------------------------

def test_policy_validation_narrowing_and_devices():
    with pytest.raises(PolicyViolationError):
        RuntimePolicy(device="tpu")
    with pytest.raises(PolicyViolationError):
        RuntimePolicy(max_threads=0)
    provider = RuntimePolicy(max_threads=8, timeout_seconds=60, max_concurrency=2)
    request = RuntimePolicy(max_threads=2, timeout_seconds=300, device="cpu")
    combined = provider.narrow(request)
    assert (combined.max_threads, combined.timeout_seconds, combined.max_concurrency,
            combined.device) == (2, 60, 2, "cpu")
    with pytest.raises(PolicyViolationError):
        RuntimePolicy(device="cpu").narrow(RuntimePolicy(device="cuda:0"))
    assert RuntimePolicy(device="cuda:0").resolve_device(["cpu"]) == "cpu"
    with pytest.raises(PolicyViolationError):
        RuntimePolicy(device="cuda:0", allow_device_fallback=False).resolve_device(["cpu"])
    assert RuntimePolicy().resolve_device(["cpu", "cuda:0"]) == "cuda:0"


def test_policy_from_existing_runtime_section():
    class NLPRuntime:  # pylint: disable=too-few-public-methods
        """Same field names as NLPRuntimeConfigV2."""
        device, threads, batch_size = "cpu", 4, 16
        memory_limit_mb_hint, allow_device_fallback = 2048, False

    policy = RuntimePolicy.from_runtime_config(NLPRuntime(), timeout_seconds=30)
    assert (policy.max_threads, policy.batch_size, policy.memory_limit_mb,
            policy.allow_device_fallback, policy.timeout_seconds) == (4, 16, 2048, False, 30)
    assert not policy.memory_limit_enforced
    assert RuntimePolicy.from_runtime_config({"threads": 2}).max_threads == 2


# -- cancellation and context ------------------------------------------------------

def test_cancellation_token_once_callbacks_and_children():
    token, seen = CancellationToken(), []
    child = token.child()
    token.add_callback(seen.append)
    assert token.cancel("first") and not token.cancel("second")
    assert token.reason == "first" and seen == ["first"] and child.cancelled
    late = []
    token.add_callback(late.append)
    assert late == ["first"]
    with pytest.raises(ExecutionCancelledError):
        token.raise_if_cancelled("step")
    parent = CancellationToken()
    own = parent.child()
    own.cancel()
    assert not parent.cancelled


def test_context_deadline_children_and_labels():
    now = [100.0]
    context = ExecutionContext.create("nlp.analyze", timeout_seconds=10, clock=lambda: now[0],
                                      provider_id="stanza", request_id="r1")
    assert context.remaining_seconds() == 10
    child = context.child("nlp.tokenize", timeout_seconds=30, stage="tokenize")
    assert child.deadline == context.deadline and child.parent_id == context.execution_id
    assert child.labels["stage"] == "tokenize" and child.provider_id == "stanza"
    with pytest.raises(TypeError):
        context.labels["x"] = 1  # frozen
    now[0] = 111.0
    assert context.expired
    with pytest.raises(ExecutionTimeoutError):
        context.check("parse")
    context.cancellation.cancel("stop")
    assert child.cancellation.cancelled
    defaulted = ExecutionContext.create("x", policy=RuntimePolicy(timeout_seconds=5),
                                        clock=lambda: 0.0)
    assert defaulted.deadline == 5.0
    assert ExecutionContext.create("x").remaining_seconds() is None


# -- errors ---------------------------------------------------------------------

def test_error_info_reads_provider_errors_and_causes():
    try:
        try:
            raise ProviderInputError("text is empty")
        except ProviderInputError as inner:
            raise ExecutionTimeoutError("deadline", stage="analyze") from inner
    except ExecutionTimeoutError as exc:
        info = ErrorInfo.from_exception(exc)
    assert (info.code, info.retryable, info.stage) == ("execution_timeout", True, "analyze")
    assert info.cause.code == "provider_input_error" and info.cause.details == {"field": "text"}
    assert ErrorInfo.from_exception(ValueError("x")).code == "ValueError"
    assert info.to_dict()["cause"]["type"] == "ProviderInputError"


# -- resources ------------------------------------------------------------------

def test_shared_resource_created_once_and_closed_by_last_user():
    manager, created, closed = ResourceManager(), [], []

    def factory():
        time.sleep(0.05)
        created.append(1)
        return object()

    threads = [threading.Thread(target=manager.acquire, args=("pipeline:pl", factory,
                                                             closed.append)) for _ in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert created == [1] and manager.users("pipeline:pl") == 5
    for _ in range(4):
        manager.release("pipeline:pl", close_when_unused=True)
    assert not closed
    manager.release("pipeline:pl", close_when_unused=True)
    assert len(closed) == 1 and manager.users("pipeline:pl") == 0
    with manager.lease("ocr", lambda: "model", closer=closed.append) as value:
        assert value == "model"
    assert manager.close_all() == {} and closed[-1] == "model"


def test_slots_limit_and_queue_timeout():
    manager = ResourceManager()
    with manager.slot("stanza", 1):
        assert manager.slots_in_use("stanza") == 1
        with pytest.raises(ResourceUnavailableError):
            with manager.slot("stanza", 1, queue_timeout_seconds=0.1):
                pass
        context = ExecutionContext.create("x")
        context.cancellation.cancel()
        with pytest.raises(ExecutionCancelledError):
            with manager.slot("stanza", 1, context):
                pass
    assert manager.slots_in_use("stanza") == 0


def test_process_global_settings_conflict():
    manager = ResourceManager()
    assert manager.claim_setting("torch.num_threads", 4, "stanza")
    assert not manager.claim_setting("torch.num_threads", 4, "ocr")
    with pytest.raises(ResourceConflictError):
        manager.claim_setting("torch.num_threads", 8, "ocr")
    assert manager.claim_setting("torch.num_threads", 2, "stanza")  # its own claim
    manager.release_settings("stanza")
    assert manager.setting("torch.num_threads") is None


# -- executor -------------------------------------------------------------------

def test_execute_sync_work_records_metadata():
    def work(context, recorder):
        recorder.record_engine("stanza", "1.15.1")
        recorder.record_device("cpu", threads=4)
        recorder.note("tokens", 12)
        context.check("analyze")
        return "done"

    context = ExecutionContext.create("nlp.analyze", provider_id="stanza", request_id="r1",
                                      policy=RuntimePolicy(device="cpu"))
    result = execute_blocking(context, work, configuration_fingerprint="abc")
    meta = result.metadata
    assert result.value == "done" and meta.outcome is ExecutionOutcome.SUCCEEDED
    assert (meta.engine, meta.device_used, meta.threads, meta.extra["tokens"],
            meta.configuration_fingerprint, meta.request_id) == \
        ("stanza", "cpu", 4, 12, "abc", "r1")
    assert meta.to_dict()["outcome"] == "succeeded"


def test_provider_error_keeps_its_type_and_carries_metadata():
    def work(context, recorder):
        raise ProviderInputError("text is empty")

    with pytest.raises(ProviderInputError) as caught:
        execute_blocking(ExecutionContext.create("nlp.analyze"), work)
    meta = caught.value.execution_metadata
    assert meta.outcome is ExecutionOutcome.FAILED and meta.error.code == "provider_input_error"


def test_async_work_is_cancelled_for_real():
    stopped = []

    async def work(context, recorder):
        try:
            await asyncio.sleep(10)
        finally:
            stopped.append(True)

    async def scenario():
        context = ExecutionContext.create("ocr.recognize")
        asyncio.get_running_loop().call_later(0.05, context.cancellation.cancel, "user")
        with pytest.raises(ExecutionCancelledError) as caught:
            await execute(context, work)
        await asyncio.sleep(0)
        return caught.value

    error = asyncio.run(scenario())
    assert stopped == [True] and not error.execution_metadata.abandoned
    assert error.execution_metadata.outcome is ExecutionOutcome.CANCELLED


def test_cooperative_thread_stops_at_deadline_and_blocking_one_is_abandoned():
    def cooperative(context, recorder):
        while True:
            context.check("loop")
            time.sleep(0.01)

    def blocking(context, recorder):
        time.sleep(1.0)  # one library call that cannot be interrupted
        return "late"

    with pytest.raises(ExecutionTimeoutError) as coop:
        execute_blocking(ExecutionContext.create("x", timeout_seconds=0.1), cooperative)
    assert coop.value.execution_metadata.outcome is ExecutionOutcome.TIMED_OUT
    start = time.monotonic()
    with pytest.raises(ExecutionTimeoutError) as blocked:
        execute_blocking(ExecutionContext.create("x", timeout_seconds=0.1), blocking)
    # released at the deadline + the stop grace (0.1 + 0.25 s), not after the 1 s call
    assert time.monotonic() - start < 0.7
    assert blocked.value.execution_metadata.abandoned


def test_slot_of_abandoned_work_is_held_until_the_thread_ends():
    manager = ResourceManager()
    release = threading.Event()

    def blocking(context, recorder):
        release.wait(2)
        return "late"

    policy = RuntimePolicy(max_concurrency=1, queue_timeout_seconds=0.1)
    with pytest.raises(ExecutionTimeoutError):
        execute_blocking(ExecutionContext.create("x", timeout_seconds=0.1, policy=policy),
                         blocking, resources=manager, slot_key="engine")
    assert manager.slots_in_use("engine") == 1  # the thread still runs
    with pytest.raises(ResourceUnavailableError):
        execute_blocking(ExecutionContext.create("x", policy=policy), lambda c, r: "next",
                         resources=manager, slot_key="engine")
    release.set()
    deadline = time.monotonic() + 2
    while manager.slots_in_use("engine") and time.monotonic() < deadline:
        time.sleep(0.01)
    assert manager.slots_in_use("engine") == 0
    result = execute_blocking(ExecutionContext.create("x", policy=policy), lambda c, r: "next",
                              resources=manager, slot_key="engine")
    assert result.value == "next" and "slot:engine" in result.metadata.resources


def test_conformance_check_tells_cooperative_from_blocking_engines():
    def cooperative(context, recorder):
        for _ in range(100):
            context.check("step")
            time.sleep(0.01)

    def quick(context, recorder):
        recorder.record_engine("fake", "1")
        recorder.record_device("cpu")

    def failing(context, recorder):
        raise ProviderInputError("bad")

    good = asyncio.run(check_execution_conformance(cooperative, quick_work=quick,
                                                   failing_work=failing,
                                                   expected_error=ProviderInputError))
    assert good.ok, good.problems
    bad = asyncio.run(check_execution_conformance(lambda c, r: time.sleep(1.0), grace=0.1))
    assert not bad.results["honours_cancellation"] and not bad.ok
