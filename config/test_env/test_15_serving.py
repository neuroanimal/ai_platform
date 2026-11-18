
import tempfile
from pathlib import Path

import torch
import fastapi
import pydantic

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

print("=== VERSIONS ===")
print("PyTorch:", torch.__version__)
print("FastAPI:", fastapi.__version__)
print("Pydantic:", pydantic.__version__)

torch.manual_seed(42)

print("\n=== MODEL INITIALIZATION ===")

model = torch.nn.Sequential(
    torch.nn.Linear(4, 8),
    torch.nn.ReLU(),
    torch.nn.Linear(8, 2),
)

model.eval()

parameters = sum(p.numel() for p in model.parameters())

print("Parameters:", parameters)

assert parameters > 0

print("\n=== SINGLE INFERENCE ===")

input_tensor = torch.rand(1, 4)

with torch.inference_mode():
    output = model(input_tensor)

assert output.shape == (1, 2)
assert torch.isfinite(output).all()

print("Input:", tuple(input_tensor.shape))
print("Output:", tuple(output.shape))

print("\n=== BATCH INFERENCE ===")

for batch_size in (1, 4, 16):
    batch = torch.rand(batch_size, 4)

    with torch.inference_mode():
        result = model(batch)

    assert result.shape == (batch_size, 2)
    assert torch.isfinite(result).all()

    print(
        f"Batch {batch_size}: "
        f"{tuple(result.shape)}"
    )

print("\n=== TORCHSCRIPT ===")

example = torch.rand(1, 4)

traced_model = torch.jit.trace(model, example)

with torch.inference_mode():
    traced_output = traced_model(example)
    original_output = model(example)

assert torch.allclose(
    traced_output,
    original_output,
    atol=1e-6,
)

with tempfile.TemporaryDirectory() as tmp:
    model_path = Path(tmp) / "model.pt"

    torch.jit.save(traced_model, str(model_path))
    loaded_model = torch.jit.load(str(model_path))

    with torch.inference_mode():
        loaded_output = loaded_model(example)

    assert torch.allclose(
        loaded_output,
        original_output,
        atol=1e-6,
    )

print("TorchScript save/load: PASSED")

print("\n=== STATE DICT SERIALIZATION ===")

with tempfile.TemporaryDirectory() as tmp:
    state_path = Path(tmp) / "model_state.pt"

    torch.save(model.state_dict(), state_path)

    restored_model = torch.nn.Sequential(
        torch.nn.Linear(4, 8),
        torch.nn.ReLU(),
        torch.nn.Linear(8, 2),
    )

    state = torch.load(
        state_path,
        map_location="cpu",
        weights_only=True,
    )

    restored_model.load_state_dict(state)
    restored_model.eval()

    with torch.inference_mode():
        restored_output = restored_model(example)

    assert torch.allclose(
        restored_output,
        original_output,
        atol=1e-6,
    )

print("State dict save/load: PASSED")

print("\n=== FASTAPI APPLICATION ===")

class PredictRequest(BaseModel):
    features: list[float]


class BatchRequest(BaseModel):
    inputs: list[list[float]]


app = FastAPI(title="AI Platform Inference API")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model": "test-model",
        "device": "cpu",
    }


@app.post("/predict")
def predict(request: PredictRequest):
    if len(request.features) != 4:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=422,
            detail="Expected exactly 4 features",
        )

    tensor = torch.tensor(
        [request.features],
        dtype=torch.float32,
    )

    with torch.inference_mode():
        result = model(tensor)

    return {
        "prediction": result[0].tolist()
    }


@app.post("/predict/batch")
def predict_batch(request: BatchRequest):
    if not request.inputs:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=422,
            detail="Batch cannot be empty",
        )

    if any(len(row) != 4 for row in request.inputs):
        from fastapi import HTTPException
        raise HTTPException(
            status_code=422,
            detail="Each input must contain 4 features",
        )

    tensor = torch.tensor(
        request.inputs,
        dtype=torch.float32,
    )

    with torch.inference_mode():
        result = model(tensor)

    return {
        "predictions": result.tolist()
    }


print("\n=== HTTP TESTS ===")

client = TestClient(app)

response = client.get("/health")

assert response.status_code == 200
assert response.json()["status"] == "ok"

print("Health endpoint: PASSED")

response = client.post(
    "/predict",
    json={"features": [0.1, 0.2, 0.3, 0.4]},
)

assert response.status_code == 200

prediction = response.json()["prediction"]

assert len(prediction) == 2

print("Single prediction:", prediction)

response = client.post(
    "/predict/batch",
    json={
        "inputs": [
            [0.1, 0.2, 0.3, 0.4],
            [0.5, 0.6, 0.7, 0.8],
            [0.9, 0.8, 0.7, 0.6],
        ]
    },
)

assert response.status_code == 200

predictions = response.json()["predictions"]

assert len(predictions) == 3
assert all(len(row) == 2 for row in predictions)

print("Batch predictions:", len(predictions))

print("\n=== INPUT VALIDATION ===")

response = client.post(
    "/predict",
    json={"features": [0.1, 0.2]},
)

assert response.status_code == 422

response = client.post(
    "/predict/batch",
    json={"inputs": []},
)

assert response.status_code == 422

print("Invalid input handling: PASSED")

print("\nALL MODEL SERVING TESTS PASSED")

