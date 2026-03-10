from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.authn import require_user_from_bearer
from src.api.rate_limit import enforce_dispute_rate_limit
from src.config import get_settings
from src.db.connection import get_db
from src.db.evidence import EVENT_CATALOG, EvidenceLogEntry, generate_receipt_token, isoformat_z
from src.handlers.disputes import resolve_submission_dispute
from src.models.submission import Submission
from src.models.user import User
from src.models.vote import Vote

router = APIRouter()


@router.get("/dashboard/submissions")
async def list_submissions(
    user: Annotated[User, Depends(require_user_from_bearer)],
    session: AsyncSession = Depends(get_db),
) -> list[dict[str, str]]:
    result = await session.execute(
        select(Submission).where(Submission.user_id == user.id).order_by(Submission.created_at.desc())
    )
    rows = result.scalars().all()
    return [
        {"id": str(row.id), "raw_text": row.raw_text, "status": row.status, "hash": row.hash}
        for row in rows
    ]


@router.get("/dashboard/votes")
async def list_votes(
    user: Annotated[User, Depends(require_user_from_bearer)],
    session: AsyncSession = Depends(get_db),
) -> list[dict[str, object]]:
    result = await session.execute(select(Vote).where(Vote.user_id == user.id).order_by(Vote.created_at.desc()))
    rows = result.scalars().all()
    return [
        {
            "id": str(row.id),
            "cycle_id": str(row.cycle_id),
            "approved_cluster_ids": [str(cluster_id) for cluster_id in row.approved_cluster_ids],
        }
        for row in rows
    ]


@router.get("/dashboard/receipts")
async def list_receipts(
    user: Annotated[User, Depends(require_user_from_bearer)],
    session: AsyncSession = Depends(get_db),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
) -> dict[str, object]:
    """Return the authenticated user's evidence entries with receipt tokens.

    Only events whose payloads contain the user's ID are returned. Each
    entry includes a receipt_token (HMAC) the user can present externally
    to prove their action was recorded in the chain.
    """
    settings = get_settings()
    uid_str = str(user.id)

    receipt_event_types = {et for et, spec in EVENT_CATALOG.items() if spec.generates_receipt}
    query = (
        select(EvidenceLogEntry)
        .where(EvidenceLogEntry.event_type.in_(receipt_event_types))
        .order_by(EvidenceLogEntry.id.desc())
    )
    result = await session.execute(query)
    all_entries = result.scalars().all()

    user_entries = [e for e in all_entries if isinstance(e.payload, dict) and e.payload.get("user_id") == uid_str]
    total = len(user_entries)
    start = (page - 1) * per_page
    page_entries = user_entries[start : start + per_page]

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "entries": [
            {
                "id": entry.id,
                "timestamp": isoformat_z(entry.timestamp),
                "event_type": entry.event_type,
                "entity_type": entry.entity_type,
                "entity_id": str(entry.entity_id),
                "payload": entry.payload,
                "hash": entry.hash,
                "prev_hash": entry.prev_hash,
                "receipt_token": generate_receipt_token(entry.hash, settings.web_access_token_secret),
            }
            for entry in page_entries
        ],
    }


@router.post("/dashboard/disputes/{submission_id}")
async def open_dispute(
    submission_id: str,
    user: Annotated[User, Depends(require_user_from_bearer)],
    session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    enforce_dispute_rate_limit(str(user.id))
    try:
        submission_uuid = UUID(submission_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid submission id") from exc
    result = await session.execute(
        select(Submission).where(Submission.id == submission_uuid, Submission.user_id == user.id)
    )
    submission = result.scalar_one_or_none()
    if submission is None:
        raise HTTPException(status_code=404, detail="submission not found")

    await resolve_submission_dispute(session=session, submission=submission)
    return {"status": "under_automated_review"}
