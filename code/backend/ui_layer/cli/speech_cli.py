"""Command line for the speech stacks.

    python -m ai_platform.backend.ui_layer.cli.speech_cli list
    python -m ai_platform.backend.ui_layer.cli.speech_cli tts \
        --engine reference-tts --text "cześć" --output out.wav
    python -m ai_platform.backend.ui_layer.cli.speech_cli stt \
        --engine template-stt --input in.wav --enroll tak=tak.wav
    python -m ai_platform.backend.ui_layer.cli.speech_cli sts \
        --stt template-stt --tts reference-tts --input in.wav --output reply.wav \
        --enroll tak=tak.wav --uppercase
    python -m ai_platform.backend.ui_layer.cli.speech_cli compare \
        --text "aaa" --stt template-stt --tts reference-tts --bootstrap-template
"""

import argparse
import json
import sys
from typing import Optional

from ai_platform.backend.service_layer.micro.speech.speech_service import SpeechService
from ai_platform.common.speech.speech_exception import SpeechError
from ai_platform.common.speech.speech_registry import SpeechRegistry


def _enroll_pairs(adapter, pairs):
    if not pairs:
        return
    if not hasattr(adapter, "enroll"):
        raise SpeechError("this STT engine has no enroll(); "
                          "it is not a closed-set template matcher")
    for item in pairs:
        if "=" not in item:
            raise SpeechError(f"enrollment must be label=path, got {item!r}")
        label, path = item.split("=", 1)
        adapter.enroll(label, path)


def _transform(uppercase: bool):
    if uppercase:
        return lambda text: text.upper()
    return None


def _build(service: SpeechService, args) -> int:
    if args.command == "list":
        for row in service.describe():
            where = "offline" if row["offline"] else "network"
            print(f"{row['kind']:4} {row['name']:20} {row['family']:28} {where:8} {row['needs']}")
        return 0

    if args.command == "tts":
        result = service.synthesize(
            args.engine, args.text,
            {"pitch_hz": args.pitch_hz, "speed": args.speed, "sample_rate": args.sample_rate},
            output_path=args.output, pitch_hz=args.pitch_hz, speed=args.speed,
            sample_rate=args.sample_rate,
        )
        print(json.dumps(result.to_dict(), ensure_ascii=False))
        return 0

    if args.command == "stt":
        listener = service.registry.get(args.engine)
        listener.initialize({})
        try:
            _enroll_pairs(listener, args.enroll)
            transcript = listener.transcribe(args.input)
        finally:
            listener.shutdown()
        print(json.dumps(transcript.to_dict(), ensure_ascii=False))
        return 0

    if args.command == "sts":
        listener = service.registry.get(args.stt)
        listener.initialize({})
        speaker = service.registry.get(args.tts)
        speaker.initialize({"pitch_hz": args.pitch_hz, "speed": args.speed})
        cascade = service.registry.get("cascade")
        cascade.initialize({
            "stt": listener, "tts": speaker, "transform": _transform(args.uppercase),
        })
        try:
            _enroll_pairs(listener, args.enroll)
            exchange = cascade.converse(args.input)
        finally:
            cascade.shutdown()
            speaker.shutdown()
            listener.shutdown()
        if args.output and exchange.audio is not None and exchange.audio.samples:
            exchange.audio.write(args.output)
        print(json.dumps(exchange.to_dict(), ensure_ascii=False))
        return 0

    if args.command == "compare":
        speaker = service.registry.get(args.tts)
        speaker.initialize({"pitch_hz": args.pitch_hz, "speed": args.speed})
        listener = service.registry.get(args.stt)
        listener.initialize({})
        try:
            _enroll_pairs(listener, args.enroll)
            if args.bootstrap_template:
                if not hasattr(listener, "enroll"):
                    raise SpeechError("--bootstrap-template requires an STT engine with enroll()")
                demo = speaker.synthesize(args.text)
                listener.enroll(args.text, demo.audio)
            report = service.compare_text_and_speech(
                args.text, listener, speaker, transform=_transform(args.uppercase),
            )
        finally:
            speaker.shutdown()
            listener.shutdown()
        print(json.dumps(report.to_dict(), ensure_ascii=False))
        return 0

    raise SpeechError(f"unknown command {args.command}")


def build_parser() -> argparse.ArgumentParser:
    """Command line options of the speech CLI."""
    parser = argparse.ArgumentParser(prog="speech_cli", description="TTS, STT and STS stacks")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="print every stack")

    tts = sub.add_parser("tts", help="synthesize text")
    tts.add_argument("--engine", default="reference-tts")
    tts.add_argument("--text", required=True)
    tts.add_argument("--output", required=True)
    tts.add_argument("--pitch-hz", type=float, default=140.0)
    tts.add_argument("--speed", type=float, default=1.0)
    tts.add_argument("--sample-rate", type=int, default=16000)

    stt = sub.add_parser("stt", help="transcribe a WAV file")
    stt.add_argument("--engine", default="template-stt")
    stt.add_argument("--input", required=True)
    stt.add_argument("--enroll", action="append", default=[], metavar="LABEL=WAV")

    sts = sub.add_parser("sts", help="speech to speech through the cascade")
    sts.add_argument("--stt", default="template-stt")
    sts.add_argument("--tts", default="reference-tts")
    sts.add_argument("--input", required=True)
    sts.add_argument("--output")
    sts.add_argument("--enroll", action="append", default=[], metavar="LABEL=WAV")
    sts.add_argument("--uppercase", action="store_true")
    sts.add_argument("--pitch-hz", type=float, default=140.0)
    sts.add_argument("--speed", type=float, default=1.0)

    compare = sub.add_parser("compare", help="text pathway versus speech pathway")
    compare.add_argument("--text", required=True)
    compare.add_argument("--stt", default="template-stt")
    compare.add_argument("--tts", default="reference-tts")
    compare.add_argument("--enroll", action="append", default=[], metavar="LABEL=WAV")
    compare.add_argument("--bootstrap-template", action="store_true",
                         help="enroll the synthesized text on a template STT before listening")
    compare.add_argument("--uppercase", action="store_true")
    compare.add_argument("--pitch-hz", type=float, default=140.0)
    compare.add_argument("--speed", type=float, default=1.0)
    return parser


def main(argv: Optional[list] = None, registry: Optional[SpeechRegistry] = None) -> int:
    """Run one command. ``registry`` lets tests avoid the process-wide singleton."""
    parser = build_parser()
    args = parser.parse_args(argv)
    service = SpeechService(registry).register_defaults()
    try:
        return _build(service, args)
    except SpeechError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
