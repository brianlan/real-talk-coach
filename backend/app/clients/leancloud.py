from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class LeanCloudError(Exception):
    message: str
    status_code: int | None = None
    body: str | None = None

    def __str__(self) -> str:
        return self.message


class LeanCloudClient:
    def __init__(
        self,
        *,
        app_id: str,
        app_key: str,
        master_key: str,
        server_url: str,
        timeout: float = 10.0,
        retries: int = 2,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._retries = retries
        self._client = httpx.AsyncClient(
            base_url=server_url,
            timeout=timeout,
            transport=transport,
            headers={
                "X-LC-Id": app_id,
                "X-LC-Key": f"{master_key},master",
                "Accept": "application/json",
            },
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        last_error: Exception | None = None
        for attempt in range(self._retries + 1):
            try:
                response = await self._client.request(method, path, **kwargs)
            except httpx.RequestError as exc:
                last_error = exc
            else:
                if response.status_code >= 500:
                    last_error = LeanCloudError(
                        f"LeanCloud error {response.status_code}",
                        status_code=response.status_code,
                        body=response.text,
                    )
                else:
                    return response
            if attempt < self._retries:
                continue
        raise LeanCloudError("LeanCloud request failed") from last_error

    async def request_json(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        response = await self._request(method, path, **kwargs)
        if not response.is_success:
            raise LeanCloudError(
                f"LeanCloud error {response.status_code}: {response.text}",
                status_code=response.status_code,
                body=response.text,
            )
        if not response.text:
            return {}
        return response.json()

    async def get_json(self, path: str, **kwargs: Any) -> dict[str, Any]:
        return await self.request_json("GET", path, **kwargs)

    async def post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.request_json("POST", path, json=payload)

    async def delete_json(self, path: str) -> dict[str, Any]:
        return await self.request_json("DELETE", path)

    async def create_signed_urls(
        self, urls: list[str], ttl_seconds: int = 900
    ) -> dict[str, str]:
        payload = {"urls": urls, "ttl": ttl_seconds}
        response = await self.post_json("/1.1/fileTokens", payload)
        signed_urls = response.get("signedUrls")
        if not isinstance(signed_urls, dict):
            raise LeanCloudError("LeanCloud signed URL response missing 'signedUrls'")
        return signed_urls
