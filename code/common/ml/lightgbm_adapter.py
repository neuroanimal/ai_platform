from typing import Any, Dict
import numpy as np
from ai_platform.common.ml.base import MLAdapter

class LightGBMAdapter(MLAdapter):
    def __init__(self):
        self.initialized = False
        self.model = None

    def initialize(self, config: Dict[str, Any]) -> None:
        import lightgbm as lgb
        params = config.get("params", {"objective": "binary"})
        self.model = lgb.LGBMClassifier(**params)
        self.initialized = True

    def train(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        if not self.initialized:
            raise RuntimeError("Not initialized")
        X, y = data["X"], data["y"]
        self.model.fit(X, y)
        return {"framework": "LightGBM", "status": "trained"}

    def predict(self, data: Any, **kwargs) -> Any:
        if not self.initialized or self.model is None:
            raise RuntimeError("Model not trained")
        return self.model.predict(data)

    def save_model(self, path: str) -> None:
        import joblib
        if not self.initialized:
            raise RuntimeError("Not initialized")
        joblib.dump(self.model, path)

    def load_model(self, path: str) -> None:
        import joblib
        self.model = joblib.load(path)
        self.initialized = True

    def shutdown(self) -> None:
        self.initialized = False
        self.model = None
