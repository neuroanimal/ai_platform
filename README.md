# AI Platform

All-purpose general and broad AI Platform with Traditional and Modern AI, NLP, OCR, ML, DL, LLM, GenAI, AI Agents.

## Overview

Package ai-platform is a modular, extensible AI/DS/ML platform designed for:

- Rapid development of AI solutions
- Support for Traditional AI and Modern AI (including Generative AI)
- Maximum architectural rigor with good skeleton prepared
- Technology agnosticism
- Long-term scalability

## Principles

- Add-only evolution
- Strong layer boundaries
- Plugin-based extensibility
- Multi-language support

## Quick Start

```bash
# Install core
pip install -e .

# Install ML frameworks
make install-ml

# Install LLM support
pip install -e ".[llm]"

# Run examples
python -m ai_platform.common.example.ml_example
```

## Features

### 🤖 Machine Learning (8 Frameworks)

**Supported:** scikit-learn, XGBoost, LightGBM, CatBoost, PyTorch, TensorFlow, Keras, JAX

```python
from ai_platform.common.ml.pytorch_adapter import PyTorchAdapter
import numpy as np

# Generate data
X = np.random.randn(100, 10)
y = (X[:, 0] + X[:, 1] > 0).astype(float)

# Train model
adapter = PyTorchAdapter()
adapter.initialize({"layers": [10, 16, 1]})
result = adapter.train({"X": X, "y": y}, epochs=10)
predictions = adapter.predict(X[:5])
adapter.shutdown()
```

**Examples:** `python -m ai_platform.common.example.ml_example`

### 🧠 Large Language Models (11 Providers)

**Supported:** OpenAI, Anthropic, Google Gemini, Cohere, Mistral, HuggingFace, AWS Bedrock, Azure OpenAI, Ollama, Together AI, Replicate

```python
from ai_platform.common.llm.openai_adapter import OpenAIAdapter

llm = OpenAIAdapter()
llm.initialize({"model": "gpt-4", "api_key": "your-key"})
response = llm.generate("Explain quantum computing")
print(response)
llm.shutdown()
```

**Examples:** `python -m ai_platform.common.example.llm_example`

### 📚 RAG (Retrieval-Augmented Generation) (8 Stacks)

**Supported:** LlamaIndex, LangChain, Haystack, Verba, RAGFlow, Canopy, Embedchain, txtai

```python
from ai_platform.common.rag.llamaindex_adapter import LlamaIndexAdapter

rag = LlamaIndexAdapter()
rag.initialize({"index_type": "vector"})
rag.ingest([{"text": "AI Platform documentation..."}])
result = rag.query("What is AI Platform?")
print(result["answer"])
rag.shutdown()
```

**Examples:** `python -m ai_platform.common.example.rag_example`

### 🗄️ Vector Databases (13 Databases)

**Supported:** Pinecone, Weaviate, Qdrant, ChromaDB, Milvus, FAISS, LanceDB, Elasticsearch, OpenSearch, PGVector, SQLite-VSS, Lantern, txtai

```python
from ai_platform.common.vectordb.pinecone_adapter import PineconeAdapter

db = PineconeAdapter()
db.connect({"api_key": "your-key", "environment": "us-west1"})
db.insert([[0.1, 0.2, 0.3]], [{"id": "doc1"}])
results = db.search([0.1, 0.2, 0.3], top_k=5)
db.disconnect()
```

**Examples:** `python -m ai_platform.common.example.vectordb_example`

### 🎨 Visualization (10 Libraries)

**Supported:** Matplotlib, Plotly, Seaborn, Bokeh, Altair, D3.js, Chart.js, Vega-Lite, ggplot2 (R), Grafana, Tableau, Power BI, Superset, Metabase

```python
from ai_platform.common.visualization.plotly_adapter import PlotlyAdapter

viz = PlotlyAdapter()
viz.initialize({})
viz.create_chart({"x": [1, 2, 3], "y": [4, 5, 6]}, chart_type="line")
viz.shutdown()
```

**Examples:** `python -m ai_platform.common.example.visualization_example`

### 🔧 AI Frameworks (13 Frameworks)

**Supported:** LangChain, LangGraph, AutoGen, CrewAI, Haystack, Semantic Kernel, Griptape, AutoGPT, Langroid, Outlines, GradientJ, LangDock, Akka

```python
from ai_platform.common.framework.langchain_adapter import LangChainAdapter

framework = LangChainAdapter()
framework.initialize({"chain_type": "sequential"})
result = framework.execute({"task": "analyze sentiment"})
framework.shutdown()
```

**Examples:** `python -m ai_platform.common.example.framework_example`

### 📝 Prompt Engineering (5 Tools)

**Supported:** Guidance, LMQL, Priompt, LangChain Prompts, PromptLayer

```python
from ai_platform.common.prompt.guidance_adapter import GuidanceAdapter

prompt = GuidanceAdapter()
prompt.initialize({})
result = prompt.render("Hello {{name}}", {"name": "World"})
prompt.shutdown()
```

**Examples:** `python -m ai_platform.common.example.prompt_example`

### 🔌 AI Protocols (3 Protocols)

**Supported:** MCP (Model Context Protocol), ACP, A2A

```python
from ai_platform.common.protocol.mcp_adapter import MCPAdapter

protocol = MCPAdapter()
protocol.connect({"endpoint": "localhost:8080"})
response = protocol.send({"action": "query", "data": "..."})
protocol.disconnect()
```

**Examples:** `python -m ai_platform.common.example.protocol_example`

### 📊 Evaluation Tools (10 Tools)

