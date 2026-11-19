# Third-party components

EchoLocal's own code is under the PolyForm Noncommercial License 1.0.0 (see [LICENSE.md](LICENSE.md)).
It does not include or redistribute any model: setup downloads them from Hugging Face, and each
keeps its own license. The Python packages are installed from PyPI and the PyTorch index.

## Models

| Model | Used for | Author | License |
|---|---|---|---|
| [ResembleAI/chatterbox](https://huggingface.co/ResembleAI/chatterbox) (multilingual) | Voice cloning, text to speech | Resemble AI | MIT |
| [mobiuslabsgmbh/faster-whisper-large-v3-turbo](https://huggingface.co/mobiuslabsgmbh/faster-whisper-large-v3-turbo) | Speech to text, the check | Mobius Labs (conversion of OpenAI Whisper large-v3-turbo) | MIT |
| [facebook/nllb-200-distilled-600M](https://huggingface.co/facebook/nllb-200-distilled-600M) | Translation (optional) | Meta | **CC-BY-NC 4.0: non-commercial use only** |

## Main Python packages

| Package | Author | License |
|---|---|---|
| [chatterbox-tts](https://github.com/resemble-ai/chatterbox) | Resemble AI | MIT |
| [resemble-perth](https://github.com/resemble-ai/Perth) (audio watermark) | Resemble AI | MIT |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | SYSTRAN | MIT |
| [CTranslate2](https://github.com/OpenNMT/CTranslate2) | OpenNMT | MIT |
| [Gradio](https://github.com/gradio-app/gradio) | Hugging Face | Apache 2.0 |
| [Transformers](https://github.com/huggingface/transformers) | Hugging Face | Apache 2.0 |
| [PyTorch](https://github.com/pytorch/pytorch) | PyTorch Foundation | BSD-3-Clause |
| [PyAV](https://github.com/PyAV-Org/PyAV) | PyAV contributors | BSD-3-Clause |
| [librosa](https://github.com/librosa/librosa) | librosa developers | ISC |

Each package installs further dependencies with their own licenses; the exact versions are listed
in `Chatterbox/constraints.txt` and `Whisper/constraints.txt`.
