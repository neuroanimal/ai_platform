# Environment checks

Standalone scripts that verify the local AI/ML environment: libraries
import, a minimal model runs, a local LLM server answers. Integrated from
`config/test_env/` (2026-11-16..18); only the final version of each
script was taken - the intermediate `a/b/c/d` copies were byte-identical
to it or superseded.

They execute on import (no `main()` guard), so they are named
`env_check_*.py`, not `test_*.py`: pytest must not collect them. Run them
with `run_env_checks.py` (one process per check, timeout, logs in
`<tmp>/ai_platform_env_checks/`).

| check | area | source in config/test_env |
|---|---|---|
| 01 | NumPy, SciPy | test_01_numerical.py |
| 02 | PyTorch, scikit-learn, transformers pipeline | test_02_ml_dl.py |
| 03 | ONNX model build and ONNX Runtime | test_03_onnx.py |
| 04 | spaCy / NLP stack | test_04_nlp.py (= 04d) |
| 05 | embeddings, vector search | test_05_embeddings_vector.py |
| 06 | semantic web (RDF, OWL, OBO) | test_06_semantic_web.py |
| 07 | backend libraries | test_07_backend.py |
| 08 | MLOps stack | test_08_mlops.py (= 08d) |
| 09-14 | vision, OCR, detection, segmentation, audio, multimodal | test_09 (= 09b), 10, 11 (= 11b), 12, 13, 14 (= 14b) |
| 15 | model serving formats (TorchScript, state dict) | test_15_serving.py |
| 16 | hardware acceleration, ONNX export | test_16_acceleration.py - **changed**: exports to a temp file instead of the current directory |
| 17 | optimization (quantization, pruning) | test_17_optimization.py |
| 18 | small language models with transformers | test_18_slm_transformers.py |
| 19-24 | llama.cpp, ONNX GenAI, OpenVINO GenAI, mistral.rs, CTranslate2, GPT4All | test_19 (= 19c), 20 (= 20b), 21-24 |
| 25 | vLLM | test_25_vllm.py (= 25d) |
| 26 | Ollama through `OllamaAdapter` | test_26_ollama_v2.py |
| 27 | LocalAI Docker + WSL2 through `LocalAIAdapter` | test_27_localai_v2.py - **changed**: report to the temp dir |
| 28 | LocalAI, two models | test_28_localai_v2.py - **changed**: report to the temp dir |

Not here, because they became platform code:

- quality benchmarks (test_28_quality, test_29, test_30*) -> `ai_platform.backend.ui_layer.cli.llm_benchmark_cli` (`run`), task set in `backend/domain_layer/business_logic/llm_benchmark/`, live test in `test/non-functional/performance_test/test_llm_benchmark_live.py`;
- answer screening (test_30a v1..v4.2) -> `ai_platform.common.evaluation.answer_screening`, CLI `screen`, unit tests in `test/basic-structural/static/basic_unit_test/common/test_answer_screening.py`.
