"""Generate speech locally with Chatterbox Multilingual, cloning a voice (command line).

Usage:
    speak.py                      (batch: every texts\\<lang>.txt -> outputs\\<lang>\\001.wav, ...)
    speak.py --translate-from en --langs en,it,es   (batch from texts\\en.txt, translated on the fly)
    speak.py "Text to say" --lang en [--ref voices\\my_voice.m4a] [--out out.wav]
    speak.py --file lines.txt --lang en --ref my_voice.wav --out-dir outputs\\take1

The voice is --ref, or by default the first audio file (by name) in the voices folder.

With --file, and in batch mode, every non-empty line becomes its own numbered .wav
(001.wav, 002.wav, ...), which is what a video voiceover needs: one sentence per clip,
regenerated one at a time.

Batch mode: each file in the texts folder is named after its language code (it.txt, en.txt,
de.txt, ...) and must already be written in that language. With --translate-from <lang>, only
texts\\<lang>.txt is read and the other --langs are translated from it with NLLB-200 (offline,
non-commercial license). The same --ref voice is used for every language.
Each output folder also gets a copy of its lines (lines.txt), which Whisper\\check.py
compares the clips against.

Batch mode with --join: lines are still generated one by one (Chatterbox degrades on long
text), then joined with --pause seconds of silence into one outputs\\<lang>.wav per language,
next to outputs\\<lang>.lines.txt for the check. No per-line clips are written.

The engine itself is in tts.py, shared with the web interface.
"""
import argparse
import sys
import tempfile
from pathlib import Path

import tts


def collect_batch(texts_dir):
    """Return [(lang, lines)] for every texts_dir/<lang>.txt with a supported language code."""
    jobs = []
    for path in sorted(Path(texts_dir).glob("*.txt")):
        lang = path.stem.lower()
        if lang not in tts.SUPPORTED_LANGUAGES:
            print(f"[skip] {path.name}: '{lang}' is not a supported language code "
                  f"({', '.join(tts.SUPPORTED_LANGUAGES)})", file=sys.stderr)
            continue
        lines = tts.read_lines(path)
        if not lines:
            print(f"[skip] {path.name}: empty", file=sys.stderr)
            continue
        jobs.append((lang, lines))
    return jobs


def translate_batch(parser, texts_dir, src, targets):
    """[(lang, lines)]: texts_dir/<src>.txt as written, translated with NLLB for the other targets."""
    unknown = [code for code in [src, *targets] if code not in tts.SUPPORTED_LANGUAGES]
    if unknown:
        parser.error(f"unsupported language code(s): {', '.join(unknown)} ({', '.join(tts.SUPPORTED_LANGUAGES)})")
    if not targets:
        parser.error("--translate-from needs --langs, e.g. --langs en,it,es")
    source = Path(texts_dir) / f"{src}.txt"
    if not source.is_file():
        parser.error(f"{source} not found")
    lines = tts.read_lines(source)
    if not lines:
        parser.error(f"{source} is empty")

    sys.path.insert(0, str(tts.PROJECT / "WebUI"))
    from translate import Translator

    translator = Translator()
    jobs = []
    for code in targets:
        if code != src:
            print(f"translating {src} -> {code}...")
        jobs.append((code, translator.translate_lines(lines, src, code)))
    return jobs


def main():
    parser = argparse.ArgumentParser(description="Local multilingual TTS with voice cloning")
    parser.add_argument("text", nargs="?", help="Text to say (omit it, and --file, for batch mode)")
    parser.add_argument("--file", help="Text file, one sentence per line")
    parser.add_argument("--lang", default="en", help="Language code: en, it, es, fr, de, ...")
    parser.add_argument("--ref", default=None,
                        help="Reference recording of the voice to clone (5-15 s, clean; wav, m4a, mp3, ...). "
                             "Default: the first audio file in the voices folder")
    parser.add_argument("--out", default="outputs/out.wav", help="Output file for a single text")
    parser.add_argument("--out-dir", default=None,
                        help="Output folder for --file (default: outputs) "
                             "or for batch mode (default: <project>\\outputs, one subfolder per language)")
    parser.add_argument("--texts-dir", default=str(tts.PROJECT / "texts"),
                        help="Batch mode: folder with one <lang>.txt per language (default: <project>\\texts)")
    parser.add_argument("--langs", help="Batch mode: only these languages, comma separated (e.g. es or it,en)")
    parser.add_argument("--translate-from", metavar="LANG",
                        help="Batch mode: read only texts\\<LANG>.txt and translate it to every --langs language")
    parser.add_argument("--join", action="store_true",
                        help="Batch mode: one outputs\\<lang>.wav per language instead of one clip per line")
    parser.add_argument("--pause", type=float, default=0.5, help="With --join: silence between lines, seconds")
    parser.add_argument("--name", help="Batch mode: name the outputs <name>_<lang> (e.g. intro_en.wav) "
                                       "instead of just <lang>")
    parser.add_argument("--exaggeration", type=float, default=0.5, help="Expressiveness, 0.25-1.0")
    parser.add_argument("--cfg", type=float, default=0.5, help="Pacing/adherence, lower is slower")
    args = parser.parse_args()

    if args.ref is None:
        first = tts.default_voice()
        if first is None:
            parser.error(f"no voice: put a 5-15 s recording of the voice to clone in {tts.VOICES_DIR}, "
                         "or pass --ref")
        args.ref = str(first)
    if not Path(args.ref).is_file():
        parser.error(f"reference voice not found: {args.ref}")

    jobs = None
    if not args.text and not args.file:
        wanted = [l.strip().lower() for l in (args.langs or "").split(",") if l.strip()]
        if args.translate_from:
            jobs = translate_batch(parser, args.texts_dir, args.translate_from.lower(), wanted)
        else:
            jobs = collect_batch(args.texts_dir)
            if wanted:
                jobs = [job for job in jobs if job[0] in wanted]
        if not jobs:
            parser.error(f"no <lang>.txt files with text in {args.texts_dir}")
        print(f"batch: {', '.join(f'{lang} ({len(lines)})' for lang, lines in jobs)}  |  ref: {args.ref}")

    tmp = tempfile.TemporaryDirectory()
    ref = tts.prepare_ref(args.ref, tmp.name)
    engine = tts.Engine()
    gen = dict(ref=ref, exaggeration=args.exaggeration, cfg=args.cfg)

    def progress(lang, i, n):
        print(f"[{lang}] line {i}/{n}")

    if jobs is not None:
        out_root = Path(args.out_dir) if args.out_dir else tts.OUTPUTS_DIR
        name = tts.safe_name(args.name) or None
        for lang, lines in jobs:
            if args.join:
                engine.write_joined(lang, lines, out_root=out_root, pause=args.pause, progress=progress,
                                    name=name, **gen)
            else:
                engine.write_clips(lang, lines, out_root=out_root, progress=progress, name=name, **gen)
    elif args.file:
        out_dir = Path(args.out_dir or "outputs")
        for i, line in enumerate(tts.read_lines(args.file), 1):
            engine.save(engine.generate(line, args.lang, **gen), out_dir / f"{i:03d}.wav")
    else:
        engine.save(engine.generate(args.text, args.lang, **gen), Path(args.out))


if __name__ == "__main__":
    main()
