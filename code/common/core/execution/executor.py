"""
Execute one unit of engine work under an ExecutionContext.

``await execute(context, work)`` is the single place where deadline,
cancellation, concurrency slot, metadata and error propagation come
together, for any engine:

- ``work(context, recorder)`` may be ``async`` or a plain function. A plain
  function runs in its own daemon worker thread, so a blocking engine does
  not stop the event loop and an abandoned call never blocks the caller.
- Before starting, the context is checked; with ``slot_key`` and a policy
  ``max_concurrency`` one slot is taken from the ``ResourceManager`` (waiting
  honours cancellation, deadline and ``queue_timeout_seconds``).
- The caller waits at most until the deadline, and stops waiting as soon as
  the token is cancelled. Async work is then cancelled for real. Thread work
  cannot be killed: it gets ``stop_grace_seconds`` to stop at its next
  ``context.check``; if it does not, its late result is discarded, the metadata says
  ``abandoned=True``, and the slot stays held until the thread ends - so the
  concurrency limit stays true even for work that does not cooperate.
- Errors follow ``errors``: the engine's own exceptions keep their type;
  the deadline becomes ``ExecutionTimeoutError``, cancellation
  ``ExecutionCancelledError``. Every exception that leaves here carries
  ``execution_metadata``.

``execute_blocking`` runs the same for callers without an event loop.
"""

import asyncio
import inspect
import threading
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Generic, Optional, TypeVar, Union

from ai_platform.common.core.execution.context import ExecutionContext
from ai_platform.common.core.execution.errors import (
    ExecutionCancelledError,
    ExecutionTimeoutError,
)
from ai_platform.common.core.execution.metadata import (
    ExecutionMetadata,
    ExecutionOutcome,
    ExecutionRecorder,
)
from ai_platform.common.core.execution.resources import ResourceManager

T = TypeVar("T")
#: After the deadline or a cancellation, how long a worker thread may take to
#: stop by itself (at its next ``context.check``) before it counts as abandoned.
STOP_GRACE_SECONDS = 0.25
Work = Callable[[ExecutionContext, ExecutionRecorder], Union[T, Awaitable[T]]]


@dataclass(frozen=True)
class ExecutionResult(Generic[T]):
    """The value of the work and the facts of its execution."""

    value: T
    metadata: ExecutionMetadata


def _outcome(exc: BaseException) -> ExecutionOutcome:
    if isinstance(exc, ExecutionTimeoutError):
        return ExecutionOutcome.TIMED_OUT
    if isinstance(exc, ExecutionCancelledError):
        return ExecutionOutcome.CANCELLED
    return ExecutionOutcome.FAILED


async def _wait_for_cancel(context: ExecutionContext) -> None:
    loop = asyncio.get_running_loop()
    cancelled = asyncio.Event()
    context.cancellation.add_callback(lambda _: loop.call_soon_threadsafe(cancelled.set))
    await cancelled.wait()


class _Worker:  # pylint: disable=too-few-public-methods
    """Sync work in its own daemon thread, so abandoning it never blocks the caller.

    (``asyncio.to_thread`` uses the loop's executor, and ``asyncio.run`` waits
    for that executor on exit - a timed-out call would still block.)
    """

    def __init__(self, work: Work, context: ExecutionContext,
                 recorder: ExecutionRecorder) -> None:
        self.loop = asyncio.get_running_loop()
        self.future: asyncio.Future = self.loop.create_future()
        self._on_end: list = []
        self._lock = threading.Lock()
        self._ended = False
        self.thread = threading.Thread(target=self._target, args=(work, context, recorder),
                                       name=f"execution-{context.execution_id[:8]}",
                                       daemon=True)
        self.thread.start()

    def _target(self, work, context, recorder) -> None:
        try:
            outcome = (True, work(context, recorder))
        except BaseException as exc:  # pylint: disable=broad-exception-caught
            outcome = (False, exc)
        try:
            self.loop.call_soon_threadsafe(self._settle, outcome)
        except RuntimeError:
            pass  # the caller's loop is gone (it stopped waiting long ago)
        with self._lock:
            self._ended = True
            callbacks, self._on_end = self._on_end, []
        for callback in callbacks:
            callback()

    def _settle(self, outcome) -> None:
        if self.future.done():
            return
        if outcome[0]:
            self.future.set_result(outcome[1])
        else:
            self.future.set_exception(outcome[1])

    def when_ended(self, callback: Callable[[], None]) -> None:
        """Run ``callback`` (in the worker thread) when the work really ends."""
        with self._lock:
            if not self._ended:
                self._on_end.append(callback)
                return
        callback()


