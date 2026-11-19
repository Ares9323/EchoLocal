"""Check batch clips against their text with Whisper, loading the model once.

Usage:
    check.py [--outputs <project>\\outputs] [--cpu]

Reads every outputs\\<base>\\lines.txt written by Chatterbox\\speak.py (or the web interface) and
transcribes the matching 001.wav, 002.wav, ...; with --join output it reads outputs\\<base>.lines.txt
and transcribes outputs\\<base>.wav as a whole. <base> is <lang> or <name>_<lang> (e.g. intro_en). Words are compared after lowercasing and
dropping punctuation. Writes outputs\\check_report.txt and prints a summary.

A mismatch is something to listen to, not proof of a TTS error: Whisper gets some
words wrong by itself.
"""
import argparse
import difflib
import json
import sys
import unicodedata
from pathlib import Path

from transcribe import load_model

PROJECT = Path(__file__).resolve().parent.parent


def normalize(text):
    kept = "".join(c if not unicodedata.category(c).startswith(("P", "S")) else " " for c in text.lower())
    return " ".join(kept.split())


def tokens(text, lang):
    # Chinese and Japanese have no spaces between words: compare character by character.
    if lang in ("zh", "ja"):
        return list(normalize(text).replace(" ", ""))
    return normalize(text).split()


def lang_of(base):
    """Language code of an output name: <lang> or <name>_<lang>."""
    return base.rsplit("_", 1)[-1].lower()


def read_lines(path):
    return [l.strip() for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def diff_spans(want, got, lang):
    """[(expected, heard)] for the word spans that differ, so a long joined text stays readable."""
    sep = "" if lang in ("zh", "ja") else " "
    return [(sep.join(want[a1:a2]), sep.join(got[b1:b2]))
            for op, a1, a2, b1, b2 in difflib.SequenceMatcher(None, want, got).get_opcodes() if op != "equal"]


def word_diff(spans):
    return "\n".join(f"    expected: {e or '(nothing)'}\n    heard:    {h or '(nothing)'}" for e, h in spans)


def main():
    parser = argparse.ArgumentParser(description="Check batch TTS clips against their text with Whisper")
    parser.add_argument("--outputs", default=str(PROJECT / "outputs"), help="Batch output folder")
    parser.add_argument("--langs", help="Only these languages, comma separated (e.g. es or it,en)")
    parser.add_argument("--name", help="Only the outputs with this name (<name>_<lang>); empty string: unnamed only")
    parser.add_argument("--model", default="large-v3-turbo", help="Whisper model name")
    parser.add_argument("--cpu", action="store_true", help="Force CPU inference")
    parser.add_argument("--json", help="Also write the results to this JSON file (used by the web interface)")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    out_root = Path(args.outputs)
    # (base, wav, expected text): per-line clips first, then the joined <base>.wav files.
    # <base> is <lang> or <name>_<lang>: the language code is the part after the last underscore.
    items = []
    for lines_file in sorted(out_root.glob("*/lines.txt")):
        if lines_file.parent.name == "transcripts":
            continue
        base = lines_file.parent.name
        for i, line in enumerate(read_lines(lines_file), 1):
            items.append((base, lines_file.parent / f"{i:03d}.wav", line))
    for lines_file in sorted(out_root.glob("*.lines.txt")):
        base = lines_file.name[:-len(".lines.txt")]
        items.append((base, out_root / f"{base}.wav", " ".join(read_lines(lines_file))))
    items = [(lang_of(base), base, wav, text) for base, wav, text in items]
    if args.langs:
        wanted = {l.strip().lower() for l in args.langs.split(",") if l.strip()}
        items = [item for item in items if item[0] in wanted]
    if args.name is not None:
        items = [item for item in items if item[1] == (f"{args.name}_{item[0]}" if args.name else item[0])]
    if not items:
        sys.exit(f"nothing to check in {out_root}: run speak.bat in batch mode first")

    model = load_model(args.model, args.cpu)
    report, bad, results = [], 0, []
    for lang, _base, clip, expected in items:
        name = clip.relative_to(out_root)
        if not clip.is_file():
            bad += 1
            report.append(f"[{lang}] {name}  MISSING\n    expected: {expected}")
            results.append({"lang": lang, "file": str(clip), "ok": False, "missing": True,
                            "ratio": 0.0, "expected": expected, "heard": "", "diff": []})
            continue
        segments, _ = model.transcribe(str(clip), language=lang, vad_filter=True, beam_size=5)
        heard = " ".join(s.text.strip() for s in segments)
        want, got = tokens(expected, lang), tokens(heard, lang)
        ratio = difflib.SequenceMatcher(None, want, got).ratio()
        ok = want == got
        spans = diff_spans(want, got, lang)
        print(f"[{lang}] {name}  {'OK ' if ok else 'DIFF'}  {ratio:.0%}")
        results.append({"lang": lang, "file": str(clip), "ok": ok, "missing": False, "ratio": ratio,
                        "expected": expected, "heard": heard, "diff": spans})
        if not ok:
            bad += 1
            report.append(f"[{lang}] {name}  {ratio:.0%}\n" + word_diff(spans))
    total = len(items)

    summary = f"{total - bad}/{total} clips match"
    body = summary + ("\n\nTo listen to (Whisper can be the one that is wrong):\n\n" + "\n\n".join(report)
                      if report else "")
    (out_root / "check_report.txt").write_text(body + "\n", encoding="utf-8")
    print(f"\n{summary}. Report: {out_root / 'check_report.txt'}")
    if args.json:
        Path(args.json).write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
