"""Weights & Biases evaluation adapter.

Computes the native metrics and logs the batch means to a W&B run; the
per-example scores are logged as a ``wandb.Table``.

Configuration:

    project          default "ai_platform"
    mode             "offline" (default - nothing leaves the machine; sync
                     later with ``wandb sync``), "online" or "disabled"
    dir              local run directory, default "./wandb"
    run_name         optional
    metrics, judge   as in NativeEvaluationAdapter

Online mode needs WANDB_API_KEY. Not verified against an installed wandb
here (the package was not installed when this was written).
Previously a stub returning constant metrics; the class name and the
EvaluationAdapter methods are unchanged.
"""

from typing import Any, Dict

from ai_platform.common.evaluation.native_evaluation_adapter import (
    EvaluationError,
    NativeEvaluationAdapter,
)


class WandBAdapter(NativeEvaluationAdapter):
    """Native metrics logged to Weights & Biases."""

    TOOL = "WandB"

    def __init__(self):
        super().__init__()
        self._wandb = None
        self._run = None

    def _setup(self, config: Dict[str, Any]) -> None:
        try:
            import wandb  # pylint: disable=import-outside-toplevel
        except ImportError as exc:
            raise EvaluationError("WandBAdapter requires: pip install wandb") from exc
        self._wandb = wandb
        self._run = wandb.init(project=config.get("project", "ai_platform"),
                               mode=config.get("mode", "offline"),
                               dir=config.get("dir", "./wandb"),
                               name=config.get("run_name"), reinit=True)

    def _log(self, result: Dict[str, Any], kwargs: Dict[str, Any]) -> Dict[str, Any]:
        names = list(result["per_example"])
        rows = list(zip(*(result["per_example"][n] for n in names)))
        self._run.log({**result["metrics"],
                       "per_example": self._wandb.Table(columns=names, data=rows)})
        return {"run_id": self._run.id, "mode": self._run.settings.mode}

    def _teardown(self) -> None:
        if self._run is not None:
            self._run.finish()
        self._run = None
