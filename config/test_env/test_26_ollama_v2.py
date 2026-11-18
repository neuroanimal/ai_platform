#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TEST 26 v2: Ollama through ai_platform's OllamaAdapter.

Supersedes test_26_ollama.py and test_26x_ollama.py (both called the
Ollama REST API by hand). Checks the same things:
- server version,
- model installed (/api/tags),
- one local inference with server-side metrics (native /api/chat),
and additionally one call through the OpenAI-compatible /v1 path, so that
both transports of the adapter are exercised.
"""

import argparse

from ai_platform.common.llm.llm_exception import LLMError
from ai_platform.common.llm.ollama_adapter import OllamaAdapter

PROMPT = (
    "Wyjaśnij po polsku w 3-4 zdaniach, czym jest lokalny "
    "model językowy SLM i jakie są jego zalety."
)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="TEST 26 v2: Ollama via OllamaAdapter")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--model", default="qwen2.5:0.5b")
    parser.add_argument("--max-tokens", type=int, default=96)
    return parser.parse_args()


def main():
    """Run the checks; raise on failure."""
    args = parse_args()
    llm = OllamaAdapter()
    llm.initialize({"base_url": args.base_url, "model": args.model,
                    "temperature": 0.0, "max_tokens": args.max_tokens})

    print("=== ENVIRONMENT ===")
    print("Adapter: ai_platform.common.llm.ollama_adapter.OllamaAdapter")
    print("Endpoint:", args.base_url)
    print("Model:", args.model)

    print("\n=== OLLAMA VERSION ===")
    try:
        print("Ollama:", llm.version())
    except LLMError as exc:
        raise RuntimeError(
            "Ollama API unavailable. Check: ollama serve / snap service."
        ) from exc

    print("\n=== MODEL VERIFICATION ===")
    found = next((m for m in llm.list_local_models() if m.get("name") == args.model), None)
    assert found is not None, f"Model not found: {args.model}"
    print("Model:", found.get("name"))
    print("Size:", found.get("size"), "bytes")

    print("\n=== LOCAL INFERENCE (native /api/chat) ===")
    result = llm.native_chat_completion(
        [{"role": "user", "content": PROMPT}], keep_alive="5m", num_ctx=1024
    )
    print("\nMODEL RESPONSE:\n")
    print(result.text.strip())

    metrics = result.metrics
    print("\n=== METRICS ===")
    print("Prompt tokens:", result.usage["prompt_tokens"])
    print("Generated tokens:", result.usage["completion_tokens"])
    print(f"Model load time: {metrics['load_seconds']:.3f} s")
    print(f"Prompt evaluation: {metrics['prompt_eval_seconds']:.3f} s")
    print(f"Generation time: {metrics['eval_seconds']:.3f} s")
    print(f"Total server time: {metrics['total_seconds']:.3f} s")
    print(f"Client elapsed time: {result.elapsed_seconds:.3f} s")
    print(f"Generation speed: {metrics['tokens_per_second']:.2f} tokens/s")
    print("Done reason:", result.finish_reason)

    assert result.text.strip(), "Empty model response"
    assert result.usage["completion_tokens"] > 0, "No tokens generated"
    assert metrics["total_seconds"] > 0, "Missing server timing"

    print("\n=== OPENAI-COMPATIBLE PATH (/v1/chat/completions) ===")
    compat = llm.chat_completion([{"role": "user", "content": PROMPT}])
    print(f"Elapsed: {compat.elapsed_seconds:.3f} s, finish: {compat.finish_reason}")
    assert compat.text.strip(), "Empty response on /v1 path"

    llm.shutdown()
    print("\nALL OLLAMA TESTS PASSED")


if __name__ == "__main__":
    main()
