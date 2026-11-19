# EchoLocal

Clone a voice from a short recording and make it speak in 23 languages, translate the text on the
fly, and turn speech back into text. Everything runs on your computer: no cloud service, no
account, no upload. The voices never leave the machine.

Built on [Chatterbox Multilingual](https://github.com/resemble-ai/chatterbox) (voice cloning),
[NLLB-200](https://huggingface.co/facebook/nllb-200-distilled-600M) (translation) and
[faster-whisper](https://github.com/SYSTRAN/faster-whisper) (speech to text and a check of every
generated clip).

## Features

- **Web interface** on `http://127.0.0.1:7860`, reachable from this computer only. It follows the
  browser's language (English and Italian for now).
  - *Text to speech*: pick a voice, write the text once, tick the output languages. "Translate"
    fills an editable box per language; a box left empty is translated when you press "Generate".
    Output is one file per language (lines joined with a pause) or one clip per line, each with a
    player, a download link and the Whisper check.
  - *Speech to text*: upload a file or record from the microphone, get the transcript plus `.txt`
    and `.srt` (subtitles with timing). "Use as text to speak" sends it to the other tab.
- **Command line** for batches: one clip per line or one file per language, from text files
  already written in each language or translated on the fly from one of them.
- **Whisper check**: every generated clip is transcribed back and compared with its text, so the
  words to listen to again are listed for you.

## Requirements

| System | Notes |
|---|---|
| Windows 10/11 with an NVIDIA GPU | Recommended. Driver 550 or newer (CUDA 12.4). About 4 GB of VRAM for Chatterbox plus 2 GB for Whisper: 8 GB is enough. |
| Windows without an NVIDIA GPU | Works on the CPU, but slowly (about a minute per sentence). |
| Mac with Apple Silicon (M1 or later), macOS 14+ | Chatterbox on the Apple GPU (`mps`), Whisper on the CPU. |
| Intel Mac, macOS 12+ | CPU only, older pinned versions (torch 2.2.2), about 1-2 minutes per sentence. The web interface is untested there. |

Disk: about 8 GB for the models plus 3 GB for the Python packages. Internet is needed only during
setup. [uv](https://docs.astral.sh/uv/) is installed automatically if missing.

## Install

Windows, from PowerShell in this folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

Mac:

```bash
bash setup.sh
```

Setup creates two virtual environments (`Chatterbox/venv`, `Whisper/venv`), installs the exact
tested versions, then downloads the models from Hugging Face: Chatterbox (4 GB) into
`Chatterbox/models`, NLLB-200 (2.4 GB) into `WebUI/models`, Whisper large-v3-turbo (1.6 GB) into
`Whisper/models`. After that every script runs offline.

| Windows | Mac | Effect |
|---|---|---|
| `-Cpu` | | CPU build even if an NVIDIA GPU is present |
| `-SkipWhisper` | `--skip-whisper` | No speech to text and no check |
| `-SkipTranslation` | `--skip-translation` | No translation model: write each language yourself |
| `-SkipModels` | `--skip-models` | Packages only, no model download |

Setup can be run again at any time: it rebuilds the environments and keeps the models already
downloaded. If a download is interrupted, run it again to resume.

## Add a voice

Put an audio file (wav, m4a, mp3, flac, ogg) in `voices/`, or record one in the web interface
(*Record a new voice*: it is saved in `voices/` under the name you give it). The file name is the
voice name. A good
sample is 5-15 s of one person speaking naturally, without music or other voices. Only the first
10 s are used, and silence at both ends is trimmed automatically. Microphone and room end up in
the cloned voice, so they matter as much as the speaker.

## Web interface

```
webui.bat            (Windows)
./webui.sh           (Mac)
```

The first start loads Chatterbox (about 30 s); then it stays in memory. Options: `--port 7861`
for another port, `--no-browser` to not open the browser. The *Title* names the job: results go to
`outputs/<title>/<title>_en.wav`, `<title>_es.wav`, ... (optionally `<title>_<voice>_en.wav`), and
transcripts to `outputs/transcripts/`. Each language appears as soon as it is ready, so you can
listen to it while the others are still being generated; starting a player pauses the others.

## Command line

On a Mac use the `.sh` scripts with the same arguments.

```bat
rem One sentence
Chatterbox\speak.bat "Hello, this is a test." --lang en --ref voices\my_voice.m4a --out outputs\test.wav

rem One clip per line of a file
Chatterbox\speak.bat --file lines.txt --lang de --out-dir outputs\de

rem Every texts\<lang>.txt, one clip per line, then the Whisper check
speak_all.bat --ref voices\my_voice.m4a

rem The same, but one file per language with 0.8 s between lines, named intro_en.wav, intro_it.wav, ...
speak_joined.bat --pause 0.8 --name intro

rem Only texts\en.txt, translated on the fly into Italian and Spanish
speak_all.bat --translate-from en --langs en,it,es

rem Speech to text, with subtitles
Whisper\transcribe.bat interview.m4a --lang en --txt interview.txt --srt interview.srt

rem Check a folder of results again
Whisper\check.bat --outputs outputs\my_voice --langs it,en
```

- `texts/<lang>.txt`: the file name is the language code, one sentence per line.
- Without `--ref` the first file in `voices/` is used.
- `--exaggeration` (0.25-1.0, default 0.5) sets the expressiveness, `--cfg` (default 0.5) the pace:
  lower is slower.
- `--langs it,en` limits a batch (and the check) to those languages; `check --name intro` only
  checks the outputs with that name.
- Without `--lang`, `transcribe` detects the language.

### Output layout

```
<folder>/<base>/001.wav, 002.wav, ...  + lines.txt     one clip per line
<folder>/<base>.wav + <base>.lines.txt                 one file per language
<folder>/check_report.txt                              the Whisper check
```

`<base>` is `<name>_<lang>` (e.g. `intro_en`) or just `<lang>` without a name; the check reads the
language from the part after the last underscore. Writing a language in one layout removes its
files in the other layout, so a folder always holds a single version per language and name.

## Languages

Arabic (ar), Chinese (zh), Danish (da), Dutch (nl), English (en), Finnish (fi), French (fr),
German (de), Greek (el), Hebrew (he), Hindi (hi), Italian (it), Japanese (ja), Korean (ko),
Malay (ms), Norwegian (no), Polish (pl), Portuguese (pt), Russian (ru), Spanish (es),
Swahili (sw), Swedish (sv), Turkish (tr).

## Good to know

- **A Whisper mismatch is something to listen to, not proof of an error.** Whisper gets some words
  wrong by itself (rare or poetic words, some inflections, accents dropped). Trust your ears.
- **Translation is a draft.** NLLB-200 is good on plain sentences and weak on poetry or idioms:
  read the boxes before generating.
- Write one sentence per line: Chatterbox degrades on long text, so each line is generated on its
  own (and joined afterwards in the one file mode).
- On a laptop, keep it plugged in: on battery the GPU slows down a lot.
- `setuptools` must stay below 81 in the Chatterbox environment (the watermark library still uses
  `pkg_resources`); setup takes care of it.
- No ffmpeg needed: audio files are decoded with PyAV.

## Responsible use

Clone only your own voice or voices you have explicit permission to use, and do not use generated
speech to deceive anyone. Chatterbox embeds an inaudible [Perth](https://github.com/resemble-ai/Perth)
watermark in every clip, so generated audio can be recognized as such.

## Adding an interface language

The interface strings are in [`WebUI/ui_strings.py`](WebUI/ui_strings.py): copy the `en`
dictionary under the new language code, translate the values and keep the `{placeholders}`.

## License

EchoLocal is released under the [PolyForm Noncommercial License 1.0.0](LICENSE.md): free for
personal, research, educational and other non-commercial use. The models and libraries keep their
own licenses (see [NOTICE.md](NOTICE.md)); in particular the NLLB-200 translation model is
CC-BY-NC 4.0, non-commercial only.
