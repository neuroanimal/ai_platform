"""GNU Octave adapter.

Runs a script with ``octave-cli --quiet --no-window-system --eval <script>``
(separate process per call, see
``script_tool_support.py``) and returns its standard output.

Previously a stub returning a fabricated result; the class name and the
ScientificToolAdapter methods are unchanged.
"""

from typing import List

from ai_platform.common.scientific_tool.script_tool_support import ScriptToolAdapter


class OctaveAdapter(ScriptToolAdapter):
    """GNU Octave scripts."""

    TOOLS = ["octave-cli", "octave"]
    HINT = 'install GNU Octave'

    def command(self, script: str) -> List[str]:
        """octave-cli --quiet --no-window-system --eval <script>"""
        return [self.executable, "--quiet", "--no-window-system", "--eval", script]
