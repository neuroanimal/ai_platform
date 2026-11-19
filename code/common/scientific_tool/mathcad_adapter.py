"""Mathcad adapter - not implemented, on purpose.

PTC Mathcad Prime is a Windows-only desktop application; its automation
API is a Windows COM/.NET interface. It cannot be driven from this
platform's Linux/WSL2 environment, and no headless command line exists to
wrap.

Instead of returning a fabricated result (what the earlier stub did), every
method raises ``NotImplementedError``. For scriptable computation use
``OctaveAdapter``, ``SageMathAdapter`` or ``MathematicaAdapter``; for
symbolic maths in-process, SymPy.

The class name is kept so that registries and imports do not break.
"""

from typing import Any, Dict

from ai_platform.common.scientific_tool.base import ScientificToolAdapter

_MESSAGE = ("MathCADAdapter is not implemented: Mathcad Prime is automated only through "
            "Windows COM. Use OctaveAdapter, SageMathAdapter or SymPy instead.")


class MathCADAdapter(ScientificToolAdapter):
    """Placeholder that refuses to pretend; see the module docstring."""

    def connect(self, config: Dict[str, Any]) -> None:
        """Not implemented."""
        raise NotImplementedError(_MESSAGE)

    def execute(self, script: str, **kwargs) -> Any:
        """Not implemented."""
        raise NotImplementedError(_MESSAGE)

    def disconnect(self) -> None:
        """Nothing to release."""
