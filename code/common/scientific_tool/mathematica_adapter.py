"""Wolfram Mathematica / Wolfram Engine adapter.

Runs a script with ``wolframscript -code <script>`` (separate process per call, see
``script_tool_support.py``) and returns its standard output.

Works with Mathematica or the free Wolfram Engine (activated licence
required). Not verified here (no Wolfram installation).

Previously a stub returning a fabricated result; the class name and the
ScientificToolAdapter methods are unchanged.
"""

from typing import List

from ai_platform.common.scientific_tool.script_tool_support import ScriptToolAdapter


class MathematicaAdapter(ScriptToolAdapter):
    """Wolfram Mathematica / Wolfram Engine scripts."""

    TOOLS = ["wolframscript"]
    HINT = 'install Wolfram Engine or Mathematica'

    def command(self, script: str) -> List[str]:
        """wolframscript -code <script>"""
        return [self.executable, "-code", script]
