import json

import httpx
import pytest

from app.clients.llm import EvaluatorClient, LLMError, QwenClient


@pytest.mark.asyncio
async def test_qwen_generate_retries_and_parses():
    calls = {"count": 0}

    async def handler(request):
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(502, text="bad gateway")
        payload = json.loads(request.content)
        assert payload["model"] == "qwen3-omni-flash"
        assert request.headers["Authorization"].startswith("Bearer ")
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    client = QwenClient(
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key="secret",
        retries=1,
        transport=httpx.MockTransport(handler),
    )

    result = await client.generate({"model": "qwen3-omni-flash"})

    assert result["choices"][0]["message"]["content"] == "ok"
    assert calls["count"] == 2

    await client.close()


@pytest.mark.asyncio
async def test_qwen_asr_requires_text_field():
    async def handler(request):
        return httpx.Response(200, json={"choices": [{"message": {"content": ""}}]})

    client = QwenClient(
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key="secret",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(LLMError) as exc:
        await client.asr({"model": "qwen-asr", "input": "ZGF0YQ==", "stream": False})

    assert "Missing 'text'" in str(exc.value)

    await client.close()


@pytest.mark.asyncio
async def test_evaluator_retries_on_request_error():
    calls = {"count": 0}

    async def handler(request):
        calls["count"] += 1
        if calls["count"] == 1:
            raise httpx.ReadTimeout("timeout", request=request)
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    client = EvaluatorClient(
        base_url="https://api.chataiapi.com/v1",
        api_key="secret",
        retries=1,
        transport=httpx.MockTransport(handler),
    )

    result = await client.evaluate({"model": "gpt-5-mini"})

    assert result["choices"][0]["message"]["content"] == "ok"
    assert calls["count"] == 2

    await client.close()
