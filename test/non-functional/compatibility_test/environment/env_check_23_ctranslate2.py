
import os
import time
from pathlib import Path

import ctranslate2
from transformers import AutoTokenizer

MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
MODEL_DIR = Path.home() / "models/ctranslate2/qwen25-05b-int8"

PROMPT = (
    "Wyjaśnij po polsku w 3-4 zdaniach, czym jest lokalny "
    "model językowy SLM i jakie są jego zalety."
)
MAX_NEW_TOKENS = 96

print("=== ENVIRONMENT ===")
print("Python:", os.sys.version.split()[0])
print("CTranslate2:", ctranslate2.__version__)
print("Model:", MODEL_ID)
print("Device: CPU")
print("Quantization: INT8")

assert MODEL_DIR.exists(), f"Model not found: {MODEL_DIR}"

model_size = sum(
    p.stat().st_size for p in MODEL_DIR.rglob("*") if p.is_file()
)
print(f"Model size: {model_size / 1024**2:.2f} MB")

print("\n=== TOKENIZER ===")
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)

messages = [{"role": "user", "content": PROMPT}]
chat_prompt = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True,
)

tokens = tokenizer.convert_ids_to_tokens(
    tokenizer.encode(chat_prompt, add_special_tokens=False)
)

print("Input tokens:", len(tokens))

print("\n=== MODEL LOAD ===")
t0 = time.perf_counter()
generator = ctranslate2.Generator(
    str(MODEL_DIR),
    device="cpu",
    inter_threads=1,
    intra_threads=max(1, os.cpu_count() or 1),
)
load_time = time.perf_counter() - t0
print(f"Load time: {load_time:.2f} s")

print("\n=== LOCAL INFERENCE ===")
t0 = time.perf_counter()

results = generator.generate_batch(
    [tokens],
    max_length=len(tokens) + MAX_NEW_TOKENS,
    sampling_topk=1,
    include_prompt_in_result=False,
)

elapsed = time.perf_counter() - t0
generated_ids = results[0].sequences_ids[0]
output = tokenizer.decode(
    generated_ids,
    skip_special_tokens=True,
).strip()

print("\nMODEL RESPONSE:\n")
print(output)

print("\n=== METRICS ===")
print("Generated tokens:", len(generated_ids))
print(f"Inference time: {elapsed:.2f} s")
print(
    f"Generation speed: "
    f"{len(generated_ids) / elapsed if elapsed else 0:.2f} tokens/s"
)

assert output, "Empty model response"
assert generated_ids, "No tokens generated"

print("\nALL CTRANSLATE2 TESTS PASSED")

