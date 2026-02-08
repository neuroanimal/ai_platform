# AI Platform - Installation Guide

## Quick Start (Automated)

### Option 1: Interactive Script

```bash
chmod +x install.sh
./install.sh
```

### Option 2: Makefile

```bash
# Install everything (includes PyTorch/TensorFlow)
make install-all

# Install specific components
make install-llm
make install-ml
make install-rag
```

## Manual Installation

### Option 1: Install All (Full Platform)

```bash
pip install -r config/requirements/requirements-ai-platform.txt
```

### Option 2: Modular Installation (Recommended)

```bash
# Core only
pip install -e .

# Add specific modules
pip install -e ".[llm]"        # LLM providers
pip install -e ".[ml]"         # ML frameworks
pip install -e ".[vectordb]"   # Vector databases
pip install -e ".[rag]"        # RAG frameworks
pip install -e ".[viz]"        # Visualization

# Install everything
pip install -e ".[all]"
```

## JavaScript/Node.js Dependencies

```bash
cd config/requirements
npm install
```

## R Dependencies

```bash
Rscript config/requirements/install_r_packages.R
```

## Notes

- **Adapters are scaffolds**: They define interfaces but need actual SDK implementations
- **Optional dependencies**: Install only what you need to keep environment lean
- **Version compatibility**: Check individual package docs for compatibility
- **PyTorch/TensorFlow**: Install separately due to platform-specific builds:

  ```bash
  # PyTorch (CPU)
  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
  
  # TensorFlow
  pip install tensorflow
  ```

## Example: Minimal Setup for LLM + RAG

```bash
pip install -e .
pip install -e ".[llm,rag,vectordb]"
```
