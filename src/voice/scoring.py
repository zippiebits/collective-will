"""Voice verification scoring: cosine similarity, decision matrix, embedding utils."""

from __future__ import annotations

import struct
from typing import Literal

import numpy as np

# 192-dim ECAPA-TDNN embedding → 192 * 4 bytes = 768 bytes
EMBEDDING_DIM = 192
EMBEDDING_BYTES = EMBEDDING_DIM * 4  # float32


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two embedding vectors."""
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    dot = float(np.dot(va, vb))
    norm_a = float(np.linalg.norm(va))
    norm_b = float(np.linalg.norm(vb))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def serialize_embedding(embedding: list[float]) -> bytes:
    """Pack a float32 embedding list into raw bytes for DB storage."""
    return struct.pack(f"<{len(embedding)}f", *embedding)


def deserialize_embedding(data: bytes) -> list[float]:
    """Unpack raw bytes back into a float32 embedding list."""
    count = len(data) // 4
    return list(struct.unpack(f"<{count}f", data))


def average_embeddings(embeddings: list[list[float]]) -> list[float]:
    """Compute the element-wise mean of multiple embedding vectors."""
    arr = np.array(embeddings, dtype=np.float32)
    mean = arr.mean(axis=0)
    return list(mean.tolist())


def voice_decision(
    embedding_similarity: float,
    transcription_score: float,
    sim_high: float,
    sim_moderate: float,
    trans_standard: float,
    trans_strict: float,
) -> Literal["accept", "reject"]:
    """Apply the dual-verification decision matrix.

    - High similarity (>= sim_high) + transcription >= trans_standard → accept
    - Moderate similarity (>= sim_moderate) + transcription >= trans_strict → accept
    - Otherwise → reject
    """
    if embedding_similarity >= sim_high and transcription_score >= trans_standard:
        return "accept"
    if embedding_similarity >= sim_moderate and transcription_score >= trans_strict:
        return "accept"
    return "reject"
