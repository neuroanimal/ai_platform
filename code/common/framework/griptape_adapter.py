"""Griptape adapter.

Configuration: ``structure`` - a Griptape ``Agent``, ``Pipeline`` or
``Workflow``. ``execute({"input": "..."})`` calls ``structure.run(input)``;
``output`` is ``structure.output.value`` (the last task's output artifact).

Not verified against an installed Griptape here (the package was not
installed when this was written); unit tests drive it with a stand-in
object. Previously a stub echoing the task; the class name and the
FrameworkAdapter methods are unchanged.
"""

from typing import Any, Dict

from ai_platform.common.framework.framework_support import (
    FrameworkBase,
    task_input,
)


class GriptapeAdapter(FrameworkBase):
    """Runs a Griptape structure."""

    FRAMEWORK = "Griptape"

    def _run(self, task: Dict[str, Any]):
        target = self._needs('structure', 'a griptape Agent, Pipeline or Workflow')
        value = task_input(task)
        result = target.run(*(value if isinstance(value, (list, tuple)) else [value]))
        artifact = getattr(result, "output", None) or getattr(target, "output", None)
        return getattr(artifact, "value", artifact), result
