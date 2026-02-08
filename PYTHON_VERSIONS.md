# Python Version Strategy

## Virtual Environments

This project uses two linked virtual environments to support both stable (3.13) and experimental (3.15) Python versions:

- **`.venv`** (Python 3.13) - Production, LLM, RAG, VectorDB
- **`.venv.ai`** (Python 3.15) - Experimental, Visualization, ML

## Package Compatibility

### Python 3.15 Compatible

- ✅ matplotlib, pandas, numpy, pillow
- ✅ plotly, seaborn
- ✅ scikit-learn, xgboost

### Python 3.13 Required (no 3.15 wheels yet)

- ❌ pydantic-core (used by langchain, anthropic, cohere)
- ❌ grpcio (used by qdrant-client)
- ❌ chromadb, llama-index

## Usage

```bash
# For LLM/RAG work
source ~/repo/.venv/bin/activate
pip install -e ".[llm,rag,vectordb]"

# For visualization/ML
source ~/repo/.venv.ai/bin/activate
export PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1
pip install --prefer-binary -e ".[viz,ml]"
```

## Notes

The venvs share packages via symlinks where possible. Packages with compiled extensions (.so files) are version-specific and cannot be shared.
