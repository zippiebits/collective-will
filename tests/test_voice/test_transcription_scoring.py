"""Tests for transcription scoring: word-overlap (EN) and subsequence+homophone (FA).

Ported from voice-service/tests/test_transcribe_farsi.py + English scoring tests.
"""

from __future__ import annotations

import pytest

from src.voice.transcription_scoring import (
    _farsi_word_similarity,
    farsi_phrase_score,
    score_transcription,
    word_overlap_score,
)


class TestFarsiWordSimilarity:
    """Per-word subsequence + homophone scoring."""

    def test_exact_match(self) -> None:
        assert _farsi_word_similarity("لطفا", "لطفا") == 1.0
        assert _farsi_word_similarity("بزن", "بزن") == 1.0

    def test_partial_match(self) -> None:
        assert _farsi_word_similarity("بزن", "بزا") == pytest.approx(2 / 3, abs=0.01)

    def test_homophone_t_and_t(self) -> None:
        # لطفا vs لوتفن: ط→ت, match ل ت ف (3/4)
        assert _farsi_word_similarity("لطفا", "لوتفن") == pytest.approx(3 / 4, abs=0.01)

    def test_extra_letters_allowed(self) -> None:
        # حرف vs هرش: ح→ه, match ه ر (2/3)
        assert _farsi_word_similarity("حرف", "هرش") == pytest.approx(2 / 3, abs=0.01)

    def test_empty_expected(self) -> None:
        assert _farsi_word_similarity("", "anything") == 1.0

    def test_no_match(self) -> None:
        assert _farsi_word_similarity("کتاب", "مهم") == 0.0

    def test_subsequence_all_extras(self) -> None:
        # اب vs اوبی: both letters in order → 1.0
        assert _farsi_word_similarity("اب", "اوبی") == 1.0


class TestFarsiPhraseScore:
    """Phrase = average of best per-word scores."""

    def test_exact_phrase(self) -> None:
        assert farsi_phrase_score("لطفا کمی آرام‌تر حرف بزن", "لطفا کمی آرام‌تر حرف بزن") == 1.0

    def test_one_word_wrong(self) -> None:
        expected = "لطفا کمی آرام‌تر حرف بزن"
        trans = "لوتفن کمی آرام‌تر حرف بزن"
        score = farsi_phrase_score(trans, expected)
        assert score >= 0.85

    def test_empty_expected(self) -> None:
        assert farsi_phrase_score("anything", "") == 1.0

    def test_empty_transcription(self) -> None:
        assert farsi_phrase_score("", "لطفا") == 0.0


class TestWordOverlapScore:
    def test_exact_match(self) -> None:
        assert word_overlap_score("hello world", "hello world") == 1.0

    def test_partial_match(self) -> None:
        assert word_overlap_score("hello there", "hello world") == 0.5

    def test_no_match(self) -> None:
        assert word_overlap_score("foo bar", "hello world") == 0.0

    def test_empty_expected(self) -> None:
        assert word_overlap_score("anything", "") == 1.0

    def test_extra_words_in_transcription(self) -> None:
        assert word_overlap_score("well hello beautiful world today", "hello world") == 1.0

    def test_case_insensitive(self) -> None:
        assert word_overlap_score("Hello World", "hello world") == 1.0


class TestScoreTranscription:
    def test_english_uses_word_overlap(self) -> None:
        score = score_transcription("hello world", "hello world", "en")
        assert score == 1.0

    def test_farsi_uses_phrase_score(self) -> None:
        score = score_transcription("لطفا کمی آرام‌تر حرف بزن", "لطفا کمی آرام‌تر حرف بزن", "fa")
        assert score == 1.0
