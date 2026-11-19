"""Tableau adapter - not implemented, on purpose.

Tableau dashboards are authored in Tableau Desktop / the web editor and
stored in workbooks (.twb/.twbx). The Tableau REST API publishes, lists and
manages *existing* workbooks and data sources; it has no operation that
builds a dashboard from data, which is what ``create_dashboard(data)``
promises. Generating .twb XML by hand is undocumented and fragile.

Instead of returning a fake URL (what the earlier stub did), every method
raises ``NotImplementedError``. Working alternatives: ``GrafanaAdapter``
(data embedded in the dashboard), ``PowerBIAdapter`` (push dataset +
dashboard), or the HTML outputs of the visualization adapters.

The class name is kept so that registries and imports do not break.
"""

from typing import Any, Dict

from ai_platform.common.visualization_tool.base import VisualizationToolAdapter

_MESSAGE = ("TableauAdapter is not implemented: the Tableau REST API cannot build dashboards "
            "from data. Use GrafanaAdapter or PowerBIAdapter instead.")


class TableauAdapter(VisualizationToolAdapter):
    """Placeholder that refuses to pretend; see the module docstring."""

    def connect(self, config: Dict[str, Any]) -> None:
        """Not implemented."""
        raise NotImplementedError(_MESSAGE)

    def create_dashboard(self, data: Any, **kwargs) -> str:
        """Not implemented."""
        raise NotImplementedError(_MESSAGE)

    def disconnect(self) -> None:
        """Nothing to release."""