async def _run(context: ExecutionContext, work: Work, recorder: ExecutionRecorder,
               on_abandon: Callable[["_Worker"], None], grace: float):
    """Run ``work``; returns its value, or raises timeout/cancellation/the engine's error."""
    worker = None
    if inspect.iscoroutinefunction(work):
        task = asyncio.ensure_future(work(context, recorder))
    else:
        worker = _Worker(work, context, recorder)
        task = worker.future
    watcher = asyncio.ensure_future(_wait_for_cancel(context))
    try:
        done, _ = await asyncio.wait({task, watcher}, timeout=context.remaining_seconds(),
                                     return_when=asyncio.FIRST_COMPLETED)
    finally:
        watcher.cancel()
    if task in done:
        return task.result()
    # Deadline or cancellation came first. Async work can be cancelled; a thread cannot.
    stopped = True
    if worker is None:
        task.cancel()
    else:
        # A cooperative worker notices the deadline or the token at its next
        # context.check(); give it ``grace`` seconds before calling it abandoned.
        done, _ = await asyncio.wait({task}, timeout=grace)
        stopped = task in done
        if stopped and not task.cancelled():
            task.exception()  # retrieved: its result or error is dropped on purpose
        else:
            task.cancel()  # the caller stops waiting; the thread's late result is dropped
            on_abandon(worker)
    details = {"abandoned": not stopped}
    if context.cancellation.cancelled:
        raise ExecutionCancelledError(f"execution cancelled: {context.cancellation.reason}",
                                      stage=context.operation,
                                      details={**details, "reason": context.cancellation.reason})
    raise ExecutionTimeoutError(f"{context.operation} did not finish before the deadline",
                                stage=context.operation, details=details)


async def execute(context: ExecutionContext, work: Work, *,  # pylint: disable=too-many-arguments
                  resources: Optional[ResourceManager] = None, slot_key: Optional[str] = None,
                  configuration_fingerprint: Optional[str] = None,
                  recorder: Optional[ExecutionRecorder] = None,
                  stop_grace_seconds: float = STOP_GRACE_SECONDS) -> ExecutionResult:
    """Run ``work`` under ``context``; see the module docstring."""
    recorder = recorder or ExecutionRecorder(context, configuration_fingerprint)
    slot = None
    abandoned: list = []

    def on_abandon(worker: _Worker) -> None:
        abandoned.append(worker)
        if slot is not None:  # keep the slot until the thread really ends
            worker.when_ended(lambda: slot.__exit__(None, None, None))

    try:
        context.check("before start")
        limit = context.policy.max_concurrency
        if slot_key and limit:
            manager = resources or ResourceManager()
            slot = manager.slot(slot_key, limit, context, context.policy.queue_timeout_seconds)
            recorder.queue_seconds = await asyncio.to_thread(slot.__enter__)
            recorder.record_resource(f"slot:{slot_key}")
            context.check("after waiting for a slot")
        value = await _run(context, work, recorder, on_abandon, stop_grace_seconds)
    except BaseException as exc:
        metadata = recorder.finish(_outcome(exc), exc, abandoned=bool(abandoned))
        try:
            exc.execution_metadata = metadata
        except AttributeError:  # pragma: no cover - exceptions without a __dict__
            pass
        raise
    finally:
        if slot is not None and not abandoned:
            slot.__exit__(None, None, None)
    return ExecutionResult(value, recorder.finish(ExecutionOutcome.SUCCEEDED))


def execute_blocking(context: ExecutionContext, work: Work, **kwargs: Any) -> ExecutionResult:
    """``execute`` for code without a running event loop."""
    return asyncio.run(execute(context, work, **kwargs))
