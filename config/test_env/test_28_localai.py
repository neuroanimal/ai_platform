import json
import time
from pathlib import Path

import requests

BASE_URL = "http://127.0.0.1:8081"
MODELS = [
    "qwen25-05b-localai",
    "qwen25-15b-localai",
]

PROMPT = (
    "Wyjaśnij po polsku, czym różni się inflacja CPI od zmiany kursu "
    "USD/PLN. Podaj konkretny przykład liczbowy i wyjaśnij, "
    "dlaczego tych dwóch zjawisk nie należy utożsamiać."
)

results = []

print("=== TEST 28: LocalAI - Qwen 0.5B vs 1.5B ===")

for model in MODELS:
    print(f"\n--- Model: {model} ---")

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": PROMPT}],
        "temperature": 0,
        "max_tokens": 256,
    }

    start = time.perf_counter()

    try:
        response = requests.post(
            f"{BASE_URL}/v1/chat/completions",
            json=payload,
            timeout=300,
        )
        elapsed = time.perf_counter() - start
        response.raise_for_status()

        data = response.json()
        answer = data["choices"][0]["message"]["content"]

        result = {
            "model": model,
            "status": "PASS",
            "elapsed_seconds": round(elapsed, 3),
            "answer": answer,
            "usage": data.get("usage"),
            "finish_reason": data["choices"][0].get("finish_reason"),
        }

        print("Inference: PASS")
        print(f"Elapsed: {elapsed:.3f} s")
        print(f"Finish reason: {result['finish_reason']}")
        print(f"Usage: {result['usage']}")
        print("Response:")
        print(answer)

    except Exception as exc:
        result = {
            "model": model,
            "status": "FAIL",
            "error": str(exc),
        }
        print(f"FAIL: {exc}")

    results.append(result)

output = {
    "test": 28,
    "runtime": "LocalAI",
    "endpoint": BASE_URL,
    "results": results,
}

report = Path("results/test_28_localai.json")
report.parent.mkdir(parents=True, exist_ok=True)
report.write_text(
    json.dumps(output, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print(f"\nReport: {report.resolve()}")
print("\n=== SUMMARY ===")
for result in results:
    print(f"{result['model']}: {result['status']}")

