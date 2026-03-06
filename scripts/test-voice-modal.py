#!/usr/bin/env python3
"""Run voice embedding tests against the Modal-deployed ECAPA2 endpoint.

Uses the same real .ogg fixtures and manifest as test-voice-transcription.py,
but only runs embedding checks (same-speaker similarity, cross-speaker distinction).
No transcription — Modal endpoint returns embeddings only.

Usage:
    # Deploy first: modal deploy modal_functions/voice_embedding.py
    # Then run (replace URL with the one printed by deploy):
    uv run python scripts/test-voice-modal.py --url https://YOUR_USER--collective-will-voice-process.modal.run
"""

from __future__ import annotations

import argparse
import base64
import json
import math
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import httpx

FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "voice-samples"

# Unified embedding thresholds (ECAPA2: same-speaker min ~0.57, cross-speaker max ~0.31)
SAME_SPEAKER_THRESHOLD = 0.45
CROSS_SPEAKER_MAX_THRESHOLD = 0.40


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def same_speaker_threshold(_locale_a: str, _locale_b: str) -> float:
    return SAME_SPEAKER_THRESHOLD


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Test Modal voice embedding endpoint with real .ogg fixtures (same/cross-speaker)"
    )
    parser.add_argument(
        "--url",
        required=True,
        help="Modal web endpoint URL (from 'modal deploy modal_functions/voice_embedding.py')",
    )
    parser.add_argument("--timeout", type=int, default=90, help="Request timeout per sample (default 90s)")
    args = parser.parse_args()

    manifest_path = FIXTURES / "manifest.json"
    if not manifest_path.exists():
        print(f"ERROR: {manifest_path} not found")
        sys.exit(1)

    with open(manifest_path) as f:
        manifest = json.load(f)

    # Modal endpoint: POST {"audio_b64": "..."} -> {"embedding": [...], "model_version": "..."}
    url = args.url.rstrip("/")
    print(f"Modal endpoint: {url}")
    print(f"Fixtures: {FIXTURES} ({len(manifest['samples'])} samples)")
    print()

    embeddings: dict[str, list[float]] = {}
    file_to_speaker: dict[str, str] = {}
    file_to_locale: dict[str, str] = {}
    failed_fetches: list[str] = []

    for sample in manifest["samples"]:
        audio_path = FIXTURES / sample["file"]
        if not audio_path.exists():
            print(f"SKIP {sample['file']}: file not found")
            failed_fetches.append(sample["file"])
            continue

        audio_b64 = base64.b64encode(audio_path.read_bytes()).decode("ascii")
        print(f"  {sample['file']} ({sample['locale']}, {sample['speaker']}) ... ", end="", flush=True)

        try:
            resp = httpx.post(
                url,
                json={"audio_b64": audio_b64},
                timeout=args.timeout,
            )
            resp.raise_for_status()
            result = resp.json()
            embedding = result.get("embedding", [])
            model = result.get("model_version", "?")
            if not embedding:
                print("FAIL (no embedding)")
                failed_fetches.append(sample["file"])
                continue
            embeddings[sample["file"]] = embedding
            file_to_speaker[sample["file"]] = sample["speaker"]
            file_to_locale[sample["file"]] = sample["locale"]
            print(f"OK ({len(embedding)}-dim, {model})")
        except Exception as e:
            print(f"FAIL: {e}")
            failed_fetches.append(sample["file"])

    if failed_fetches:
        print(f"\nERROR: Failed to get embeddings for: {failed_fetches}")
        sys.exit(1)

    if len(embeddings) < 2:
        print("Need at least 2 samples with embeddings to run similarity checks.")
        sys.exit(1)

    by_speaker: dict[str, list[str]] = defaultdict(list)
    for fname, spk in file_to_speaker.items():
        by_speaker[spk].append(fname)

    # ── Part 2: Same-speaker embedding similarity ──
    print(f"\n{'='*70}")
    print("PART 2: Same-speaker embedding similarity (per language-pair thresholds)")
    print(f"  Unified threshold >= {SAME_SPEAKER_THRESHOLD}")
    print(f"{'='*70}\n")

    same_passed = 0
    same_failed = 0
    same_sims: list[float] = []

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
        print("  Only one speaker — skipping cross-speaker comparison.\n")
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
    total_passed = same_passed + cross_passed
    total_failed = same_failed + cross_failed

    print(f"{'='*70}")
    print("FINAL RESULTS (Modal embedding only; no transcription)")
    print(f"  Same-speaker sim: {same_passed} passed, {same_failed} failed")
    print(f"  Cross-speaker:    {cross_passed} passed, {cross_failed} failed")
    print(f"  Total:            {total_passed} passed, {total_failed} failed")
    print(f"{'='*70}")
    sys.exit(1 if total_failed else 0)


if __name__ == "__main__":
    main()
