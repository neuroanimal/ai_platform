#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TEST 28 v2: LocalAI - Qwen 0.5B vs 1.5B on one open question, via LocalAIAdapter.

Same scenario as test_28_localai.py, transport replaced by LocalAIAdapter,
plus a warm-up request per model so the measured time excludes model load.
"""

import argparse
import json
from pathlib import Path

from ai_platform.common.llm.llm_exception import LLMError
from ai_platform.common.llm.localai_adapter import LocalAIAdapter

PROMPT = (
    "Wyjaśnij po polsku, czym różni się inflacja CPI od zmiany kursu "
    "USD/PLN. Podaj konkretny przykład liczbowy i wyjaśnij, "
    "dlaczego tych dwóch zjawisk nie należy utożsamiać."
)
OUTPUT_FILE = Path(__file__).resolve().parent / "results" / "test_28_localai_v2.json"


def run_model(base_url, model, max_tokens):
    """Warm up and query one model; errors are recorded, not raised."""
    llm = LocalAIAdapter()
    llm.initialize({"base_url": base_url, "model": model,
                    "temperature": 0, "max_tokens": max_tokens})
    try:
        warmup = llm.chat_completion([{"role": "user", "content": "OK?"}], max_tokens=4)
        result = llm.chat_completion([{"role": "user", "content": PROMPT}])
        return {
            "model": model,
            "status": "PASS",
            "load_and_warmup_seconds": round(warmup.elapsed_seconds, 3),
            "elapsed_seconds": round(result.elapsed_seconds, 3),
            "answer": result.text,
            "usage": result.usage,
            "finish_reason": result.finish_reason,
        }
    except LLMError as exc:
        return {"model": model, "status": "FAIL", "error": str(exc)}
    finally:
        llm.shutdown()


def main():
    """Run both models and write the report."""
    parser = argparse.ArgumentParser(description="TEST 28 v2: LocalAI Qwen 0.5B vs 1.5B")
    parser.add_argument("--base-url", default="http://127.0.0.1:8081")
    parser.add_argument("--models", nargs="+",
                        default=["qwen25-05b-localai", "qwen25-15b-localai"])
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--output", default=str(OUTPUT_FILE))
    args = parser.parse_args()

    print("=== TEST 28 v2: LocalAI - model comparison ===")
    results = []

    for model in args.models:
        print(f"\n--- Model: {model} ---")
        result = run_model(args.base_url, model, args.max_tokens)
        results.append(result)

        if result["status"] == "PASS":
            print("Inference: PASS")
            print(f"Warm-up (incl. load): {result['load_and_warmup_seconds']} s")
            print(f"Elapsed: {result['elapsed_seconds']} s")
            print(f"Finish reason: {result['finish_reason']}")
            print(f"Usage: {result['usage']}")
            print("Response:")
            print(result["answer"])
        else:
            print(f"FAIL: {result['error']}")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({
        "test": 28,
        "version": "2",
        "runtime": "LocalAI",
        "adapter": "ai_platform.common.llm.localai_adapter.LocalAIAdapter",
        "endpoint": args.base_url,
        "results": results,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nReport: {output.resolve()}")
    print("\n=== SUMMARY ===")
    for result in results:
        print(f"{result['model']}: {result['status']}")


if __name__ == "__main__":
    main()
