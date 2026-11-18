"""TensorBoard evaluation adapter.

Computes the native metrics and writes the batch means as scalars
(``eval/<metric>``) with ``torch.utils.tensorboard.SummaryWriter`` (or
``tensorboardX`` when torch is absent). Each ``evaluate`` call is one step,
so repeated evaluations draw a curve.

Configuration:

    log_dir          default "./runs/ai_platform_eval"
    tag_prefix       default "eval"
    metrics, judge   as in NativeEvaluationAdapter

The result gets ``log_dir`` and ``step``. Previously a stub returning
constant metrics; the class name and the EvaluationAdapter methods are
unchanged.
"""

from typing import Any, Dict

from ai_platform.common.evaluation.native_evaluation_adapter import (
    EvaluationError,
    NativeEvaluationAdapter,
)


class TensorBoardAdapter(NativeEvaluationAdapter):
    """Native metrics written as TensorBoard scalars."""

    TOOL = "TensorBoard"

    def __init__(self):
        super().__init__()
        self.log_dir = None
        self.tag_prefix = "eval"
        self.step = 0
        self._writer = None

    def _setup(self, config: Dict[str, Any]) -> None:
        try:
            from torch.utils.tensorboard import SummaryWriter  # pylint: disable=import-outside-toplevel
        except ImportError:
            try:
                from tensorboardX import SummaryWriter  # pylint: disable=import-outside-toplevel
            except ImportError as exc:
                raise EvaluationError(
                    "TensorBoardAdapter requires torch+tensorboard or tensorboardX") from exc
        self.log_dir = config.get("log_dir", "./runs/ai_platform_eval")
        self.tag_prefix = config.get("tag_prefix", "eval")
        self.step = 0
        self._writer = SummaryWriter(log_dir=self.log_dir)

    def _log(self, result: Dict[str, Any], kwargs: Dict[str, Any]) -> Dict[str, Any]:
        step = kwargs.get("step", self.step)
        for name, value in result["metrics"].items():
            self._writer.add_scalar(f"{self.tag_prefix}/{name}", value, global_step=step)
        self._writer.flush()
        self.step = step + 1
        return {"log_dir": self.log_dir, "step": step}

    def _teardown(self) -> None:
        if self._writer is not None:
            self._writer.close()
        self._writer = None
