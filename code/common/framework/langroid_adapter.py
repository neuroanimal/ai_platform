"""Langroid adapter.

Configuration: ``task`` - a ``langroid.Task`` wrapping a ``ChatAgent``.
``execute({"input": "...", "turns": n})`` calls ``task.run(input, turns=n)``
(default ``turns`` -1 = until done); ``output`` is the final message content.

Not verified against an installed Langroid here (the package was not
installed when this was written); unit tests drive it with a stand-in
object. Previously a stub echoing the task; the class name and the
FrameworkAdapter methods are unchanged.
"""

from typing import Any, Dict

from ai_platform.common.framework.framework_support import (
    FrameworkBase,
    task_input,
)


class LangroidAdapter(FrameworkBase):
    """Runs a Langroid task."""

    FRAMEWORK = "Langroid"

    def _run(self, task: Dict[str, Any]):
        target = self._needs('task', 'a langroid.Task')
        result = target.run(task_input(task), turns=int(task.get("turns", -1)))
        return getattr(result, "content", result), result
