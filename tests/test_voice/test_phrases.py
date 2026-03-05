"""Tests for voice phrase pool and selection."""

from __future__ import annotations

import pytest

from src.voice.phrases import PHRASES_EN, PHRASES_FA, get_phrase, select_phrases


class TestPhrasePools:
    def test_english_pool_size(self) -> None:
        assert len(PHRASES_EN) == 100

    def test_farsi_pool_size(self) -> None:
        assert len(PHRASES_FA) == 100

    def test_no_empty_phrases(self) -> None:
        for phrase in PHRASES_EN:
            assert len(phrase.strip()) > 0
        for phrase in PHRASES_FA:
            assert len(phrase.strip()) > 0

    def test_no_duplicate_english(self) -> None:
        assert len(set(PHRASES_EN)) == len(PHRASES_EN)

    def test_no_duplicate_farsi(self) -> None:
        assert len(set(PHRASES_FA)) == len(PHRASES_FA)


class TestSelectPhrases:
    def test_select_correct_count(self) -> None:
        ids = select_phrases("en", 3)
        assert len(ids) == 3

    def test_no_duplicates(self) -> None:
        ids = select_phrases("en", 10)
        assert len(set(ids)) == 10

    def test_exclude_ids(self) -> None:
        excluded = [0, 1, 2]
        ids = select_phrases("en", 3, exclude_ids=excluded)
        for eid in excluded:
            assert eid not in ids

    def test_farsi_locale(self) -> None:
        ids = select_phrases("fa", 3)
        assert len(ids) == 3
        for pid in ids:
            assert 0 <= pid < len(PHRASES_FA)

    def test_not_enough_phrases_raises(self) -> None:
        with pytest.raises(ValueError, match="Not enough phrases"):
            select_phrases("en", 101)

    def test_exclude_all_raises(self) -> None:
        with pytest.raises(ValueError, match="Not enough phrases"):
            select_phrases("en", 1, exclude_ids=list(range(100)))


class TestGetPhrase:
    def test_valid_english(self) -> None:
        phrase = get_phrase("en", 0)
        assert phrase == PHRASES_EN[0]

    def test_valid_farsi(self) -> None:
        phrase = get_phrase("fa", 50)
        assert phrase == PHRASES_FA[50]

    def test_invalid_id_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid phrase_id"):
            get_phrase("en", -1)

    def test_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid phrase_id"):
            get_phrase("en", 100)
