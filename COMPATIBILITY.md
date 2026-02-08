# AI Platform - Compatibility Notes

## Python Version Compatibility

### Tested Versions

- ✅ Python 3.13.x - **Recommended**
- ⚠️ Python 3.15.x - **Partial support** (some packages not yet compatible)

### Python 3.15 Known Issues

#### Not Compatible

1. **FAISS (faiss-cpu)**
   - Status: No Python 3.15 wheels available
   - Alternative: Use ChromaDB, Qdrant, or Milvus
   - Tracking: <https://github.com/facebookresearch/faiss/issues>

2. **Some ML Libraries**
   - May have delayed Python 3.15 support
   - Check individual package PyPI pages

#### Requires Manual Installation

1. **PyTorch**
   - Reason: Platform-specific builds
   - Install: `pip install torch --index-url https://download.pytorch.org/whl/cpu`

2. **TensorFlow**
   - Reason: Platform-specific builds
   - Install: `pip install tensorflow`

3. **JAX**
   - Reason: Platform-specific builds
   - Install: `pip install jax[cpu]`

## Adapter Implementation Status

### Interface vs Implementation

All adapters follow this pattern:

- ✅ **Interface defined** - Base class with abstract methods
- ✅ **Scaffold created** - Minimal implementation for testing
- ❌ **Real SDK integration** - Actual API calls not yet implemented

### What Works Now

- Registry pattern and adapter discovery
- Interface contracts and type hints
- Example code execution (with mock responses)
- Architecture and structure

### What Needs Implementation

- Actual API calls to external services
- Authentication and credential management
- Error handling and retries
- Real data processing

## Platform-Specific Notes

### Linux (Ubuntu/Debian)

```bash
# Required for scientific computing
sudo apt-get install gfortran libopenblas-dev

# Optional for image/video
sudo apt-get install imagemagick ffmpeg

# Optional for LaTeX
sudo apt-get install texlive-full
```

### macOS

```bash
# Using Homebrew
brew install gcc openblas

# Optional
brew install imagemagick ffmpeg
brew install --cask mactex
```

### Windows

- Use WSL2 for best compatibility
- Or install packages via conda/mamba

## External Service Requirements

### LLM Providers (Require API Keys)

- OpenAI: <https://platform.openai.com/api-keys>
- Anthropic: <https://console.anthropic.com/>
- Google: <https://makersuite.google.com/app/apikey>
- Cohere: <https://dashboard.cohere.com/api-keys>

### Vector Databases (May Require Setup)

- Qdrant: Can run locally or cloud
- ChromaDB: Local by default
- Pinecone: Cloud service, requires API key
- Milvus: Requires Docker or installation

### Scientific Computing Tools (Require Installation)

- MATLAB: Commercial license required
- Mathematica: Commercial license required
- Octave: Free alternative to MATLAB

## Dependency Conflicts

### Known Conflicts

1. **NumPy versions**
   - Some packages require NumPy < 2.0
   - Others require NumPy >= 2.0
   - Solution: Use virtual environments per project

2. **Protobuf versions**
   - TensorFlow and other packages may conflict
   - Solution: Pin compatible versions

### Resolution Strategy

```bash
# Create isolated environments
python -m venv .venv-llm    # For LLM work
python -m venv .venv-ml     # For ML work
python -m venv .venv-viz    # For visualization
```

## Performance Notes

### Large Dependencies

These packages are large and take time to install:

- PyTorch: ~2GB
- TensorFlow: ~500MB
- SciPy: Requires compilation (with gfortran)

### Recommended Installation Order

1. Core dependencies first
2. Add one category at a time
3. Test after each addition

## Future Compatibility

### Monitoring

Track these for Python 3.15+ support:

- [ ] FAISS
- [ ] Some ML frameworks
- [ ] Scientific computing packages

### Migration Path

When packages add Python 3.15 support:

1. Update `pyproject.toml`
2. Update `requirements-ai-platform.txt`
3. Test thoroughly
4. Update this document

## Getting Help

### Before Opening an Issue

1. Check Python version: `python --version`
2. Check installed packages: `pip list`
3. Try with Python 3.13 if using 3.15
4. Check package-specific documentation

### Useful Commands

```bash
# Check Python version
python --version

# Check installed packages
pip list | grep -E "torch|tensorflow|faiss|chromadb"

# Verify installation
python -c "import code.common; print('OK')"

# Test specific adapter
python code/common/example/llm_example.py
```
