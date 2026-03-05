"""faster-whisper transcription with word-overlap scoring."""

from __future__ import annotations

import logging
import re
import tempfile
from typing import Any, Optional

from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

_model: Any = None

# Persian homophones: letters that sound the same in modern Farsi (from Arabic script).
# Map each to a canonical form for comparison. Sources: LELB Society, Wikipedia Persian phonology.
_FARSI_PHONETIC_MAP: dict[str, str] = {
    # ت (te) and ط (tâ) → /t/
    "\u0637": "\u062A",  # ط → ت
    # س (sin), ص (sâd), ث (se) → /s/
    "\u0635": "\u0633",  # ص → س
    "\u062B": "\u0633",  # ث → س
    # ز (ze), ظ (zâ), ض (zâd), ذ (zâl) → /z/
    "\u0638": "\u0632",  # ظ → ز
    "\u0636": "\u0632",  # ض → ز
    "\u0630": "\u0632",  # ذ → ز
    # ق (qaf) and غ (ghayn) → /ɣ/ (gh)
    "\u0642": "\u063A",  # ق → غ
    # ح (he) and ه (he) → /h/
    "\u062D": "\u0647",  # ح → ه
}


def load_model() -> Any:
    """Load (or return cached) faster-whisper model."""
    global _model
    if _model is None:
        logger.info("Loading faster-whisper model")
        _model = WhisperModel(
            "small",
            device="cpu",
            compute_type="int8",
        )
        logger.info("faster-whisper model loaded")
    return _model


def _normalize_text(text: str) -> list[str]:
    """Lowercase, strip punctuation, split into words."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    return text.split()


def _strip_punctuation(text: str) -> str:
    """Remove all punctuation from text; collapse multiple spaces to one."""
    text = re.sub(r"[^\w\s]", "", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def _normalize_farsi_phonetic(word: str) -> str:
    """Map Farsi word to canonical form using homophone equivalence (for comparison only)."""
    return "".join(_FARSI_PHONETIC_MAP.get(c, c) for c in word)


def _farsi_word_similarity(expected_word: str, trans_word: str) -> float:
    """Score how much of expected word appears in order in trans word (Farsi).

    Uses subsequence match: expected letters must appear in transcription in the same
    order; extra letters in transcription are allowed. Homophone letters count as match.
    Returns fraction of expected word length matched, in [0, 1].
    """
    if not expected_word:
        return 1.0
    e = _normalize_farsi_phonetic(expected_word)
    t = _normalize_farsi_phonetic(trans_word)
    if not e:
        return 1.0
    # Subsequence: how many chars of e appear in order in t
    i, j, matched = 0, 0, 0
    while i < len(e) and j < len(t):
        if e[i] == t[j]:
            matched += 1
            i += 1
        j += 1
    return matched / len(e)


def _strip_farsi_word(w: str) -> str:
    """Remove punctuation and zero-width chars; keep letters (Perso-Arabic and Latin)."""
    if not w:
        return ""
    # Remove whitespace, ZWJ/ZWNJ, and punctuation (keeps letters/digits)
    return re.sub(r"[\s\u200c\u200d\W]", "", w, flags=re.UNICODE)


def _farsi_phrase_score(transcription: str, expected: str) -> float:
    """Score expected phrase against transcription using Farsi per-word similarity.

    For each expected word, take the best matching transcribed word (subsequence + homophones),
    then average. Words are split on whitespace; punctuation stripped per word.
    """
    trans_words = [_strip_farsi_word(w) for w in transcription.split() if w.strip()]
    expected_words = [_strip_farsi_word(w) for w in expected.split() if w.strip()]
    trans_words = [w for w in trans_words if w]
    expected_words = [w for w in expected_words if w]
    if not expected_words:
        return 1.0
    if not trans_words:
        return 0.0
    scores = []
    for exp in expected_words:
        best = max(
            (_farsi_word_similarity(exp, tw) for tw in trans_words),
            default=0.0,
        )
        scores.append(best)
    return sum(scores) / len(scores)


def word_overlap_score(transcription: str, expected: str) -> float:
    """Compute word overlap score between transcription and expected phrase.

    Returns a float in [0, 1] representing the fraction of expected words
    found in the transcription.
    """
    trans_words = set(_normalize_text(transcription))
    expected_words = _normalize_text(expected)

    if not expected_words:
        return 1.0

    matches = sum(1 for w in expected_words if w in trans_words)
    return matches / len(expected_words)


def transcribe_audio(
    wav_bytes: bytes, expected_phrase: str, language: Optional[str] = None
) -> tuple[str, float]:
    """Transcribe audio and score against expected phrase.

    If language is set (e.g. 'en', 'fa'), faster-whisper uses it for transcription;
    otherwise it auto-detects. Passing language improves accuracy for short clips.
    Returns (transcription_text, overlap_score).
    """
    model = load_model()

    if language is not None:
        language = language.strip().lower() or None

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
        tmp.write(wav_bytes)
        tmp.flush()
        segments, _info = model.transcribe(tmp.name, language=language, beam_size=5, vad_filter=True)
        segments = list(segments)

    raw = " ".join(s.text for s in segments).strip()
    transcription = _strip_punctuation(raw)

    if language == "fa":
        score = _farsi_phrase_score(transcription, expected_phrase)
    else:
        score = word_overlap_score(transcription, expected_phrase)
    return transcription, score
