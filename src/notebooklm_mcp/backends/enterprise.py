"""Enterprise backend — официальный NotebookLM Enterprise REST API."""
from __future__ import annotations
import base64
import mimetypes
from pathlib import Path
from typing import Any

import aiofiles
import httpx

from ..auth.gcloud import get_access_token
from ..config import get_settings
from .base import NotebookLMBackend

_PODCAST_BASE = "https://discoveryengine.googleapis.com/v1"


class EnterpriseBackend(NotebookLMBackend):
    _features = frozenset({"podcast"})

    def __init__(self) -> None:
        cfg = get_settings()
        if not cfg.project_number:
            raise RuntimeError(
                "NOTEBOOKLM_PROJECT_NUMBER обязателен для Enterprise режима"
            )
        self._http = httpx.AsyncClient(timeout=cfg.timeout)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {get_access_token()}",
            "Content-Type": "application/json",
        }

    async def _get(self, url: str, params: dict | None = None) -> Any:
        r = await self._http.get(url, headers=self._headers(), params=params)
        _raise(r)
        return r.json()

    async def _post(self, url: str, body: dict | None = None) -> Any:
        r = await self._http.post(url, headers=self._headers(), json=body or {})
        _raise(r)
        return r.json()

    async def _delete(self, url: str) -> Any:
        r = await self._http.delete(url, headers=self._headers())
        _raise(r)
        return r.json()

    async def _post_raw(
        self, url: str, data: bytes, content_type: str, extra: dict | None = None
    ) -> Any:
        h = self._headers()
        h["Content-Type"] = content_type
        if extra:
            h.update(extra)
        r = await self._http.post(url, headers=h, content=data)
        _raise(r)
        return r.json()

    # ── Notebooks ────────────────────────────────────────────────────────────

    async def notebook_create(self, title: str) -> dict:
        cfg = get_settings()
        return await self._post(cfg.notebooks_url, {"title": title})

    async def notebook_get(self, notebook_id: str) -> dict:
        cfg = get_settings()
        return await self._get(cfg.notebook_url(notebook_id))

    async def notebook_list(self, page_size: int = 100) -> dict:
        cfg = get_settings()
        url = f"{cfg.notebooks_url}:listRecentlyViewed"
        return await self._get(url, params={"pageSize": min(page_size, 500)})

    async def notebook_delete(self, notebook_ids: list[str]) -> dict:
        cfg = get_settings()
        url = f"{cfg.notebooks_url}:batchDelete"
        names = [cfg.notebook_name(nid) for nid in notebook_ids]
        return await self._post(url, {"names": names})

    async def notebook_share(self, notebook_id: str, grants: list[dict]) -> dict:
        cfg = get_settings()
        url = f"{cfg.notebook_url(notebook_id)}:share"
        account_roles = [{"email": g["email"], "role": g["role"]} for g in grants]
        return await self._post(url, {"accountAndRoles": account_roles})

    # ── Sources ──────────────────────────────────────────────────────────────

    async def source_add(self, notebook_id: str, user_contents: list[dict]) -> dict:
        cfg = get_settings()
        url = f"{cfg.sources_url(notebook_id)}:batchCreate"
        contents = [_build_enterprise_content(c) for c in user_contents]
        return await self._post(url, {"userContents": contents})

    async def source_upload_file(
        self, notebook_id: str, file_path: str, display_name: str
    ) -> dict:
        cfg = get_settings()
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Файл не найден: {file_path}")

        mime, _ = mimetypes.guess_type(str(path))
        mime = mime or "application/octet-stream"
        name = display_name or path.name

        async with aiofiles.open(path, "rb") as f:
            data = await f.read()

        return await self._post_raw(
            cfg.source_upload_url(notebook_id),
            data=data,
            content_type=mime,
            extra={
                "X-Goog-Upload-File-Name": name,
                "X-Goog-Upload-Protocol": "raw",
            },
        )

    async def source_get(self, notebook_id: str, source_id: str) -> dict:
        cfg = get_settings()
        return await self._get(cfg.source_url(notebook_id, source_id))

    async def source_delete(self, notebook_id: str, source_ids: list[str]) -> dict:
        cfg = get_settings()
        url = f"{cfg.sources_url(notebook_id)}:batchDelete"
        names = [cfg.source_name(notebook_id, sid) for sid in source_ids]
        return await self._post(url, {"names": names})

    # ── Audio overview ────────────────────────────────────────────────────────

    async def audio_overview_create(
        self,
        notebook_id: str,
        source_ids: list[str] | None,
        episode_focus: str,
        language_code: str,
    ) -> dict:
        cfg = get_settings()
        body: dict = {"languageCode": language_code}
        if source_ids:
            body["sourceIds"] = [{"id": sid} for sid in source_ids]
        if episode_focus:
            body["episodeFocus"] = episode_focus
        return await self._post(cfg.audio_overviews_url(notebook_id), body)

    async def audio_overview_delete(self, notebook_id: str) -> dict:
        cfg = get_settings()
        url = f"{cfg.audio_overviews_url(notebook_id)}/default"
        return await self._delete(url)

    # ── Podcast ───────────────────────────────────────────────────────────────

    async def podcast_create(
        self,
        focus: str,
        length: str,
        contexts: list[dict],
        title: str,
        description: str,
        language_code: str,
    ) -> dict:
        cfg = get_settings()
        body: dict = {
            "podcastConfig": {
                "focus": focus,
                "length": length,
                "languageCode": language_code,
            },
            "contexts": contexts,
        }
        if title:
            body["title"] = title
        if description:
            body["description"] = description
        return await self._post(cfg.podcasts_url, body)

    async def podcast_download(self, operation_name: str, output_path: str) -> str:
        url = f"{_PODCAST_BASE}/{operation_name}:download?alt=media"
        h = {"Authorization": f"Bearer {get_access_token()}"}
        r = await self._http.get(url, headers=h)
        _raise(r)

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(path, "wb") as f:
            await f.write(r.content)
        return str(path.resolve())

    async def aclose(self) -> None:
        await self._http.aclose()


# ── Helpers ───────────────────────────────────────────────────────────────────

_DRIVE_MIME = {
    "doc":   "application/vnd.google-apps.document",
    "slide": "application/vnd.google-apps.presentation",
}


def _build_enterprise_content(c: dict) -> dict:
    kind = c.get("kind")
    name = c.get("display_name", "")

    if kind == "web":
        body: dict = {"url": c["url"]}
        if name:
            body["sourceName"] = name
        return {"webContent": body}

    if kind == "text":
        body = {"content": c["text"]}
        if name:
            body["sourceName"] = name
        return {"textContent": body}

    if kind == "drive":
        body = {
            "documentId": c["document_id"],
            "mimeType": _DRIVE_MIME.get(c.get("doc_type", "doc"), _DRIVE_MIME["doc"]),
        }
        if name:
            body["sourceName"] = name
        return {"googleDriveContent": body}

    if kind == "youtube":
        return {"videoContent": {"youtubeUrl": c["youtube_url"]}}

    raise ValueError(f"Неизвестный тип источника: {kind}")


def _raise(r: httpx.Response) -> None:
    if r.is_error:
        try:
            detail = r.json()
        except Exception:
            detail = r.text
        raise RuntimeError(f"API ошибка {r.status_code}: {detail}")
