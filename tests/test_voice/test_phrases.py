"""Tests for voice phrase pool and selection."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import src.voice.phrases as phrases_mod
from src.voice.phrases import _reset_cache, get_phrase, pool_size, select_phrases


class TestFileLoading:
    """Tests for loading phrases from a JSON file."""

    def test_loads_from_json_file(self) -> None:
        _reset_cache()
        data = {
            "en": ["Hello world from the test", "Another phrase here today", "A third phrase for testing"],
            "fa": ["سلام از تست", "جمله دوم فارسی", "جمله سوم فارسی"],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f, ensure_ascii=False)
            path = f.name

        mock_settings = MagicMock()
        mock_settings.voice_phrases_file = path
        with patch("src.config.get_settings", return_value=mock_settings):
            result = phrases_mod._load_phrases()

        assert result["en"] == data["en"]
        assert result["fa"] == data["fa"]
        Path(path).unlink()
        _reset_cache()

    def test_missing_file_raises(self) -> None:
        _reset_cache()
        mock_settings = MagicMock()
        mock_settings.voice_phrases_file = "/nonexistent/voice-phrases.json"
        with (
            patch("src.config.get_settings", return_value=mock_settings),
            pytest.raises(FileNotFoundError, match="Voice phrases file not found"),
        ):
            phrases_mod._load_phrases()
        _reset_cache()

    def test_missing_locale_key_raises(self) -> None:
        _reset_cache()
        data = {"en": ["A phrase"]}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name

        mock_settings = MagicMock()
        mock_settings.voice_phrases_file = path
        with (
            patch("src.config.get_settings", return_value=mock_settings),
            pytest.raises(ValueError, match="must contain 'en' and 'fa' keys"),
        ):
            phrases_mod._load_phrases()
        Path(path).unlink()
        _reset_cache()

    def test_too_few_phrases_raises(self) -> None:
        _reset_cache()
        data = {"en": ["Only one"], "fa": ["Only one"]}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name

        mock_settings = MagicMock()
        mock_settings.voice_phrases_file = path
        with (
            patch("src.config.get_settings", return_value=mock_settings),
            pytest.raises(ValueError, match="must have at least 3 phrases"),
        ):
            phrases_mod._load_phrases()
        Path(path).unlink()
        _reset_cache()


class TestPoolSize:
    def test_english_pool_size(self) -> None:
        assert pool_size("en") == 20

    def test_farsi_pool_size(self) -> None:
        assert pool_size("fa") == 20


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
            assert 0 <= pid < pool_size("fa")

    def test_not_enough_phrases_raises(self) -> None:
        with pytest.raises(ValueError, match="Not enough phrases"):
            select_phrases("en", 21)

    def test_exclude_all_raises(self) -> None:
        with pytest.raises(ValueError, match="Not enough phrases"):
            select_phrases("en", 1, exclude_ids=list(range(20)))


class TestGetPhrase:
    def test_valid_english(self) -> None:
        phrase = get_phrase("en", 0)
        assert "Test phrase number 0" in phrase

    def test_valid_farsi(self) -> None:
        phrase = get_phrase("fa", 5)
        assert "5" in phrase

    def test_invalid_id_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid phrase_id"):
            get_phrase("en", -1)

    def test_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid phrase_id"):
            get_phrase("en", 20)
