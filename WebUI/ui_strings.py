"""Interface strings, one dictionary per language (key -> text).

Static labels go through gr.I18n (translated in the browser from its language); messages built
at run time (errors, progress, results) go through t(locale, key), with the locale read from the
browser's Accept-Language header. English is the fallback for a missing language or key.

To add a language: copy the "en" dictionary under its code (e.g. "de") and translate the values,
keeping the {placeholders}.
"""
import gradio as gr

STRINGS = {
    "en": {
        "title": "## EchoLocal\nVoice cloning, translation and transcription, all on this computer: nothing leaves it.",
        "tab_tts": "Text to speech",
        "tab_stt": "Speech to text",
        "voice": "Voice (files in the voices folder)",
        "refresh": "Refresh voice list",
        "voice_sample": "Voice sample",
        "no_voices": "**No voices yet.** Put a clean 5-15 s recording of the voice to clone in the `voices` "
                     "folder (wav, m4a, mp3, flac, ogg; the file name is the voice name), then click "
                     "*Refresh voice list*. Only clone voices you have permission to use.",
        "src_lang": "Language of the text",
        "out_langs": "Output languages",
        "text": "Text, one sentence per line",
        "translate": "Translate",
        "translate_off": "Translation model not installed: write the text of each language yourself, "
                         "or run setup again without skipping translation.",
        "translation_box": "Translation, editable",
        "options": "Options",
        "output": "Output",
        "mode_joined": "One file per language",
        "mode_clips": "One clip per line",
        "pause": "Pause between lines (s), one file mode",
        "expressiveness": "Expressiveness",
        "pace": "Pace (lower is slower)",
        "job_title": "Title",
        "job_title_info": "Names the output: outputs/<title>/<title>_en.wav, <title>_es.wav, ... "
                          "Empty: the voice name.",
        "voice_in_name": "Add the voice name to the file names (<title>_<voice>_en.wav)",
        "translate_status": "Translating to {lang} ({i}/{n})...",
        "translate_done": "Translation done: read the boxes and fix them if needed before generating.",
        "box_translating": "Translating...",
        "box_waiting": "Waiting for its turn...",
        "card_waiting": "Waiting",
        "card_working": "Generating...",
        "card_checking": "Checking with Whisper...",
        "check": "Check with Whisper afterwards",
        "generate": "Generate",
        "download": "Download",
        "stt_audio": "Audio: upload a file or record",
        "stt_lang": "Language",
        "auto": "Detect automatically",
        "transcribe": "Transcribe",
        "transcript": "Transcript",
        "stt_files": "Files (.txt, .srt subtitles)",
        "use_text": "Use as text to speak",
        "err_no_text": "Write the text first, one sentence per line.",
        "err_no_targets": "Tick at least one output language.",
        "err_no_voice": "Pick a voice first (put a recording in the voices folder, then Refresh).",
        "err_voice_missing": "Voice not found in the voices folder: {name}",
        "err_translation": "The translation model is not installed: fill in every language box, "
                           "or run setup again without skipping translation.",
        "err_whisper_venv": "Whisper is not installed ({path}): run setup without skipping it, or untick the check.",
        "err_check": "Whisper check failed: {tail}",
        "err_no_audio": "Upload or record some audio first.",
        "err_transcribe": "Transcription failed: {tail}",
        "prog_translating": "Translating to {lang}",
        "prog_line": "{lang}: line {i}/{n}",
        "prog_check": "Checking with Whisper",
        "prog_transcribing": "Transcribing with Whisper",
        "done": "Done. Languages: {langs}, lines: {lines}, in `{folder}`.",
        "chk_match": "**Whisper: match**",
        "chk_missing": "**Whisper: file missing**",
        "chk_diff": "**Whisper: {ratio}**. Listen to: {spans}",
        "chk_span": "expected *{expected}*, heard *{heard}*",
        "nothing": "(nothing)",
        "detected": "Language: {lang}, duration {duration:.1f} s. Saved in `{folder}`.",
    },
    "it": {
        "title": "## EchoLocal\nClonazione della voce, traduzione e trascrizione, tutto su questo computer: "
                 "non esce niente.",
        "tab_tts": "Da testo a voce",
        "tab_stt": "Da voce a testo",
        "voice": "Voce (file nella cartella voices)",
        "refresh": "Aggiorna l'elenco delle voci",
        "voice_sample": "Campione della voce",
        "no_voices": "**Nessuna voce.** Metti nella cartella `voices` una registrazione pulita di 5-15 s "
                     "della voce da clonare (wav, m4a, mp3, flac, ogg; il nome del file è il nome della voce), "
                     "poi premi *Aggiorna l'elenco delle voci*. Clona solo voci che hai il permesso di usare.",
        "src_lang": "Lingua del testo",
        "out_langs": "Lingue di uscita",
        "text": "Testo, una frase per riga",
        "translate": "Traduci",
        "translate_off": "Modello di traduzione non installato: scrivi tu il testo di ogni lingua, "
                         "oppure rilancia il setup senza saltare la traduzione.",
        "translation_box": "Traduzione, modificabile",
        "options": "Opzioni",
        "output": "Uscita",
        "mode_joined": "Un file per lingua",
        "mode_clips": "Una clip per riga",
        "pause": "Pausa tra le righe (s), modalità un file",
        "expressiveness": "Espressività",
        "pace": "Ritmo (più basso è più lento)",
        "job_title": "Titolo",
        "job_title_info": "Dà il nome all'uscita: outputs/<titolo>/<titolo>_en.wav, <titolo>_es.wav, ... "
                          "Vuoto: il nome della voce.",
        "voice_in_name": "Aggiungi il nome della voce ai file (<titolo>_<voce>_en.wav)",
        "translate_status": "Traduzione in {lang} ({i}/{n})...",
        "translate_done": "Traduzione finita: rileggi i riquadri e correggili se serve prima di generare.",
        "box_translating": "Traduzione in corso...",
        "box_waiting": "In attesa del suo turno...",
        "card_waiting": "In attesa",
        "card_working": "Generazione in corso...",
        "card_checking": "Controllo con Whisper...",
        "check": "Controlla con Whisper alla fine",
        "generate": "Genera",
        "download": "Scarica",
        "stt_audio": "Audio: carica un file o registra",
        "stt_lang": "Lingua",
        "auto": "Riconosci in automatico",
        "transcribe": "Trascrivi",
        "transcript": "Trascrizione",
        "stt_files": "File (.txt, sottotitoli .srt)",
        "use_text": "Usa come testo da leggere",
        "err_no_text": "Scrivi prima il testo, una frase per riga.",
        "err_no_targets": "Spunta almeno una lingua di uscita.",
        "err_no_voice": "Scegli prima una voce (metti una registrazione nella cartella voices, poi Aggiorna).",
        "err_voice_missing": "Voce non trovata nella cartella voices: {name}",
        "err_translation": "Il modello di traduzione non è installato: compila tutti i riquadri delle lingue, "
                           "oppure rilancia il setup senza saltare la traduzione.",
        "err_whisper_venv": "Whisper non è installato ({path}): rilancia il setup senza saltarlo, "
                            "oppure togli la spunta al controllo.",
        "err_check": "Controllo di Whisper fallito: {tail}",
        "err_no_audio": "Carica o registra prima un audio.",
        "err_transcribe": "Trascrizione fallita: {tail}",
        "prog_translating": "Traduzione in {lang}",
        "prog_line": "{lang}: riga {i}/{n}",
        "prog_check": "Controllo con Whisper",
        "prog_transcribing": "Trascrizione con Whisper",
        "done": "Fatto. Lingue: {langs}, righe: {lines}, in `{folder}`.",
        "chk_match": "**Whisper: corrisponde**",
        "chk_missing": "**Whisper: file mancante**",
        "chk_diff": "**Whisper: {ratio}**. Da ascoltare: {spans}",
        "chk_span": "atteso *{expected}*, sentito *{heard}*",
        "nothing": "(niente)",
        "detected": "Lingua: {lang}, durata {duration:.1f} s. Salvato in `{folder}`.",
    },
}

I18N = gr.I18n(**STRINGS)


def label(key):
    """A static label, translated in the browser."""
    return I18N(key)


def locale_of(request):
    """The first supported language in the browser's Accept-Language header, else English."""
    header = ""
    if request is not None:
        header = request.headers.get("accept-language", "") or ""
    for part in header.split(","):
        code = part.split(";")[0].strip().lower().split("-")[0]
        if code in STRINGS:
            return code
    return "en"


def t(locale, key, **values):
    """A run-time message in the given language (English if missing)."""
    text = STRINGS.get(locale, {}).get(key) or STRINGS["en"][key]
    return text.format(**values) if values else text
