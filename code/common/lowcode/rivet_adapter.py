"""Rivet adapter - not implemented, on purpose.

Rivet (Ironclad) graphs are executed by its Node.js runtime
(``@ironclad/rivet-node``) or the desktop app; there is no HTTP API that a
Python adapter could deploy to or call that could be confirmed.

Instead of returning fabricated ids and results (what the earlier stub
did), every method raises ``NotImplementedError``. Working alternatives:
``N8nAdapter``, ``FlowiseAdapter``, ``LangFlowAdapter``.

The class name is kept so that registries and imports do not break.
"""

from typing import Any, Dict

from ai_platform.common.lowcode.base import LowCodeAdapter

_MESSAGE = (
    "RivetAdapter is not implemented: Rivet graphs run in Node.js, no HTTP API confirmed. "
    "Use N8nAdapter, FlowiseAdapter or LangFlowAdapter instead."
)


class RivetAdapter(LowCodeAdapter):
    """Placeholder that refuses to pretend; see the module docstring."""

    def connect(self, config: Dict[str, Any]) -> None:
        """Not implemented."""
        raise NotImplementedError(_MESSAGE)

    def deploy_workflow(self, workflow: Dict[str, Any]) -> str:
        """Not implemented."""
        raise NotImplementedError(_MESSAGE)

    def execute_workflow(self, workflow_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Not implemented."""
        raise NotImplementedError(_MESSAGE)

    def disconnect(self) -> None:
        """Nothing to release."""
