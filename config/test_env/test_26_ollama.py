
import json
import time
import urllib.request
from importlib.metadata import version

MODEL = "qwen2.5:0.5b"
API = "http://localhost:11434"

PROMPT = (
    "Wyjaśnij po polsku w 3-4 zdaniach, czym jest lokalny "
    "model językowy SLM i jakie są jego zalety."
)

MAX_TOKENS = 96


def api_request(endpoint, payload=None):
    url = f"{API}{endpoint}"

    if payload is None:
        request = urllib.request.Request(url)
    else:
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
        )

    with urllib.request.urlopen(request, timeout=600) as response:
        return json.loads(response.read().decode("utf-8"))


def ns_to_seconds(value):
    return value / 1_000_000_000


def main():
    print("=== ENVIRONMENT ===")

    server = api_request("/api/version")
    print("Ollama:", server["version"])
    print("Python package:", version("ollama") if False else "Not required")
    print("Model:", MODEL)
    print("API:", API)

    print("\n=== MODEL INFERENCE ===")

    payload = {
        "model": MODEL,
        "prompt": PROMPT,
        "stream": False,
        "options": {
            "temperature": 0.0,
            "num_predict": MAX_TOKENS,
        },
    }

    t0 = time.perf_counter()
    result = api_request("/api/generate", payload)
    client_time = time.perf_counter() - t0

    output = result["response"].strip()

    print("\nMODEL RESPONSE:\n")
    print(output)

    load_duration = result.get("load_duration", 0)
    prompt_duration = result.get("prompt_eval_duration", 0)
    eval_duration = result.get("eval_duration", 0)
    total_duration = result.get("total_duration", 0)

    prompt_tokens = result.get("prompt_eval_count", 0)
    generated_tokens = result.get("eval_count", 0)

    print("\n=== METRICS ===")
    print("Model load:", f"{ns_to_seconds(load_duration):.3f} s")
    print("Prompt evaluation:", f"{ns_to_seconds(prompt_duration):.3f} s")
    print("Generation:", f"{ns_to_seconds(eval_duration):.3f} s")
    print("Server total:", f"{ns_to_seconds(total_duration):.3f} s")
    print("Client total:", f"{client_time:.3f} s")
    print("Prompt tokens:", prompt_tokens)
    print("Generated tokens:", generated_tokens)

    speed = (
        generated_tokens / ns_to_seconds(eval_duration)
        if eval_duration else 0
    )

    print(f"Generation speed: {speed:.2f} tokens/s")

    assert output, "Empty model response"
    assert generated_tokens > 0, "No tokens generated"
    assert result.get("done"), "Generation did not finish"

    print("\nALL OLLAMA TESTS PASSED")


if __name__ == "__main__":
    main()

