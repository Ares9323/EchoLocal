"""Shared Chatterbox engine, used by speak.py (command line) and WebUI\\app.py (web interface).

Output layout, the same for both and read back by Whisper\\check.py:
    one clip per line:  <out_root>\\<base>\\001.wav, 002.wav, ... + <out_root>\\<base>\\lines.txt
    joined:             <out_root>\\<base>.wav + <out_root>\\<base>.lines.txt
where <base> is <name>_<lang> (e.g. intro_en, or intro_marco_en) or just <lang> without a name.
Writing a language in one layout removes that language's files in the other, so a folder never
holds two different takes of the same language.

The weights are downloaded once into Chatterbox\\models by download.py (setup runs it); at run
time nothing is fetched (HF_HUB_OFFLINE=1).
"""
import os
import platform
import re
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
VOICES_DIR = PROJECT / "voices"
OUTPUTS_DIR = PROJECT / "outputs"
AUDIO_EXTS = {".wav", ".m4a", ".mp3", ".flac", ".ogg", ".aac", ".opus"}

os.environ.setdefault("HF_HOME", str(ROOT / "models"))
# The weights are downloaded once by setup (download.py): never reach Hugging Face at run time.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
# On a Mac (mps), let the few ops Metal does not implement fall back to the CPU instead of failing.
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

# resemble-perth (the watermark) still imports pkg_resources; setuptools<81 keeps it working, the warning is noise.
warnings.filterwarnings("ignore", message="pkg_resources is deprecated", category=UserWarning)

import torch  # noqa: E402  (HF_HOME must be set before the model code imports huggingface_hub)
import torchaudio as ta  # noqa: E402
from chatterbox.models.s3gen import S3GEN_SR  # noqa: E402
from chatterbox.mtl_tts import SUPPORTED_LANGUAGES, ChatterboxMultilingualTTS  # noqa: E402

CLIP_NAME = re.compile(r"^\d{3}\.wav$")


def list_voices(voices_dir=VOICES_DIR):
    """Audio files in the voices folder, sorted by name."""
    folder = Path(voices_dir)
    if not folder.is_dir():
        return []
    return sorted((p for p in folder.iterdir() if p.suffix.lower() in AUDIO_EXTS), key=lambda p: p.name.lower())


def default_voice():
    """The first voice in the voices folder, or None if it is empty."""
    voices = list_voices()
    return voices[0] if voices else None


def read_lines(path):
    return split_lines(Path(path).read_text(encoding="utf-8-sig"))


def split_lines(text):
    return [line.strip() for line in text.splitlines() if line.strip()]


def pick_device():
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available() and platform.machine() == "arm64":
        # Apple Silicon GPU. Intel Macs stay on the CPU: their torch 2.2 mps on AMD GPUs is untested.
        return "mps"
    return "cpu"


def prepare_ref(path, tmp_dir, log=print):
    """Decode the reference (wav, flac, ogg, m4a, mp3, ...) to mono, trim leading and trailing
    silence, write it as a wav in tmp_dir. Chatterbox only uses the first 10 s of the reference,
    so silence at the start wastes part of them."""
    import av
    import librosa
    import numpy as np

    resampler = av.AudioResampler(format="flt", layout="mono", rate=S3GEN_SR)
    chunks = []
    with av.open(str(path)) as container:
        for frame in container.decode(audio=0):
            chunks += [f.to_ndarray().reshape(-1) for f in resampler.resample(frame)]
        chunks += [f.to_ndarray().reshape(-1) for f in resampler.resample(None)]
    audio = np.concatenate(chunks)
    trimmed, (start, end) = librosa.effects.trim(audio, top_db=40)
    out = Path(tmp_dir) / "ref.wav"
    ta.save(str(out), torch.from_numpy(trimmed).unsqueeze(0), S3GEN_SR)
    log(f"ref: {path}  ({len(audio) / S3GEN_SR:.1f} s, trimmed {start / S3GEN_SR:.1f} s at the start "
        f"and {(len(audio) - end) / S3GEN_SR:.1f} s at the end; first 10 s used)")
    return out


def output_base(lang, name=None):
    """File / folder name of one language's output: <name>_<lang>, or just <lang> without a name.
    The language code is always the part after the last underscore (Whisper/check.py relies on it)."""
    return f"{name}_{lang}" if name else lang


def safe_name(text):
    """A file-name-safe version of a title or a voice name: lowercase letters, digits, _ and -."""
    return re.sub(r"[^\w\-]+", "_", (text or "").strip().lower()).strip("_")


def _write_lines(path, lines):
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _remove_clips(lang_dir):
    if lang_dir.is_dir():
        for old in lang_dir.iterdir():
            if CLIP_NAME.match(old.name) or old.name == "lines.txt":
                old.unlink()
        if not any(lang_dir.iterdir()):
            lang_dir.rmdir()


class Engine:
    """Chatterbox loaded once; generate() can be called many times."""

    def __init__(self, device=None, log=print):
        self.device = device or pick_device()
        self.log = log
        log(f"device: {self.device}")
        self.model = ChatterboxMultilingualTTS.from_pretrained(device=self.device)
        self.sr = self.model.sr

    def generate(self, text, lang, ref, exaggeration=0.5, cfg=0.5):
        return self.model.generate(
            text,
            language_id=lang,
            audio_prompt_path=str(ref),
            exaggeration=exaggeration,
            cfg_weight=cfg,
        ).cpu()

    def save(self, wav, out_path):
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        ta.save(str(out_path), wav, self.sr)
        self.log(f"{out_path}  ({wav.shape[-1] / self.sr:.1f} s)")
        return out_path

    def write_joined(self, lang, lines, ref, out_root, pause=0.5, exaggeration=0.5, cfg=0.5, progress=None,
                     name=None):
        """All lines of one language, generated one by one, joined with `pause` s of silence."""
        out_root = Path(out_root)
        base = output_base(lang, name)
        gap = torch.zeros(1, int(pause * self.sr))
        parts = []
        for i, line in enumerate(lines, 1):
            if progress:
                progress(lang, i, len(lines))
            if parts:
                parts.append(gap)
            parts.append(self.generate(line, lang, ref, exaggeration, cfg))
        out_root.mkdir(parents=True, exist_ok=True)
        _remove_clips(out_root / base)
        _write_lines(out_root / f"{base}.lines.txt", lines)
        return self.save(torch.cat(parts, dim=-1), out_root / f"{base}.wav")

    def write_clips(self, lang, lines, ref, out_root, exaggeration=0.5, cfg=0.5, progress=None, name=None):
        """One numbered clip per line in <out_root>\\<name>_<lang>\\ (or <lang>\\ without a name)."""
        out_root = Path(out_root)
        base = output_base(lang, name)
        out_dir = out_root / base
        _remove_clips(out_dir)
        for stale in (out_root / f"{base}.wav", out_root / f"{base}.lines.txt"):
            stale.unlink(missing_ok=True)
        out_dir.mkdir(parents=True, exist_ok=True)
        _write_lines(out_dir / "lines.txt", lines)
        paths = []
        for i, line in enumerate(lines, 1):
            if progress:
                progress(lang, i, len(lines))
            paths.append(self.save(self.generate(line, lang, ref, exaggeration, cfg), out_dir / f"{i:03d}.wav"))
        return paths
