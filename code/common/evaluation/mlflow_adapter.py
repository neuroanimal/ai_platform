"""MLflow evaluation adapter.

Computes the native metrics (see ``native_evaluation_adapter.py``) and logs
them to an MLflow run: batch means as metrics, per-example scores as the
artifact ``per_example.json``.

Configuration:

    tracking_uri     e.g. "http://127.0.0.1:5000" or "sqlite:///mlflow.db";
                     default: MLflow's own default (MLFLOW_TRACKING_URI or ./mlruns)
    experiment_name  default "default_experiment"
    artifact_location  where a *new* experiment stores artifacts (e.g.
                     per_example.json); default MLflow's ./mlruns in the
                     current directory, even with a sqlite tracking URI
    run_name         optional; evaluate(run_name=...) overrides per call
    metrics, judge   as in NativeEvaluationAdapter

The result gets ``experiment`` and ``run_id``. Previously a stub returning
constant metrics; the class name and the EvaluationAdapter methods are
unchanged.
"""

from typing import Any, Dict

from ai_platform.common.evaluation.native_evaluation_adapter import (
    EvaluationError,
    NativeEvaluationAdapter,
)


class MLflowAdapter(NativeEvaluationAdapter):
    """Native metrics logged to MLflow."""

    TOOL = "MLflow"

    def __init__(self):
        super().__init__()
        self.experiment_name = None
        self.run_name = None
        self.runs = []
        self._mlflow = None

    def _setup(self, config: Dict[str, Any]) -> None:
        try:
            import mlflow  # pylint: disable=import-outside-toplevel
        except ImportError as exc:
            raise EvaluationError("MLflowAdapter requires: pip install mlflow") from exc
        self._mlflow = mlflow
        if config.get("tracking_uri"):
            mlflow.set_tracking_uri(config["tracking_uri"])
        self.experiment_name = config.get("experiment_name", "default_experiment")
        self.run_name = config.get("run_name")
        if config.get("artifact_location") and \
                mlflow.get_experiment_by_name(self.experiment_name) is None:
            mlflow.create_experiment(self.experiment_name,
                                     artifact_location=config["artifact_location"])
        mlflow.set_experiment(self.experiment_name)

    def _log(self, result: Dict[str, Any], kwargs: Dict[str, Any]) -> Dict[str, Any]:
        with self._mlflow.start_run(run_name=kwargs.get("run_name", self.run_name)) as run:
            self._mlflow.log_metrics(result["metrics"])
            self._mlflow.log_param("n_examples", result["n"])
            self._mlflow.log_dict(result["per_example"], "per_example.json")
        self.runs.append(run.info.run_id)
        return {"experiment": self.experiment_name, "run_id": run.info.run_id}

    def _teardown(self) -> None:
        self.runs.clear()
