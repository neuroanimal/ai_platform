"""Example usage of evaluation tool adapters."""

import tempfile

from ai_platform.common.evaluation.evaluation_registry import get_registry
from ai_platform.common.evaluation.native_evaluation_adapter import (
    EvaluationError,
    NativeEvaluationAdapter,
)
from ai_platform.common.evaluation.ragas_adapter import RAGASAdapter
from ai_platform.common.evaluation.hf_evaluate_adapter import HFEvaluateAdapter
from ai_platform.common.evaluation.mlflow_adapter import MLflowAdapter
from ai_platform.common.evaluation.wandb_adapter import WandBAdapter
from ai_platform.common.evaluation.tensorboard_adapter import TensorBoardAdapter
from ai_platform.common.evaluation.deepeval_adapter import DeepEvalAdapter
from ai_platform.common.evaluation.langsmith_adapter import LangSmithAdapter
from ai_platform.common.evaluation.trulens_adapter import TrulensAdapter
from ai_platform.common.evaluation.humanloop_adapter import HumanLoopAdapter
from ai_platform.common.evaluation.mirascope_adapter import MiraScopeAdapter

def main():
    """Register all evaluation tools and run the usable ones on a small batch."""
    registry = get_registry()

    tools = {
        "native": NativeEvaluationAdapter,
        "ragas": RAGASAdapter,
        "hf_evaluate": HFEvaluateAdapter,
        "mlflow": MLflowAdapter,
        "wandb": WandBAdapter,
        "tensorboard": TensorBoardAdapter,
        "deepeval": DeepEvalAdapter,
        "langsmith": LangSmithAdapter,
        "trulens": TrulensAdapter,
        "humanloop": HumanLoopAdapter,
        "mirascope": MiraScopeAdapter,
    }

    for name, adapter_class in tools.items():
        registry.register(name, adapter_class)

    print(f"Registered {len(tools)} evaluation tools: {registry.list()}\n")

    predictions = ["17 times 23 is 391.", "No, it is not a mammal.", "12%"]
    references = ["391", "Yes, it is a mammal.", "12%"]

    # Tracking tools write into a temporary directory, nothing is sent anywhere.
    with tempfile.TemporaryDirectory() as tmp:
        configs = {
            "mlflow": {"tracking_uri": f"sqlite:///{tmp}/mlflow.db", "experiment_name": "example",
                       "artifact_location": f"{tmp}/artifacts"},
            "tensorboard": {"log_dir": f"{tmp}/tb"},
            "wandb": {"mode": "offline", "dir": tmp},
        }
        for name in tools:
            adapter = registry.get(name)
            try:
                adapter.initialize(configs.get(name, {}))
                result = adapter.evaluate(predictions, references)
                shown = {k: round(v, 3) for k, v in result["metrics"].items()}
                print(f"{name:12} OK      {shown}")
            except (EvaluationError, NotImplementedError) as exc:
                print(f"{name:12} skipped {type(exc).__name__}: {str(exc)[:80]}")
            finally:
                adapter.shutdown()


if __name__ == "__main__":
    main()
