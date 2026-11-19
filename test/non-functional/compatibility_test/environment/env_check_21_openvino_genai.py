
import os
import time
from pathlib import Path

import openvino as ov
import openvino_genai as ov_genai

MODEL_DIR = (
    Path.home()
    / "models"
    / "openvino"
    / "qwen25-05b-int4"
)

PROMPT = (
    "<|im_start|>user\n"
    "Wyjaśnij po polsku w 3-4 zdaniach, czym jest lokalny "
    "model językowy SLM i jakie są jego zalety."
    "<|im_end|>\n"
    "<|im_start|>assistant\n"
)

MAX_NEW_TOKENS = 96

print("=== ENVIRONMENT ===")
print("Python:", os.sys.version.split()[0])
print("OpenVINO:", ov.__version__)
print("Devices:", ov.Core().available_devices)
print("Model:", MODEL_DIR)

assert MODEL_DIR.exists(), f"Model not found: {MODEL_DIR}"

model_bytes = sum(
    p.stat().st_size for p in MODEL_DIR.rglob("*") if p.is_file()
)
print(f"Model size: {model_bytes / 1024**2:.2f} MB")

print("\n=== MODEL LOAD ===")
t0 = time.perf_counter()
pipeline = ov_genai.LLMPipeline(str(MODEL_DIR), "CPU")
load_time = time.perf_counter() - t0
print(f"Load time: {load_time:.2f} s")

print("\n=== LOCAL INFERENCE ===")
config = ov_genai.GenerationConfig()
config.max_new_tokens = MAX_NEW_TOKENS
config.do_sample = False

t0 = time.perf_counter()
output = pipeline.generate(PROMPT, config)
elapsed = time.perf_counter() - t0

if isinstance(output, str):
    response = output.strip()
else:
    response = str(output).strip()

print("\nMODEL RESPONSE:\n")
print(response)

print("\n=== METRICS ===")
print(f"Inference time: {elapsed:.2f} s")
print("Max new tokens:", MAX_NEW_TOKENS)

assert response, "Empty model response"

print("\nALL OPENVINO GENAI TESTS PASSED")

