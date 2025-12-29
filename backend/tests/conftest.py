import httpx
import pytest

from app.clients.leancloud import LeanCloudClient
from app.clients.llm import EvaluatorClient, QwenClient


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
