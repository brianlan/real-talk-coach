import pytest

from app.config import SettingsError, load_settings


def _set_required_envs(monkeypatch):
    monkeypatch.setenv("MONGO_HOST", "localhost")
    monkeypatch.setenv("MONGO_PORT", "27017")
    monkeypatch.setenv("MONGO_DB", "real-talk-coach")
    monkeypatch.setenv("MINIO_ENDPOINT", "localhost:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "minioadmin")
    monkeypatch.setenv("MINIO_SECRET_KEY", "minioadmin")
    monkeypatch.setenv("MINIO_BUCKET", "audio")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "dash")
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_BASE", "https://api.chataiapi.com/v1")
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_KEY", "secret")
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_MODEL", "gpt-5-mini")
    monkeypatch.setenv("EVALUATOR_MODEL", "gpt-5-mini")
    monkeypatch.setenv("OBJECTIVE_CHECK_API_KEY", "secret")
    monkeypatch.setenv("OBJECTIVE_CHECK_MODEL", "gpt-5-mini")
    monkeypatch.setenv("STUB_USER_ID", "pilot-user")
    monkeypatch.setenv("ADMIN_ACCESS_TOKEN", "admin-token")


def test_missing_required_envs_raise_actionable_error(monkeypatch):
    for name in [
        "MONGO_HOST",
        "MONGO_PORT",
        "MONGO_DB",
        "DASHSCOPE_API_KEY",
        "OPENAI_COMPATIBLE_API_BASE",
        "OPENAI_COMPATIBLE_API_KEY",
        "OPENAI_COMPATIBLE_API_MODEL",
        "EVALUATOR_MODEL",
        "OBJECTIVE_CHECK_API_KEY",
        "OBJECTIVE_CHECK_MODEL",
        "STUB_USER_ID",
        "ADMIN_ACCESS_TOKEN",
    ]:
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(SettingsError) as exc:
        load_settings()

    message = str(exc.value)
    assert "Missing required environment variable" in message
    assert "DASHSCOPE_API_KEY" in message


def test_invalid_urls_are_rejected(monkeypatch):
    _set_required_envs(monkeypatch)
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_BASE", "not-a-url")

    with pytest.raises(SettingsError) as exc:
        load_settings()

    assert "Invalid URL for OPENAI_COMPATIBLE_API_BASE" in str(exc.value)


def test_objective_check_base_defaults_to_evaluator_base(monkeypatch):
    _set_required_envs(monkeypatch)
    monkeypatch.delenv("OBJECTIVE_CHECK_API_BASE", raising=False)

    settings = load_settings()

    assert settings.objective_check_api_base == settings.openai_compatible_api_base


def test_volcengine_envs_are_optional_and_empty_is_treated_as_missing(monkeypatch):
    _set_required_envs(monkeypatch)
    monkeypatch.setenv("VOLCENGINE_ACCESS_KEY_ID", "")
    monkeypatch.setenv("VOLCENGINE_SECRET_ACCESS_KEY", "")
    monkeypatch.setenv("VOLCENGINE_RTC_APP_ID", "")
    monkeypatch.setenv("VOLCENGINE_RTC_APP_KEY", "")
    monkeypatch.setenv("VOLCENGINE_VOICE_CHAT_ENDPOINT", "")
    monkeypatch.setenv("VOLCENGINE_VOICE_MODEL_ID", "")

    settings = load_settings()

    assert settings.volcengine_access_key_id is None
    assert settings.volcengine_secret_access_key is None
    assert settings.volcengine_rtc_app_id is None
    assert settings.volcengine_rtc_app_key is None
    assert settings.volcengine_voice_chat_endpoint is None
    assert settings.volcengine_voice_model_id is None
