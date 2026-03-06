#!/usr/bin/env python3
"""End-to-end test for cloud voice pipeline: OpenAI transcription + Modal embedding.

Sends the same real .ogg fixtures used by test-voice-transcription.py to:
  1. OpenAI GPT-4o-transcribe for transcription + local scoring
  2. Modal ECAPA2 endpoint for speaker embeddings + similarity checks

This is the cloud equivalent of test-voice-transcription.py (which targeted local voice-service).

Usage:
    # Requires OPENAI_API_KEY in env (or .env.secrets) and a deployed Modal endpoint.
    uv run python scripts/test-voice-cloud.py --url https://khatami-mehrdad--collective-will-voice-process.modal.run

    # Or use the dev URL from `modal run`:
    uv run python scripts/test-voice-cloud.py --url https://khatami-mehrdad--collective-will-voice-process-dev.modal.run
"""

from __future__ import annotations

import argparse
import base64
import json
import math
import os
import re
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import httpx

FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "voice-samples"

# Unified transcription threshold (GPT-4o-transcribe scores ~1.0 for both EN and FA)
TRANSCRIPTION_THRESHOLD = 0.70

# Unified embedding thresholds (ECAPA2: same-speaker min ~0.57, cross-speaker max ~0.31)
SAME_SPEAKER_THRESHOLD = 0.45
CROSS_SPEAKER_MAX_THRESHOLD = 0.40

# Farsi homophone equivalence map (same as transcription_scoring.py)
_FARSI_HOMOPHONES: dict[str, str] = {
    "\u0637": "\u062a",  # ط → ت
    "\u0635": "\u0633",  # ص → س
    "\u062b": "\u0633",  # ث → س
    "\u0638": "\u0632",  # ظ → ز
    "\u0636": "\u0632",  # ض → ز
    "\u0630": "\u0632",  # ذ → ز
    "\u063a": "\u0642",  # غ → ق
    "\u062d": "\u0647",  # ح → ه
}


def _normalize_farsi(text: str) -> str:
    out: list[str] = []
    for ch in text:
        out.append(_FARSI_HOMOPHONES.get(ch, ch))
    return "".join(out)


