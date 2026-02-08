# Evaluation Tool Support

Model and LLM evaluation tool adapters.

## Supported Tools

- **RAGAS**: RAG evaluation framework
- **HuggingFace Evaluate**: Metrics library
- **MLflow**: Experiment tracking
- **Weights & Biases**: ML experiment tracking
- **TensorBoard**: Visualization toolkit
- **DeepEval**: LLM evaluation framework
- **LangSmith**: LangChain evaluation
- **Trulens**: LLM observability
- **HumanLoop**: Human feedback and evaluation

## Usage

```python
from code.common.evaluation.evaluation_registry import get_registry
from code.common.evaluation.ragas_adapter import RAGASAdapter

registry = get_registry()
registry.register("ragas", RAGASAdapter)

evaluator = registry.get("ragas")
evaluator.initialize({})
results = evaluator.evaluate(predictions, references)
print(results)
evaluator.shutdown()
```
