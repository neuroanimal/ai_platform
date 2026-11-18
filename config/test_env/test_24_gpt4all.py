
import os
import time
from pathlib import Path

from gpt4all import GPT4All

MODEL_PATH = (
    Path.home()
    / "models"
    / "gguf"
    / "qwen25-05b"
)

MODEL_FILE = "Qwen2.5-0.5B-Instruct-Q4_K_M.gguf"

PROMPT = (
    "Wyjaśnij po polsku w 3-4 zdaniach, czym jest lokalny "
    "model językowy SLM i jakie są jego zalety."
)

MAX_TOKENS = 96

model_file = MODEL_PATH / MODEL_FILE

print("=== ENVIRONMENT ===")
print("Python:", os.sys.version.split()[0])
print("Engine: GPT4All")
print("Model:", model_file)
print("Device: CPU")

assert model_file.exists(), f"GGUF not found: {model_file}"

print(f"Model size: {model_file.stat().st_size / 1024**2:.2f} MB")

print("\n=== MODEL LOAD ===")
t0 = time.perf_counter()

model = GPT4All(
    model_name=MODEL_FILE,
    model_path=str(MODEL_PATH),
    allow_download=False,
    device="cpu",
    n_threads=max(1, os.cpu_count() or 1),
    n_ctx=2048,
    verbose=False,
)

load_time = time.perf_counter() - t0
print(f"Load time: {load_time:.2f} s")

print("\n=== LOCAL INFERENCE ===")
t0 = time.perf_counter()

with model.chat_session():
    output = model.generate(
        PROMPT,
        max_tokens=MAX_TOKENS,
        temp=0.0,
    )

elapsed = time.perf_counter() - t0

print("\nMODEL RESPONSE:\n")
print(output)

print("\n=== METRICS ===")
print(f"Inference time: {elapsed:.2f} s")
print("Max new tokens:", MAX_TOKENS)

assert output.strip(), "Empty model response"

model.close()

print("\nALL GPT4ALL TESTS PASSED")

