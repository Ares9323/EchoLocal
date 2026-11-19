"""Transcribe an audio file locally with faster-whisper.

Usage:
    transcribe.py <audio file> [--lang it] [--model large-v3-turbo] [--cpu]
                  [--txt out.txt] [--srt out.srt] [--json out.json]
    transcribe.py --download [--model large-v3-turbo]

Prints the transcript to stdout; --txt / --srt / --json also write it to files (--srt keeps the
timing, as subtitles; --json is used by the web interface). Without --lang the language is
detected. Models are cached in ./models next to this script: setup downloads them once
(--download), then nothing is fetched at run time.
"""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODELS_DIR = ROOT / "models"
DEFAULT_MODEL = "large-v3-turbo"


def add_cuda_dll_dirs():
    # cuBLAS / cuDNN come from the nvidia-* pip wheels; Windows must be told where their DLLs live.
    site = ROOT / "venv" / "Lib" / "site-packages" / "nvidia"
    if not site.is_dir():
        return
    for bin_dir in site.glob("*/bin"):
        os.add_dll_directory(str(bin_dir))
        os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ["PATH"]


def download(name=DEFAULT_MODEL):
    """Fetch the model into ./models (setup runs this once)."""
    os.environ["HF_HUB_OFFLINE"] = "0"  # before faster_whisper imports huggingface_hub
    from faster_whisper import download_model

    return download_model(name, cache_dir=str(MODELS_DIR))


def load_model(name=DEFAULT_MODEL, cpu=False):
    add_cuda_dll_dirs()
    # Downloaded once by setup (--download): never reach Hugging Face at run time.
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    import ctranslate2
    from faster_whisper import WhisperModel

    if not cpu and ctranslate2.get_cuda_device_count() == 0:
        print("[no CUDA GPU found, using CPU]", file=sys.stderr)
        cpu = True

    if cpu:
        return WhisperModel(name, device="cpu", compute_type="int8", download_root=str(MODELS_DIR))
    return WhisperModel(name, device="cuda", compute_type="float16", download_root=str(MODELS_DIR))


def srt_time(seconds):
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def to_srt(segments):
    return "\n".join(f"{i}\n{srt_time(s['start'])} --> {srt_time(s['end'])}\n{s['text']}\n"
                     for i, s in enumerate(segments, 1))


def main():
    parser = argparse.ArgumentParser(description="Local speech-to-text with faster-whisper")
    parser.add_argument("audio", nargs="?", help="Path to the audio file (ogg, oga, mp3, wav, m4a, ...)")
    parser.add_argument("--lang", default=None, help="Language code, e.g. it or en (auto-detect if omitted)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Whisper model name")
    parser.add_argument("--cpu", action="store_true", help="Force CPU inference")
    parser.add_argument("--txt", help="Also write the transcript to this text file")
    parser.add_argument("--srt", help="Also write the transcript with timing to this subtitle file")
    parser.add_argument("--json", help="Also write text, language and segments to this JSON file")
    parser.add_argument("--download", action="store_true", help="Download the model and exit")
    args = parser.parse_args()

    if args.download:
        print(f"Whisper {args.model}: {download(args.model)}")
        return
    if not args.audio:
        parser.error("the audio file is required")

    model = load_model(args.model, args.cpu)
    found, info = model.transcribe(args.audio, language=args.lang, vad_filter=True, beam_size=5)
    segments = [{"start": s.start, "end": s.end, "text": s.text.strip()} for s in found]
    text = " ".join(s["text"] for s in segments)

    sys.stdout.reconfigure(encoding="utf-8")
    print(text)
    print(f"[language: {info.language}, duration: {info.duration:.1f}s]", file=sys.stderr)
    if args.txt:
        Path(args.txt).write_text(text + "\n", encoding="utf-8")
    if args.srt:
        Path(args.srt).write_text(to_srt(segments), encoding="utf-8")
    if args.json:
        Path(args.json).write_text(json.dumps(
            {"text": text, "language": info.language, "duration": info.duration, "segments": segments},
            ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
