"""Haystack adapter.

Configuration: ``pipeline`` - a Haystack 2.x ``Pipeline`` (components
connected with Haystack's API). ``execute({"input": {component: {param: value}}})``
calls ``pipeline.run(input)``; ``output`` is the result dict.
(For retrieval-augmented QA see ``common/rag/haystack_rag_adapter.py``.)

Not verified against an installed Haystack here (the package was not
installed when this was written); unit tests drive it with a stand-in
object. Previously a stub echoing the task; the class name and the
FrameworkAdapter methods are unchanged.
"""

from typing import Any, Dict

from ai_platform.common.framework.framework_support import (
    FrameworkBase,
    task_input,
)


class HaystackAdapter(FrameworkBase):
    """Runs a Haystack pipeline."""

    FRAMEWORK = "Haystack"

    def _run(self, task: Dict[str, Any]):
        target = self._needs('pipeline', 'a haystack.Pipeline')
        result = target.run(task_input(task))
        return result, result