**Supported:** DeepEval, MLflow, LangSmith, Trulens, HumanLoop, HF Evaluate, TensorBoard, RAGAS, WandB, MiraScope

```python
from ai_platform.common.evaluation.deepeval_adapter import DeepEvalAdapter

evaluator = DeepEvalAdapter()
evaluator.initialize({})
metrics = evaluator.evaluate(predictions, references)
print(metrics)
evaluator.shutdown()
```

**Examples:** `python -m ai_platform.common.example.evaluation_example`

### 🎯 Low-Code/No-Code (6 Platforms)

**Supported:** Flowise, Langflow, n8n, AgentGPT, Rivet, SuperAGI

```python
from ai_platform.common.lowcode.flowise_adapter import FlowiseAdapter

platform = FlowiseAdapter()
platform.connect({"url": "http://localhost:3000"})
workflow_id = platform.deploy_workflow({"name": "my_flow"})
result = platform.execute_workflow(workflow_id, {"input": "data"})
platform.disconnect()
```

**Examples:** `python -m ai_platform.common.example.lowcode_example`

### 📄 Document Processing

#### YAML Processing Tool

Integrated YAML uncommenting functionality for DevOps and configuration management:

```python
from ai_platform.common.tool.yaml_uncommenter import YAMLUncommenter

uncommenter = YAMLUncommenter()
success = uncommenter.process(
    input_path="template.yaml",
    output_path="result.yaml",
    system_size="standard-system"
)
```

#### Engine Interface

```python
from ai_platform.common.engine.yaml_processing_engine import YAMLProcessingEngine

engine = YAMLProcessingEngine()
result = engine.process_template(
    input_path="template.yaml",
    output_path="result.yaml",
    mrcf_path="config.json",
    helm_path="charts/",
    system_size="large-system"
)
```

#### CLI Usage

```bash
python code/common/tool/yaml_cli.py input.yaml output.yaml --flavor standard-system --helm charts/
```

#### JSON Schema Processing

```python
from ai_platform.common.engine.jsonschema_processing_engine import JSONSchemaProcessingEngine

engine = JSONSchemaProcessingEngine()
result = engine.process_schema("schema.json", "output.json")
```

**Examples:**

- `python -m ai_platform.common.example.yaml_processing_example`
- `python -m ai_platform.common.example.jsonschema_processing_example`

### 🖼️ Image Tools (4 Tools)

**Supported:** ImageMagick, GIMP, Inkscape, Dia

### 🎬 Video Tools (3 Tools)

**Supported:** FFmpeg, VLC, VirtualDub

### 📐 Scientific Tools (5 Tools)

**Supported:** MATLAB, Octave, Mathematica, SageMath, Mathcad

### 📊 LaTeX Graphics (6 Libraries)

**Supported:** TikZ, PGF, PGFPlots, CircuiTikZ, Asymptote, MetaPost

### 🎨 SVG Tools (5 Libraries)

**Supported:** Inkscape, SVG.js, Snap.svg, Raphaël, svgwrite

## Architecture

```text
ai_platform/
├── code/
│   ├── common/          # Shared components
│   │   ├── ml/          # ML adapters
│   │   ├── llm/         # LLM adapters
│   │   ├── rag/         # RAG adapters
│   │   ├── vectordb/    # Vector DB adapters
│   │   ├── framework/   # AI framework adapters
│   │   ├── evaluation/  # Evaluation tools
│   │   ├── engine/      # Processing engines
│   │   └── example/     # Usage examples
│   ├── backend/         # Backend services
│   └── frontend/        # Frontend channels
├── test/                # Test suites
├── doc/                 # Documentation
└── data/                # Data files
```

See [Architecture](doc/arch/ARCHITECTURE.md) and [Dependency Rules](doc/arch/DEPENDENCY_RULES.md) for details.

## Installation

```bash
# Core installation
pip install -e .

# Install all ML frameworks
make install-ml

# Install LLM support
pip install -e ".[llm]"

# Install RAG components
pip install -e ".[rag,vectordb]"

# Install visualization
pip install -e ".[viz]"

# Install everything
make install-all
```

## Running Examples

```bash
# ML examples
python -m ai_platform.common.example.ml_example

# LLM examples
python -m ai_platform.common.example.llm_example

# RAG examples
python -m ai_platform.common.example.rag_example

# Framework examples
python -m ai_platform.common.example.framework_example

# All examples are in code/common/example/
```

## Testing

```bash
# Run all tests
pytest test/

# Run ML integration tests
pytest test/functional/integration_test/test_ml_adapters.py

# Run specific test
pytest test/functional/integration_test/test_yaml_processing.py -v
```

## Registry Pattern

All adapters use a registry pattern for easy management:

```python
from ai_platform.common.ml.ml_registry import get_registry

registry = get_registry()
registry.register("pytorch", PyTorchAdapter)
registry.register("tensorflow", TensorFlowAdapter)

# List all registered
print(registry.list())

# Get adapter
ml = registry.get("pytorch")
```

## Contributing

1. Follow add-only evolution principle
2. Respect layer boundaries
3. Add tests for new features
4. Update documentation

## License

See [LICENSE](LICENSE) file.

## Documentation

- [Architecture](doc/arch/ARCHITECTURE.md)
- [Dependency Rules](doc/arch/DEPENDENCY_RULES.md)
- [Known Issues](KNOWN_ISSUES.md)
- [Installation Guide](INSTALL.md)

## Support

For issues and questions, please check:

- [Known Issues](KNOWN_ISSUES.md)
- [Examples](code/common/example/)
- [Tests](test/)
