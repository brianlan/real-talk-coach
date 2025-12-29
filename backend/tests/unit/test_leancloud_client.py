import httpx
import pytest

from app.clients.leancloud import LeanCloudClient, LeanCloudError


@pytest.mark.asyncio
async def test_retries_on_server_error():
    calls = {"count": 0}

    async def handler(request):
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(500, json={"error": "server"})
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    client = LeanCloudClient(
        app_id="app",
        app_key="key",
        master_key="master",
        server_url="https://api.leancloud.cn",
        retries=1,
        transport=transport,
    )

    result = await client.get_json("/1.1/classes/Scenario")

    assert result == {"ok": True}
    assert calls["count"] == 2

    await client.close()


@pytest.mark.asyncio
async def test_signed_url_helper():
    async def handler(request):
        return httpx.Response(200, json={"signedUrls": {"a": "b"}})

    transport = httpx.MockTransport(handler)
    client = LeanCloudClient(
        app_id="app",
        app_key="key",
        master_key="master",
        server_url="https://api.leancloud.cn",
        transport=transport,
    )

    result = await client.create_signed_urls(["a"], ttl_seconds=60)

    assert result == {"a": "b"}

    await client.close()


@pytest.mark.asyncio
async def test_error_surface_on_client_error():
    async def handler(request):
        return httpx.Response(400, text="bad request")

    transport = httpx.MockTransport(handler)
    client = LeanCloudClient(
        app_id="app",
        app_key="key",
        master_key="master",
        server_url="https://api.leancloud.cn",
        transport=transport,
    )

    with pytest.raises(LeanCloudError) as exc:
        await client.get_json("/1.1/classes/Scenario")

    assert exc.value.status_code == 400
    assert exc.value.body == "bad request"

    await client.close()
