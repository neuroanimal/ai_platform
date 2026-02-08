from typing import Any, Dict
import numpy as np
from ai_platform.common.ml.base import MLAdapter

class KerasAdapter(MLAdapter):
    def __init__(self):
        self.initialized = False
        self.model = None

    def initialize(self, config: Dict[str, Any]) -> None:
        from tensorflow import keras
        layers = config.get("layers", [64, 32, 1])
        self.model = keras.Sequential([
            keras.layers.Dense(layers[i], activation='relu' if i < len(layers)-1 else 'sigmoid')
            for i in range(len(layers))
        ])
        self.model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
        self.initialized = True

    def train(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        if not self.initialized:
            raise RuntimeError("Not initialized")
        X, y = data["X"], data["y"]
        epochs = kwargs.get("epochs", 10)
        self.model.fit(X, y, epochs=epochs, verbose=0)
        return {"framework": "Keras", "status": "trained", "epochs": epochs}

    def predict(self, data: Any, **kwargs) -> Any:
        if not self.initialized or self.model is None:
            raise RuntimeError("Model not trained")
        return self.model.predict(data, verbose=0)

    def save_model(self, path: str) -> None:
        if not self.initialized:
            raise RuntimeError("Not initialized")
        self.model.save(path)

    def load_model(self, path: str) -> None:
        from tensorflow import keras
        self.model = keras.models.load_model(path)
        self.initialized = True

    def shutdown(self) -> None:
        self.initialized = False
        self.model = None
