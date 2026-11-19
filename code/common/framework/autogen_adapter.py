"""AutoGen adapter.

Configuration: ``agent`` - an AutoGen AgentChat agent or team (e.g.
``AssistantAgent``, ``RoundRobinGroupChat``; AutoGen 0.4+). ``execute`` runs
``await agent.run(task=input)`` to completion; ``output`` is the content of
the last message of the ``TaskResult``.

Not verified against an installed AutoGen here (the package was not
installed when this was written); unit tests drive it with a stand-in
object. Previously a stub echoing the task; the class name and the
FrameworkAdapter methods are unchanged.
"""

from typing import Any, Dict

from ai_platform.common.framework.framework_support import (
    FrameworkBase,
    run_sync,
    task_input,
)


class AutoGenAdapter(FrameworkBase):
    """Runs a AutoGen agent or team."""

    FRAMEWORK = "AutoGen"

    def _run(self, task: Dict[str, Any]):
        target = self._needs('agent', 'an autogen_agentchat agent or team')
        result = run_sync(target.run(task=task_input(task)))
        messages = getattr(result, "messages", None) or []
        return (getattr(messages[-1], "content", None) if messages else None), result
