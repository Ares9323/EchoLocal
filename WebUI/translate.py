"""Local translation with NLLB-200 (facebook/nllb-200-distilled-600M), offline, on the CPU.

The model is downloaded once into WebUI\\models (about 2.4 GB) by Chatterbox\\download.py;
nothing is fetched at run time. It stays on the CPU so the GPU is left to Chatterbox and Whisper.
License of the model: CC-BY-NC 4.0, non-commercial use only.

Text is translated line by line, so the output keeps one sentence per line like the input.
"""
from pathlib import Path

MODEL_ID = "facebook/nllb-200-distilled-600M"
CACHE_DIR = Path(__file__).resolve().parent / "models" / "hub"

# Chatterbox language code -> NLLB (FLORES-200) code.
NLLB_CODES = {
    "ar": "arb_Arab", "da": "dan_Latn", "de": "deu_Latn", "el": "ell_Grek", "en": "eng_Latn",
    "es": "spa_Latn", "fi": "fin_Latn", "fr": "fra_Latn", "he": "heb_Hebr", "hi": "hin_Deva",
    "it": "ita_Latn", "ja": "jpn_Jpan", "ko": "kor_Hang", "ms": "zsm_Latn", "nl": "nld_Latn",
    "no": "nob_Latn", "pl": "pol_Latn", "pt": "por_Latn", "ru": "rus_Cyrl", "sv": "swe_Latn",
    "sw": "swh_Latn", "tr": "tur_Latn", "zh": "zho_Hans",
}


def available():
    """True if the model has been downloaded."""
    return any(CACHE_DIR.glob("models--facebook--nllb-200-distilled-600M/snapshots/*/config.json"))


def download():
    """Fetch the model into WebUI/models (used by Chatterbox/download.py)."""
    from huggingface_hub import snapshot_download

    snapshot_download(MODEL_ID, cache_dir=CACHE_DIR,
                      allow_patterns=["*.json", "*.model", "pytorch_model.bin"])


class Translator:
    """Loaded on first use (a few seconds), then kept in memory."""

    def __init__(self, device="cpu"):
        self.device = device
        self._model = None
        self._tokenizer = None

    def _load(self):
        if self._model is None:
            if not available():
                raise RuntimeError("translation model not downloaded: run setup again without "
                                   "skipping translation, or Chatterbox/download.py")
            from transformers import AutoModelForSeq2SeqLM, NllbTokenizerFast
            from transformers.utils import logging as hf_logging

            hf_logging.disable_progress_bar()

            # The NLLB tokenizer class directly: AutoTokenizer in transformers 5.2 fails on this model
            # type (m2m_100). The fast one reads tokenizer.json, so it also works with transformers
            # 4.46.3 (Intel Mac), where the slow one would need sentencepiece, which is not installed.
            self._tokenizer = NllbTokenizerFast.from_pretrained(MODEL_ID, cache_dir=CACHE_DIR, local_files_only=True)
            self._model = AutoModelForSeq2SeqLM.from_pretrained(
                MODEL_ID, cache_dir=CACHE_DIR, local_files_only=True).to(self.device).eval()

    def translate_lines(self, lines, src, tgt, batch_size=8):
        """Translate a list of sentences from language code src to tgt (Chatterbox codes)."""
        if src == tgt or not lines:
            return list(lines)
        import torch

        self._load()
        tok = self._tokenizer
        tok.src_lang = NLLB_CODES[src]
        target_id = tok.convert_tokens_to_ids(NLLB_CODES[tgt])
        out = []
        for start in range(0, len(lines), batch_size):
            batch = lines[start:start + batch_size]
            enc = tok(batch, return_tensors="pt", padding=True, truncation=True, max_length=512).to(self.device)
            with torch.inference_mode():
                ids = self._model.generate(**enc, forced_bos_token_id=target_id, num_beams=4,
                                           max_new_tokens=int(enc["input_ids"].shape[1] * 2 + 16))
            out += [t.strip() for t in tok.batch_decode(ids, skip_special_tokens=True)]
        return out
