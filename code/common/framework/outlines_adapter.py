"""Outlines adapter.

Structured generation: Configuration: ``generator`` - an Outlines callable
that produces output constrained to a type/JSON schema (e.g. built with
``outlines.Generator(model, MySchema)`` in Outlines 1.x). ``execute({"input":
"prompt", "kwargs": {...}})`` calls ``generator(input, **kwargs)``;
``output`` is the (parsed) structured result.

Not verified against an installed Outlines here (the package was not
installed when this was written); unit tests drive it with a stand-in
object. Previously a stub echoing the task; the class name and the
FrameworkAdapter methods are unchanged.
"""

from typing import Any, Dict

from ai_platform.common.framework.framework_support import (
    FrameworkBase,
    task_input,
)


class OutlinesAdapter(FrameworkBase):
    """Runs a Outlines generator."""

    FRAMEWORK = "Outlines"

    def _run(self, task: Dict[str, Any]):
        target = self._needs('generator', 'an Outlines generator / model call')
        result = target(task_input(task), **task.get("kwargs", {}))
        return result, result
