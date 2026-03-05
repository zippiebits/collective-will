"""Tests for voice scoring: cosine similarity, decision matrix, embedding serialization."""

from __future__ import annotations

import pytest

from src.voice.scoring import (
    average_embeddings,
    cosine_similarity,
    deserialize_embedding,
    serialize_embedding,
    voice_decision,
)


class TestCosineSimilarity:
    def test_identical_vectors(self) -> None:
        v = [1.0, 2.0, 3.0]
        assert cosine_similarity(v, v) == pytest.approx(1.0, abs=1e-6)

    def test_orthogonal_vectors(self) -> None:
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert cosine_similarity(a, b) == pytest.approx(0.0, abs=1e-6)

    def test_opposite_vectors(self) -> None:
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert cosine_similarity(a, b) == pytest.approx(-1.0, abs=1e-6)

    def test_zero_vector(self) -> None:
        a = [0.0, 0.0]
        b = [1.0, 2.0]
        assert cosine_similarity(a, b) == 0.0

    def test_similar_vectors(self) -> None:
        a = [1.0, 2.0, 3.0]
        b = [1.1, 2.1, 3.1]
        sim = cosine_similarity(a, b)
        assert sim > 0.99


class TestEmbeddingSerialization:
    def test_round_trip(self) -> None:
        original = [0.1, 0.2, 0.3, -0.5, 1.0]
        serialized = serialize_embedding(original)
        deserialized = deserialize_embedding(serialized)
        assert len(deserialized) == len(original)
        for a, b in zip(original, deserialized, strict=True):
            assert a == pytest.approx(b, abs=1e-6)

    def test_192_dim(self) -> None:
        """Test with actual ECAPA-TDNN dimension."""
        original = [float(i) / 192 for i in range(192)]
        serialized = serialize_embedding(original)
        assert len(serialized) == 192 * 4  # float32
        deserialized = deserialize_embedding(serialized)
        assert len(deserialized) == 192


class TestAverageEmbeddings:
    def test_single_embedding(self) -> None:
        emb = [1.0, 2.0, 3.0]
        avg = average_embeddings([emb])
        for a, b in zip(avg, emb, strict=True):
            assert a == pytest.approx(b, abs=1e-6)

    def test_two_embeddings(self) -> None:
        a = [1.0, 0.0, 4.0]
        b = [3.0, 2.0, 0.0]
        avg = average_embeddings([a, b])
        assert avg[0] == pytest.approx(2.0, abs=1e-6)
        assert avg[1] == pytest.approx(1.0, abs=1e-6)
        assert avg[2] == pytest.approx(2.0, abs=1e-6)

    def test_three_embeddings(self) -> None:
        embeddings = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]
        avg = average_embeddings(embeddings)
        assert avg[0] == pytest.approx(3.0, abs=1e-6)
        assert avg[1] == pytest.approx(4.0, abs=1e-6)


class TestVoiceDecision:
    """Test the dual-verification decision matrix."""

    # Default thresholds from config
    SIM_HIGH = 0.50
    SIM_MOD = 0.35
    TRANS_STD = 0.70
    TRANS_STRICT = 0.90

    def test_high_sim_standard_trans_accept(self) -> None:
        result = voice_decision(0.60, 0.75, self.SIM_HIGH, self.SIM_MOD, self.TRANS_STD, self.TRANS_STRICT)
        assert result == "accept"

    def test_high_sim_low_trans_reject(self) -> None:
        result = voice_decision(0.60, 0.50, self.SIM_HIGH, self.SIM_MOD, self.TRANS_STD, self.TRANS_STRICT)
        assert result == "reject"

    def test_moderate_sim_strict_trans_accept(self) -> None:
        result = voice_decision(0.40, 0.95, self.SIM_HIGH, self.SIM_MOD, self.TRANS_STD, self.TRANS_STRICT)
        assert result == "accept"

    def test_moderate_sim_standard_trans_reject(self) -> None:
        result = voice_decision(0.40, 0.75, self.SIM_HIGH, self.SIM_MOD, self.TRANS_STD, self.TRANS_STRICT)
        assert result == "reject"

    def test_low_sim_reject(self) -> None:
        result = voice_decision(0.20, 1.0, self.SIM_HIGH, self.SIM_MOD, self.TRANS_STD, self.TRANS_STRICT)
        assert result == "reject"

    def test_boundary_high_sim(self) -> None:
        result = voice_decision(0.50, 0.70, self.SIM_HIGH, self.SIM_MOD, self.TRANS_STD, self.TRANS_STRICT)
        assert result == "accept"

    def test_boundary_moderate_sim(self) -> None:
        result = voice_decision(0.35, 0.90, self.SIM_HIGH, self.SIM_MOD, self.TRANS_STD, self.TRANS_STRICT)
        assert result == "accept"

    def test_just_below_moderate_reject(self) -> None:
        result = voice_decision(0.34, 1.0, self.SIM_HIGH, self.SIM_MOD, self.TRANS_STD, self.TRANS_STRICT)
        assert result == "reject"
