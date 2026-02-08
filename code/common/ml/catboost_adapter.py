from typing import Any, Dict
import numpy as np
from code.common.ml.base import MLAdapter

class CatBoostAdapter(MLAdapter):
    def __init__(self):
        self.initialized = False
        self.model = None

    def initialize(self, config: Dict[str, Any]) -> None:
        from catboost import CatBoostClassifier
        params = config.get("params", {"iterations": 100, "verbose": False})
        self.model = CatBoostClassifier(**params)
        self.initialized = True

    def train(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        if not self.initialized:
            raise RuntimeError("Not initialized")
        X, y = data["X"], data["y"]
        self.model.fit(X, y)
        return {"framework": "CatBoost", "status": "trained"}

    def predict(self, data: Any, **kwargs) -> Any:
        if not self.initialized or self.model is None:
            raise RuntimeError("Model not trained")
        return self.model.predict(data)

    def save_model(self, path: str) -> None:
        if not self.initialized:
            raise RuntimeError("Not initialized")
        self.model.save_model(path)

    def load_model(self, path: str) -> None:
        from catboost import CatBoostClassifier
        self.model = CatBoostClassifier()
        self.model.load_model(path)
        self.initialized = True

    def shutdown(self) -> None:
        self.initialized = False
        self.model = None
