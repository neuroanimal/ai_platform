"""SageMath adapter.

Runs a script with ``sage -c <script>`` (separate process per call, see
``script_tool_support.py``) and returns its standard output.

Not verified here (no SageMath installation).

Previously a stub returning a fabricated result; the class name and the
ScientificToolAdapter methods are unchanged.
"""

from typing import List

from ai_platform.common.scientific_tool.script_tool_support import ScriptToolAdapter


class SageMathAdapter(ScriptToolAdapter):
    """SageMath scripts."""

    TOOLS = ["sage"]
    HINT = 'install SageMath'

    def command(self, script: str) -> List[str]:
        """sage -c <script>"""
        return [self.executable, "-c", script]
