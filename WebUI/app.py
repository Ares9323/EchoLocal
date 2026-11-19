"""EchoLocal web interface: text to speech with a cloned voice (with translation and a Whisper
check), and speech to text.

Run with webui.bat (Windows) or webui.sh (Mac/Linux) from the project folder (--port, --no-browser); it opens
http://127.0.0.1:7860 in the browser. It listens on this computer only (127.0.0.1): the voices
never leave it. The interface follows the browser's language (strings in ui_strings.py).

Runs in the Chatterbox venv. Pieces it connects:
    Chatterbox/tts.py         engine (loaded once at startup, kept in memory)
    WebUI/translate.py        NLLB-200 translation, offline, on the CPU (optional)
    Whisper/check.py          the check, run in its own venv as a subprocess (--json)
    Whisper/transcribe.py     speech to text, same venv and same way
Voices are the audio files in voices/. A job is saved as outputs/<title>/<title>_<lang>.wav
(or <title>_<voice>_<lang>.wav), same layout as speak.py --name; transcripts go to outputs/transcripts/.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
sys.path.insert(0, str(PROJECT / "Chatterbox"))

import tts  # noqa: E402  (sets HF_HOME / offline mode before anything imports huggingface_hub)
import translate  # noqa: E402

import gradio as gr  # noqa: E402
import soundfile as sf  # noqa: E402
from ui_strings import I18N, label, locale_of, t  # noqa: E402

LANGS = list(tts.SUPPORTED_LANGUAGES.items())  # [(code, English name)]
CODES = [code for code, _ in LANGS]
NAMES = dict(LANGS)
LANG_CHOICES = [(f"{name} ({code})", code) for code, name in LANGS]
WHISPER_DIR = PROJECT / "Whisper"
WHISPER_PY = WHISPER_DIR / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
TRANSCRIPTS_DIR = tts.OUTPUTS_DIR / "transcripts"

# Result cards use the same surface and border as the other blocks; a job still running shows an
# animated bar in place of the player.
CSS = """
.el-card { border: 1px solid var(--block-border-color); border-radius: var(--block-radius);
           background: var(--block-background-fill); padding: var(--block-padding); gap: var(--spacing-md); }
.el-card h3 { margin: 0; }
.el-pending { display: flex; flex-direction: column; gap: 10px; padding: 18px 4px; color: var(--body-text-color-subdued); }
.el-pending .el-bar { height: 6px; border-radius: 3px; overflow: hidden; background: var(--background-fill-secondary); }
.el-pending .el-bar::after { content: ""; display: block; height: 100%; width: 35%; border-radius: 3px;
           background: var(--color-accent); opacity: .8; animation: el-slide 1.4s ease-in-out infinite; }
