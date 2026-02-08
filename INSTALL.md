# AI Platform - Installation Guide

## Prerequisites

### System Requirements

- **Python**: 3.13+ (3.15 tested)
- **Node.js**: 18+ (for JavaScript adapters)
- **R**: 4.0+ (for R adapters)
- **Julia**: 1.9+ (for Julia adapters)

### System Dependencies (Linux/Ubuntu)

```bash
# Required for SciPy and scientific computing
sudo apt-get install gfortran

# Optional: For image/video processing
sudo apt-get install imagemagick ffmpeg

# Optional: For LaTeX/TikZ
sudo apt-get install texlive-full
```

## Quick Start

### Option 1: Automated Installation (Recommended)

```bash
# Interactive installer
chmod +x install.sh
./install.sh

# Or use Makefile
make install-all    # Everything
make install-llm    # LLM only
make install-ml     # ML frameworks
```

### Option 2: Manual Installation

```bash
# Core only
pip install -e .

# With specific components
pip install -e ".[llm]"              # LLM providers
pip install -e ".[ml]"               # ML frameworks
pip install -e ".[vectordb]"         # Vector databases
pip install -e ".[rag]"              # RAG frameworks
pip install -e ".[viz]"              # Visualization

# Multiple components
pip install -e ".[llm,rag,vectordb,viz]"
```

## Component Details

### LLM Providers

```bash
pip install -e ".[llm]"
```

Includes: OpenAI, Anthropic, Google Gemini, Cohere

### ML Frameworks

```bash
pip install -e ".[ml]"
```

Includes: scikit-learn, XGBoost

**Note**: PyTorch and TensorFlow require separate installation:

```bash
# PyTorch (CPU)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# TensorFlow
pip install tensorflow
```

### Vector Databases

```bash
pip install -e ".[vectordb]"
```

Includes: ChromaDB, Qdrant

### RAG Frameworks

```bash
pip install -e ".[rag]"
```

Includes: LlamaIndex, LangChain

### Visualization

```bash
pip install -e ".[viz]"
```

Includes: Plotly, Matplotlib, Seaborn

## Known Compatibility Issues

### Python 3.15 Incompatibilities

| Package        | Status                     | Workaround                          |
| -------------- | -------------------------- | ----------------------------------- |
| **FAISS**      | ❌ Not compatible          | Use ChromaDB or Qdrant instead      |
| **PyTorch**    | ⚠️ Requires manual install | `pip install torch ...` (see below) |
| **TensorFlow** | ⚠️ Requires manual install | `pip install tensorflow`            |
| **JAX**        | ⚠️ Requires manual install | `pip install jax[cpu]`              |

(*) `pip install torch --index-url https://download.pytorch.org/whl/cpu`

### Recommended: Use Python 3.13

For maximum compatibility, use Python 3.13:

```bash
pyenv install 3.13.0
pyenv local 3.13.0
```

## JavaScript/Node.js Dependencies

```bash
cd config/requirements
npm install
```

Includes: D3.js, Chart.js, Vega, SVG.js

## R Dependencies

```bash
Rscript config/requirements/install_r_packages.R
```

Includes: ggplot2, caret, dplyr

## Julia Dependencies

```bash
julia config/requirements/install_julia_packages.jl
```

Includes: DataFrames, Plots, MLJ

## Verification

Test installation:

```bash
# Test LLM adapters
python code/common/example/llm_example.py

# Test ML adapters
python code/common/example/ml_example.py

# Test visualization
python code/common/example/visualization_example.py
```

## TODO / Not Yet Implemented

### Adapters Status

✅ **Implemented (Interface Only)**

- All adapters have base interfaces and scaffolds
- Ready for real SDK implementations

❌ **Not Yet Implemented (Real SDKs)**

- Actual API calls to LLM providers
- Real ML model training/inference
- Actual vector database operations
- Real RAG pipeline execution

### Missing Features

1. **Authentication/API Keys**
   - Environment variable management
   - Secure credential storage
   - API key validation

2. **Error Handling**
   - Retry logic
   - Rate limiting
   - Timeout handling

3. **Logging/Monitoring**
   - Structured logging
   - Performance metrics
   - Usage tracking

4. **Testing**
   - Unit tests for all adapters
   - Integration tests
   - Mock implementations

5. **Documentation**
   - API documentation
   - Usage examples for each adapter
   - Best practices guide

### Packages Awaiting Python 3.15 Support

Monitor these for updates:

- FAISS (faiss-cpu)
- Some ML libraries may have limited support

## Troubleshooting

### Issue: "No module named 'code.common'"

```bash
export PYTHONPATH=/path/to/ai_platform
```

### Issue: "gfortran not found"

```bash
sudo apt-get install gfortran
```

### Issue: Package version conflicts

```bash
# Create fresh virtual environment
python -m venv .venv
source .venv/bin/activate
pip install -e ".[llm]"  # Start with minimal install
```

### Issue: FAISS not available

Use alternative vector databases:

```python
# Instead of FAISS
from code.common.vectordb.chromadb_adapter import ChromaDBAdapter
# or
from code.common.vectordb.qdrant_adapter import QdrantAdapter
```

## Development Installation

```bash
make install-dev
```

Includes: pytest, ruff, black, isort

## Uninstall

```bash
pip uninstall ai-platform
make clean
```

## Support

- Issues: GitHub Issues
- Documentation: `doc/` directory
- Examples: `code/common/example/`
