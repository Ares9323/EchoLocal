#!/usr/bin/env bash
DIR="$(cd "$(dirname "$0")" && pwd)"
# Like speak_all.sh, but one outputs/<lang>.wav per language: lines joined with a short pause.
# Extra arguments go to speak.py, e.g.  ./speak_joined.sh --pause 0.8 --ref voices/my_voice.m4a
set -e
bash "$DIR/Chatterbox/speak.sh" --join "$@"
bash "$DIR/Whisper/check.sh"
