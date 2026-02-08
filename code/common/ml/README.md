# ML Framework Support

Machine Learning framework adapters.

## Supported Frameworks

- **TensorFlow**: Google's ML framework
- **PyTorch**: Facebook's deep learning framework
- **Scikit-Learn**: Classical ML algorithms
- **Keras**: High-level neural networks API
- **JAX**: High-performance numerical computing
- **XGBoost**: Gradient boosting framework
- **LightGBM**: Fast gradient boosting
- **CatBoost**: Gradient boosting with categorical features
- **MXNet**: Apache deep learning framework

## Usage

```python
from code.common.ml.ml_registry import get_registry
from code.common.ml.pytorch_adapter import PyTorchAdapter

registry = get_registry()
registry.register("pytorch", PyTorchAdapter)

ml = registry.get("pytorch")
ml.initialize({"model_type": "cnn"})
result = ml.train({"X": train_data, "y": labels})
predictions = ml.predict(test_data)
ml.save_model("model.pth")
ml.shutdown()
```
