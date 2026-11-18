
import os
import time
from importlib.metadata import version

from vllm import LLM, SamplingParams

MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
MAX_TOKENS = 96

PROMPT = (
    "Wyjaśnij po polsku w 3-4 zdaniach, czym jest lokalny "
    "model językowy SLM i jakie są jego zalety."
)

print("=== ENVIRONMENT ===")
print("Python:", os.sys.version.split()[0])
print("vLLM:", version("vllm"))
print("Model:", MODEL)
print("Device: CPU")
print("Dtype: float32")

print("\n=== MODEL LOAD ===")
t0 = time.perf_counter()

llm = LLM(
    model=MODEL,
    device="cpu",
    dtype="float32",
    max_model_len=1024,
    max_num_seqs=1,
    enforce_eager=True,
    disable_log_stats=True,
)

load_time = time.perf_counter() - t0
print(f"Load time: {load_time:.2f} s")

print("\n=== LOCAL INFERENCE ===")

tokenizer = llm.get_tokenizer()

prompt = tokenizer.apply_chat_template(
    [{"role": "user", "content": PROMPT}],
    tokenize=False,
    add_generation_prompt=True,
)

sampling = SamplingParams(
    temperature=0.0,
    max_tokens=MAX_TOKENS,
)

t0 = time.perf_counter()
results = llm.generate([prompt], sampling)
elapsed = time.perf_counter() - t0

result = results[0]
output = result.outputs[0].text.strip()
generated_tokens = len(result.outputs[0].token_ids)

print("\nMODEL RESPONSE:\n")
print(output)

print("\n=== METRICS ===")
print("Generated tokens:", generated_tokens)
print(f"Inference time: {elapsed:.2f} s")
print(
    f"Generation speed: "
    f"{generated_tokens / elapsed if elapsed else 0:.2f} tokens/s"
)

assert output, "Empty model response"
assert generated_tokens > 0, "No tokens generated"

print("\nALL VLLM TESTS PASSED")

