from __future__ import annotations

from dataclasses import dataclass
import os
from urllib.parse import urlparse


class SettingsError(ValueError):
    pass


@dataclass(frozen=True)
class Settings:
    lean_app_id: str
    lean_app_key: str
    lean_master_key: str
    lean_server_url: str
    dashscope_api_key: str
    qwen_bearer: str | None
    chatai_api_base: str
    chatai_api_key: str
    chatai_api_model: str
    evaluator_model: str
    objective_check_api_base: str
    objective_check_api_key: str
    objective_check_model: str
    stub_user_id: str


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SettingsError(f"Missing required environment variable: {name}")
    return value


def _optional_env(name: str) -> str | None:
    value = os.getenv(name, "").strip()
    return value or None


def _require_url(name: str, value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise SettingsError(f"Invalid URL for {name}: {value}")
    return value


def load_settings() -> Settings:
    lean_app_id = _require_env("LEAN_APP_ID")
    lean_app_key = _require_env("LEAN_APP_KEY")
    lean_master_key = _require_env("LEAN_MASTER_KEY")
    lean_server_url = _require_url(
        "LEAN_SERVER_URL",
        os.getenv("LEAN_SERVER_URL", "https://api.leancloud.cn").strip(),
    )
    dashscope_api_key = _require_env("DASHSCOPE_API_KEY")
    qwen_bearer = _optional_env("QWEN_BEARER")
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

    return Settings(
        lean_app_id=lean_app_id,
        lean_app_key=lean_app_key,
        lean_master_key=lean_master_key,
        lean_server_url=lean_server_url,
        dashscope_api_key=dashscope_api_key,
        qwen_bearer=qwen_bearer,
        chatai_api_base=chatai_api_base,
        chatai_api_key=chatai_api_key,
        chatai_api_model=chatai_api_model,
        evaluator_model=evaluator_model,
        objective_check_api_base=objective_check_api_base,
        objective_check_api_key=objective_check_api_key,
        objective_check_model=objective_check_model,
        stub_user_id=stub_user_id,
    )
