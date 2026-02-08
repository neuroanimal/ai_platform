from typing import Any, Dict
import numpy as np
from code.common.ml.base import MLAdapter

class PyTorchAdapter(MLAdapter):
    def __init__(self):
        self.initialized = False
        self.model = None
        self.device = None

    def initialize(self, config: Dict[str, Any]) -> None:
        import torch
        import torch.nn as nn
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        layers = config.get("layers", [64, 32, 1])
        modules = []
        for i in range(len(layers) - 1):
            modules.append(nn.Linear(layers[i], layers[i+1]))
            if i < len(layers) - 2:
                modules.append(nn.ReLU())
        self.model = nn.Sequential(*modules).to(self.device)
        self.initialized = True

    def train(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        import torch
        import torch.nn as nn
        if not self.initialized:
            raise RuntimeError("Not initialized")
        X = torch.FloatTensor(data["X"]).to(self.device)
        y = torch.FloatTensor(data["y"]).to(self.device)
        optimizer = torch.optim.Adam(self.model.parameters())
        criterion = nn.BCEWithLogitsLoss()
        epochs = kwargs.get("epochs", 10)
        for _ in range(epochs):
            optimizer.zero_grad()
            output = self.model(X)
            loss = criterion(output.squeeze(), y)
            loss.backward()
            optimizer.step()
        return {"framework": "PyTorch", "status": "trained", "epochs": epochs}

    def predict(self, data: Any, **kwargs) -> Any:
        import torch
        if not self.initialized or self.model is None:
            raise RuntimeError("Model not trained")
        X = torch.FloatTensor(data).to(self.device)
        with torch.no_grad():
            return self.model(X).cpu().numpy()

    def save_model(self, path: str) -> None:
        import torch
        if not self.initialized:
            raise RuntimeError("Not initialized")
        torch.save(self.model.state_dict(), path)

    def load_model(self, path: str) -> None:
        import torch
        self.model.load_state_dict(torch.load(path))
        self.initialized = True

    def shutdown(self) -> None:
        self.initialized = False
        self.model = None
