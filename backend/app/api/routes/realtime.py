from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, cast
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.clients.mongodb import MongoDBClient
from app.config import Settings, SettingsError, load_settings
from app.dependencies import get_mongodb_client
from app.repositories.session_repository import PracticeSessionRecord, SessionRepository

router = APIRouter()


class RealtimeTokenRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)


class RealtimeTokenResponse(BaseModel):
    token: str
    room_id: str
    app_id: str


class RealtimeStartRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    system_prompt: str = Field(..., min_length=1)


class RealtimeStartResponse(BaseModel):
    session_id: str
    room_id: str
    rtc_task_id: str
    realtime_state: str


class RealtimeStopRequest(BaseModel):
    session_id: str = Field(..., min_length=1)


class RealtimeStopResponse(BaseModel):
    session_id: str
    realtime_state: str


def _repo(mongodb: MongoDBClient = Depends(get_mongodb_client)) -> SessionRepository:
    return SessionRepository(mongodb)


def _is_rtc_error(exc: Exception) -> bool:
    return exc.__class__.__name__ in {"VolcengineRTCError", "VolcengineAPIError", "VolcengineAuthError"}


@dataclass(frozen=True)
class RealtimeVolcengineConfig:
    access_key_id: str
    secret_access_key: str
    rtc_app_id: str
    rtc_app_key: str
    voice_chat_endpoint: str
    voice_model_id: str


def _require_volcengine_settings(settings: Settings) -> RealtimeVolcengineConfig:
    required_fields = [
        ("VOLCENGINE_ACCESS_KEY_ID", settings.volcengine_access_key_id),
        ("VOLCENGINE_SECRET_ACCESS_KEY", settings.volcengine_secret_access_key),
        ("VOLCENGINE_RTC_APP_ID", settings.volcengine_rtc_app_id),
        ("VOLCENGINE_RTC_APP_KEY", settings.volcengine_rtc_app_key),
        ("VOLCENGINE_VOICE_CHAT_ENDPOINT", settings.volcengine_voice_chat_endpoint),
        ("VOLCENGINE_VOICE_MODEL_ID", settings.volcengine_voice_model_id),
    ]
    for env_name, value in required_fields:
        if not value:
            raise SettingsError(f"Missing required environment variable: {env_name}")
    return RealtimeVolcengineConfig(
        access_key_id=cast(str, settings.volcengine_access_key_id),
        secret_access_key=cast(str, settings.volcengine_secret_access_key),
        rtc_app_id=cast(str, settings.volcengine_rtc_app_id),
        rtc_app_key=cast(str, settings.volcengine_rtc_app_key),
        voice_chat_endpoint=cast(str, settings.volcengine_voice_chat_endpoint),
        voice_model_id=cast(str, settings.volcengine_voice_model_id),
    )


async def _rtc_client() -> AsyncIterator[Any]:
    try:
        config = _require_volcengine_settings(load_settings())
    except SettingsError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    rtc_module = __import__("app.clients.volcengine_rtc", fromlist=["VolcengineRTCClient"])
    client = rtc_module.VolcengineRTCClient(
        access_key_id=config.access_key_id,
        secret_access_key=config.secret_access_key,
        app_id=config.rtc_app_id,
        app_key=config.rtc_app_key,
        voice_chat_endpoint=config.voice_chat_endpoint,
        voice_model_id=config.voice_model_id,
    )
    try:
        yield client
    finally:
        await client.close()


def _room_id(session: PracticeSessionRecord) -> str:
    return session.rtc_room_id or f"session-{session.id}"


@router.post("/realtime/token", response_model=RealtimeTokenResponse)
async def create_realtime_token(
    payload: RealtimeTokenRequest,
    repo: SessionRepository = Depends(_repo),
    rtc: Any = Depends(_rtc_client),
):
    session = await repo.get_session(payload.session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    room_id = _room_id(session)
    try:
        token = rtc.generate_rtc_token(room_id=room_id, user_id=payload.user_id)
    except Exception as exc:
        if not _is_rtc_error(exc):
            raise
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return RealtimeTokenResponse(
        token=token,
        room_id=room_id,
        app_id=_require_volcengine_settings(load_settings()).rtc_app_id,
    )


@router.post("/realtime/start", response_model=RealtimeStartResponse)
async def start_realtime_chat(
    payload: RealtimeStartRequest,
    repo: SessionRepository = Depends(_repo),
    rtc: Any = Depends(_rtc_client),
):
    session = await repo.get_session(payload.session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    room_id = _room_id(session)
    task_id = session.rtc_task_id or f"rtc-{uuid4().hex}"
    try:
        await rtc.start_voice_chat(
            room_id=room_id,
            task_id=task_id,
            system_prompt=payload.system_prompt,
        )
    except Exception as exc:
        if not _is_rtc_error(exc):
            raise
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    updated = await repo.update_session(
        payload.session_id,
        {
            "mode": "realtime",
            "rtcRoomId": room_id,
            "rtcTaskId": task_id,
            "realtimeState": "active",
        },
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    return RealtimeStartResponse(
        session_id=payload.session_id,
        room_id=room_id,
        rtc_task_id=task_id,
        realtime_state="active",
    )


@router.post("/realtime/stop", response_model=RealtimeStopResponse)
async def stop_realtime_chat(
    payload: RealtimeStopRequest,
    repo: SessionRepository = Depends(_repo),
    rtc: Any = Depends(_rtc_client),
):
    session = await repo.get_session(payload.session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    room_id = _room_id(session)
    task_id = session.rtc_task_id
    if not task_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Session has no active realtime task",
        )

    try:
        await rtc.stop_voice_chat(room_id=room_id, task_id=task_id)
    except Exception as exc:
        if not _is_rtc_error(exc):
            raise
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    updated = await repo.update_session(
        payload.session_id,
        {
            "realtimeState": "ended",
        },
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    return RealtimeStopResponse(session_id=payload.session_id, realtime_state="ended")
