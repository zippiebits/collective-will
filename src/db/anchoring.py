from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import Date, DateTime, String, and_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.config import Settings
from src.db.connection import Base
from src.db.evidence import EvidenceLogEntry, append_evidence


class DailyAnchor(Base):
    __tablename__ = "daily_anchors"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    day: Mapped[date] = mapped_column(Date, unique=True, nullable=False, index=True)
    merkle_root: Mapped[str] = mapped_column(String(64), nullable=False)
    published_receipt: Mapped[str | None] = mapped_column(String, nullable=True)
    anchor_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


def _pair_hash(left: str, right: str) -> str:
    payload = f"{left}{right}".encode()
    return hashlib.sha256(payload).hexdigest()


def compute_merkle_root(leaves: list[str]) -> str:
    if not leaves:
        raise ValueError("Cannot compute Merkle root for empty leaves")
    level = leaves[:]
    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])
        next_level: list[str] = []
        for idx in range(0, len(level), 2):
            next_level.append(_pair_hash(level[idx], level[idx + 1]))
        level = next_level
    return level[0]


async def compute_daily_merkle_root(session: AsyncSession, day: date) -> str | None:
    start = datetime.combine(day, time.min).replace(tzinfo=UTC)
    end = start + timedelta(days=1)
    result = await session.execute(
        select(EvidenceLogEntry)
        .where(and_(EvidenceLogEntry.timestamp >= start, EvidenceLogEntry.timestamp < end))
        .order_by(EvidenceLogEntry.id.asc())
    )
    entries = list(result.scalars().all())
    if not entries:
        return None

    root = compute_merkle_root([entry.hash for entry in entries])
    existing = await session.execute(select(DailyAnchor).where(DailyAnchor.day == day))
    anchor = existing.scalar_one_or_none()
    if anchor is None:
        anchor = DailyAnchor(day=day, merkle_root=root, anchor_metadata={"entry_count": len(entries)})
        session.add(anchor)
        await session.flush()
        await append_evidence(
            session=session,
            event_type="anchor_computed",
            entity_type="daily_anchor",
            entity_id=entries[-1].entity_id,
            payload={"day": day.isoformat(), "merkle_root": root, "entry_count": len(entries)},
        )
    return root


async def publish_daily_merkle_root(
    root: str,
    day: date,
    settings: Settings,
    session: AsyncSession | None = None,
) -> str | None:
    if not settings.witness_publish_enabled:
        return None
    if not settings.witness_api_key:
        raise ValueError("WITNESS_API_KEY is required when publication is enabled")

    if session is not None:
        entity_id = await _anchor_entity_id(session, day)
        await append_evidence(
            session=session,
            event_type="anchor_publish_attempted",
            entity_type="daily_anchor",
            entity_id=entity_id,
            payload={"day": day.isoformat(), "merkle_root": root},
        )
    else:
        from uuid import NAMESPACE_URL, uuid5

        entity_id = uuid5(NAMESPACE_URL, f"daily-anchor:{day.isoformat()}")

    http_payload = {"day": day.isoformat(), "root": root}
    headers = {"Authorization": f"Bearer {settings.witness_api_key}"}
    try:
        async with httpx.AsyncClient(timeout=settings.witness_http_timeout_seconds) as client:
            response = await client.post(f"{settings.witness_api_url}/anchors", json=http_payload, headers=headers)
            response.raise_for_status()
            receipt_value = response.json().get("id")
            receipt = str(receipt_value) if receipt_value is not None else None
    except Exception as exc:
        if session is not None:
            await append_evidence(
                session=session,
                event_type="anchor_publish_failed",
                entity_type="daily_anchor",
                entity_id=entity_id,
                payload={"day": day.isoformat(), "merkle_root": root, "error_type": type(exc).__name__},
            )
        raise

    if session is not None:
        result = await session.execute(select(DailyAnchor).where(DailyAnchor.day == day))
        anchor = result.scalar_one_or_none()
        if anchor is not None:
            anchor.published_receipt = receipt
        await append_evidence(
            session=session,
            event_type="anchor_publish_succeeded",
            entity_type="daily_anchor",
            entity_id=entity_id,
            payload={"day": day.isoformat(), "merkle_root": root, "receipt": receipt or ""},
        )
    return receipt


async def _anchor_entity_id(session: AsyncSession, day: date) -> UUID:
    """Resolve a stable entity_id for anchoring evidence entries.

    Reuses the entity_id from the anchor_computed event for this day,
    so all anchoring events for the same day share a consistent ID.
    """
    from uuid import NAMESPACE_URL, uuid5

    result = await session.execute(
        select(EvidenceLogEntry.entity_id)
        .where(EvidenceLogEntry.event_type == "anchor_computed")
        .order_by(EvidenceLogEntry.id.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is not None:
        return row
    return uuid5(NAMESPACE_URL, f"daily-anchor:{day.isoformat()}")
