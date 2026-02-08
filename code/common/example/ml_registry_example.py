"""Example usage of ML framework adapters with registry pattern."""

import numpy as np
from ai_platform.common.ml.ml_registry import get_registry
from ai_platform.common.ml.tensorflow_adapter import TensorFlowAdapter
from ai_platform.common.ml.pytorch_adapter import PyTorchAdapter
from ai_platform.common.ml.scikitlearn_adapter import ScikitLearnAdapter
from ai_platform.common.ml.keras_adapter import KerasAdapter
from ai_platform.common.ml.jax_adapter import JAXAdapter
from ai_platform.common.ml.xgboost_adapter import XGBoostAdapter
from ai_platform.common.ml.lightgbm_adapter import LightGBMAdapter
from ai_platform.common.ml.catboost_adapter import CatBoostAdapter
from ai_platform.common.ml.mxnet_adapter import MXNetAdapter

def main():
    registry = get_registry()

    frameworks = {
        "tensorflow": TensorFlowAdapter,
        "pytorch": PyTorchAdapter,
        "scikitlearn": ScikitLearnAdapter,
        "keras": KerasAdapter,
        "jax": JAXAdapter,
        "xgboost": XGBoostAdapter,
        "lightgbm": LightGBMAdapter,
        "catboost": CatBoostAdapter,
        "mxnet": MXNetAdapter,
    }

    for name, adapter_class in frameworks.items():
        registry.register(name, adapter_class)

    print(f"Registered {len(frameworks)} ML frameworks: {registry.list()}\n")

    np.random.seed(42)
    X = np.random.randn(50, 10)
    y = (X[:, 0] + X[:, 1] > 0).astype(float)

    for name in ["scikitlearn", "xgboost", "lightgbm"]:
        print(f"\n=== Testing {name} via registry ===")
        adapter = registry.get(name)
        adapter.initialize({})
        result = adapter.train({"X": X, "y": y})
        print(f"{result['framework']}: {result['status']}")
        predictions = adapter.predict(X[:5])
        print(f"Predictions: {predictions}")
        adapter.shutdown()

if __name__ == "__main__":
    main()
