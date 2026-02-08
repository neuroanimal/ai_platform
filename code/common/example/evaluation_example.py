"""Example usage of evaluation tool adapters."""

from code.common.evaluation.evaluation_registry import get_registry
from code.common.evaluation.ragas_adapter import RAGASAdapter
from code.common.evaluation.hf_evaluate_adapter import HFEvaluateAdapter
from code.common.evaluation.mlflow_adapter import MLflowAdapter
from code.common.evaluation.wandb_adapter import WandBAdapter
from code.common.evaluation.tensorboard_adapter import TensorBoardAdapter
from code.common.evaluation.deepeval_adapter import DeepEvalAdapter
from code.common.evaluation.langsmith_adapter import LangSmithAdapter
from code.common.evaluation.trulens_adapter import TrulensAdapter
from code.common.evaluation.humanloop_adapter import HumanLoopAdapter
from code.common.evaluation.mirascope_adapter import MiraScopeAdapter

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
