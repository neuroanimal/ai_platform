
import os
import time
from pathlib import Path

from huggingface_hub import snapshot_download
import onnxruntime_genai as og

MODEL_REPO = "microsoft/Phi-3-mini-4k-instruct-onnx"
MODEL_SUBDIR = "cpu_and_mobile/cpu-int4-rtn-block-32-acc-level-4"
MODEL_ROOT = Path.home() / "models" / "onnx" / "phi3-mini"
MODEL_DIR = MODEL_ROOT / MODEL_SUBDIR

PROMPT = (
    "<|user|>\n"
    "Wyjaśnij po polsku w 3-4 zdaniach, czym jest lokalny "
    "model językowy SLM i jakie są jego zalety. "
    "<|end|>\n<|assistant|>"
)
MAX_NEW_TOKENS = 96

print("=== ENVIRONMENT ===")
print("Python:", os.sys.version.split()[0])
print("Model:", MODEL_REPO)
print("Quantization: INT4")
print("Device: CPU")

print("\n=== MODEL DOWNLOAD ===")
MODEL_ROOT.mkdir(parents=True, exist_ok=True)

if not (MODEL_DIR / "genai_config.json").exists():
    snapshot_download(
        repo_id=MODEL_REPO,
        local_dir=str(MODEL_ROOT),
        allow_patterns=[f"{MODEL_SUBDIR}/*"],
    )

assert (MODEL_DIR / "genai_config.json").exists(), (
    f"Missing genai_config.json: {MODEL_DIR}"
)

model_bytes = sum(
    p.stat().st_size for p in MODEL_DIR.rglob("*") if p.is_file()
)
print(f"Model directory: {MODEL_DIR}")
print(f"Model size: {model_bytes / 1024**2:.2f} MB")

print("\n=== RUNTIME ===")
print("ONNX Runtime GenAI:", getattr(og, "__version__", "unknown"))


print("CUDA available:", og.is_cuda_available())
print("ROCm available:", getattr(og, "is_rocm_available", lambda: False)())
print("DirectML available:", getattr(og, "is_dml_available", lambda: False)())
print("OpenVINO available:", getattr(og, "is_openvino_available", lambda: False)())


print("\n=== MODEL LOAD ===")
t0 = time.perf_counter()
model = og.Model(str(MODEL_DIR))
tokenizer = og.Tokenizer(model)
load_time = time.perf_counter() - t0
print(f"Load time: {load_time:.2f} s")
print("Device type:", model.device_type)

print("\n=== LOCAL INFERENCE ===")
input_tokens = tokenizer.encode(PROMPT)
params = og.GeneratorParams(model)
params.set_search_options(
    max_length=len(input_tokens) + MAX_NEW_TOKENS,
    do_sample=False,
)

generator = og.Generator(model, params)
t0 = time.perf_counter()
generator.append_tokens(input_tokens)

while not generator.is_done():
    generator.generate_next_token()

elapsed = time.perf_counter() - t0
sequence = generator.get_sequence(0)
output = tokenizer.decode(sequence[len(input_tokens):]).strip()

generated_tokens = len(sequence) - len(input_tokens)
tokens_per_second = generated_tokens / elapsed if elapsed else 0

print("\nMODEL RESPONSE:\n")
print(output)

print("\n=== METRICS ===")
print("Input tokens:", len(input_tokens))
print("Generated tokens:", generated_tokens)
print(f"Inference time: {elapsed:.2f} s")
print(f"Generation speed: {tokens_per_second:.2f} tokens/s")

assert output, "Empty model response"
assert generated_tokens > 0, "No tokens generated"

print("\nALL ONNX RUNTIME GENAI TESTS PASSED")

