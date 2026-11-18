import json
import time
import urllib.request
import urllib.error

from importlib.metadata import version

BASE_URL = "http://localhost:11434"
MODEL = "qwen2.5:0.5b"
MAX_TOKENS = 96

PROMPT = (
    "Wyjaśnij po polsku w 3-4 zdaniach, czym jest lokalny "
    "model językowy SLM i jakie są jego zalety."
)


def request_json(endpoint, payload=None):
    url = BASE_URL + endpoint

    if payload is None:
        req = urllib.request.Request(url)
    else:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

    with urllib.request.urlopen(req, timeout=600) as response:
        return json.loads(response.read().decode("utf-8"))


def main():
    print("=== ENVIRONMENT ===")
    print("Python runtime: Ollama API")
    print("Ollama package: external runtime")
    print("Model:", MODEL)

    print("\n=== OLLAMA VERSION ===")
    try:
        info = request_json("/api/version")
        print("Ollama:", info.get("version", "unknown"))
    except Exception as exc:
        raise RuntimeError(
            "Ollama API unavailable. Check: ollama serve / snap service."
        ) from exc

    print("\n=== MODEL VERIFICATION ===")
    tags = request_json("/api/tags")
    models = tags.get("models", [])

    found = next(
        (m for m in models if m.get("name") == MODEL),
        None,
    )

    assert found is not None, f"Model not found: {MODEL}"

    print("Model:", found.get("name"))
    print("Size:", found.get("size"), "bytes")

    print("\n=== LOCAL INFERENCE ===")

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": PROMPT}
        ],
        "stream": False,
        "keep_alive": "5m",
        "options": {
            "temperature": 0.0,
            "num_predict": MAX_TOKENS,
            "num_ctx": 1024,
        },
    }

    t0 = time.perf_counter()
    result = request_json("/api/chat", payload)
    client_elapsed = time.perf_counter() - t0

    output = result.get("message", {}).get("content", "").strip()

    total_duration = result.get("total_duration", 0) / 1e9
    load_duration = result.get("load_duration", 0) / 1e9
    prompt_duration = result.get("prompt_eval_duration", 0) / 1e9
    eval_duration = result.get("eval_duration", 0) / 1e9

    prompt_tokens = result.get("prompt_eval_count", 0)
    generated_tokens = result.get("eval_count", 0)

    print("\nMODEL RESPONSE:\n")
    print(output)

    print("\n=== METRICS ===")
    print("Prompt tokens:", prompt_tokens)
    print("Generated tokens:", generated_tokens)
    print(f"Model load time: {load_duration:.3f} s")
    print(f"Prompt evaluation: {prompt_duration:.3f} s")
    print(f"Generation time: {eval_duration:.3f} s")
    print(f"Total server time: {total_duration:.3f} s")
    print(f"Client elapsed time: {client_elapsed:.3f} s")

    speed = (
        generated_tokens / eval_duration
        if eval_duration > 0 else 0
    )

    print(f"Generation speed: {speed:.2f} tokens/s")
    print("Done reason:", result.get("done_reason"))

    assert output, "Empty model response"
    assert generated_tokens > 0, "No tokens generated"
    assert total_duration > 0, "Missing server timing"

    print("\nALL OLLAMA TESTS PASSED")


if __name__ == "__main__":
    main()
