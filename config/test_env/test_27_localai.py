
#!/usr/bin/env python3
"""Test 27: LocalAI — Docker and native WSL2 instances."""

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

MODEL = "qwen25-05b-localai"
PROMPT = (
    "Wyjaśnij krótko, czym różni się inflacja CPI od kursu walutowego. "
    "Odpowiedz po polsku."
)
INSTANCES = {
    "Docker": "http://127.0.0.1:8080",
    "WSL2": "http://127.0.0.1:8081",
}
OUTPUT_DIR = Path(__file__).resolve().parent / "results"
OUTPUT_FILE = OUTPUT_DIR / "test_27_localai.json"


def request_json(url, payload=None, timeout=120):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def test_instance(name, base_url):
    result = {
        "instance": name,
        "url": base_url,
        "models": None,
        "model_available": False,
        "inference_pass": False,
        "response": None,
        "usage": None,
        "error": None,
        "elapsed_seconds": None,
    }

    try:
        models = request_json(f"{base_url}/v1/models")
        result["models"] = models
        available = [
            item.get("id") for item in models.get("data", [])
        ]
        result["model_available"] = MODEL in available

        if not result["model_available"]:
            raise RuntimeError(f"Model {MODEL!r} not found: {available}")

        payload = {
            "model": MODEL,
            "messages": [{"role": "user", "content": PROMPT}],
            "temperature": 0,
            "max_tokens": 128,
        }

        start = time.perf_counter()
        completion = request_json(
            f"{base_url}/v1/chat/completions",
            payload,
        )
        result["elapsed_seconds"] = round(
            time.perf_counter() - start, 3
        )

        choices = completion.get("choices", [])
        if not choices:
            raise RuntimeError("API returned no completion choices")

        result["response"] = choices[0].get("message", {}).get("content")
        result["usage"] = completion.get("usage")
        result["finish_reason"] = choices[0].get("finish_reason")
        result["inference_pass"] = bool(result["response"])

    except (urllib.error.URLError, TimeoutError, RuntimeError,
            json.JSONDecodeError, KeyError) as exc:
        result["error"] = str(exc)

    return result


def main():
    print("=== TEST 27: LocalAI ===", flush=True)
    print(f"Model: {MODEL}", flush=True)

    results = []
    for name, url in INSTANCES.items():
        print(f"\n--- {name}: {url} ---", flush=True)
        result = test_instance(name, url)
        results.append(result)

        print(f"Model available: {result['model_available']}")
        print(f"Inference: {'PASS' if result['inference_pass'] else 'FAIL'}")
        print(f"Elapsed: {result['elapsed_seconds']} s")
        if result["response"]:
            print("Response:")
            print(result["response"])
        if result["error"]:
            print(f"ERROR: {result['error']}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "test": 27,
        "name": "LocalAI",
        "model": MODEL,
        "prompt": PROMPT,
        "results": results,
    }
    OUTPUT_FILE.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n=== SUMMARY ===")
    for result in results:
        status = "PASS" if result["inference_pass"] else "FAIL"
        print(f"{result['instance']}: {status}")

    print(f"\nReport: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

