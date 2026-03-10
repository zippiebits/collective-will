"""Tests for voice embedding encryption."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from cryptography.fernet import Fernet

from src.voice.crypto import decrypt_embedding, encrypt_embedding
from src.voice.scoring import deserialize_embedding, serialize_embedding


def _mock_settings(key: str | None = None) -> MagicMock:
    s = MagicMock()
    s.voice_encryption_key = key
    return s


class TestEncryptDecryptRoundTrip:
    def test_round_trip_with_key(self) -> None:
        key = Fernet.generate_key().decode()
        raw = serialize_embedding([0.1] * 192)

        with patch("src.voice.crypto.get_settings", return_value=_mock_settings(key)):
            encrypted = encrypt_embedding(raw)
            assert encrypted != raw
            decrypted = decrypt_embedding(encrypted)
            assert decrypted == raw

    def test_embedding_values_preserved(self) -> None:
        key = Fernet.generate_key().decode()
        original = [float(i) / 192 for i in range(192)]
        raw = serialize_embedding(original)

        with patch("src.voice.crypto.get_settings", return_value=_mock_settings(key)):
            encrypted = encrypt_embedding(raw)
            decrypted = decrypt_embedding(encrypted)
            restored = deserialize_embedding(decrypted)
            assert len(restored) == 192
            for a, b in zip(original, restored, strict=True):
                assert abs(a - b) < 1e-6

    def test_no_key_passthrough(self) -> None:
        raw = serialize_embedding([1.0] * 192)

        with patch("src.voice.crypto.get_settings", return_value=_mock_settings(None)):
            encrypted = encrypt_embedding(raw)
            assert encrypted == raw
            decrypted = decrypt_embedding(encrypted)
            assert decrypted == raw

    def test_decrypt_legacy_unencrypted(self) -> None:
        """When key is set but data is raw binary (legacy), decrypt returns it as-is."""
        key = Fernet.generate_key().decode()
        raw = serialize_embedding([0.5] * 192)

        with patch("src.voice.crypto.get_settings", return_value=_mock_settings(key)):
            decrypted = decrypt_embedding(raw)
            assert decrypted == raw

    def test_different_keys_cannot_decrypt(self) -> None:
        key1 = Fernet.generate_key().decode()
        key2 = Fernet.generate_key().decode()
        raw = serialize_embedding([1.0] * 192)

        with patch("src.voice.crypto.get_settings", return_value=_mock_settings(key1)):
            encrypted = encrypt_embedding(raw)

        # With a different key, should fall back to raw (legacy path)
        with patch("src.voice.crypto.get_settings", return_value=_mock_settings(key2)):
            result = decrypt_embedding(encrypted)
            # Since decryption fails with wrong key, it returns encrypted blob as-is (legacy path)
            assert result == encrypted
