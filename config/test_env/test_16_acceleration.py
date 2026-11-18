import sys
import warnings
import numpy as np
import torch
import torch.nn as nn

print("=== VERSIONS ===")
print("Python:", sys.version.split()[0])
print("PyTorch:", torch.__version__)
print("CUDA build:", torch.version.cuda)
print("ROCm build:", torch.version.hip)

print("\n=== HARDWARE DETECTION ===")

devices = ["cpu"]

if torch.cuda.is_available():
    devices.append("cuda")

if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
    devices.append("mps")

if hasattr(torch, "xpu") and torch.xpu.is_available():
    devices.append("xpu")

for device in devices:
    print(f"Available PyTorch device: {device}")

print("\n=== DEVICE INFERENCE ===")

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
x = torch.randn(16, 128)

for device in devices:
    try:
        device_model = model.to(device)
        device_input = x.to(device)

        with torch.inference_mode():
            output = device_model(device_input)

        assert output.shape == (16, 10)
        assert torch.isfinite(output).all()

        print(f"{device}: PASSED — {tuple(output.shape)}")

    except Exception as exc:
        print(f"{device}: FAILED — {type(exc).__name__}: {exc}")
        if device == "cpu":
            raise

    finally:
        model = model.cpu()
        x = x.cpu()

print("\n=== ONNX RUNTIME PROVIDERS ===")

try:
    import onnx
    import onnxruntime as ort

    print("ONNX:", onnx.__version__)
    print("ONNX Runtime:", ort.__version__)

    available = ort.get_available_providers()
    print("Available providers:", available)

    class ExportModel(nn.Module):
        def __init__(self):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(128, 64),
                nn.ReLU(),
                nn.Linear(64, 10),
            )

        def forward(self, x):
            return self.net(x)

    export_model = ExportModel().eval()
    sample = torch.randn(4, 128)

    torch.onnx.export(
        export_model,
        sample,
        "test_16_acceleration.onnx",
        input_names=["input"],
        output_names=["output"],
        dynamic_axes={
            "input": {0: "batch"},
            "output": {0: "batch"},
        },
        opset_version=17,
        dynamo=False,
    )

    onnx.checker.check_model("test_16_acceleration.onnx")
    print("ONNX export and validation: PASSED")

    print("\n=== PROVIDER INFERENCE ===")

    for provider in available:
        try:
            session = ort.InferenceSession(
                "test_16_acceleration.onnx",
                providers=[provider],
            )

            result = session.run(
                ["output"],
                {"input": sample.numpy()},
            )[0]

            assert result.shape == (4, 10)
            assert np.isfinite(result).all()

            print(f"{provider}: PASSED — {result.shape}")

        except Exception as exc:
            print(f"{provider}: FAILED — {type(exc).__name__}: {exc}")

except ImportError as exc:
    print("ONNX Runtime test skipped:", exc)

print("\n=== HARDWARE SUMMARY ===")
print("PyTorch devices:", devices)

if torch.version.hip:
    print("AMD ROCm build detected.")
elif torch.version.cuda:
    print("NVIDIA CUDA build detected.")
else:
    print("No CUDA/ROCm build detected.")

print("\nALL AVAILABLE HARDWARE TESTS COMPLETED")

