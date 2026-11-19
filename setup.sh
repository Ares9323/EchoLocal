#!/usr/bin/env bash
# Sets up EchoLocal on a Mac: the voice-cloning TTS (Chatterbox), translation (NLLB-200) and
# speech to text / the check (faster-whisper).
# Apple Silicon (M1 or later), macOS 14+: same versions as Windows, Chatterbox on the Apple GPU (mps).
# Intel Mac, macOS 12+: torch 2.6 has no Intel build, so the exact older versions in
# */constraints-mac-intel.txt (torch 2.2.2, transformers 4.46.3) are installed. CPU only: slow.
# Run from any folder:  bash setup.sh
# Options: --skip-whisper skips speech to text and the check, --skip-translation the translation
# model, --skip-models installs the packages only.
# Downloaded: uv (if missing), Python, the Python packages (about 1.5 GB), then the models from
# Hugging Face (Chatterbox 4 GB, NLLB 2.4 GB, Whisper 1.6 GB). After that everything runs offline.
# Re-running it rebuilds the venvs; models already downloaded are kept.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
SKIP_WHISPER=0
SKIP_TRANSLATION=0
SKIP_MODELS=0
for arg in "$@"; do
    case "$arg" in
        --skip-whisper) SKIP_WHISPER=1 ;;
        --skip-translation) SKIP_TRANSLATION=1 ;;
        --skip-models) SKIP_MODELS=1 ;;
        *) echo "unknown option: $arg" >&2; exit 2 ;;
    esac
done
step() { printf '\n\033[36m== %s\033[0m\n' "$1"; }

INTEL=0
if [ "$(uname)" = "Darwin" ] && [ "$(uname -m)" = "x86_64" ]; then
    INTEL=1
    echo "Intel Mac: installing the older tested versions (torch 2.2.2), CPU only."
fi

step 'uv'
if ! command -v uv >/dev/null 2>&1; then
    echo 'uv not found, installing it (astral.sh)...'
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi
uv --version

step 'Chatterbox venv'
CB="$ROOT/Chatterbox"
uv venv --clear --python 3.11 "$CB/venv"
PY="$CB/venv/bin/python"
if [ "$INTEL" = 1 ]; then
    # Full pinned list; --no-deps because chatterbox-tts 0.1.7 declares torch==2.6.0, which Intel Macs cannot get.
    uv pip install --python "$PY" --no-deps -r "$CB/constraints-mac-intel.txt"
else
    # On macOS the PyPI torch build already includes the Apple GPU backend (mps).
    uv pip install --python "$PY" torch==2.6.0 torchaudio==2.6.0
    # setuptools<81: resemble-perth needs pkg_resources, otherwise the model fails with "'NoneType' object is not callable".
    # av (PyAV): decodes .m4a/.mp3 reference recordings, which librosa cannot read without ffmpeg.
    uv pip install --python "$PY" chatterbox-tts==0.1.7 "setuptools<81" av==18.1.0 -c "$CB/constraints.txt"
fi

if [ "$SKIP_WHISPER" = 0 ]; then
    step 'Whisper venv'
    WH="$ROOT/Whisper"
    # No GPU build on a Mac: faster-whisper runs on the CPU (int8).
    if [ "$INTEL" = 1 ]; then
        uv venv --clear --python 3.11 "$WH/venv"
        uv pip install --python "$WH/venv/bin/python" --no-deps -r "$WH/constraints-mac-intel.txt"
    else
        # 3.13 like the Windows install: the pinned numpy 2.5.4 needs Python 3.12+.
        uv venv --clear --python 3.13 "$WH/venv"
        uv pip install --python "$WH/venv/bin/python" faster-whisper==1.2.1 -c "$WH/constraints.txt"
    fi
fi

# Copies from Windows lose the executable bit.
chmod +x "$ROOT"/*.sh "$ROOT"/Chatterbox/*.sh "$ROOT"/Whisper/*.sh

if [ "$SKIP_MODELS" = 0 ]; then
    step 'Models (from Hugging Face)'
    if [ "$SKIP_TRANSLATION" = 1 ]; then
        "$PY" "$CB/download.py" --skip-translation
    else
        "$PY" "$CB/download.py"
    fi
    if [ "$SKIP_WHISPER" = 0 ]; then
        "$ROOT/Whisper/venv/bin/python" "$ROOT/Whisper/transcribe.py" --download
    fi
fi

mkdir -p "$ROOT/voices" "$ROOT/outputs"

step 'Check'
"$PY" -c "import torch; print('torch', torch.__version__, '| Apple GPU (mps):', torch.backends.mps.is_available())"
printf '\n\033[32mDone. Put a 5-15 s recording of a voice in the voices folder, then run ./webui.sh\033[0m\n'
