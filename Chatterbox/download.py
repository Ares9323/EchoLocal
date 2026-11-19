"""Download the models used in the Chatterbox venv, once (setup runs this).

Usage:
    download.py [--skip-translation]

    Chatterbox Multilingual (ResembleAI/chatterbox, about 4 GB)  -> Chatterbox\\models
    NLLB-200 translation (facebook/nllb-200-distilled-600M, 2.4 GB) -> WebUI\\models

Both come straight from Hugging Face. After this, every script runs offline.
Re-running it is safe: files already in place are not downloaded again.
"""
import argparse
import os
import sys
from pathlib import Path

# Must be set before tts (and with it huggingface_hub) is imported: tts only sets it if missing.
os.environ["HF_HUB_OFFLINE"] = "0"

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "WebUI"))

import tts  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Download the Chatterbox and NLLB models")
    parser.add_argument("--skip-translation", action="store_true",
                        help="Skip NLLB-200 (2.4 GB): the web interface then cannot translate")
    args = parser.parse_args()

    print("Chatterbox Multilingual (about 4 GB)...")
    tts.ChatterboxMultilingualTTS.from_pretrained(device="cpu")
    if not args.skip_translation:
        from translate import download as download_nllb

        print("NLLB-200 translation model (about 2.4 GB)...")
        download_nllb()
    print("Models ready.")


if __name__ == "__main__":
    main()