.el-pending.el-waiting .el-bar::after { animation: none; width: 0; }
@keyframes el-slide { 0% { margin-left: -35%; } 100% { margin-left: 100%; } }
"""

# One player at a time: starting an audio pauses the one that was playing. Patched on the prototype
# because the players' media elements are not always attached to the page.
HEAD = """<script>
(() => {
  const play = HTMLMediaElement.prototype.play;
  let current = null;
  HTMLMediaElement.prototype.play = function (...args) {
    if (current && current !== this && !current.paused) current.pause();
    current = this;
    return play.apply(this, args);
  };
})();
</script>"""

engine = None  # tts.Engine, loaded in main()
translator = translate.Translator()


def voice_names():
    return [p.name for p in tts.list_voices()]


def voice_path(name, locale):
    if not name:
        raise gr.Error(t(locale, "err_no_voice"))
    path = (tts.VOICES_DIR / name).resolve()
    if path.parent != tts.VOICES_DIR.resolve() or not path.is_file():
        raise gr.Error(t(locale, "err_voice_missing", name=name))
    return path


def mode_choices(locale):
    return [(t(locale, "mode_joined"), "joined"), (t(locale, "mode_clips"), "clips")]


def stt_lang_choices(locale):
    return [(t(locale, "auto"), "auto")] + LANG_CHOICES


def box_updates(src, targets, values=None, placeholders=None):
    """One update per language textbox: visible for targets other than the source language."""
    values, placeholders = values or {}, placeholders or {}
    updates = []
    for code in CODES:
        extra = {}
        if code in values:
            extra["value"] = values[code]
        if code in placeholders:
            extra["placeholder"] = placeholders[code]
        updates.append(gr.Textbox(visible=code in targets and code != src, **extra))
    return updates


def translate_lines(lines, src, code, locale):
    try:
        return translator.translate_lines(lines, src, code)
    except RuntimeError:
        raise gr.Error(t(locale, "err_translation"))


def translate_all(src, text, targets, locale):
    """Fill the language boxes one by one; the boxes still to do show a placeholder."""
    lines = tts.split_lines(text or "")
    if not lines:
        raise gr.Error(t(locale, "err_no_text"))
    todo = [code for code in CODES if code in targets and code != src]
    values = {code: "" for code in todo}
    for n, code in enumerate(todo):
        placeholders = {c: t(locale, "box_translating" if c == code else "box_waiting") for c in todo[n:]}
        status = t(locale, "translate_status", lang=NAMES[code], i=n + 1, n=len(todo))
        yield *box_updates(src, targets, values, placeholders), status
        values[code] = "\n".join(translate_lines(lines, src, code, locale))
    yield *box_updates(src, targets, values, {c: "" for c in todo}), t(locale, "translate_done")


def run_whisper(script, args, locale, error_key):
    """A script of the Whisper folder in its own venv; raises gr.Error with the last lines on failure."""
    if not WHISPER_PY.is_file():
        raise gr.Error(t(locale, "err_whisper_venv", path=WHISPER_PY))
    env = {k: v for k, v in os.environ.items() if k != "HF_HOME"}
    proc = subprocess.run([str(WHISPER_PY), str(WHISPER_DIR / script), *args], cwd=WHISPER_DIR, env=env,
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        tail = "\n".join((proc.stderr or proc.stdout).strip().splitlines()[-5:])
        raise gr.Error(t(locale, error_key, tail=tail))
    return proc


def run_check(out_root, langs, name, locale):
    """Whisper/check.py on the outputs of this job; returns {wav path: result}."""
    with tempfile.TemporaryDirectory() as tmp:
        report = Path(tmp) / "check.json"
        run_whisper("check.py", ["--outputs", str(out_root), "--langs", ",".join(langs), "--name", name,
                                 "--json", str(report)], locale, "err_check")
        if not report.is_file():
            raise gr.Error(t(locale, "err_check", tail="no report"))
        return {str(Path(r["file"]).resolve()): r for r in json.loads(report.read_text(encoding="utf-8"))}


def job_names(title, voice, with_voice):
    """(folder, file name prefix): outputs/<title>/ and <title> or <title>_<voice>."""
    voice_name = tts.safe_name(Path(voice or "").stem)
    title = tts.safe_name(title) or voice_name or "untitled"
    return title, f"{title}_{voice_name}" if with_voice and voice_name else title


def generate(voice, src, text, targets, mode, pause, exaggeration, cfg, title, with_voice, check, locale, *boxes,
             progress=gr.Progress()):
    """Generator: yields the result cards after every language, so finished ones can be played
    while the others are still being made."""
    if not targets:
        raise gr.Error(t(locale, "err_no_targets"))
    source_lines = tts.split_lines(text or "")
    if not source_lines:
        raise gr.Error(t(locale, "err_no_text"))
    ref_file = voice_path(voice, locale)
    folder, name = job_names(title, voice, with_voice)
    out_root = tts.OUTPUTS_DIR / folder

    # Lines per language: the source text as written, the (edited) translation for the others;
    # an empty translation box is translated when its turn comes.
    codes = [c for c in CODES if c in targets]
    items = [{"code": c, "mode": mode, "state": "waiting", "lines": [], "files": [], "checks": []} for c in codes]
    state = {"locale": locale, "items": items}
    total = len(source_lines) * len(codes)
    done = {"n": 0}

    def step(lang, i, n):
        progress((done["n"], total), desc=t(locale, "prog_line", lang=NAMES[lang], i=i, n=n))
        done["n"] += 1

    with tempfile.TemporaryDirectory() as tmp:
        ref = tts.prepare_ref(ref_file, tmp)
        gen = dict(ref=ref, exaggeration=exaggeration, cfg=cfg, progress=step, name=name)
        for item in items:
            code = item["code"]
            item["state"] = "working"
            yield state, ""
            if code == src:
                lines = source_lines
            else:
                lines = tts.split_lines(boxes[CODES.index(code)] or "")
                if not lines:
                    progress((done["n"], total), desc=t(locale, "prog_translating", lang=NAMES[code]))
                    lines = translate_lines(source_lines, src, code, locale)
            if mode == "joined":
                files = [engine.write_joined(code, lines, out_root=out_root, pause=pause, **gen)]
            else:
                files = engine.write_clips(code, lines, out_root=out_root, **gen)
            item.update(state="checking" if check else "done", lines=lines, files=[str(f) for f in files],
                        checks=[None] * len(files))
            yield state, ""

    if check:
        progress((total, total), desc=t(locale, "prog_check"))
        checks = run_check(out_root, codes, name, locale)
        for item in items:
            item["state"] = "done"
            item["checks"] = [checks.get(str(Path(f).resolve())) for f in item["files"]]
    lines_total = sum(len(item["lines"]) for item in items)
    yield state, t(locale, "done", langs=len(items), lines=lines_total, folder=out_root)


def check_line(result, locale):
    if result is None:
        return ""
    if result["ok"]:
        return t(locale, "chk_match")
    if result.get("missing"):
        return t(locale, "chk_missing")
    nothing = t(locale, "nothing")
    spans = "; ".join(t(locale, "chk_span", expected=e or nothing, heard=h or nothing) for e, h in result["diff"])
    return t(locale, "chk_diff", ratio=f"{result['ratio']:.0%}", spans=spans)


def pending_html(text, moving=True):
    cls = "el-pending" if moving else "el-pending el-waiting"
    return f'<div class="{cls}"><span>{escape(text)}</span><div class="el-bar"></div></div>'


def transcribe(audio, lang, locale, progress=gr.Progress()):
    """Speech to text: transcript, a status line, the .txt/.srt files, the detected language."""
    if not audio:
        raise gr.Error(t(locale, "err_no_audio"))
    progress(0, desc=t(locale, "prog_transcribing"))
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    base = TRANSCRIPTS_DIR / f"{tts.safe_name(Path(audio).stem) or 'audio'}_{time.strftime('%Y%m%d-%H%M%S')}"
    txt, srt = base.with_suffix(".txt"), base.with_suffix(".srt")
    with tempfile.TemporaryDirectory() as tmp:
        result_file = Path(tmp) / "transcript.json"
        args = [str(audio), "--json", str(result_file), "--txt", str(txt), "--srt", str(srt)]
        if lang and lang != "auto":
            args += ["--lang", lang]
        run_whisper("transcribe.py", args, locale, "err_transcribe")
        result = json.loads(result_file.read_text(encoding="utf-8"))
    detected = result["language"]
    info = t(locale, "detected", lang=NAMES.get(detected, detected), duration=result["duration"],
             folder=TRANSCRIPTS_DIR)
    return result["text"], info, [str(txt), str(srt)], detected


def build():
    voices = voice_names()
    first_voice = voices[0] if voices else None
    can_translate = translate.available()
    with gr.Blocks(title="EchoLocal") as demo:
        locale = gr.State("en")
        gr.Markdown(label("title"))
        with gr.Tabs() as tabs:
            with gr.Tab(label("tab_tts"), id="tts"):
                with gr.Row():
                    with gr.Column(scale=2):
                        voice = gr.Dropdown(voices, value=first_voice, label=label("voice"))
                        refresh = gr.Button(label("refresh"), size="sm")
                    preview = gr.Audio(value=str(tts.VOICES_DIR / first_voice) if first_voice else None,
                                       label=label("voice_sample"), type="filepath", interactive=False, scale=3)
                no_voices = gr.Markdown(label("no_voices"), visible=not voices)
                with gr.Accordion(label("rec_title"), open=not voices):
                    gr.Markdown(label("rec_hint"))
                    with gr.Row():
                        rec_audio = gr.Audio(sources=["microphone"], type="filepath", label=label("rec_audio"),
                                             scale=3)
                        with gr.Column(scale=2):
                            rec_name = gr.Textbox(label=label("rec_name"))
                            rec_save = gr.Button(label("rec_save"))
                    rec_status = gr.Markdown()
                with gr.Row():
                    src = gr.Dropdown(LANG_CHOICES, value="en", label=label("src_lang"))
                    targets = gr.CheckboxGroup(LANG_CHOICES, value=["en"], label=label("out_langs"))
                text = gr.Textbox(lines=6, label=label("text"))
                translate_btn = gr.Button(label("translate"), visible=can_translate)
                translate_status = gr.Markdown()
                gr.Markdown(label("translate_off"), visible=not can_translate)
                boxes = [gr.Textbox(lines=4, label=f"{name} ({code})", info=label("translation_box"), visible=False)
                         for code, name in LANGS]
                with gr.Accordion(label("options"), open=True):
                    with gr.Row():
                        mode = gr.Radio(mode_choices("en"), value="joined", label=label("output"))
                        pause = gr.Slider(0, 2, value=0.5, step=0.1, label=label("pause"))
                    with gr.Row():
                        exaggeration = gr.Slider(0.25, 1.0, value=0.5, step=0.05, label=label("expressiveness"))
                        cfg = gr.Slider(0.2, 1.0, value=0.5, step=0.05, label=label("pace"))
                    with gr.Row():
                        title = gr.Textbox(label=label("job_title"), info=label("job_title_info"))
                        with gr.Column():
                            with_voice = gr.Checkbox(value=False, label=label("voice_in_name"))
                            check = gr.Checkbox(value=True, label=label("check"))
                generate_btn = gr.Button(label("generate"), variant="primary")
                status = gr.Markdown()
                results = gr.State({"locale": "en", "items": []})

                @gr.render(inputs=results)
                def show(state):
                    loc = state["locale"]
                    for r in state["items"]:
                        with gr.Column(elem_classes="el-card"):
                            gr.Markdown(f"### {NAMES[r['code']]} ({r['code']})")
                            if r["state"] in ("waiting", "working"):
                                gr.HTML(pending_html(t(loc, "card_" + r["state"]), moving=r["state"] == "working"))
                                continue
                            for i, (path, chk) in enumerate(zip(r["files"], r["checks"]), 1):
                                name = Path(path).name if r["mode"] == "joined" else f"{i:03d}: {r['lines'][i - 1][:90]}"
                                gr.Audio(value=path, label=name, type="filepath", interactive=False)
                                if r["state"] == "checking":
                                    gr.HTML(pending_html(t(loc, "card_checking")))
                                elif chk is not None:
                                    gr.Markdown(check_line(chk, loc))
                            gr.File(value=r["files"], label=t(loc, "download"), interactive=False)

            with gr.Tab(label("tab_stt"), id="stt"):
                with gr.Row():
                    audio_in = gr.Audio(sources=["upload", "microphone"], type="filepath", label=label("stt_audio"),
                                        scale=3)
                    stt_lang = gr.Dropdown(stt_lang_choices("en"), value="auto", label=label("stt_lang"), scale=1)
                transcribe_btn = gr.Button(label("transcribe"), variant="primary")
                transcript = gr.Textbox(lines=8, label=label("transcript"), interactive=True)
                stt_info = gr.Markdown()
                stt_files = gr.File(label=label("stt_files"), interactive=False)
                use_btn = gr.Button(label("use_text"))
                detected = gr.State("")

        def on_load(request: gr.Request):
            loc = locale_of(request)
            start = loc if loc in CODES else "en"
            return (loc, gr.Dropdown(value=start), gr.CheckboxGroup(value=[start]),
                    gr.Radio(choices=mode_choices(loc)), gr.Dropdown(choices=stt_lang_choices(loc)))

        def on_voice(v):
            return str(tts.VOICES_DIR / v) if v else None

        def on_refresh(v):
            names = voice_names()
            value = v if v in names else (names[0] if names else None)
            return gr.Dropdown(choices=names, value=value), gr.Markdown(visible=not names)

        def save_recording(audio, name, loc):
            """Copy a microphone recording into voices/<name>.wav and select it."""
            if not audio:
                raise gr.Error(t(loc, "err_rec_none"))
            stem = re.sub(r"[^\w\-]+", "_", (name or "").strip()).strip("_")
            if not stem:
                raise gr.Error(t(loc, "err_rec_name"))
            if any(Path(v).stem.lower() == stem.lower() for v in voice_names()):
                raise gr.Error(t(loc, "err_rec_exists", name=stem))
            seconds = sf.info(audio).duration
            if seconds < 5:
                raise gr.Error(t(loc, "err_rec_short", seconds=seconds))
            tts.VOICES_DIR.mkdir(exist_ok=True)
            target = tts.VOICES_DIR / f"{stem}{Path(audio).suffix.lower() or '.wav'}"
            shutil.copyfile(audio, target)
            return (gr.Dropdown(choices=voice_names(), value=target.name), gr.Markdown(visible=False),
                    None, "", t(loc, "rec_saved", name=target.name))

        def use_transcript(text_value, lang_value):
            src_update = gr.Dropdown(value=lang_value) if lang_value in CODES else gr.Dropdown()
            return text_value, src_update, gr.Tabs(selected="tts")

        # Light UI updates skip the queue: the queue runs one job at a time (a single GPU), and a box
        # appearing or a voice preview must not wait behind a generation.
        fast = dict(queue=False, show_progress="hidden")
        demo.load(on_load, None, [locale, src, targets, mode, stt_lang], **fast)
        voice.change(on_voice, voice, preview, **fast)
        refresh.click(on_refresh, voice, [voice, no_voices], **fast)
        rec_save.click(save_recording, [rec_audio, rec_name, locale],
                       [voice, no_voices, rec_audio, rec_name, rec_status], **fast)
        src.change(box_updates, [src, targets], boxes, **fast)
        targets.change(box_updates, [src, targets], boxes, **fast)
        use_btn.click(use_transcript, [transcript, detected], [text, src, tabs], **fast)
        translate_btn.click(translate_all, [src, text, targets, locale], [*boxes, translate_status],
                            show_progress="hidden")
        generate_btn.click(generate,
                           [voice, src, text, targets, mode, pause, exaggeration, cfg, title, with_voice, check,
                            locale, *boxes],
                           [results, status], show_progress_on=status)
        transcribe_btn.click(transcribe, [audio_in, stt_lang, locale], [transcript, stt_info, stt_files, detected],
                             show_progress_on=stt_info)
    return demo


def main():
    global engine
    parser = argparse.ArgumentParser(description="EchoLocal web interface (this computer only)")
    parser.add_argument("--port", type=int, default=7860, help="Port on 127.0.0.1 (default 7860)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open the browser")
    args = parser.parse_args()
    tts.VOICES_DIR.mkdir(exist_ok=True)
    tts.OUTPUTS_DIR.mkdir(exist_ok=True)
    print("Loading Chatterbox (about 30 s)...")
    engine = tts.Engine()
    demo = build()
    demo.queue(default_concurrency_limit=1)  # one job at a time: a single GPU
    demo.launch(server_name="127.0.0.1", server_port=args.port, inbrowser=not args.no_browser,
                allowed_paths=[str(tts.VOICES_DIR), str(tts.OUTPUTS_DIR)], i18n=I18N, css=CSS, head=HEAD)


if __name__ == "__main__":
    main()
