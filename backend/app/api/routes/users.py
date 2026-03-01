from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Header, Request
from pydantic import BaseModel

router = APIRouter()

_GITHUB_SESSION_COOKIE_NAMES = (
    "authjs.session-token",
    "__Secure-authjs.session-token",
    "next-auth.session-token",
    "__Secure-next-auth.session-token",
)


class UserResponse(BaseModel):
    id: str
    type: Literal["github", "anonymous"]
    createdAt: datetime


def _decode_jwt_payload(token: str) -> dict[str, object] | None:
    parts = token.split(".")
    if len(parts) != 3:
        return None

    payload = parts[1]
    padding = "=" * (-len(payload) % 4)
    try:
        decoded = base64.urlsafe_b64decode(f"{payload}{padding}")
        data = json.loads(decoded.decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return None

    if isinstance(data, dict):
        return data
    return None


def _extract_bearer_token(request: Request) -> str | None:
    authorization = request.headers.get("authorization")
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2:
        return None
    scheme, token = parts
    if scheme.lower() != "bearer" or not token:
        return None
    return token


def _github_subject_from_request(request: Request) -> str | None:
    bearer_token = _extract_bearer_token(request)
    if bearer_token:
        payload = _decode_jwt_payload(bearer_token)
        if payload:
            subject = payload.get("sub")
            email = payload.get("email")
            if isinstance(subject, str) and subject:
                return subject
            if isinstance(email, str) and email:
                return email

    for cookie_name in _GITHUB_SESSION_COOKIE_NAMES:
        raw_cookie = request.cookies.get(cookie_name)
        if not raw_cookie:
            continue
        payload = _decode_jwt_payload(raw_cookie)
        if payload:
            subject = payload.get("sub")
            email = payload.get("email")
            if isinstance(subject, str) and subject:
                return subject
            if isinstance(email, str) and email:
                return email
    return None


def _has_github_session_cookie(request: Request) -> bool:
    return any(request.cookies.get(name) for name in _GITHUB_SESSION_COOKIE_NAMES)


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    request: Request,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> UserResponse:
    github_subject = _github_subject_from_request(request)
    has_github_session = _has_github_session_cookie(request)
    user_type: Literal["github", "anonymous"] = (
        "github" if (github_subject or has_github_session) else "anonymous"
    )

    cookie_user_id = request.cookies.get("rtc_user_id")
    resolved_user_id = x_user_id or github_subject or cookie_user_id or str(uuid4())

    return UserResponse(
        id=resolved_user_id,
        type=user_type,
        createdAt=datetime.now(timezone.utc),
    )
