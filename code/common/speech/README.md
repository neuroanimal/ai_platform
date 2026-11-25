# Speech (TTS, STT, STS)

Several stacks behind one registry, so a pipeline can be pointed at a
different engine without rewriting the call. The offline baseline needs no
extra packages: formant TTS (`reference-tts`), closed-set STT
(`template-stt`) and a cascade (`cascade`).

```python
from ai_platform.common.speech.catalog import register_all
from ai_platform.common.speech.speech_registry import SpeechRegistry

registry = SpeechRegistry()
register_all(registry)
speaker = registry.get("reference-tts")
speaker.initialize({})
audio = speaker.synthesize("cześć")
```

An LLM from `common.llm` rewrites the transcript if you pass it as the
cascade transform. The speech package does not import the LLM package:

```python
from ai_platform.backend.service_layer.micro.speech.speech_service import (
    SpeechService, llm_reply_transform,
)

service = SpeechService().register_defaults()
cascade = service.build_cascade(
    "template-stt", "reference-tts", transform=llm_reply_transform(llm),
)
```

## Stacks

| Name | Kind | Family | Needs |
| --- | --- | --- | --- |
| reference-tts | tts | traditional formant | stdlib |
| espeak | tts | eSpeak NG CLI | `espeak-ng` |
| festival | tts | Festival `text2wave` | `text2wave` |
| piper | tts | local ONNX | `piper` + `model` |
| pyttsx3 | tts | OS voice bridge | `pip install pyttsx3` |
| kokoro | tts | local neural | `kokoro-onnx` + weights, or `engine` |
| coqui | tts | local neural | `TTS` + `model_name`, or `engine` |
| silero-tts | tts | local neural | `engine`, or `allow_download` |
| edge-tts | tts | cloud neural, MP3 | `edge-tts` + `allow_network`, or `synthesize` |
| gtts | tts | Google Translate, MP3 | `gTTS` + `allow_network`, or `factory` |
| openai-tts | tts | OpenAI-compatible HTTP | `api_key`; `base_url` for LocalAI |
| template-stt | stt | closed-set features | stdlib, `enroll()` |
| whisper | stt | openai-whisper | `model` or `engine` |
| faster-whisper | stt | CTranslate2 | `model` or `engine` |
| whisper-cpp | stt | whisper.cpp CLI | binary + ggml `model` |
| vosk | stt | Kaldi | `model_path` or `recognizer` |
| wav2vec2 | stt | transformers pipeline | `model` or `engine` |
| nemo | stt | NVIDIA NeMo | `model_name` or `engine` |
| speechrecognition | stt | Sphinx by default | package; network backends need `allow_network` |
| openai-stt | stt | OpenAI-compatible HTTP | `api_key`; `base_url` for LocalAI |
| cascade | sts | STT + transform + TTS | live adapters |
| local-duplex | sts | energy VAD + cascade | live adapters |
| openai-realtime | sts | Realtime events | `transport.exchange` |
| gemini-live | sts | Live messages | `transport.exchange` |
| moshi | sts | frame in, frame out | `engine(frame) -> frame` |

CLI: `python -m ai_platform.backend.ui_layer.cli.speech_cli list`

Example: `python -m ai_platform.common.example.speech_example`

Text pathway versus speech pathway (word error rate of the original sentence
against what STT heard, and of the two replies):

```bash
python -m ai_platform.backend.ui_layer.cli.speech_cli compare \
    --text "aaa" --bootstrap-template --uppercase
```
