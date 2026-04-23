from typing import Any
import httpx

from .auth import get_access_token


class NotebookLMClient:
    def __init__(self) -> None:
        self._http = httpx.AsyncClient(timeout=120.0)

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {get_access_token()}",
            "Content-Type": "application/json",
        }

    async def get(self, url: str, params: dict | None = None) -> Any:
        response = await self._http.get(url, headers=self._auth_headers(), params=params)
        _raise_for_status(response)
        return response.json()

    async def post(self, url: str, body: dict | None = None) -> Any:
        response = await self._http.post(url, headers=self._auth_headers(), json=body or {})
        _raise_for_status(response)
        return response.json()

    async def delete(self, url: str) -> Any:
        response = await self._http.delete(url, headers=self._auth_headers())
        _raise_for_status(response)
        return response.json()

    async def post_raw(
        self,
        url: str,
        data: bytes,
        content_type: str,
        extra_headers: dict[str, str] | None = None,
    ) -> Any:
        headers = self._auth_headers()
        headers["Content-Type"] = content_type
        if extra_headers:
            headers.update(extra_headers)
        response = await self._http.post(url, headers=headers, content=data)
        _raise_for_status(response)
        return response.json()

    async def download(self, url: str) -> bytes:
        headers = {"Authorization": f"Bearer {get_access_token()}"}
        response = await self._http.get(url, headers=headers)
        _raise_for_status(response)
        return response.content

    async def aclose(self) -> None:
        await self._http.aclose()


def _raise_for_status(response: httpx.Response) -> None:
    if response.is_error:
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        raise RuntimeError(
            f"API error {response.status_code}: {detail}"
        )


_client: NotebookLMClient | None = None


def get_client() -> NotebookLMClient:
    global _client
    if _client is None:
        _client = NotebookLMClient()
    return _client
