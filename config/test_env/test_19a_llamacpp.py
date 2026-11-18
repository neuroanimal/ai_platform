
import subprocess
import time
import platform
from pathlib import Path

# ============================================================
# CONFIGURATION
# ============================================================

LLAMA_CLI = Path.home() / "tools/llama.cpp/build/bin/llama-cli"

MODEL = (
    Path.home()
    / "models/gguf/qwen25-05b/"
    / "Qwen2.5-0.5B-Instruct-Q4_K_M.gguf"
)

MAX_TOKENS = 96

PROMPT = (
    "<|im_start|>user\n"
    "Wyjaśnij po polsku w 3-4 zdaniach, czym jest lokalny "
    "model językowy SLM i jakie są jego zalety.\n"
    "<|im_end|>\n"
    "<|im_start|>assistant\n"
)

# ============================================================
# ENVIRONMENT
# ============================================================

print("=== ENVIRONMENT ===")
print("Python:", platform.python_version())
print("Platform:", platform.platform())

assert LLAMA_CLI.exists(), f"Missing binary: {LLAMA_CLI}"
assert MODEL.exists(), f"Missing model: {MODEL}"

print("llama.cpp binary:", LLAMA_CLI)
print("Model:", MODEL)
print("Model size:", round(MODEL.stat().st_size / 1024**2, 2), "MB")

# ============================================================
# VERSION
# ============================================================

print("\n=== LLAMA.CPP VERSION ===")

version = subprocess.run(
    [str(LLAMA_CLI), "--version"],
    capture_output=True,
    text=True,
    timeout=30
)

print(version.stdout)
print(version.stderr)

assert version.returncode == 0



# ============================================================
# MODEL METADATA
# ============================================================

print("\n=== MODEL METADATA ===")

metadata = subprocess.run(
    [
        str(LLAMA_CLI),
        "-m", str(MODEL),
        "--verbose",
        "-n", "0",
        "-p", "test"
    ],
    capture_output=True,
    text=True,
    timeout=60
)

metadata_output = metadata.stdout + metadata.stderr

print(metadata_output[-4000:])

assert metadata.returncode == 0, "GGUF model loading failed"
assert "Qwen" in metadata_output or "qwen" in metadata_output.lower()




# ============================================================
# LOCAL INFERENCE
# ============================================================

print("\n=== LOCAL INFERENCE ===")
print("Device: CPU")
print("Quantization: Q4_K_M")
print("Max new tokens:", MAX_TOKENS)

command = [
    str(LLAMA_CLI),
    "-m", str(MODEL),
    "-p", PROMPT,
    "-n", str(MAX_TOKENS),
    "--temp", "0",
    "--no-display-prompt",
    "--no-warmup"
]

start = time.perf_counter()

result = subprocess.run(
    command,
    capture_output=True,
    text=True,
    timeout=300
)

elapsed = time.perf_counter() - start

output = result.stdout.strip()
diagnostics = result.stderr.strip()

print("\nMODEL RESPONSE:")
print(output)

print("\n=== INFERENCE METRICS ===")
print("Elapsed time:", round(elapsed, 2), "s")
print("Return code:", result.returncode)

if diagnostics:
    print("\nLLAMA.CPP DIAGNOSTICS:")
    print(diagnostics[-5000:])

assert result.returncode == 0, "llama.cpp inference failed"
assert output, "Model returned empty output"

print("\n=== SUMMARY ===")
print("Engine: llama.cpp")
print("Model: Qwen2.5-0.5B-Instruct")
print("Format: GGUF")
print("Quantization: Q4_K_M")
print("Inference: PASSED")

print("\nALL LLAMA.CPP TESTS PASSED")


