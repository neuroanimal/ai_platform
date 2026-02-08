#!/bin/bash
# AI Platform - Automated Installation Script

set -e

echo "=== AI Platform Installation ==="

# Install system dependencies (Linux/WSL)
if [[ "${OSTYPE}" == "linux-gnu"* ]]; then
    echo "Installing system dependencies..."
    sudo apt-get update
    sudo apt-get install -y libjpeg-dev zlib1g-dev libtiff-dev libfreetype6-dev liblcms2-dev libwebp-dev gfortran
fi

# Detect platform
if [[ "${OSTYPE}" == "linux-gnu"* ]]; then
    export PLATFORM="linux"
elif [[ "${OSTYPE}" == "darwin"* ]]; then
    export PLATFORM="mac"
else
    export PLATFORM="other"
fi

# Install core
echo "Installing core dependencies..."
pip install -e .

# Ask user what to install
echo ""
echo "Select components to install:"
echo "1) All (LLM, ML, VectorDB, RAG, Viz)"
echo "2) LLM only"
echo "3) ML only"
echo "4) Custom selection"
echo "5) Skip optional dependencies"
read -r -p "Choice [1-5]: " choice

case ${choice} in
    1)
        echo "Installing all components..."
        export PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1
        pip install -e ".[all]"

        # Install PyTorch
        echo "Installing PyTorch..."
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

        # Install TensorFlow
        echo "Installing TensorFlow..."
        pip install tensorflow
        ;;
    2)
        export PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1
        pip install -e ".[llm]"
        ;;
    3)
        export PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1
        pip install -e ".[ml]"
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
        pip install tensorflow
        ;;
    4)
        echo "Available: llm, ml, vectordb, rag, viz"
        read -r -p "Enter comma-separated list (e.g., llm,rag): " components
        export PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1
        pip install -e ".[${components}]"

        if [[ ${components} == *"ml"* ]]; then
            echo "Installing PyTorch and TensorFlow..."
            pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
            pip install tensorflow
        fi
        ;;
    5)
        echo "Skipping optional dependencies"
        ;;
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Installing JavaScript dependencies..."
if command -v yarn &> /dev/null; then
    cd config/requirements && yarn install && cd ../..
    echo "JavaScript dependencies installed"
else
    echo "Warning: yarn not found. Skip with: sudo npm install -g yarn"
fi

echo ""
echo "=== Setup Complete ==="
echo "Run examples: python code/common/example/llm_example.py"
