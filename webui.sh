#!/usr/bin/env bash
# Web interface: pick a voice from voices/, write or translate the text, generate, listen. Opens http://127.0.0.1:7860
DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$DIR/Chatterbox/venv/bin/python" "$DIR/WebUI/app.py" "$@"
