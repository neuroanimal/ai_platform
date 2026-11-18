
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
        "languages": {
            "pl": {
                "prompt": (
                    "Ile wynosi 17 razy 23? "
                    "Podaj wynik i obliczenie."
                ),
                "expected": "391",
            },
            "en": {
                "prompt": (
                    "What is 17 times 23? "
                    "Give the result and show the calculation."
                ),
                "expected": "391",
            },
        },
    },
    {
        "id": "percentage_change",
        "category": "mathematics",
        "languages": {
            "pl": {
                "prompt": (
                    "Cena produktu wzrosła ze 100 zł do 112 zł. "
                    "O ile procent wzrosła?"
                ),
                "expected": "12%",
            },
            "en": {
                "prompt": (
                    "The price of a product increased from "
                    "100 PLN to 112 PLN. By what percentage "
                    "did it increase?"
                ),
                "expected": "12%",
            },
        },
    },
    {
        "id": "logical_syllogism",
        "category": "logic",
        "languages": {
            "pl": {
                "prompt": (
                    "Wszystkie koty są ssakami. Mruczek jest kotem. "
                    "Czy Mruczek jest ssakiem? Uzasadnij."
                ),
                "expected": "Tak, Mruczek jest ssakiem.",
            },
            "en": {
                "prompt": (
                    "All cats are mammals. Mrruczek is a cat. "
                    "Is Mrruczek a mammal? Explain your answer."
                ),
                "expected": "Yes, Mrruczek is a mammal.",
            },
        },
    },
    {
        "id": "currency_vs_inflation",
        "category": "economics",
        "languages": {
            "pl": {
                "prompt": (
                    "Czy wzrost kursu USD/PLN oznacza automatycznie "
                    "wzrost inflacji CPI w Polsce? Wyjaśnij krótko."
                ),
                "expected": (
                    "Nie. Kurs walutowy może wpływać na ceny importu "
                    "i CPI, ale wzrost kursu nie oznacza "
                    "automatycznie wzrostu CPI."
                ),
            },
            "en": {
                "prompt": (
                    "Does an increase in the USD/PLN exchange rate "
                    "automatically mean an increase in CPI inflation "
                    "in Poland? Explain briefly."
                ),
                "expected": (
                    "No. The exchange rate can affect import prices "
                    "and CPI, but an increase in the exchange rate "
                    "does not automatically mean an increase in CPI."
                ),
            },
        },
    },
]


def run_test(model, test, language):
    language_data = test["languages"][language]

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": language_data["prompt"],
            }
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
        "language": language,
        "prompt": language_data["prompt"],
        "expected": language_data["expected"],
        "answer": answer,
        "elapsed_seconds": round(elapsed, 3),
        "usage": data.get("usage"),
        "finish_reason": choice.get("finish_reason"),
        "status": "PASS",
    }


def main():
    results = []

    languages = ["pl", "en"]

    print("=== TEST 30: BILINGUAL QUALITY BENCHMARK ===")
    print(f"Models: {len(MODELS)}")
    print(f"Tasks: {len(PROMPTS)}")
    print(f"Languages: {', '.join(languages)}")
    print(
        f"Total requests: "
        f"{len(MODELS) * len(PROMPTS) * len(languages)}"
    )

    for model in MODELS:
        print(f"\n{'=' * 60}")
        print(f"MODEL: {model}")
        print("=" * 60)

        for test in PROMPTS:
            for language in languages:
                print(
                    f"\nTEST: {test['id']} "
                    f"[{language.upper()}]"
                )

                try:
                    result = run_test(
                        model,
                        test,
                        language,
                    )
                    results.append(result)

                    print(
                        f"TIME: "
                        f"{result['elapsed_seconds']} s"
                    )
                    print(f"USAGE: {result['usage']}")
                    print(f"FINISH: {result['finish_reason']}")
                    print(f"ANSWER: {result['answer']}")

                except Exception as exc:
                    results.append({
                        "model": model,
                        "test_id": test["id"],
                        "category": test["category"],
                        "language": language,
                        "status": "FAIL",
                        "error": str(exc),
                    })

                    print(f"FAIL: {exc}")

    report = {
        "test": "30",
        "name": "bilingual_quality_benchmark",
        "runtime": "LocalAI",
        "endpoint": BASE_URL,
        "languages": languages,
        "models": MODELS,
        "temperature": 0,
        "max_tokens": 384,
        "results": results,
    }

    output = Path(
        "results/test_30_bilingual_quality.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)

    output.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\n=== SUMMARY ===")

    for model in MODELS:
        for language in languages:
            model_results = [
                r for r in results
                if r["model"] == model
                and r["language"] == language
            ]

            passed = sum(
                r["status"] == "PASS"
                for r in model_results
            )

            print(
                f"{model} [{language.upper()}]: "
                f"{passed}/{len(PROMPTS)} "
                "technical executions"
            )

    print(f"\nReport: {output.resolve()}")


if __name__ == "__main__":
    main()

