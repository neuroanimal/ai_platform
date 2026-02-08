#!/usr/bin/env python3
"""Standalone ML example that works around 'code' package naming conflict."""

import sys
import os

# Get the project root directory
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import numpy as np

def generate_data(n_samples=100):
    """Generate synthetic binary classification data."""
    np.random.seed(42)
    X = np.random.randn(n_samples, 10)
    y = (X[:, 0] + X[:, 1] > 0).astype(float)
    return X, y

def example_sklearn():
    try:
        from ai_platform.common.ml.scikitlearn_adapter import ScikitLearnAdapter
        print("\n=== Scikit-Learn Example ===")
        X, y = generate_data()
        adapter = ScikitLearnAdapter()
        adapter.initialize({"model_type": "logistic"})
        result = adapter.train({"X": X, "y": y})
        print(f"Training: {result}")
        predictions = adapter.predict(X[:5])
        print(f"Predictions: {predictions}")
        adapter.shutdown()
    except Exception as e:
        print(f"\n=== Scikit-Learn Example === SKIPPED: {e}")

def example_pytorch():
    try:
        # Import torch BEFORE importing from 'code' package
        import torch
        import torch.nn as nn
        from ai_platform.common.ml.pytorch_adapter import PyTorchAdapter
        print("\n=== PyTorch Example ===")
        X, y = generate_data()
        adapter = PyTorchAdapter()
        adapter.initialize({"layers": [10, 16, 1]})
        result = adapter.train({"X": X, "y": y}, epochs=5)
        print(f"Training: {result}")
        predictions = adapter.predict(X[:5])
        print(f"Predictions shape: {predictions.shape}")
        adapter.shutdown()
    except Exception as e:
        print(f"\n=== PyTorch Example === SKIPPED: {e}")

def example_tensorflow():
    try:
        # Import tensorflow BEFORE importing from 'code' package
        import tensorflow as tf
        from ai_platform.common.ml.tensorflow_adapter import TensorFlowAdapter
        print("\n=== TensorFlow Example ===")
        X, y = generate_data()
        adapter = TensorFlowAdapter()
        adapter.initialize({"layers": [10, 16, 1]})
        result = adapter.train({"X": X, "y": y}, epochs=5)
        print(f"Training: {result}")
        predictions = adapter.predict(X[:5])
        print(f"Predictions shape: {predictions.shape}")
        adapter.shutdown()
    except Exception as e:
        print(f"\n=== TensorFlow Example === SKIPPED: {e}")

def example_xgboost():
    try:
        from ai_platform.common.ml.xgboost_adapter import XGBoostAdapter
        print("\n=== XGBoost Example ===")
        X, y = generate_data()
        adapter = XGBoostAdapter()
        adapter.initialize({"params": {"max_depth": 3}})
        result = adapter.train({"X": X, "y": y})
        print(f"Training: {result}")
        predictions = adapter.predict(X[:5])
        print(f"Predictions: {predictions}")
        adapter.shutdown()
    except Exception as e:
        print(f"\n=== XGBoost Example === SKIPPED: {e}")

def example_jax():
    try:
        from ai_platform.common.ml.jax_adapter import JAXAdapter
        print("\n=== JAX Example ===")
        X, y = generate_data()
        adapter = JAXAdapter()
        adapter.initialize({"input_dim": 10, "output_dim": 1})
        result = adapter.train({"X": X, "y": y}, epochs=5, lr=0.01)
        print(f"Training: {result}")
        predictions = adapter.predict(X[:5])
        print(f"Predictions shape: {predictions.shape}")
        adapter.shutdown()
    except Exception as e:
        print(f"\n=== JAX Example === SKIPPED: {e}")

def main():
    print("ML Framework Adapters - Standalone Examples")
    print("=" * 50)
    print("\nWorkaround for 'code' package naming conflict\n")
    
    example_sklearn()
    example_xgboost()
    example_pytorch()
    example_tensorflow()
    example_jax()
    
    print("\n" + "=" * 50)
    print("Examples completed!")

if __name__ == "__main__":
    main()
