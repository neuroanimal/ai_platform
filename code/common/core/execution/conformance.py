"""
Conformance checks of the execution contract, for any engine adapter.

A future provider (NLP, OCR/HTR, speech, ...) proves it honours the contract
by passing its own unit of work to these checks in its tests:

    report = await check_execution_conformance(lambda ctx, rec: provider.run(ctx, rec))
    assert report.ok, report.problems

What is checked:

- ``honours_cancellation``: cancelled shortly after start, the work stops
  (raises ``ExecutionCancelledError`` from ``context.check``) instead of
  being abandoned;
- ``honours_deadline``: with a short deadline the work stops by itself;
- ``reports_metadata``: a normal run fills ``record_engine`` and
  ``record_device``;
- ``error_types_kept``: an error raised by the work reaches the caller with
  its own type and with ``execution_metadata`` attached.

Engines that cannot stop mid-call (one blocking library call) fail the first
two checks; that is a true statement about the engine, and the metadata of
such runs says ``abandoned``. ``required`` lets a provider declare which
checks it promises.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence

from ai_platform.common.core.execution.context import ExecutionContext
from ai_platform.common.core.execution.errors import (
    ExecutionCancelledError,
    ExecutionTimeoutError,
)
from ai_platform.common.core.execution.executor import execute

CHECKS = ("honours_cancellation", "honours_deadline", "reports_metadata", "error_types_kept")


@dataclass
class ConformanceReport:
    """Result of each check and what went wrong."""

    results: Dict[str, bool] = field(default_factory=dict)
    problems: List[str] = field(default_factory=list)
    required: Sequence[str] = CHECKS

    @property
    def ok(self) -> bool:
        """True when every required check passed."""
        return all(self.results.get(name) for name in self.required)


async def _stops(work, *, cancel_after: Optional[float], timeout: Optional[float],
                 grace: float) -> bool:
    context = ExecutionContext.create("conformance", timeout_seconds=timeout)
    if cancel_after is not None:
        asyncio.get_running_loop().call_later(cancel_after, context.cancellation.cancel,
                                              "conformance check")
    try:
        await execute(context, work)
    except (ExecutionCancelledError, ExecutionTimeoutError) as exc:
        if not exc.execution_metadata.abandoned:
            return True
        # Abandoned by the executor: did the work stop on its own shortly after?
        end = time.monotonic() + grace
        while time.monotonic() < end:
            await asyncio.sleep(0.02)
        return False
    return False  # finished normally despite the cancellation / deadline


async def check_execution_conformance(  # pylint: disable=too-many-arguments
        long_work: Callable, *, quick_work: Optional[Callable] = None,
        failing_work: Optional[Callable] = None, expected_error: type = Exception,
        required: Sequence[str] = CHECKS, grace: float = 0.5) -> ConformanceReport:
    """Run the checks. ``long_work`` must take clearly longer than 0.3 s if not stopped."""
    report = ConformanceReport(required=required)
    report.results["honours_cancellation"] = await _stops(long_work, cancel_after=0.1,
                                                          timeout=None, grace=grace)
    report.results["honours_deadline"] = await _stops(long_work, cancel_after=None,
                                                      timeout=0.1, grace=grace)
    if quick_work is not None:
        result = await execute(ExecutionContext.create("conformance"), quick_work)
        report.results["reports_metadata"] = bool(result.metadata.engine
                                                  and result.metadata.device_used)
    if failing_work is not None:
        try:
            await execute(ExecutionContext.create("conformance"), failing_work)
            kept = False
        except Exception as exc:  # pylint: disable=broad-exception-caught
            kept = isinstance(exc, expected_error) and hasattr(exc, "execution_metadata")
        report.results["error_types_kept"] = kept
    for name in required:
        if not report.results.get(name):
            report.problems.append(f"{name}: not satisfied" if name in report.results
                                   else f"{name}: not checked (work for it not given)")
    return report
