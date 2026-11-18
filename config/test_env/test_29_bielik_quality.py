import json
import time
from pathlib import Path

import requests

BASE_URL = "http://127.0.0.1:8081"

MODELS = [
    "qwen25-05b-localai",
    "qwen25-15b-localai",
    "bielik-15b-localai",
]

PROMPTS = [
    {
        "id": "arithmetic_multiplication",
        "category": "mathematics",
        "prompt": "Ile wynosi 17 razy 23? Podaj wynik i obliczenie.",
        "expected": "391",
    },
    {
        "id": "percentage_change",
        "category": "mathematics",
        "prompt": "Cena produktu wzrosła ze 100 zł do 112 zł. O ile procent wzrosła?",
        "expected": "12%",
    },
    {
        "id": "logical_syllogism",
        "category": "logic",
        "prompt": (
            "Wszystkie koty są ssakami. Mruczek jest kotem. "
            "Czy Mruczek jest ssakiem? Uzasadnij."
        ),
        "expected": "Tak, Mruczek jest ssakiem.",
    },
    {
        "id": "currency_vs_inflation",
        "category": "economics",
        "prompt": (
            "Czy wzrost kursu USD/PLN oznacza automatycznie wzrost "
            "inflacji CPI w Polsce? Wyjaśnij krótko."
        ),
        "expected": (
            "Nie. Kurs walutowy może wpływać na ceny importu i CPI, "
            "ale wzrost kursu nie oznacza automatycznie wzrostu CPI."
        ),
    },
]


def run_test(model, test):
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": test["prompt"]}
        ],
        "temperature": 0,
        "max_tokens": 384,
    }

    start = time.perf_counter()

    response = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        json=payload,
        timeout=300,
    )

    elapsed = time.perf_counter() - start
    response.raise_for_status()

    data = response.json()
    choice = data["choices"][0]

    answer = choice["message"]["content"]

    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("Model returned an empty answer")

    return {
        "model": model,
        "test_id": test["id"],
        "category": test["category"],
        "prompt": test["prompt"],
        "expected": test["expected"],
        "answer": answer,
        "elapsed_seconds": round(elapsed, 3),
        "usage": data.get("usage"),
        "finish_reason": choice.get("finish_reason"),
        "status": "PASS",
    }


def main():
    results = []

    print("=== TEST 29: BIELIK AND QWEN QUALITY BENCHMARK ===")

    for model in MODELS:
        print(f"\n{'=' * 60}")
        print(f"MODEL: {model}")
        print("=" * 60)

        for test in PROMPTS:
            print(f"\nTEST: {test['id']}")

            try:
                result = run_test(model, test)
                results.append(result)

                print(f"TIME: {result['elapsed_seconds']} s")
                print(f"USAGE: {result['usage']}")
                print(f"FINISH: {result['finish_reason']}")
                print(f"ANSWER: {result['answer']}")

            except Exception as exc:
                results.append({
                    "model": model,
                    "test_id": test["id"],
                    "category": test["category"],
                    "status": "FAIL",
                    "error": str(exc),
                })
                print(f"FAIL: {exc}")

    report = {
        "test": "29",
        "runtime": "LocalAI",
        "endpoint": BASE_URL,
        "temperature": 0,
        "max_tokens": 384,
        "results": results,
    }

    output = Path("results/test_29_bielik_quality.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n=== SUMMARY ===")

    for model in MODELS:
        model_results = [
            r for r in results if r["model"] == model
        ]
        passed = sum(r["status"] == "PASS" for r in model_results)
        print(f"{model}: {passed}/{len(PROMPTS)} technical executions")

    print(f"\nReport: {output.resolve()}")


if __name__ == "__main__":
    main()

