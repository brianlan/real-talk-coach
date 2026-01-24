import httpx
import pytest

from app.clients.leancloud import LeanCloudClient
from app.clients.llm import EvaluatorClient, QwenClient


@pytest.fixture(autouse=True)
def _set_default_env(monkeypatch):
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
    monkeypatch.setenv("ADMIN_ACCESS_TOKEN", "admin-token")


@pytest.fixture
async def leancloud_client():
    async def handler(request):
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    client = LeanCloudClient(
        app_id="app",
        app_key="key",
        master_key="master",
        server_url="https://api.leancloud.cn",
        transport=transport,
    )
    yield client
    await client.close()


@pytest.fixture
async def qwen_client():
    async def handler(request):
        if request.url.path.endswith("/chat/completions"):
            return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})
        return httpx.Response(200, json={"text": "ok"})

    transport = httpx.MockTransport(handler)
    client = QwenClient(
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key="secret",
        transport=transport,
    )
    yield client
    await client.close()


@pytest.fixture
async def evaluator_client():
    async def handler(request):
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    transport = httpx.MockTransport(handler)
    client = EvaluatorClient(
        base_url="https://api.chataiapi.com/v1",
        api_key="secret",
        transport=transport,
    )
    yield client
    await client.close()
