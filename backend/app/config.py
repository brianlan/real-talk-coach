from __future__ import annotations

from dataclasses import dataclass
import os
from urllib.parse import urlparse


class SettingsError(ValueError):
    pass


@dataclass(frozen=True)
class Settings:
    mongo_host: str
    mongo_port: int
    mongo_db: str
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str
    minio_public_endpoint: str | None
    dashscope_api_key: str
    qwen_voice_id: str | None
    chatai_api_base: str
    chatai_api_key: str
    chatai_api_model: str
    evaluator_model: str
    objective_check_api_base: str
    objective_check_api_key: str
    objective_check_model: str
    stub_user_id: str
    admin_access_token: str
    admin_audit_admin_id: str | None
    admin_auth_disabled: bool


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SettingsError(f"Missing required environment variable: {name}")
    return value


def _optional_env(name: str) -> str | None:
    value = os.getenv(name, "").strip()
    return value or None


def _optional_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off", ""}:
        return False
    raise SettingsError(f"Invalid boolean for {name}: {value}")


def _require_url(name: str, value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise SettingsError(f"Invalid URL for {name}: {value}")
    return value


def _optional_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value.strip())
    except ValueError:
        raise SettingsError(f"Invalid integer for {name}: {value}")


def load_settings() -> Settings:
    mongo_host = os.getenv("MONGO_HOST", "localhost").strip()
    mongo_port = _optional_int("MONGO_PORT", 27017)
    mongo_db = os.getenv("MONGO_DB", "real-talk-coach").strip()
    minio_endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000").strip()
    minio_access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin").strip()
    minio_secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin").strip()
    minio_bucket = os.getenv("MINIO_BUCKET", "audio").strip()
    minio_public_endpoint = _optional_env("MINIO_PUBLIC_ENDPOINT")
    dashscope_api_key = _require_env("DASHSCOPE_API_KEY")
    qwen_voice_id = _optional_env("QWEN_VOICE_ID")
    chatai_api_base = _require_url("CHATAI_API_BASE", _require_env("CHATAI_API_BASE"))
    chatai_api_key = _require_env("CHATAI_API_KEY")
    chatai_api_model = _require_env("CHATAI_API_MODEL")
    evaluator_model = _require_env("EVALUATOR_MODEL")
    objective_check_api_base = _optional_env("OBJECTIVE_CHECK_API_BASE") or chatai_api_base
    objective_check_api_base = _require_url(
        "OBJECTIVE_CHECK_API_BASE", objective_check_api_base
    )
    objective_check_api_key = _require_env("OBJECTIVE_CHECK_API_KEY")
    objective_check_model = _require_env("OBJECTIVE_CHECK_MODEL")
    stub_user_id = _require_env("STUB_USER_ID")
    admin_access_token = _require_env("ADMIN_ACCESS_TOKEN")
    admin_audit_admin_id = _optional_env("ADMIN_AUDIT_ADMIN_ID")
    admin_auth_disabled = _optional_bool("ADMIN_AUTH_DISABLED", default=False)

    return Settings(
        mongo_host=mongo_host,
        mongo_port=mongo_port,
        mongo_db=mongo_db,
        minio_endpoint=minio_endpoint,
        minio_access_key=minio_access_key,
        minio_secret_key=minio_secret_key,
        minio_bucket=minio_bucket,
        minio_public_endpoint=minio_public_endpoint,
        dashscope_api_key=dashscope_api_key,
        qwen_voice_id=qwen_voice_id,
        chatai_api_base=chatai_api_base,
        chatai_api_key=chatai_api_key,
        chatai_api_model=chatai_api_model,
        evaluator_model=evaluator_model,
        objective_check_api_base=objective_check_api_base,
        objective_check_api_key=objective_check_api_key,
        objective_check_model=objective_check_model,
        stub_user_id=stub_user_id,
        admin_access_token=admin_access_token,
        admin_audit_admin_id=admin_audit_admin_id,
        admin_auth_disabled=admin_auth_disabled,
    )
