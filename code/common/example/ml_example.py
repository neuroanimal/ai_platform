"""Example usage of ML framework adapters."""

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
    except ImportError as e:
        print(f"\n=== Scikit-Learn Example === SKIPPED: {e}")

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
    except ImportError as e:
        print(f"\n=== XGBoost Example === SKIPPED: {e}")

def example_lightgbm():
    try:
        from ai_platform.common.ml.lightgbm_adapter import LightGBMAdapter
        print("\n=== LightGBM Example ===")
        X, y = generate_data()
        adapter = LightGBMAdapter()
        adapter.initialize({"params": {"num_leaves": 31}})
        result = adapter.train({"X": X, "y": y})
        print(f"Training: {result}")
        predictions = adapter.predict(X[:5])
        print(f"Predictions: {predictions}")
        adapter.shutdown()
    except ImportError as e:
        print(f"\n=== LightGBM Example === SKIPPED: {e}")

def example_catboost():
    try:
        from ai_platform.common.ml.catboost_adapter import CatBoostAdapter
        print("\n=== CatBoost Example ===")
        X, y = generate_data()
        adapter = CatBoostAdapter()
        adapter.initialize({"params": {"iterations": 50, "verbose": False}})
        result = adapter.train({"X": X, "y": y})
        print(f"Training: {result}")
        predictions = adapter.predict(X[:5])
        print(f"Predictions: {predictions}")
        adapter.shutdown()
    except ImportError as e:
        print(f"\n=== CatBoost Example === SKIPPED: {e}")

def example_pytorch():
    try:
        import sys
        import importlib
        # Work around 'code' package name conflict with stdlib
        if 'torch' in sys.modules:
            importlib.reload(sys.modules['torch'])
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
    except (ImportError, AttributeError) as e:
        print(f"\n=== PyTorch Example === SKIPPED: {e}")

def example_tensorflow():
    try:
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
    except (ImportError, AttributeError) as e:
        print(f"\n=== TensorFlow Example === SKIPPED: {e}")

def example_keras():
    try:
        from ai_platform.common.ml.keras_adapter import KerasAdapter
        print("\n=== Keras Example ===")
        X, y = generate_data()
        adapter = KerasAdapter()
        adapter.initialize({"layers": [10, 16, 1]})
        result = adapter.train({"X": X, "y": y}, epochs=5)
        print(f"Training: {result}")
        predictions = adapter.predict(X[:5])
        print(f"Predictions shape: {predictions.shape}")
        adapter.shutdown()
    except (ImportError, AttributeError) as e:
        print(f"\n=== Keras Example === SKIPPED: {e}")

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
    except (ImportError, AttributeError) as e:
        print(f"\n=== JAX Example === SKIPPED: {e}")

def example_mxnet():
    try:
        from ai_platform.common.ml.mxnet_adapter import MXNetAdapter
        print("\n=== MXNet Example ===")
        X, y = generate_data()
        adapter = MXNetAdapter()
        adapter.initialize({"layers": [10, 16, 1]})
        result = adapter.train({"X": X, "y": y.reshape(-1, 1)}, epochs=5)
        print(f"Training: {result}")
        predictions = adapter.predict(X[:5])
        print(f"Predictions shape: {predictions.shape}")
        adapter.shutdown()
    except (ImportError, AttributeError, OSError) as e:
        print(f"\n=== MXNet Example === SKIPPED: {e}")

def main():
    print("ML Framework Adapters Examples")
    print("=" * 50)
    print("\nDirect adapter usage with real training:\n")
    
    example_sklearn()
    example_xgboost()
    example_lightgbm()
    example_catboost()
    example_pytorch()
    example_tensorflow()
    example_keras()
    example_jax()
    example_mxnet()
    
    print("\n" + "=" * 50)
    print("All examples completed successfully!")
    print("\nNote: For registry-based usage, see ml_registry_example.py")

if __name__ == "__main__":
    main()
