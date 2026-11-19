"""CrewAI adapter.

Configuration: ``crew`` - a ``crewai.Crew`` built with CrewAI's API (agents,
tasks, process). ``execute({"input": {...}})`` calls
``crew.kickoff(inputs=input)``; ``output`` is ``CrewOutput.raw``.

Not verified against an installed CrewAI here (the package was not
installed when this was written); unit tests drive it with a stand-in
object. Previously a stub echoing the task; the class name and the
FrameworkAdapter methods are unchanged.
"""

from typing import Any, Dict

from ai_platform.common.framework.framework_support import (
    FrameworkBase,
    task_input,
)


class CrewAIAdapter(FrameworkBase):
    """Runs a CrewAI crew."""

    FRAMEWORK = "CrewAI"

    def _run(self, task: Dict[str, Any]):
        target = self._needs('crew', 'a crewai.Crew')
        value = task_input(task)
        result = target.kickoff(inputs=value if isinstance(value, dict) else {"input": value})
        return getattr(result, "raw", str(result)), result
