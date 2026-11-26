"""
Execute one unit of engine work under an ExecutionContext.

``await execute(context, work)`` is the single place where deadline,
cancellation, concurrency slot, metadata and error propagation come
together, for any engine:

- ``work(context, recorder)`` may be ``async`` or a plain function. A plain
  function runs in its own daemon worker thread, so a blocking engine does
  not stop the event loop and an abandoned call never blocks the caller.
  Async work that needs a thread for a blocking library call uses
  ``run_in_thread(context, recorder, fn, ...)`` - NOT ``asyncio.to_thread``:
  cancelling a coroutine that awaits ``to_thread`` does not stop the thread,
  and the executor would not know that the thread is still running.
- Before starting, the context is checked; with ``slot_key`` and a policy
  ``max_concurrency`` one slot is taken from the ``ResourceManager`` (waiting
  honours cancellation, deadline and ``queue_timeout_seconds``).
- The caller waits at most until the deadline, and stops waiting as soon as
  the token is cancelled. Then the work gets ``stop_grace_seconds`` to really
  end: the async task is cancelled and awaited, every worker thread it
  started (and the thread of plain work) is waited for - cooperative work
  stops at its next ``context.check``. Work still running after the grace
  period is ``abandoned``: its late result is dropped, the metadata says so,
  and ``PendingWork`` tracks it until it really ends.
- "Really ended" means: the task is done AND every worker thread has
  returned. Only then is the concurrency slot released, and only then does
  ``exc.execution_work.done()`` become true - so the slot limit and a
  provider's ``close()`` never act on work that is still running.
- Errors follow ``errors``: the engine's own exceptions keep their type;
  the deadline becomes ``ExecutionTimeoutError``, cancellation
  ``ExecutionCancelledError``. Every exception that leaves here carries
  ``execution_metadata`` and ``execution_work`` (a ``PendingWork``).

``execute_blocking`` runs the same for callers without an event loop.
"""

import asyncio
import inspect
import threading
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Generic, List, Optional, TypeVar, Union

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
Work = Callable[[ExecutionContext, ExecutionRecorder], Union[T, Awaitable[T]]]
#: After the deadline or a cancellation, how long the work may take to end
#: by itself (at its next ``context.check``) before it counts as abandoned.
STOP_GRACE_SECONDS = 0.25
_POLL = 0.01


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


class _Worker:  # pylint: disable=too-few-public-methods
    """A callable in its own daemon thread (abandoning it never blocks the caller).

    (``asyncio.to_thread`` uses the loop's executor, and ``asyncio.run`` waits
    for that executor on exit - a timed-out call would still block.)
    """

    def __init__(self, function: Callable[[], Any], name: str) -> None:
        self.loop = asyncio.get_running_loop()
        self.future: asyncio.Future = self.loop.create_future()
        self.ended = threading.Event()
        self._on_end: List[Callable[[], None]] = []
        self._lock = threading.Lock()
        self.thread = threading.Thread(target=self._target, args=(function,), name=name,
                                       daemon=True)
        self.thread.start()

    def _target(self, function) -> None:
        try:
            outcome = (True, function())
        except BaseException as exc:  # pylint: disable=broad-exception-caught
            outcome = (False, exc)
        try:
            self.loop.call_soon_threadsafe(self._settle, outcome)
        except RuntimeError:
            pass  # the caller's loop is gone (it stopped waiting long ago)
        with self._lock:
            self.ended.set()
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
        """Run ``callback`` when the thread really ends (at once if it has)."""
        with self._lock:
            if not self.ended.is_set():
                self._on_end.append(callback)
                return
        callback()


def _workers(recorder: ExecutionRecorder) -> List[_Worker]:
    workers = getattr(recorder, "_workers", None)
    if workers is None:
        workers = []
        recorder._workers = workers  # pylint: disable=protected-access
    return workers


