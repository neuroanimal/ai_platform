
import numpy as np
import onnx
import onnxruntime as ort

from onnx import helper, TensorProto

print("=== ONNX MODEL CREATION ===")

X = helper.make_tensor_value_info(
    "X", TensorProto.FLOAT, [None, 2]
)
Y = helper.make_tensor_value_info(
    "Y", TensorProto.FLOAT, [None, 1]
)

W = helper.make_tensor(
    "W", TensorProto.FLOAT, [2, 1], [2.0, 3.0]
)
B = helper.make_tensor(
    "B", TensorProto.FLOAT, [1], [1.0]
)

node = helper.make_node(
    "Gemm", ["X", "W", "B"], ["Y"]
)

graph = helper.make_graph(
    [node],
    "LinearRegression",
    [X],
    [Y],
    [W, B]
)

model = helper.make_model(
    graph,
    producer_name="ai-platform-test",
    opset_imports=[helper.make_opsetid("", 13)]
)

model.ir_version = 10
onnx.checker.check_model(model)

path = "/tmp/ai_platform_linear.onnx"
onnx.save(model, path)

print("ONNX validation: OK")

print("\n=== ONNX RUNTIME ===")

session = ort.InferenceSession(
    path,
    providers=["CPUExecutionProvider"]
)

data = np.array([
    [1.0, 2.0],
    [3.0, 4.0],
    [5.0, 6.0]
], dtype=np.float32)

result = session.run(
    ["Y"],
    {"X": data}
)[0]

expected = data @ np.array([[2.0], [3.0]]) + 1.0

print("Predictions:", result.flatten())
print("Expected:", expected.flatten())

assert np.allclose(result, expected)

print("Available providers:", ort.get_available_providers())
print("\nALL ONNX TESTS PASSED")

