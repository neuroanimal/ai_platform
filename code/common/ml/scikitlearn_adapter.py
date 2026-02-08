from typing import Any, Dict
import numpy as np
from code.common.ml.base import MLAdapter

class ScikitLearnAdapter(MLAdapter):
    def __init__(self):
        self.initialized = False
        self.model = None
        self.model_type = None

    def initialize(self, config: Dict[str, Any]) -> None:
        from sklearn.linear_model import LogisticRegression
        from sklearn.ensemble import RandomForestClassifier
        self.model_type = config.get("model_type", "logistic")
        if self.model_type == "logistic":
            self.model = LogisticRegression()
        elif self.model_type == "random_forest":
            self.model = RandomForestClassifier()
        self.initialized = True

    def train(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        if not self.initialized:
            raise RuntimeError("Not initialized")
        X, y = data["X"], data["y"]
        self.model.fit(X, y)
        return {"framework": "ScikitLearn", "status": "trained", "model_type": self.model_type}

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
