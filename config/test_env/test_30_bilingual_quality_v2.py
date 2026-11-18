#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TEST 30 v2: bilingual (PL/EN) quality benchmark against an
OpenAI-compatible endpoint (LocalAI by default).

Zmiany względem test_30_bilingual_quality.py:
- poprawiona pisownia podmiotu w promptach EN ("Mruczek", nie "Mrruczek");
  analiza v4.2 akceptuje obie formy, więc raporty v1 i v2 są porównywalne;
- rozgrzewka (warm-up) każdego modelu przed pomiarem - pierwsze zapytanie
  obejmuje ładowanie modelu i nie trafia do wyników, jego czas jest
  zapisany osobno jako load_and_warmup_seconds;
- powtórzenia (--repeats, domyślnie 3) z polem run_index;
- podsumowanie z medianą czasu odpowiedzi;
- parametry z linii poleceń (--base-url, --models, --max-tokens, ...).

"status": "PASS" oznacza wyłącznie poprawne wykonanie zapytania HTTP
i niepustą odpowiedź - NIE poprawność merytoryczną. Ocenę wstępną
robi test_30a_analysis_v4_2.py.
"""

import argparse
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT = BASE_DIR / "results" / "test_30_bilingual_quality_v2.json"

DEFAULT_BASE_URL = "http://127.0.0.1:8081"

DEFAULT_MODELS = [
    "qwen25-05b-localai",
    "qwen25-15b-localai",
    "bielik-15b-localai",
]

LANGUAGES = ["pl", "en"]

WARMUP_PROMPT = "Odpowiedz jednym słowem: OK."

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
                # v1 miało tu "Mrruczek" (literówka).
                "prompt": (
                    "All cats are mammals. Mruczek is a cat. "
                    "Is Mruczek a mammal? Explain your answer."
                ),
                "expected": "Yes, Mruczek is a mammal.",
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


def chat(base_url, model, prompt, max_tokens, temperature, timeout):  # pylint: disable=too-many-positional-arguments
    """Send one chat completion; return (response_json, elapsed_seconds)."""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    start = time.perf_counter()
    response = requests.post(
        f"{base_url}/v1/chat/completions",
        json=payload,
        timeout=timeout,
    )
    elapsed = time.perf_counter() - start
    response.raise_for_status()
    return response.json(), elapsed


def warm_up(args, model):
    """Load the model with a throw-away request; return seconds or error."""
    try:
        _, elapsed = chat(
            args.base_url, model, WARMUP_PROMPT, 8, 0, args.timeout
        )
        return {"status": "PASS", "load_and_warmup_seconds": round(elapsed, 3)}
    except (requests.RequestException, ValueError) as exc:
        return {"status": "FAIL", "error": str(exc)}


def run_test(args, model, test, language, run_index):
    """Run one prompt once and return a result record."""
    language_data = test["languages"][language]

    data, elapsed = chat(
        args.base_url,
        model,
        language_data["prompt"],
        args.max_tokens,
        args.temperature,
        args.timeout,
    )

    choice = data["choices"][0]
    answer = choice["message"]["content"]

    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("Model returned an empty answer")

    return {
        "model": model,
        "test_id": test["id"],
        "category": test["category"],
        "language": language,
        "run_index": run_index,
        "prompt": language_data["prompt"],
        "expected": language_data["expected"],
        "answer": answer,
        "elapsed_seconds": round(elapsed, 3),
        "usage": data.get("usage"),
        "finish_reason": choice.get("finish_reason"),
        "status": "PASS",
    }


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--max-tokens", type=int, default=384)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    return parser.parse_args()


def summarize(results, models, repeats):
    """Return per model/language counts and latency statistics."""
    summary = {}

    for model in models:
        for language in LANGUAGES:
            rows = [
                r for r in results
                if r["model"] == model and r["language"] == language
            ]
            times = [r["elapsed_seconds"] for r in rows if r["status"] == "PASS"]
            summary[f"{model} [{language.upper()}]"] = {
                "technical_pass": len(times),
                "expected_executions": len(PROMPTS) * repeats,
                "median_seconds": round(statistics.median(times), 3) if times else None,
                "max_seconds": max(times) if times else None,
                "truncated": sum(r.get("finish_reason") == "length" for r in rows),
            }

    return summary


def main():
    """Run the benchmark and write the JSON report."""
    args = parse_args()
    results = []
    warmups = {}

    total = len(args.models) * len(PROMPTS) * len(LANGUAGES) * args.repeats

    print("=== TEST 30 v2: BILINGUAL QUALITY BENCHMARK ===")
    print(f"Endpoint: {args.base_url}")
    print(f"Models: {len(args.models)}  Tasks: {len(PROMPTS)}  "
          f"Languages: {', '.join(LANGUAGES)}  Repeats: {args.repeats}")
    print(f"Total measured requests: {total} (+{len(args.models)} warm-up)")

    for model in args.models:
        print(f"\n{'=' * 60}\nMODEL: {model}\n{'=' * 60}")

        warmups[model] = warm_up(args, model)
        print(f"WARM-UP: {warmups[model]}")

        if warmups[model]["status"] == "FAIL":
            print("Skipping model - warm-up failed.")
            continue

        for run_index in range(args.repeats):
            for test in PROMPTS:
                for language in LANGUAGES:
                    label = f"{test['id']} [{language.upper()}] run {run_index}"
                    try:
                        result = run_test(args, model, test, language, run_index)
                        results.append(result)
                        print(f"{label}: {result['elapsed_seconds']} s, "
                              f"finish={result['finish_reason']}")
                    except (requests.RequestException, ValueError,
                            KeyError, IndexError) as exc:
                        results.append({
                            "model": model,
                            "test_id": test["id"],
                            "category": test["category"],
                            "language": language,
                            "run_index": run_index,
                            "prompt": test["languages"][language]["prompt"],
                            "expected": test["languages"][language]["expected"],
                            "status": "FAIL",
                            "error": str(exc),
                        })
                        print(f"{label}: FAIL {exc}")

    report = {
        "test": "30",
        "version": "2",
        "name": "bilingual_quality_benchmark",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "runtime": "OpenAI-compatible (LocalAI)",
        "endpoint": args.base_url,
        "languages": LANGUAGES,
        "models": args.models,
        "repeats": args.repeats,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "warmup": warmups,
        "status_semantics": "PASS = HTTP success and non-empty answer only",
        "summary": summarize(results, args.models, args.repeats),
        "results": results,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n=== SUMMARY (technical executions, not correctness) ===")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"\nReport: {output.resolve()}")


if __name__ == "__main__":
    main()
