from typing import Any, Dict
import numpy as np
from code.common.ml.base import MLAdapter

class JAXAdapter(MLAdapter):
    def __init__(self):
        self.initialized = False
        self.params = None

    def initialize(self, config: Dict[str, Any]) -> None:
        import jax.numpy as jnp
        from jax import random
        key = random.PRNGKey(0)
        input_dim = config.get("input_dim", 64)
        output_dim = config.get("output_dim", 1)
        self.params = {
            'w': random.normal(key, (input_dim, output_dim)),
            'b': jnp.zeros(output_dim)
        }
        self.initialized = True

    def train(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        import jax.numpy as jnp
        from jax import grad
        if not self.initialized:
            raise RuntimeError("Not initialized")
        X, y = jnp.array(data["X"]), jnp.array(data["y"])
        lr = kwargs.get("lr", 0.01)
        epochs = kwargs.get("epochs", 10)
        for _ in range(epochs):
            pred = jnp.dot(X, self.params['w']) + self.params['b']
            loss = jnp.mean((pred.squeeze() - y) ** 2)
            grad_w = jnp.dot(X.T, (pred.squeeze() - y)) / len(y)
            grad_b = jnp.mean(pred.squeeze() - y)
            self.params['w'] -= lr * grad_w.reshape(self.params['w'].shape)
            self.params['b'] -= lr * grad_b
        return {"framework": "JAX", "status": "trained", "epochs": epochs}

    def predict(self, data: Any, **kwargs) -> Any:
        import jax.numpy as jnp
        if not self.initialized or self.params is None:
            raise RuntimeError("Model not trained")
        X = jnp.array(data)
        return np.array(jnp.dot(X, self.params['w']) + self.params['b'])

    def save_model(self, path: str) -> None:
        if not self.initialized:
            raise RuntimeError("Not initialized")
        np.savez(path, **{k: np.array(v) for k, v in self.params.items()})

    def load_model(self, path: str) -> None:
        import jax.numpy as jnp
        loaded = np.load(path)
        self.params = {k: jnp.array(loaded[k]) for k in loaded.files}
        self.initialized = True

    def shutdown(self) -> None:
        self.initialized = False
        self.params = None
