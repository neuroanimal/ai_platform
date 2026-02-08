"""Integration tests for ML framework adapters."""

import pytest
import numpy as np
from code.common.ml.scikitlearn_adapter import ScikitLearnAdapter
from code.common.ml.xgboost_adapter import XGBoostAdapter
from code.common.ml.lightgbm_adapter import LightGBMAdapter
from code.common.ml.catboost_adapter import CatBoostAdapter
from code.common.ml.pytorch_adapter import PyTorchAdapter
from code.common.ml.tensorflow_adapter import TensorFlowAdapter
from code.common.ml.keras_adapter import KerasAdapter
from code.common.ml.jax_adapter import JAXAdapter
from code.common.ml.mxnet_adapter import MXNetAdapter

@pytest.fixture
def sample_data():
    """Generate sample data for testing."""
    np.random.seed(42)
    X = np.random.randn(50, 10)
    y = (X[:, 0] + X[:, 1] > 0).astype(float)
    return X, y

def test_sklearn_adapter(sample_data):
    X, y = sample_data
    adapter = ScikitLearnAdapter()
    adapter.initialize({"model_type": "logistic"})
    result = adapter.train({"X": X, "y": y})
    assert result["framework"] == "ScikitLearn"
    assert result["status"] == "trained"
    predictions = adapter.predict(X[:5])
    assert len(predictions) == 5
    adapter.shutdown()

def test_xgboost_adapter(sample_data):
    X, y = sample_data
    adapter = XGBoostAdapter()
    adapter.initialize({"params": {"max_depth": 3}})
    result = adapter.train({"X": X, "y": y})
    assert result["framework"] == "XGBoost"
    assert result["status"] == "trained"
    predictions = adapter.predict(X[:5])
    assert len(predictions) == 5
    adapter.shutdown()

def test_lightgbm_adapter(sample_data):
    X, y = sample_data
    adapter = LightGBMAdapter()
    adapter.initialize({"params": {"num_leaves": 31}})
    result = adapter.train({"X": X, "y": y})
    assert result["framework"] == "LightGBM"
    assert result["status"] == "trained"
    predictions = adapter.predict(X[:5])
    assert len(predictions) == 5
    adapter.shutdown()

def test_catboost_adapter(sample_data):
    X, y = sample_data
    adapter = CatBoostAdapter()
    adapter.initialize({"params": {"iterations": 10, "verbose": False}})
    result = adapter.train({"X": X, "y": y})
    assert result["framework"] == "CatBoost"
    assert result["status"] == "trained"
    predictions = adapter.predict(X[:5])
    assert len(predictions) == 5
    adapter.shutdown()

def test_pytorch_adapter(sample_data):
    X, y = sample_data
    adapter = PyTorchAdapter()
    adapter.initialize({"layers": [10, 16, 1]})
    result = adapter.train({"X": X, "y": y}, epochs=3)
    assert result["framework"] == "PyTorch"
    assert result["status"] == "trained"
    predictions = adapter.predict(X[:5])
    assert predictions.shape[0] == 5
    adapter.shutdown()

def test_tensorflow_adapter(sample_data):
    X, y = sample_data
    adapter = TensorFlowAdapter()
    adapter.initialize({"layers": [10, 16, 1]})
    result = adapter.train({"X": X, "y": y}, epochs=3)
    assert result["framework"] == "TensorFlow"
    assert result["status"] == "trained"
    predictions = adapter.predict(X[:5])
    assert predictions.shape[0] == 5
    adapter.shutdown()

def test_keras_adapter(sample_data):
    X, y = sample_data
    adapter = KerasAdapter()
    adapter.initialize({"layers": [10, 16, 1]})
    result = adapter.train({"X": X, "y": y}, epochs=3)
    assert result["framework"] == "Keras"
    assert result["status"] == "trained"
    predictions = adapter.predict(X[:5])
    assert predictions.shape[0] == 5
    adapter.shutdown()

def test_jax_adapter(sample_data):
    X, y = sample_data
    adapter = JAXAdapter()
    adapter.initialize({"input_dim": 10, "output_dim": 1})
    result = adapter.train({"X": X, "y": y}, epochs=3, lr=0.01)
    assert result["framework"] == "JAX"
    assert result["status"] == "trained"
    predictions = adapter.predict(X[:5])
    assert predictions.shape[0] == 5
    adapter.shutdown()

def test_mxnet_adapter(sample_data):
    X, y = sample_data
    adapter = MXNetAdapter()
    adapter.initialize({"layers": [10, 16, 1]})
    result = adapter.train({"X": X, "y": y.reshape(-1, 1)}, epochs=3)
    assert result["framework"] == "MXNet"
    assert result["status"] == "trained"
    predictions = adapter.predict(X[:5])
    assert predictions.shape[0] == 5
    adapter.shutdown()
