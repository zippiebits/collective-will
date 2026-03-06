"""Transcription scoring: word-overlap (English) and subsequence + homophone (Farsi).

Ported from voice-service/app/transcribe.py to run in the backend.
"""

from __future__ import annotations

import re

# Persian homophones: letters that sound the same in modern Farsi.
# Map each to a canonical form for comparison.
_FARSI_PHONETIC_MAP: dict[str, str] = {
    "\u0637": "\u062A",  # ط → ت (te)
    "\u0635": "\u0633",  # ص → س (sin)
    "\u062B": "\u0633",  # ث → س (sin)
    "\u0638": "\u0632",  # ظ → ز (ze)
    "\u0636": "\u0632",  # ض → ز (ze)
    "\u0630": "\u0632",  # ذ → ز (ze)
    "\u0642": "\u063A",  # ق → غ (ghayn)
    "\u062D": "\u0647",  # ح → ه (he)
}


def _normalize_text(text: str) -> list[str]:
    """Lowercase, strip punctuation, split into words."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    return text.split()


def _strip_punctuation(text: str) -> str:
    """Remove all punctuation; collapse whitespace."""
    text = re.sub(r"[^\w\s]", "", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def _normalize_farsi_phonetic(word: str) -> str:
    """Map Farsi word to canonical form using homophone equivalence."""
    return "".join(_FARSI_PHONETIC_MAP.get(c, c) for c in word)


def _farsi_word_similarity(expected_word: str, trans_word: str) -> float:
    """Score how much of expected word appears in order in trans word (Farsi).

    Uses subsequence match with homophone normalization.
    Returns fraction of expected word length matched, in [0, 1].
    """
    if not expected_word:
        return 1.0
    e = _normalize_farsi_phonetic(expected_word)
    t = _normalize_farsi_phonetic(trans_word)
    if not e:
        return 1.0
    i, j, matched = 0, 0, 0
    while i < len(e) and j < len(t):
        if e[i] == t[j]:
            matched += 1
            i += 1
        j += 1
    return matched / len(e)


def _strip_farsi_word(w: str) -> str:
    """Remove punctuation and zero-width chars; keep letters."""
    if not w:
        return ""
    return re.sub(r"[\s\u200c\u200d\W]", "", w, flags=re.UNICODE)


def farsi_phrase_score(transcription: str, expected: str) -> float:
    """Score expected phrase against transcription using Farsi per-word similarity.

    For each expected word, take the best matching transcribed word,
    then average. Words split on whitespace; punctuation stripped per word.
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
    """Fraction of expected words found in the transcription."""
    trans_words = set(_normalize_text(transcription))
    expected_words = _normalize_text(expected)
    if not expected_words:
        return 1.0
    matches = sum(1 for w in expected_words if w in trans_words)
    return matches / len(expected_words)


def score_transcription(transcription: str, expected_phrase: str, language: str) -> float:
    """Score a transcription against expected phrase, using language-appropriate method."""
    clean = _strip_punctuation(transcription)
    if language == "fa":
        return farsi_phrase_score(clean, expected_phrase)
    return word_overlap_score(clean, expected_phrase)
