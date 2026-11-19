#!/usr/bin/env bash
DIR="$(cd "$(dirname "$0")" && pwd)"
# Every texts/<lang>.txt -> outputs/<lang>/001.wav, ... with the same voice, then a Whisper check.
# Extra arguments go to speak.py, e.g.  ./speak_all.sh --ref voices/my_voice.m4a --exaggeration 0.7
set -e
bash "$DIR/Chatterbox/speak.sh" "$@"
bash "$DIR/Whisper/check.sh"
