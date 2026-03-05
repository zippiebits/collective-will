"""Tests for Farsi transcription scoring: subsequence match + homophone equivalence."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Allow importing app when run from voice-service root: PYTHONPATH=app pytest tests/
APP = Path(__file__).resolve().parent.parent / "app"
if str(APP.parent) not in sys.path:
    sys.path.insert(0, str(APP.parent))

from app.transcribe import _farsi_phrase_score, _farsi_word_similarity


class TestFarsiWordSimilarity:
    """Per-word subsequence + homophone scoring."""

    def test_exact_match(self) -> None:
        assert _farsi_word_similarity("لطفا", "لطفا") == 1.0
        assert _farsi_word_similarity("بزن", "بزن") == 1.0

    def test_partial_match_bza_vs_bzan(self) -> None:
        # بزن (b-z-n) vs بزا (b-z-a): ب and ز match in order, ن vs ا no match → 2/3
        assert _farsi_word_similarity("بزن", "بزا") == pytest.approx(2 / 3, abs=0.01)

    def test_homophone_t_and_t(self) -> None:
        # لطفا (l-t-f-a) vs لوتفن (l-o-t-f-n): ط→ت, so expected ل ت ف ا, trans ل و ت ف ن
        # In order: ل, ت, ف match (3); ا vs ن no match. Score 3/4
        assert _farsi_word_similarity("لطفا", "لوتفن") == pytest.approx(3 / 4, abs=0.01)

    def test_extra_letters_in_transcription_allowed(self) -> None:
        # Expected "حرف" (h-r-f), trans "هرش" (h-r-sh). ح→ه: ه ر ف vs ه ر ش. Match ه ر (2), ف≠ش. 2/3
        assert _farsi_word_similarity("حرف", "هرش") == pytest.approx(2 / 3, abs=0.01)

    def test_empty_expected(self) -> None:
        assert _farsi_word_similarity("", "anything") == 1.0

    def test_no_match(self) -> None:
        # No shared letters (کتاب vs مهم)
        assert _farsi_word_similarity("کتاب", "مهم") == 0.0

    def test_subsequence_all_extras(self) -> None:
        # Expected "اب" (a-b), trans "اوبی" (a-o-b-y): both letters in order → 1.0
        assert _farsi_word_similarity("اب", "اوبی") == 1.0


class TestFarsiPhraseScore:
    """Phrase = average of best per-word scores."""

    def test_exact_phrase(self) -> None:
        assert _farsi_phrase_score("لطفا کمی آرام‌تر حرف بزن", "لطفا کمی آرام‌تر حرف بزن") == 1.0

    def test_one_word_wrong_still_partial_credit(self) -> None:
        # لطفا→لوتفن (3/4), بقیه عین: (3/4 + 1 + 1 + 1 + 1) / 5
        expected = "لطفا کمی آرام‌تر حرف بزن"
        trans = "لوتفن کمی آرام‌تر حرف بزن"
        score = _farsi_phrase_score(trans, expected)
        assert score >= 0.85  # first word 0.75, others 1.0

    def test_empty_expected(self) -> None:
        assert _farsi_phrase_score("anything", "") == 1.0

    def test_empty_transcription(self) -> None:
        assert _farsi_phrase_score("", "لطفا") == 0.0