async def run_in_thread(context: ExecutionContext, recorder: ExecutionRecorder,
                        function: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Run a blocking ``function`` in a worker thread that the executor tracks.

    Use it inside async work instead of ``asyncio.to_thread``: when the
    execution times out or is cancelled, this coroutine is cancelled at once,
    but the executor keeps counting the thread as running until it returns.
    """
    worker = _Worker(lambda: function(*args, **kwargs),
                     name=f"execution-{context.execution_id[:8]}")
    _workers(recorder).append(worker)
    return await worker.future


class PendingWork:
    """The real work of one execution: done when the task AND all its threads ended."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._open = 1  # released by seal()
        self._callbacks: List[Callable[[], None]] = []
        self._done = threading.Event()

    def _add(self) -> Callable[[], None]:
        with self._lock:
            self._open += 1
        return self._close

    def _close(self) -> None:
        with self._lock:
            self._open -= 1
            if self._open:
                return
            self._done.set()
            callbacks, self._callbacks = self._callbacks, []
        for callback in callbacks:
            callback()

    def track_task(self, task: asyncio.Future) -> None:
        """Count ``task`` until it is done."""
        close = self._add()
        task.add_done_callback(lambda _: close())

    def track_worker(self, worker: _Worker) -> None:
        """Count a worker thread until it returns."""
        worker.when_ended(self._add())

    def seal(self) -> None:
        """No more parts will be added."""
        self._close()

    def done(self) -> bool:
        """True when every tracked part has ended."""
        return self._done.is_set()

    def add_done_callback(self, callback: Callable[[], None]) -> None:
        """Run ``callback`` when done (in whichever thread ends last; at once if done)."""
        with self._lock:
            if not self._done.is_set():
                self._callbacks.append(callback)
                return
        callback()

    def wait(self, timeout: Optional[float] = None) -> bool:
        """Block until done or ``timeout``; True when done."""
        return self._done.wait(timeout)


async def _wait_for_cancel(context: ExecutionContext) -> None:
    loop = asyncio.get_running_loop()
    cancelled = asyncio.Event()
    context.cancellation.add_callback(lambda _: loop.call_soon_threadsafe(cancelled.set))
    await cancelled.wait()


async def _settle_after_stop(task: asyncio.Future, recorder: ExecutionRecorder,
                             is_async: bool, grace: float) -> bool:
    """Ask the work to stop and wait up to ``grace``; True when it really ended."""
    end = time.monotonic() + grace
    if is_async:
        task.cancel()
    while time.monotonic() < end:
        threads_ended = all(w.ended.is_set() for w in _workers(recorder))
        if task.done() and threads_ended:
            break
        await asyncio.sleep(_POLL)
    if task.done() and not task.cancelled():
        task.exception()  # retrieved: a late result or error is dropped on purpose
    return task.done() and all(w.ended.is_set() for w in _workers(recorder))


async def _run(context: ExecutionContext, work: Work, recorder: ExecutionRecorder,
               pending: PendingWork, grace: float):
    """Run ``work``; returns its value, or raises timeout/cancellation/the engine's error."""
    is_async = inspect.iscoroutinefunction(work)
    if is_async:
        task = asyncio.ensure_future(work(context, recorder))
    else:
        task = asyncio.ensure_future(run_in_thread(context, recorder, work, context, recorder))
    pending.track_task(task)
    watcher = asyncio.ensure_future(_wait_for_cancel(context))
    try:
        done, _ = await asyncio.wait({task, watcher}, timeout=context.remaining_seconds(),
                                     return_when=asyncio.FIRST_COMPLETED)
    finally:
        watcher.cancel()
        for worker in _workers(recorder):  # threads started so far, and later ones
            pending.track_worker(worker)
    if task in done:
        return task.result()
    stopped = await _settle_after_stop(task, recorder, is_async, grace)
    for worker in _workers(recorder):  # threads started while stopping
        pending.track_worker(worker)
    details = {"abandoned": not stopped}
    if context.cancellation.cancelled:
        raise ExecutionCancelledError(f"execution cancelled: {context.cancellation.reason}",
                                      stage=context.operation,
                                      details={**details, "reason": context.cancellation.reason})
    raise ExecutionTimeoutError(f"{context.operation} did not finish before the deadline",
                                stage=context.operation, details=details)


async def execute(context: ExecutionContext, work: Work, *,  # pylint: disable=too-many-arguments,too-many-locals
                  resources: Optional[ResourceManager] = None, slot_key: Optional[str] = None,
                  configuration_fingerprint: Optional[str] = None,
                  recorder: Optional[ExecutionRecorder] = None,
                  stop_grace_seconds: float = STOP_GRACE_SECONDS) -> ExecutionResult:
    """Run ``work`` under ``context``; see the module docstring."""
    recorder = recorder or ExecutionRecorder(context, configuration_fingerprint)
    pending = PendingWork()
    slot = None
    try:
        context.check("before start")
        limit = context.policy.max_concurrency
        if slot_key and limit:
            manager = resources or ResourceManager()
            slot = manager.slot(slot_key, limit, context, context.policy.queue_timeout_seconds)
            recorder.queue_seconds = await asyncio.to_thread(slot.__enter__)
            recorder.record_resource(f"slot:{slot_key}")
            # The slot is released only when the work really ended.
            held = slot
            pending.add_done_callback(lambda: held.__exit__(None, None, None))
            context.check("after waiting for a slot")
        value = await _run(context, work, recorder, pending, stop_grace_seconds)
    except BaseException as exc:
        details = getattr(exc, "details", None)
        abandoned = isinstance(details, dict) and bool(details.get("abandoned"))
        metadata = recorder.finish(_outcome(exc), exc, abandoned=abandoned)
        try:
            exc.execution_metadata = metadata
            exc.execution_work = pending
        except AttributeError:  # pragma: no cover - exceptions without a __dict__
            pass
        raise
    finally:
        pending.seal()
    return ExecutionResult(value, recorder.finish(ExecutionOutcome.SUCCEEDED))


def execute_blocking(context: ExecutionContext, work: Work, **kwargs: Any) -> ExecutionResult:
    """``execute`` for code without a running event loop."""
    return asyncio.run(execute(context, work, **kwargs))
