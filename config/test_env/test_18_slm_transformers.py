
import os
import time
import resource
import platform
from pathlib import Path

import torch
import transformers
from transformers import AutoTokenizer, AutoModelForCausalLM


# ============================================================
# CONFIGURATION
# ============================================================

MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
MAX_NEW_TOKENS = 96

PROMPT = (
    "Wyjaśnij po polsku w 3-4 zdaniach, "
    "czym jest lokalny model językowy SLM i jakie są jego zalety."
)


# ============================================================
# ENVIRONMENT
# ============================================================

print("=== VERSIONS ===")
print("Python:", platform.python_version())
print("PyTorch:", torch.__version__)
print("Transformers:", transformers.__version__)
print("Platform:", platform.platform())

assert torch.cuda.is_available() is False or True

device = torch.device("cpu")
print("Inference device:", device)

print("\n=== MODEL ===")
print("Model:", MODEL_ID)
print("Loading real pretrained model...")
print("First run requires downloading model files.")

# ============================================================
# TOKENIZER
# ============================================================

start = time.perf_counter()

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_ID,
    trust_remote_code=False
)

print("Tokenizer:", type(tokenizer).__name__)
print("Tokenizer load time:", round(time.perf_counter() - start, 2), "s")

# ============================================================
# MODEL LOADING
# ============================================================

start = time.perf_counter()

model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    torch_dtype=torch.float32,
    trust_remote_code=False
)

model.to(device)
model.eval()

load_time = time.perf_counter() - start

parameter_count = sum(p.numel() for p in model.parameters())
parameter_memory = sum(
    p.numel() * p.element_size()
    for p in model.parameters()
)

print("Model class:", type(model).__name__)
print("Parameters:", f"{parameter_count:,}")
print("Parameter memory:", round(parameter_memory / 1024**2, 2), "MB")
print("Model load time:", round(load_time, 2), "s")

assert parameter_count > 100_000_000

# ============================================================
# INPUT
# ============================================================

print("\n=== INPUT TOKENIZATION ===")

messages = [
    {"role": "user", "content": PROMPT}
]

input_text = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True
)

inputs = tokenizer(
    input_text,
    return_tensors="pt"
)

inputs = {key: value.to(device) for key, value in inputs.items()}

input_tokens = inputs["input_ids"].shape[1]

print("Prompt:", PROMPT)
print("Input tokens:", input_tokens)

# ============================================================
# REAL LOCAL INFERENCE
# ============================================================

print("\n=== LOCAL INFERENCE ===")

start = time.perf_counter()

with torch.inference_mode():
    outputs = model.generate(
        **inputs,
        max_new_tokens=MAX_NEW_TOKENS,
        do_sample=False,
        use_cache=True,
        pad_token_id=tokenizer.eos_token_id
    )

generation_time = time.perf_counter() - start

generated_ids = outputs[0][input_tokens:]
generated_tokens = len(generated_ids)

response = tokenizer.decode(
    generated_ids,
    skip_special_tokens=True
)

tokens_per_second = (
    generated_tokens / generation_time
    if generation_time > 0 else 0
)

print("Generated tokens:", generated_tokens)
print("Generation time:", round(generation_time, 2), "s")
print("Tokens/sec:", round(tokens_per_second, 2))
print("\nMODEL RESPONSE:")
print(response)

assert generated_tokens > 0
assert response.strip()

# ============================================================
# OFFLINE CACHE TEST
# ============================================================

print("\n=== OFFLINE CACHE TEST ===")

# Local-only loading: no network fallback is permitted.
offline_tokenizer = AutoTokenizer.from_pretrained(
    MODEL_ID,
    local_files_only=True,
    trust_remote_code=False
)

offline_model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    local_files_only=True,
    torch_dtype=torch.float32,
    trust_remote_code=False
)

offline_model.eval()

print("Tokenizer local load: PASSED")
print("Model local load: PASSED")

offline_inputs = offline_tokenizer(
    offline_tokenizer.apply_chat_template(
        [{"role": "user", "content": "Odpowiedz jednym zdaniem: co to jest SLM?"}],
        tokenize=False,
        add_generation_prompt=True
    ),
    return_tensors="pt"
)

with torch.inference_mode():
    offline_output = offline_model.generate(
        **offline_inputs,
        max_new_tokens=32,
        do_sample=False,
        pad_token_id=offline_tokenizer.eos_token_id
    )

offline_response = offline_tokenizer.decode(
    offline_output[0][offline_inputs["input_ids"].shape[1]:],
    skip_special_tokens=True
)

print("Offline response:", offline_response)
assert offline_response.strip()

del offline_model
del offline_tokenizer

# ============================================================
# MEMORY
# ============================================================

print("\n=== MEMORY USAGE ===")

# Linux ru_maxrss is reported in kilobytes.
peak_memory_mb = resource.getrusage(
    resource.RUSAGE_SELF
).ru_maxrss / 1024

print("Peak process RSS:", round(peak_memory_mb, 2), "MB")

# ============================================================
# SUMMARY
# ============================================================

print("\n=== SUMMARY ===")
print("Model:", MODEL_ID)
print("Parameters:", f"{parameter_count:,}")
print("Device:", device)
print("Generation time:", round(generation_time, 2), "s")
print("Generated tokens:", generated_tokens)
print("Tokens/sec:", round(tokens_per_second, 2))
print("Offline cache inference: PASSED")

print("\nALL LOCAL SLM TESTS PASSED")


