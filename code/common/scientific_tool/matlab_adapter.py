"""MATLAB adapter.

Runs a script with ``matlab -batch <script>`` (MATLAB R2019a or later)
(separate process per call, see
``script_tool_support.py``) and returns its standard output.

Needs a licensed MATLAB installation; ``-batch`` runs without a desktop and
exits with a non-zero status on error. Not verified here (no MATLAB).

Previously a stub returning a fabricated result; the class name and the
ScientificToolAdapter methods are unchanged.
"""

from typing import List

from ai_platform.common.scientific_tool.script_tool_support import ScriptToolAdapter


class MATLABAdapter(ScriptToolAdapter):
    """MATLAB scripts."""

    TOOLS = ["matlab"]
    HINT = 'install MATLAB R2019a+'

    def command(self, script: str) -> List[str]:
        """matlab -batch <script>"""
        return [self.executable, "-batch", script]
