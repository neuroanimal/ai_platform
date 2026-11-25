"""Speech stacks: formant TTS, template STT, cascade, and a text-vs-speech report.

    python -m ai_platform.common.example.speech_example

Adapters whose tool, package or key is not configured are printed as skipped.
Nothing is downloaded and nothing is sent to a network API.
"""

from ai_platform.common.speech.catalog import register_all
from ai_platform.common.speech.compare import compare_pathways
from ai_platform.common.speech.speech_exception import SpeechError
from ai_platform.common.speech.speech_registry import SpeechRegistry


def main() -> None:
    """Register every stack, run the offline baseline, then probe the rest."""
    registry = SpeechRegistry()
    register_all(registry)
    print(f"Registered {len(registry.list())} speech stacks")
    for kind in ("tts", "stt", "sts"):
        print(f"  {kind}: {', '.join(registry.list_by_capability(kind))}")

    speaker = registry.get("reference-tts")
    speaker.initialize({})
    uttered = speaker.synthesize("aaa", pitch_hz=180)
    listener = registry.get("template-stt")
    listener.initialize({})
    listener.enroll("aaa", uttered.audio)
    report = compare_pathways("aaa", listener, speaker, transform=lambda text: text.upper())
    print(
        f"text reply {report.text_reply!r} | heard {report.speech_transcript!r} | "
        f"speech reply {report.speech_reply!r} | input WER {report.input_wer:.3f}"
    )
    speaker.shutdown()
    listener.shutdown()

    print("\nProbe (initialize only, no network calls):")
    for name in registry.list():
        adapter = registry.get(name)
        try:
            adapter.initialize({})
        except SpeechError as exc:
            print(f"  {name:20} skipped  {exc}")
        else:
            print(f"  {name:20} ready")
            adapter.shutdown()


if __name__ == "__main__":
    main()