def _strip_punctuation(text: str) -> str:
    text = re.sub(r"[^\w\s]", "", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def word_overlap_score(expected: str, actual: str) -> float:
    exp = _strip_punctuation(expected).lower().split()
    act = set(_strip_punctuation(actual).lower().split())
    if not exp:
        return 0.0
    return sum(1 for w in exp if w in act) / len(exp)


def _farsi_word_similarity(expected_word: str, transcribed_word: str) -> float:
    exp = _normalize_farsi(expected_word)
    trans = _normalize_farsi(transcribed_word)
    if not exp:
        return 0.0
    j = 0
    for ch in trans:
        if j < len(exp) and ch == exp[j]:
            j += 1
    return j / len(exp)


def farsi_phrase_score(expected: str, actual: str) -> float:
    exp_words = _strip_punctuation(expected).split()
    act_words = _strip_punctuation(actual).split()
    if not exp_words:
        return 0.0
    if not act_words:
        return 0.0
    scores: list[float] = []
    for ew in exp_words:
        best = max(_farsi_word_similarity(ew, aw) for aw in act_words)
        scores.append(best)
    return sum(scores) / len(scores)


def score_transcription(transcription: str, expected: str, language: str) -> float:
    if language.strip().lower() == "fa":
        return farsi_phrase_score(expected, transcription)
    return word_overlap_score(expected, transcription)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def same_speaker_threshold(_locale_a: str, _locale_b: str) -> float:
    return SAME_SPEAKER_THRESHOLD


def transcribe_openai(audio_bytes: bytes, language: str, api_key: str, timeout: int) -> str:
    """Call OpenAI GPT-4o-transcribe API."""
    resp = httpx.post(
        "https://api.openai.com/v1/audio/transcriptions",
        headers={"Authorization": f"Bearer {api_key}"},
        files={"file": ("audio.ogg", audio_bytes, "audio/ogg")},
        data={"model": "gpt-4o-transcribe", "language": language},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()["text"]


def get_embedding_modal(audio_bytes: bytes, modal_url: str, timeout: int) -> tuple[list[float], str]:
    """Call Modal ECAPA2 endpoint."""
    audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
    resp = httpx.post(
        modal_url,
        json={"audio_b64": audio_b64},
        timeout=timeout,
    )
    resp.raise_for_status()
    result = resp.json()
    return result["embedding"], result.get("model_version", "?")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="End-to-end cloud voice test: OpenAI transcription + Modal embedding"
    )
    parser.add_argument(
        "--url",
        required=True,
        help="Modal embedding endpoint URL",
    )
    parser.add_argument("--timeout", type=int, default=60, help="Request timeout per call (default 60s)")
    args = parser.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        # Try loading from .env.secrets
        secrets_path = Path(__file__).resolve().parent.parent / ".env.secrets"
        if secrets_path.exists():
            for line in secrets_path.read_text().splitlines():
                line = line.strip()
                if line.startswith("OPENAI_API_KEY="):
                    api_key = line.split("=", 1)[1].strip()
                    break
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found in env or .env.secrets")
        sys.exit(1)

    manifest_path = FIXTURES / "manifest.json"
    if not manifest_path.exists():
        print(f"ERROR: {manifest_path} not found")
        sys.exit(1)

    with open(manifest_path) as f:
        manifest = json.load(f)

    modal_url = args.url.rstrip("/")
    print(f"Modal endpoint:  {modal_url}")
    print(f"OpenAI model:    gpt-4o-transcribe")
    print(f"Fixtures:        {FIXTURES} ({len(manifest['samples'])} samples)")

    # ── Part 1: Transcription (OpenAI) + Embedding (Modal) ──
    print(f"\n{'='*70}")
    print(f"PART 1: Transcription + Embedding ({len(manifest['samples'])} samples)")
    print(f"{'='*70}\n")

    transcription_passed = 0
    transcription_failed = 0
    embeddings: dict[str, list[float]] = {}
    file_to_speaker: dict[str, str] = {}
    file_to_locale: dict[str, str] = {}

    for sample in manifest["samples"]:
        audio_path = FIXTURES / sample["file"]
        if not audio_path.exists():
            print(f"SKIP {sample['file']}: file not found")
            continue

        audio_bytes = audio_path.read_bytes()
        expected = sample["expected_phrase"]
        locale = sample["locale"]

        print(f"--- {sample['file']} ({locale}, {sample['speaker']}) ---")
        print(f"  Expected: {expected}")

        # Transcription via OpenAI
        try:
            transcription = transcribe_openai(audio_bytes, locale, api_key, args.timeout)
            score = score_transcription(transcription, expected, locale)

            print(f"  Got:      {transcription}")
            print(f"  Score:    {score:.3f}")

            trans_thresh = TRANSCRIPTION_THRESHOLD
            if score >= trans_thresh:
                print(f"  Trans:    PASS")
                transcription_passed += 1
            else:
                print(f"  Trans:    FAIL (score {score:.3f} < {trans_thresh})")
                transcription_failed += 1
        except Exception as e:
            print(f"  Trans ERROR: {e}")
            transcription_failed += 1

        # Embedding via Modal
        try:
            embedding, model = get_embedding_modal(audio_bytes, modal_url, args.timeout)
            embeddings[sample["file"]] = embedding
            file_to_speaker[sample["file"]] = sample["speaker"]
            file_to_locale[sample["file"]] = locale
            print(f"  Embed:    {len(embedding)}-dim, model: {model}")
        except Exception as e:
            print(f"  Embed ERROR: {e}")

        print()

    # ── Part 2: Same-speaker embedding similarity ──
    print(f"{'='*70}")
    print("PART 2: Same-speaker embedding similarity")
    print(f"  Unified threshold >= {SAME_SPEAKER_THRESHOLD}")
    print(f"{'='*70}\n")

    same_passed = 0
    same_failed = 0
    same_sims: list[float] = []

    by_speaker: dict[str, list[str]] = defaultdict(list)
    for fname, spk in file_to_speaker.items():
        by_speaker[spk].append(fname)

    for spk in sorted(by_speaker):
        files = sorted(by_speaker[spk])
        print(f"  Speaker {spk} ({len(files)} samples):")
        for fa, fb in combinations(files, 2):
            sim = cosine_similarity(embeddings[fa], embeddings[fb])
            same_sims.append(sim)
            loc_a = file_to_locale.get(fa, "en")
            loc_b = file_to_locale.get(fb, "en")
            thresh = same_speaker_threshold(loc_a, loc_b)
            pair_label = "-".join(sorted([loc_a, loc_b]))
            ok = sim >= thresh
            if ok:
                same_passed += 1
            else:
                same_failed += 1
            print(f"    {fa} <-> {fb}: {sim:.4f}  ({pair_label} >= {thresh})  [{'PASS' if ok else 'FAIL'}]")
        print()

    if same_sims:
        avg = sum(same_sims) / len(same_sims)
        print(f"  Same-speaker: avg={avg:.4f}, min={min(same_sims):.4f}, max={max(same_sims):.4f}\n")

    # ── Part 3: Cross-speaker distinction ──
    print(f"{'='*70}")
    print(f"PART 3: Cross-speaker distinction (expect < {CROSS_SPEAKER_MAX_THRESHOLD})")
    print(f"{'='*70}\n")

    cross_passed = 0
    cross_failed = 0
    cross_sims: list[float] = []

    speakers = sorted(by_speaker.keys())
    if len(speakers) < 2:
        print("  Only one speaker -- skipping cross-speaker comparison.\n")
    else:
        for sa, sb in combinations(speakers, 2):
            print(f"  {sa} vs {sb}:")
            for fa in sorted(by_speaker[sa]):
                for fb in sorted(by_speaker[sb]):
                    sim = cosine_similarity(embeddings[fa], embeddings[fb])
                    cross_sims.append(sim)
                    ok = sim < CROSS_SPEAKER_MAX_THRESHOLD
                    if ok:
                        cross_passed += 1
                    else:
                        cross_failed += 1
                    print(f"    {fa} <-> {fb}: {sim:.4f}  [{'PASS' if ok else 'FAIL'}]")
            print()

        if cross_sims:
            avg = sum(cross_sims) / len(cross_sims)
            print(f"  Cross-speaker: avg={avg:.4f}, min={min(cross_sims):.4f}, max={max(cross_sims):.4f}\n")

    # ── Final summary ──
    total_passed = transcription_passed + same_passed + cross_passed
    total_failed = transcription_failed + same_failed + cross_failed

    print(f"{'='*70}")
    print("FINAL RESULTS (Cloud: OpenAI transcription + Modal ECAPA2 embedding)")
    print(f"  Transcription:    {transcription_passed} passed, {transcription_failed} failed")
    print(f"  Same-speaker sim: {same_passed} passed, {same_failed} failed")
    print(f"  Cross-speaker:    {cross_passed} passed, {cross_failed} failed")
    print(f"  Total:            {total_passed} passed, {total_failed} failed")
    print(f"{'='*70}")
    sys.exit(1 if total_failed else 0)


if __name__ == "__main__":
    main()
