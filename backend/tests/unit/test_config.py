import pytest

from app.config import SettingsError, load_settings


def _set_required_envs(monkeypatch):
    monkeypatch.setenv("LEAN_APP_ID", "app")
    monkeypatch.setenv("LEAN_APP_KEY", "key")
    monkeypatch.setenv("LEAN_MASTER_KEY", "master")
    monkeypatch.setenv("LEAN_SERVER_URL", "https://api.leancloud.cn")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "dash")
    monkeypatch.setenv("CHATAI_API_BASE", "https://api.chataiapi.com/v1")
    monkeypatch.setenv("CHATAI_API_KEY", "secret")
    monkeypatch.setenv("CHATAI_API_MODEL", "gpt-5-mini")
    monkeypatch.setenv("EVALUATOR_MODEL", "gpt-5-mini")
    monkeypatch.setenv("OBJECTIVE_CHECK_API_KEY", "secret")
    monkeypatch.setenv("OBJECTIVE_CHECK_MODEL", "gpt-5-mini")
    monkeypatch.setenv("STUB_USER_ID", "pilot-user")


def test_missing_required_envs_raise_actionable_error(monkeypatch):
    for name in [
        "LEAN_APP_ID",
        "LEAN_APP_KEY",
        "LEAN_MASTER_KEY",
        "DASHSCOPE_API_KEY",
        "CHATAI_API_BASE",
        "CHATAI_API_KEY",
        "CHATAI_API_MODEL",
        "EVALUATOR_MODEL",
        "OBJECTIVE_CHECK_API_KEY",
        "OBJECTIVE_CHECK_MODEL",
        "STUB_USER_ID",
    ]:
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(SettingsError) as exc:
        load_settings()

    message = str(exc.value)
    assert "Missing required environment variable" in message
    assert "LEAN_APP_ID" in message


def test_invalid_urls_are_rejected(monkeypatch):
    _set_required_envs(monkeypatch)
    monkeypatch.setenv("LEAN_SERVER_URL", "not-a-url")

    with pytest.raises(SettingsError) as exc:
        load_settings()

    assert "Invalid URL for LEAN_SERVER_URL" in str(exc.value)


def test_objective_check_base_defaults_to_evaluator_base(monkeypatch):
    _set_required_envs(monkeypatch)
    monkeypatch.delenv("OBJECTIVE_CHECK_API_BASE", raising=False)

    settings = load_settings()

    assert settings.objective_check_api_base == settings.chatai_api_base
