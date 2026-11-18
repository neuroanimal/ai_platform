"""LangSmith evaluation adapter.

Computes the native metrics and, when a LangSmith run is named, attaches
them to that run as feedback (``Client.create_feedback``) - one feedback
entry per metric with the batch mean as score. Without a ``run_id`` the
metrics are returned but nothing is sent (``logged: False``).

Configuration:

    client           a ready ``langsmith.Client`` (tests, custom endpoints);
                     default ``langsmith.Client()``, which reads
                     LANGSMITH_API_KEY / LANGSMITH_ENDPOINT
    metrics, judge   as in NativeEvaluationAdapter

``evaluate(..., run_id="<uuid>")`` selects the run. Not verified against
the LangSmith service here (no API key); unit tests use a fake client.
Previously a stub returning constant metrics; the class name and the
EvaluationAdapter methods are unchanged.
"""

from typing import Any, Dict

from ai_platform.common.evaluation.native_evaluation_adapter import (
    EvaluationError,
    NativeEvaluationAdapter,
)


class LangSmithAdapter(NativeEvaluationAdapter):
    """Native metrics attached to a LangSmith run as feedback."""

    TOOL = "LangSmith"

    def __init__(self):
        super().__init__()
        self._client = None

    def _setup(self, config: Dict[str, Any]) -> None:
        self._client = config.get("client")
        if self._client is None:
            try:
                from langsmith import Client  # pylint: disable=import-outside-toplevel
            except ImportError as exc:
                raise EvaluationError("LangSmithAdapter requires: pip install langsmith") from exc
            self._client = Client()

    def _log(self, result: Dict[str, Any], kwargs: Dict[str, Any]) -> Dict[str, Any]:
        run_id = kwargs.get("run_id")
        if not run_id:
            return {"logged": False, "reason": "no run_id given"}
        for name, value in result["metrics"].items():
            self._client.create_feedback(run_id, key=name, score=value,
                                         comment=f"ai_platform, n={result['n']}")
        return {"logged": True, "run_id": run_id}

    def _teardown(self) -> None:
        self._client = None
