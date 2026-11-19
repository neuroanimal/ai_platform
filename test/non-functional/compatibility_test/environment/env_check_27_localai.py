#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TEST 27 v2: LocalAI - Docker and native WSL2 instances, via LocalAIAdapter.

Same checks as test_27_localai.py (model listed, one inference per
instance), transport replaced by ai_platform's LocalAIAdapter.
"""

import argparse
import json
import tempfile
from pathlib import Path

from ai_platform.common.llm.llm_exception import LLMError
from ai_platform.common.llm.localai_adapter import LocalAIAdapter

PROMPT = (
    "Wyjaśnij krótko, czym różni się inflacja CPI od kursu walutowego. "
    "Odpowiedz po polsku."
)
INSTANCES = {
    "Docker": "http://127.0.0.1:8080",
    "WSL2": "http://127.0.0.1:8081",
}
# Integrated copy: reports go to the temp directory, not into the test tree.
OUTPUT_FILE = Path(tempfile.gettempdir()) / "ai_platform_env_checks" / "test_27_localai_v2.json"


def test_instance(name, base_url, model):
    """Check one LocalAI instance; never raises, errors go into the record."""
    result = {
        "instance": name,
        "url": base_url,
        "models": None,
        "model_available": False,
        "inference_pass": False,
        "response": None,
        "usage": None,
        "finish_reason": None,
        "error": None,
        "elapsed_seconds": None,
    }

    llm = LocalAIAdapter()
    llm.initialize({"base_url": base_url, "model": model,
                    "temperature": 0, "max_tokens": 128})

    try:
        models = llm.list_models()
        result["models"] = models
        result["model_available"] = model in models

        if not result["model_available"]:
            raise LLMError(f"Model {model!r} not found: {models}")

        completion = llm.chat_completion([{"role": "user", "content": PROMPT}])
        result["response"] = completion.text
        result["usage"] = completion.usage
        result["finish_reason"] = completion.finish_reason
        result["elapsed_seconds"] = round(completion.elapsed_seconds, 3)
        result["inference_pass"] = True

    except LLMError as exc:
        result["error"] = str(exc)

    finally:
        llm.shutdown()

    return result


def main():
    """Test every instance and write the report."""
    parser = argparse.ArgumentParser(description="TEST 27 v2: LocalAI instances")
    parser.add_argument("--model", default="qwen25-05b-localai")
    parser.add_argument("--output", default=str(OUTPUT_FILE))
    args = parser.parse_args()

    print("=== TEST 27 v2: LocalAI ===", flush=True)
    print(f"Model: {args.model}", flush=True)

    results = []
    for name, url in INSTANCES.items():
        print(f"\n--- {name}: {url} ---", flush=True)
        result = test_instance(name, url, args.model)
        results.append(result)

        print(f"Model available: {result['model_available']}")
        print(f"Inference: {'PASS' if result['inference_pass'] else 'FAIL'}")
        print(f"Elapsed: {result['elapsed_seconds']} s")
        if result["response"]:
            print("Response:")
            print(result["response"])
        if result["error"]:
            print(f"ERROR: {result['error']}")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "test": 27,
        "version": "2",
        "name": "LocalAI",
        "adapter": "ai_platform.common.llm.localai_adapter.LocalAIAdapter",
        "model": args.model,
        "prompt": PROMPT,
        "results": results,
    }
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== SUMMARY ===")
    for result in results:
        print(f"{result['instance']}: {'PASS' if result['inference_pass'] else 'FAIL'}")

    print(f"\nReport: {output}")


if __name__ == "__main__":
    main()
