from typing import Any, Dict
import numpy as np
from ai_platform.common.ml.base import MLAdapter

class MXNetAdapter(MLAdapter):
    def __init__(self):
        self.initialized = False
        self.model = None
        self.ctx = None

    def initialize(self, config: Dict[str, Any]) -> None:
        import mxnet as mx
        from mxnet import gluon
        self.ctx = mx.cpu()
        layers = config.get("layers", [64, 32, 1])
        self.model = gluon.nn.Sequential()
        with self.model.name_scope():
            for i, units in enumerate(layers):
                self.model.add(gluon.nn.Dense(units, activation='relu' if i < len(layers)-1 else 'sigmoid'))
        self.model.initialize(mx.init.Xavier(), ctx=self.ctx)
        self.initialized = True

    def train(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        import mxnet as mx
        from mxnet import gluon, autograd
        if not self.initialized:
            raise RuntimeError("Not initialized")
        X = mx.nd.array(data["X"], ctx=self.ctx)
        y = mx.nd.array(data["y"], ctx=self.ctx)
        trainer = gluon.Trainer(self.model.collect_params(), 'adam')
        loss_fn = gluon.loss.SigmoidBinaryCrossEntropyLoss()
        epochs = kwargs.get("epochs", 10)
        for _ in range(epochs):
            with autograd.record():
                output = self.model(X)
                loss = loss_fn(output, y)
            loss.backward()
            trainer.step(len(X))
        return {"framework": "MXNet", "status": "trained", "epochs": epochs}

    def predict(self, data: Any, **kwargs) -> Any:
        import mxnet as mx
        if not self.initialized or self.model is None:
            raise RuntimeError("Model not trained")
        X = mx.nd.array(data, ctx=self.ctx)
        return self.model(X).asnumpy()

    def save_model(self, path: str) -> None:
        if not self.initialized:
            raise RuntimeError("Not initialized")
        self.model.save_parameters(path)

    def load_model(self, path: str) -> None:
        if self.model:
            self.model.load_parameters(path)
            self.initialized = True

    def shutdown(self) -> None:
        self.initialized = False
        self.model = None
