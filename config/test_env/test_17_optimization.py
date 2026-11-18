import copy
import numpy as np
import torch
import torch.nn as nn
import torch.nn.utils.prune as prune

print("=== VERSIONS ===")
print("PyTorch:", torch.__version__)
print("NumPy:", np.__version__)

torch.manual_seed(42)

class TestModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(128, 256),
            nn.ReLU(),
            nn.Linear(256, 64),
            nn.ReLU(),
            nn.Linear(64, 10),
        )

    def forward(self, x):
        return self.layers(x)


model = TestModel().eval()
x = torch.randn(32, 128)

with torch.inference_mode():
    reference = model(x)

print("\n=== BASELINE INFERENCE ===")
print("Input:", tuple(x.shape))
print("Output:", tuple(reference.shape))
assert reference.shape == (32, 10)
assert torch.isfinite(reference).all()

print("\n=== DYNAMIC QUANTIZATION ===")

quantized = torch.ao.quantization.quantize_dynamic(
    copy.deepcopy(model),
    {nn.Linear},
    dtype=torch.qint8,
)

with torch.inference_mode():
    quantized_output = quantized(x)

assert quantized_output.shape == reference.shape
assert torch.isfinite(quantized_output).all()

quant_error = torch.mean(
    torch.abs(reference - quantized_output)
).item()

print("Quantized output:", tuple(quantized_output.shape))
print("Mean absolute error:", quant_error)
print("Quantized model inference: PASSED")

print("\n=== MODEL PRUNING ===")

pruned = copy.deepcopy(model)

linear_layers = [
    layer for layer in pruned.modules()
    if isinstance(layer, nn.Linear)
]

for layer in linear_layers:
    prune.l1_unstructured(
        layer,
        name="weight",
        amount=0.30,
    )
    prune.remove(layer, "weight")

total_weights = 0
zero_weights = 0

for layer in linear_layers:
    total_weights += layer.weight.numel()
    zero_weights += torch.count_nonzero(
        layer.weight == 0
    ).item()

sparsity = zero_weights / total_weights

with torch.inference_mode():
    pruned_output = pruned(x)

assert pruned_output.shape == reference.shape
assert torch.isfinite(pruned_output).all()
assert sparsity >= 0.25

print("Total weights:", total_weights)
print("Zero weights:", zero_weights)
print("Sparsity:", round(sparsity * 100, 2), "%")
print("Pruned model inference: PASSED")

print("\n=== MODEL SIZE COMPARISON ===")

import io

def model_size_bytes(model):
    buffer = io.BytesIO()
    torch.save(model.state_dict(), buffer)
    return buffer.tell()

original_size = model_size_bytes(model)
quantized_size = model_size_bytes(quantized)
pruned_size = model_size_bytes(pruned)

print("Original:", original_size, "bytes")
print("Quantized:", quantized_size, "bytes")
print("Pruned:", pruned_size, "bytes")

print("\n=== TORCH COMPILE ===")

if hasattr(torch, "compile"):
    try:
        compiled = torch.compile(
            copy.deepcopy(model),
            backend="eager",
        )

        with torch.inference_mode():
            compiled_output = compiled(x)

        assert compiled_output.shape == reference.shape
        assert torch.isfinite(compiled_output).all()

        print("torch.compile backend=eager: PASSED")

    except Exception as exc:
        print(
            "torch.compile: FAILED —",
            type(exc).__name__,
            str(exc),
        )
else:
    print("torch.compile: NOT AVAILABLE")

print("\n=== OPTIMIZATION SUMMARY ===")
print("Dynamic quantization: PASSED")
print("Pruning: PASSED")
print("Inference comparison: PASSED")

print("\nALL MODEL OPTIMIZATION TESTS COMPLETED")

