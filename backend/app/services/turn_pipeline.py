from __future__ import annotations

import base64
import asyncio
from datetime import datetime, timezone
from typing import Any

from app.api.routes.session_socket import hub
from app.clients.leancloud import LeanCloudClient
from app.clients.llm import QwenClient
from app.config import load_settings
from app.repositories.scenario_repository import ScenarioRepository
from app.repositories.session_repository import SessionRepository
from app.services.audio import (
    AudioConversionError,
    convert_audio_to_mp3,
    convert_wav_to_mp3,
    decode_audio_base64,
)
from app.services.objective_check import run_objective_check
from app.services.session_service import terminate_session
from app.telemetry.otel import start_span
from app.telemetry.tracing import emit_event, emit_metric

QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
QWEN_MODEL = "qwen3-omni-flash"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_qwen_text(response: dict[str, Any]) -> str:
    choices = response.get("choices", [])
    if not choices:
        return ""
    message = choices[0].get("message", {})
    return message.get("content", "")


def _extract_qwen_audio(response: dict[str, Any]) -> bytes | None:
    choices = response.get("choices", [])
    if not choices:
        return None
    message = choices[0].get("message", {})
    audio = message.get("audio") or {}
    payload = audio.get("data") or audio.get("content")
    if not payload:
        return None
    return decode_audio_base64(payload)


def _turn_payload(turn) -> dict[str, Any]:
    return {
        "id": turn.id,
        "sessionId": turn.session_id,
        "sequence": turn.sequence,
        "speaker": turn.speaker,
        "transcript": turn.transcript,
        "audioFileId": turn.audio_file_id,
        "audioUrl": turn.audio_url,
        "asrStatus": turn.asr_status,
        "createdAt": turn.created_at,
        "startedAt": turn.started_at,
        "endedAt": turn.ended_at,
        "context": turn.context,
        "latencyMs": turn.latency_ms,
    }


