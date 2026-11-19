
import os
import time

from mistralrs import Runner, Which, ChatCompletionRequest

MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
MAX_TOKENS = 96

PROMPT = (
    "Wyjaśnij po polsku w 3-4 zdaniach, czym jest lokalny "
    "model językowy SLM i jakie są jego zalety."
)

print("=== ENVIRONMENT ===")
print("Python:", os.sys.version.split()[0])
print("Engine: mistral.rs")
print("Model:", MODEL)
print("Device: CPU")
print("Quantization: INT4")

print("\n=== MODEL LOAD ===")
t0 = time.perf_counter()

runner = Runner(
    which=Which.Plain(model_id=MODEL),
    in_situ_quant="4",
)

load_time = time.perf_counter() - t0
print(f"Load time: {load_time:.2f} s")

print("\n=== LOCAL INFERENCE ===")
request = ChatCompletionRequest(
    model="default",
    messages=[
        {"role": "user", "content": PROMPT}
    ],
    max_tokens=MAX_TOKENS,
    temperature=0.0,
)

t0 = time.perf_counter()
response = runner.send_chat_completion_request(request)
elapsed = time.perf_counter() - t0

content = response.choices[0].message.content

if isinstance(content, list):
    output = "\n".join(
        str(item) for item in content
    ).strip()
else:
    output = str(content or "").strip()

print("\nMODEL RESPONSE:\n")
print(output)

print("\n=== METRICS ===")
print(f"Inference time: {elapsed:.2f} s")
print("Max new tokens:", MAX_TOKENS)

assert output, "Empty model response"
assert response.choices, "No completion choices returned"

print("\nALL MISTRAL.RS TESTS PASSED")

