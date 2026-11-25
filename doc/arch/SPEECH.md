# Speech domain

TTS, STT and STS are one domain with many stacks. The domain follows the
same rules as ML and LLM adapters.

## Where code lives

| Path | Layer | Role |
| --- | --- | --- |
| `code/common/speech/` | common | Contracts, WAV/PCM helpers, registries, adapters. No backend imports. |
| `code/backend/service_layer/micro/speech/` | service | `SpeechService`, including `llm_reply_transform` for any `chat()` adapter. |
| `code/backend/ui_layer/cli/speech_cli.py` | ui | `list`, `tts`, `stt`, `sts`, `compare`. |
| `code/common/example/speech_example.py` | example | Offline baseline plus a probe of every other stack. |
| `test/basic-structural/static/basic_unit_test/common/test_speech_adapters.py` | test | Adapters, with injected runners and engines. |
| `test/functional/integration_test/test_speech_sts.py` | test | Cascade, duplex, text-versus-speech, CLI. |

Registration is explicit (`catalog.register_all` or `SpeechPlugin.register`).
Importing a module does not register it and does not download weights.

## Swapping a stack

Keep the call, change the name:

```python
service = SpeechService().register_defaults()
service.synthesize("reference-tts", "cześć", output_path="a.wav")
service.synthesize("piper", "cześć", {"model": "pl.onnx", "executable": "piper"})
```

Speech versus text is `compare_pathways` / `speech_cli compare`: the same
rewrite runs on the original sentence and on whatever STT heard after TTS.

## What is intentionally not faked

- A missing binary, package, model or API key raises `SpeechConfigError`.
- Network backends refuse to run unless `allow_network=True` (or a transport
  / opener / factory was injected).
- MP3 engines return bytes in `SynthesisResult.raw` and leave PCM empty.
- Template STT returns a label only from enrolled audio. No enrollment, no guess.