def _qwen_generation_payload(
    *,
    model: str,
    messages: list[dict[str, str]],
    voice_id: str | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    if voice_id:
        payload["modalities"] = ["text", "audio"]
        payload["audio"] = {"voice": voice_id, "format": "wav"}
    else:
        payload["modalities"] = ["text"]
    return payload


def _persona_block(persona: dict[str, Any] | None, label: str) -> str:
    if not persona:
        return f"{label}: (not provided)"
    name = persona.get("name") or "Unknown"
    role = persona.get("role") or "Unknown"
    background = persona.get("background") or "Not provided"
    return f"{label}: {name} ({role}). Background: {background}"


def _build_initiation_messages(scenario: Any) -> list[dict[str, str]]:
    title = getattr(scenario, "title", "") or ""
    description = getattr(scenario, "description", "") or ""
    objective = getattr(scenario, "objective", "") or ""
    end_criteria = getattr(scenario, "end_criteria", None) or getattr(
        scenario, "endCriteria", []
    )
    prompt = getattr(scenario, "prompt", "") or ""
    ai_persona = getattr(scenario, "ai_persona", None) or getattr(
        scenario, "aiPersona", None
    )
    trainee_persona = getattr(scenario, "trainee_persona", None) or getattr(
        scenario, "traineePersona", None
    )
    criteria_text = ", ".join(end_criteria) if end_criteria else "Not provided"

    system_lines = [
        "You are the AI roleplayer for a practice conversation.",
        _persona_block(ai_persona, "Your persona"),
        _persona_block(trainee_persona, "Trainee persona"),
    ]
    if title:
        system_lines.append(f"Scenario title: {title}")
    if description:
        system_lines.append(f"Scenario description: {description}")
    if objective:
        system_lines.append(f"Objective: {objective}")
    system_lines.append(f"End criteria: {criteria_text}")
    system_lines.append("You must start the conversation as the AI.")

    user_prompt = prompt or "Begin the conversation in character."
    return [
        {"role": "system", "content": "\n".join(system_lines)},
        {"role": "user", "content": user_prompt},
    ]


async def generate_initial_ai_turn(*, session_id: str, scenario: Any) -> None:
    settings = load_settings()
    lc_client = LeanCloudClient(
        app_id=settings.lean_app_id,
        app_key=settings.lean_app_key,
        master_key=settings.lean_master_key,
        server_url=settings.lean_server_url,
    )
    qwen_client = QwenClient(
        base_url=QWEN_BASE_URL,
        api_key=settings.dashscope_api_key,
    )
    repo = SessionRepository(lc_client)

    try:
        with start_span(
            "turn.initiation",
            {"sessionId": session_id},
        ):
            messages = _build_initiation_messages(scenario)
            try:
                payload = _qwen_generation_payload(
                    model=QWEN_MODEL,
                    messages=messages,
                    voice_id=settings.qwen_voice_id,
                )
                generation_response = await qwen_client.generate(payload)
            except Exception as exc:
                emit_event(
                    "turn.initiation_failed",
                    session_id=session_id,
                    attributes={"reason": "qwen_generation_failed", "error": str(exc)},
                )
                await _terminate_for_qwen_error(repo, session_id)
                return

            transcript = _parse_qwen_text(generation_response)
            now = _utc_now()
            ai_turn = await repo.add_turn(
                {
                    "sessionId": session_id,
                    "sequence": 0,
                    "speaker": "ai",
                    "transcript": transcript or "",
                    "audioFileId": "pending",
                    "audioUrl": "",
                    "asrStatus": "not_applicable",
                    "startedAt": now,
                    "endedAt": now,
                    "context": "",
                    "latencyMs": -1,
                }
            )

            ai_audio_url = None
            ai_audio_id = None
            try:
                wav_bytes = _extract_qwen_audio(generation_response)
                if wav_bytes:
                    mp3_bytes = convert_wav_to_mp3(wav_bytes)
                    upload_ai = await lc_client.upload_file(
                        f"turn-{ai_turn.id}.mp3", mp3_bytes, "audio/mpeg"
                    )
                    ai_audio_id = upload_ai.get("objectId") or upload_ai.get("name")
                    ai_audio_url = upload_ai.get("url")
            except AudioConversionError as exc:
                emit_event(
                    "turn.audio_error",
                    session_id=session_id,
                    turn_id=ai_turn.id,
                    attributes={"reason": str(exc)},
                )

            if ai_audio_id:
                await repo.update_turn(
                    ai_turn.id,
                    {
                        "audioFileId": ai_audio_id,
                        "audioUrl": ai_audio_url or "",
                    },
                )
                ai_turn = await repo.get_turn(ai_turn.id)

            await hub.broadcast(
                session_id,
                {
                    "type": "ai_turn",
                    "turn": _turn_payload(ai_turn),
                },
            )
            emit_metric(
                "turn.ai_created",
                1,
                session_id=session_id,
                turn_id=ai_turn.id,
            )

            if transcript:
                end_criteria = getattr(scenario, "end_criteria", None) or getattr(
                    scenario, "endCriteria", []
                )
                objective = getattr(scenario, "objective", "") or ""
                if end_criteria or objective:
                    objective_result = await run_objective_check(
                        scenario_objective=objective,
                        transcript=transcript,
                        end_criteria=end_criteria,
                    )
                    if objective_result.status in {"succeeded", "failed"}:
                        await repo.update_session(
                            session_id,
                            {
                                "objectiveStatus": objective_result.status,
                                "objectiveReason": objective_result.reason,
                            },
                        )
                        await terminate_session(
                            repo,
                            session_id,
                            "objective_met"
                            if objective_result.status == "succeeded"
                            else "objective_failed",
                            _utc_now(),
                        )
    finally:
        await qwen_client.close()
        await lc_client.close()


async def enqueue_turn_pipeline(*, session_id: str, turn_id: str, audio_base64: str) -> None:
    await _process_turn(session_id=session_id, turn_id=turn_id, audio_base64=audio_base64)


async def _process_turn(*, session_id: str, turn_id: str, audio_base64: str) -> None:
    settings = load_settings()
    lc_client = LeanCloudClient(
        app_id=settings.lean_app_id,
        app_key=settings.lean_app_key,
        master_key=settings.lean_master_key,
        server_url=settings.lean_server_url,
    )
    qwen_client = QwenClient(
        base_url=QWEN_BASE_URL,
        api_key=settings.dashscope_api_key,
    )
    repo = SessionRepository(lc_client)

    try:
        with start_span(
            "turn.pipeline",
            {"sessionId": session_id, "turnId": turn_id},
        ):
            try:
                audio_bytes = base64.b64decode(audio_base64, validate=True)
            except ValueError:
                await _handle_audio_error(repo, session_id, turn_id, "Audio decode failed")
                return
            try:
                mp3_bytes = convert_audio_to_mp3(audio_bytes)
            except AudioConversionError:
                await _handle_audio_error(repo, session_id, turn_id, "Audio conversion failed")
                return

            upload = await lc_client.upload_file(
                f"turn-{turn_id}.mp3", mp3_bytes, "audio/mpeg"
            )
            file_id = upload.get("objectId") or upload.get("name")
            await repo.update_turn(
                turn_id,
                {
                    "audioFileId": file_id,
                    "audioUrl": upload.get("url"),
                    "asrStatus": "pending",
                },
            )

            turns = await repo.list_turns(session_id)
            max_sequence = max((turn.sequence for turn in turns), default=-1)

            generation_task = qwen_client.generate(
                _qwen_generation_payload(
                    model=QWEN_MODEL,
                    messages=[
                        {"role": "system", "content": "You are an AI coach."},
                        {"role": "user", "content": "Respond to the trainee."},
                    ],
                    voice_id=settings.qwen_voice_id,
                )
            )
            mp3_base64 = base64.b64encode(mp3_bytes).decode("utf-8")
            asr_task = qwen_client.asr({"model": QWEN_MODEL, "input": mp3_base64})

            generation_response, asr_response = await asyncio.gather(
                generation_task, asr_task, return_exceptions=True
            )

            if isinstance(generation_response, Exception):
                emit_event(
                    "turn.ai_generation_failed",
                    session_id=session_id,
                    turn_id=turn_id,
                    attributes={"error": str(generation_response)},
                )
                await _terminate_for_qwen_error(repo, session_id)
                return

            transcript = _parse_qwen_text(generation_response)
            ai_turn = await repo.add_turn(
                {
                    "sessionId": session_id,
                    "sequence": max_sequence + 1,
                    "speaker": "ai",
                    "transcript": transcript or None,
                    "audioFileId": "pending",
                    "audioUrl": None,
                    "asrStatus": None,
                    "startedAt": _utc_now(),
                    "endedAt": _utc_now(),
                    "context": None,
                    "latencyMs": None,
                }
            )

            ai_audio_url = None
            ai_audio_id = None
            try:
                wav_bytes = _extract_qwen_audio(generation_response)
                if wav_bytes:
                    mp3_bytes = convert_wav_to_mp3(wav_bytes)
                    upload_ai = await lc_client.upload_file(
                        f"turn-{ai_turn.id}.mp3", mp3_bytes, "audio/mpeg"
                    )
                    ai_audio_id = upload_ai.get("objectId") or upload_ai.get("name")
                    ai_audio_url = upload_ai.get("url")
            except AudioConversionError as exc:
                emit_event(
                    "turn.audio_error",
                    session_id=session_id,
                    turn_id=ai_turn.id,
                    attributes={"reason": str(exc)},
                )

            if ai_audio_id:
                await repo.update_turn(
                    ai_turn.id,
                    {
                        "audioFileId": ai_audio_id,
                        "audioUrl": ai_audio_url,
                    },
                )
                ai_turn = await repo.get_turn(ai_turn.id)

            await hub.broadcast(
                session_id,
                {
                    "type": "ai_turn",
                    "turn": _turn_payload(ai_turn),
                },
            )
            emit_metric(
                "turn.ai_created",
                1,
                session_id=session_id,
                turn_id=ai_turn.id,
            )

            if isinstance(asr_response, Exception):
                await repo.update_turn(turn_id, {"asrStatus": "failed"})
            else:
                await repo.update_turn(
                    turn_id,
                    {"asrStatus": "completed", "transcript": asr_response.get("text")},
                )

            if transcript and asr_response and not isinstance(asr_response, Exception):
                scenario_repo = ScenarioRepository(lc_client)
                scenario = await _fetch_scenario(repo, scenario_repo, session_id)
                if scenario:
                    objective = await run_objective_check(
                        scenario_objective=scenario.get("objective", ""),
                        transcript=transcript,
                        end_criteria=scenario.get("endCriteria", []),
                    )
                    if objective.status in {"succeeded", "failed"}:
                        await repo.update_session(
                            session_id,
                            {
                                "objectiveStatus": objective.status,
                                "objectiveReason": objective.reason,
                            },
                        )
                        await terminate_session(
                            repo,
                            session_id,
                            "objective_met"
                            if objective.status == "succeeded"
                            else "objective_failed",
                            _utc_now(),
                        )
    finally:
        await qwen_client.close()
        await lc_client.close()


async def _terminate_for_qwen_error(repo: SessionRepository, session_id: str) -> None:
    await repo.update_session(
        session_id,
        {
            "status": "ended",
            "terminationReason": "qa_error",
            "endedAt": _utc_now(),
        },
    )
    emit_event(
        "session.terminated",
        session_id=session_id,
        attributes={"reason": "qa_error", "source": "qwen"},
    )
    await hub.broadcast(
        session_id,
        {
            "type": "termination",
            "termination": {"reason": "qa_error", "terminatedAt": _utc_now()},
            "message": "Qwen is unavailable. Please retry your turn.",
        },
    )


async def _handle_audio_error(
    repo: SessionRepository, session_id: str, turn_id: str, reason: str
) -> None:
    await repo.update_turn(turn_id, {"asrStatus": "failed", "audioFileId": "missing"})
    emit_event(
        "turn.audio_error",
        session_id=session_id,
        turn_id=turn_id,
        attributes={"reason": reason},
    )
    emit_metric(
        "turn.audio_error",
        1,
        session_id=session_id,
        turn_id=turn_id,
        attributes={"reason": reason},
    )
    await hub.broadcast(
        session_id,
        {
            "type": "termination",
            "termination": {"reason": "media_error", "terminatedAt": _utc_now()},
            "message": "Audio upload failed. Please resend your turn.",
        },
    )


async def _fetch_scenario(
    repo: SessionRepository,
    scenario_repo: ScenarioRepository,
    session_id: str,
) -> dict[str, Any] | None:
    session = await repo.get_session(session_id)
    if not session:
        return None
    scenario = await scenario_repo.get(session.scenario_id)
    if not scenario:
        return None
    return {
        "objective": scenario.objective,
        "endCriteria": scenario.end_criteria,
    }
