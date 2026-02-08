"""Example usage of evaluation tool adapters."""

from ai_platform.common.evaluation.evaluation_registry import get_registry
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
    registry = get_registry()

    tools = {
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

    for name in tools.keys():
        adapter = registry.get(name)
        adapter.initialize({})
        result = adapter.evaluate(["pred1"], ["ref1"])
        print(f"{result['tool']}: OK")
        adapter.shutdown()

if __name__ == "__main__":
    main()
