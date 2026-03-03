from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rate_limit import (
    enforce_subscribe_rate_limit,
    enforce_verify_rate_limit,
    enforce_web_session_rate_limit,
    get_request_ip,
)
from src.db.connection import get_db
from src.handlers.identity import exchange_web_session_code, subscribe_email, verify_magic_link

router = APIRouter()


class SubscribeRequest(BaseModel):
    email: EmailStr
    locale: str = "fa"
    messaging_account_ref: str


class WebSessionRequest(BaseModel):
    email: EmailStr
    code: str


@router.post("/subscribe")
async def subscribe(
    payload: SubscribeRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    enforce_subscribe_rate_limit(request)
    requester_ip = get_request_ip(request)
    user, token = await subscribe_email(
        session=session,
        email=str(payload.email),
        locale=payload.locale,
        requester_ip=requester_ip,
        messaging_account_ref=payload.messaging_account_ref,
    )
    if user is None:
        raise HTTPException(status_code=429, detail=token or "signup blocked")
    # Token is delivered via email — do not include it in the API response.
    return {"status": "pending_verification"}


@router.post("/verify/{token}")
async def verify(
    token: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    enforce_verify_rate_limit(request)
    ok, status, email, web_session_code = await verify_magic_link(session=session, token=token)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid or expired verification link")
    return {
        "status": status,
        "email": email or "",
        "web_session_code": web_session_code or "",
    }


@router.post("/web-session")
async def web_session(
    payload: WebSessionRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    enforce_web_session_rate_limit(request)
    ok, access_token = await exchange_web_session_code(
        session=session,
        email=str(payload.email),
        code=payload.code,
    )
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid or expired session code")
    return {"status": "ok", "email": str(payload.email), "access_token": access_token}
