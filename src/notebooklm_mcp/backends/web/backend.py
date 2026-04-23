"""Web backend — реализация через notebooklm.google.com batchexecute RPC."""
from __future__ import annotations
import mimetypes
import uuid
from pathlib import Path
from typing import Any

import aiofiles

from ..base import NotebookLMBackend
from .client import get_web_client
from .parsers import safe_get
from . import rpc as R


class WebBackend(NotebookLMBackend):
    _features = frozenset({
        "notebook_rename", "notebook_describe",
        "source_rename", "source_sync_drive", "source_describe",
        "studio", "query", "research", "notes",
        "share_public", "exports", "downloads",
    })

    def _c(self):
        return get_web_client()

    # ── Notebooks ────────────────────────────────────────────────────────────

    async def notebook_create(self, title: str) -> dict:
        result = await self._c().call(R.RPC_NOTEBOOK_CREATE, [None, title, [2]])
        notebook_id = safe_get(result, 0, 0) or safe_get(result, 1, 0)
        return {"notebookId": notebook_id, "title": title}

    async def notebook_get(self, notebook_id: str) -> dict:
        result = await self._c().call(
            R.RPC_NOTEBOOK_GET, [[2], notebook_id],
            source_path=f"/notebook/{notebook_id}",
        )
        return _parse_notebook(result, notebook_id)

    async def notebook_list(self, page_size: int = 100) -> dict:
        # Формат параметров как у актуального web-клиента NotebookLM: [null, 1, null, [2]]
        result = await self._c().call(R.RPC_NOTEBOOK_LIST, [None, 1, None, [2]])
        notebooks = []
        rows = safe_get(result, 0) if isinstance(result, list) and result else result
        if not isinstance(rows, list):
            rows = []
        for item in rows:
            if not isinstance(item, list) or len(item) < 3:
                continue
            title = item[0] if isinstance(item[0], str) else "Untitled"
            sources = item[1] if isinstance(item[1], list) else []
            nid = item[2]
            notebooks.append({
                "notebookId": nid,
                "title": title,
                "sourceCount": len(sources),
            })
        if page_size >= 0 and len(notebooks) > page_size:
            notebooks = notebooks[:page_size]
        return {"notebooks": notebooks}

    async def notebook_delete(self, notebook_ids: list[str]) -> dict:
        for nid in notebook_ids:
            await self._c().call(R.RPC_NOTEBOOK_DELETE, [[2], nid])
        return {"deleted": notebook_ids}

    async def notebook_rename(self, notebook_id: str, new_title: str) -> dict:
        await self._c().call(R.RPC_NOTEBOOK_RENAME, [[2], notebook_id, new_title])
        return {"notebookId": notebook_id, "title": new_title}

    async def notebook_describe(self, notebook_id: str) -> dict:
        result = await self._c().call(
            R.RPC_NOTEBOOK_DESCRIBE, [[2], notebook_id],
            source_path=f"/notebook/{notebook_id}",
        )
        return {
            "summary": safe_get(result, 0, 0, default=""),
            "suggested_topics": safe_get(result, 1) or [],
        }

    async def notebook_share(self, notebook_id: str, grants: list[dict]) -> dict:
        payload = [[g["email"], _web_role_code(g["role"])] for g in grants]
        await self._c().call(
            R.RPC_SHARE_SET, [[2], notebook_id, payload],
            source_path=f"/notebook/{notebook_id}",
        )
        return {"shared": True}

    async def notebook_share_public(self, notebook_id: str, is_public: bool) -> dict:
        await self._c().call(
            R.RPC_SHARE_SET,
            [[2], notebook_id, None, 1 if is_public else 0],
            source_path=f"/notebook/{notebook_id}",
        )
        return {"is_public": is_public}

    async def notebook_share_status(self, notebook_id: str) -> dict:
        result = await self._c().call(
            R.RPC_SHARE_STATUS, [[2], notebook_id],
            source_path=f"/notebook/{notebook_id}",
        )
        return {
            "is_public": bool(safe_get(result, 0, 2)),
            "collaborators": safe_get(result, 0, 1) or [],
        }

    # ── Sources ──────────────────────────────────────────────────────────────

    async def source_add(self, notebook_id: str, user_contents: list[dict]) -> dict:
        """
        user_contents — список dict с полями kind, url, text, document_id, doc_type, youtube_url, display_name
        """
        source_params = [_build_source_param(c) for c in user_contents]
        result = await self._c().call(
            R.RPC_SOURCE_ADD,
            [source_params, notebook_id, [2], [1, None, None, None, None, None, None, None, None, None, None, None, None, None, [1]]],
            source_path=f"/notebook/{notebook_id}",
        )
        sources = []
        raw = safe_get(result, 0) or []
        for item in raw:
            sources.append({
                "sourceId": safe_get(item, 0),
                "title": safe_get(item, 1),
                "status": safe_get(item, 4),
            })
        return {"sources": sources}

    async def source_upload_file(
        self, notebook_id: str, file_path: str, display_name: str
    ) -> dict:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Файл не найден: {file_path}")

        name = display_name or path.name
        mime, _ = mimetypes.guess_type(str(path))
        mime = mime or "application/octet-stream"

        # Step 1: Зарегистрировать файл
        result = await self._c().call(
            R.RPC_SOURCE_FILE_INIT,
            [[[name]], notebook_id, [2], [1, None, None, None, None, None, None, None, None, None, None, None, None, None, [1]]],
            source_path=f"/notebook/{notebook_id}",
        )
        source_id = safe_get(result, 0, 0) or safe_get(result, 0)
        if not source_id:
            raise RuntimeError("Не удалось получить source_id при регистрации файла")

        # Steps 2-3: Загрузить файл
        async with aiofiles.open(path, "rb") as f:
            data = await f.read()

        await self._c().upload_file(notebook_id, source_id, name, data, mime)
        return {"sourceId": source_id, "title": name}

    async def source_get(self, notebook_id: str, source_id: str) -> dict:
        result = await self._c().call(
            R.RPC_SOURCE_GET, [[2], notebook_id, source_id],
            source_path=f"/notebook/{notebook_id}",
        )
        return {
            "sourceId": source_id,
            "title": safe_get(result, 0, 1, default=""),
            "wordCount": safe_get(result, 0, 2, default=0),
            "status": safe_get(result, 0, 4, default=""),
        }

    async def source_delete(self, notebook_id: str, source_ids: list[str]) -> dict:
        for sid in source_ids:
            await self._c().call(
                R.RPC_SOURCE_DELETE, [[2], notebook_id, sid],
                source_path=f"/notebook/{notebook_id}",
            )
        return {"deleted": source_ids}

    async def source_rename(
        self, notebook_id: str, source_id: str, new_title: str
    ) -> dict:
        await self._c().call(
            R.RPC_SOURCE_RENAME, [[2], notebook_id, source_id, new_title],
            source_path=f"/notebook/{notebook_id}",
        )
        return {"sourceId": source_id, "title": new_title}

    async def source_sync_drive(self, source_ids: list[str]) -> dict:
        await self._c().call(R.RPC_SOURCE_SYNC_DRIVE, [[2], source_ids])
        return {"synced": source_ids}

    async def source_describe(self, source_id: str) -> dict:
        result = await self._c().call(R.RPC_SOURCE_DESCRIBE, [[2], source_id])
        return {
            "summary": safe_get(result, 0, default=""),
            "keywords": safe_get(result, 1) or [],
        }

    # ── Audio overview ────────────────────────────────────────────────────────

    async def audio_overview_create(
        self,
        notebook_id: str,
        source_ids: list[str] | None,
        episode_focus: str,
        language_code: str,
    ) -> dict:
        sources_nested = [[[sid]] for sid in (source_ids or [])]
        audio_opts = [
            None,
            [
                episode_focus,
                R.AUDIO_LENGTH_CODE["default"],
                None,
                sources_nested or None,
                language_code,
                None,
                R.AUDIO_FORMAT_CODE["deep_dive"],
            ],
        ]
        result = await self._c().call(
            R.RPC_STUDIO_CREATE,
            [[2], notebook_id, [None, None, R.STUDIO_TYPE["audio"], sources_nested, None, None, audio_opts]],
            source_path=f"/notebook/{notebook_id}",
        )
        artifact_id = safe_get(result, 0, 0, default="")
        return {"artifactId": artifact_id, "status": "in_progress"}

    async def audio_overview_delete(self, notebook_id: str) -> dict:
        await self._c().call(
            R.RPC_STUDIO_DELETE, [[2], notebook_id, None, R.STUDIO_TYPE["audio"]],
            source_path=f"/notebook/{notebook_id}",
        )
        return {"deleted": True}

    # ── Studio ───────────────────────────────────────────────────────────────

    async def studio_create(
        self, notebook_id: str, artifact_type: str, **kwargs: Any
    ) -> dict:
        from ...models.common import StudioOptions
        opts = StudioOptions(**kwargs)
        sources_nested = [[[sid]] for sid in opts.source_ids]
        type_code = R.STUDIO_TYPE.get(artifact_type)
        if type_code is None:
            raise ValueError(f"Неизвестный тип артефакта: {artifact_type}")

        params = _build_studio_params(artifact_type, notebook_id, sources_nested, opts)
        result = await self._c().call(
            R.RPC_STUDIO_CREATE, params,
            source_path=f"/notebook/{notebook_id}",
        )
        artifact_id = safe_get(result, 0, 0, default="")
        return {"artifactId": artifact_id, "type": artifact_type, "status": "in_progress"}

    async def studio_status(self, notebook_id: str) -> dict:
        result = await self._c().call(
            R.RPC_STUDIO_POLL,
            [[2], notebook_id, 'NOT artifact.status = "ARTIFACT_STATUS_SUGGESTED"'],
            source_path=f"/notebook/{notebook_id}",
        )
        artifacts = []
        for item in (safe_get(result, 0) or []):
            if not isinstance(item, list):
                continue
            status_code = safe_get(item, 4, default=0)
            artifacts.append({
                "artifactId": safe_get(item, 0),
                "title": safe_get(item, 1),
                "type": safe_get(item, 2),
                "status": R.STUDIO_STATUS.get(status_code, "unknown"),
            })
        return {"artifacts": artifacts}

    async def studio_delete(self, notebook_id: str, artifact_id: str) -> dict:
        await self._c().call(
            R.RPC_STUDIO_DELETE, [[2], notebook_id, artifact_id],
            source_path=f"/notebook/{notebook_id}",
        )
        return {"deleted": artifact_id}

    async def studio_revise(
        self,
        notebook_id: str,
        artifact_id: str,
        slide_instructions: list[dict],
    ) -> dict:
        result = await self._c().call(
            R.RPC_STUDIO_REVISE_SLIDES,
            [[2], notebook_id, artifact_id, slide_instructions],
            source_path=f"/notebook/{notebook_id}",
        )
        new_id = safe_get(result, 0, 0, default="")
        return {"artifactId": new_id, "status": "in_progress"}

    # ── Query ─────────────────────────────────────────────────────────────────

    async def notebook_query(
        self,
        notebook_id: str,
        query: str,
        source_ids: list[str] | None = None,
        conversation_id: str | None = None,
    ) -> dict:
        sources = [[[sid]] for sid in (source_ids or [])]
        conv_id = conversation_id or str(uuid.uuid4())
        params = [sources, query, None, [2, None, [1]], conv_id]
        answer = await self._c().query(params)
        return {"answer": answer, "conversationId": conv_id}

    # ── Research ─────────────────────────────────────────────────────────────

    async def research_start(
        self, notebook_id: str, query: str, source: str, mode: str
    ) -> dict:
        source_code = R.RESEARCH_SOURCE_CODE.get(source, 1)
        mode_code = R.RESEARCH_MODE_CODE.get(mode, 1)
        rpc = R.RPC_RESEARCH_DEEP if mode == "deep" else R.RPC_RESEARCH_FAST
        result = await self._c().call(
            rpc, [[2], notebook_id, query, source_code, mode_code],
            source_path=f"/notebook/{notebook_id}",
        )
        task_id = safe_get(result, 0, default="")
        return {"taskId": task_id, "status": "in_progress"}

    async def research_status(self, notebook_id: str, task_id: str) -> dict:
        result = await self._c().call(
            R.RPC_RESEARCH_POLL, [[2], notebook_id, task_id],
            source_path=f"/notebook/{notebook_id}",
        )
        sources = safe_get(result, 0) or []
        status = safe_get(result, 1, default="in_progress")
        return {"taskId": task_id, "status": status, "sources": sources}

    async def research_import(
        self, notebook_id: str, task_id: str, source_indices: list[int] | None
    ) -> dict:
        await self._c().call(
            R.RPC_RESEARCH_IMPORT,
            [[2], notebook_id, task_id, source_indices or []],
            source_path=f"/notebook/{notebook_id}",
        )
        return {"imported": True}

    # ── Notes ─────────────────────────────────────────────────────────────────

    async def note_create(
        self, notebook_id: str, content: str, title: str
    ) -> dict:
        result = await self._c().call(
            R.RPC_NOTE_CREATE, [[2], notebook_id, title, content],
            source_path=f"/notebook/{notebook_id}",
        )
        note_id = safe_get(result, 0, default="")
        return {"noteId": note_id, "title": title}

    async def note_list(self, notebook_id: str) -> dict:
        result = await self._c().call(
            R.RPC_NOTE_LIST, [[2], notebook_id],
            source_path=f"/notebook/{notebook_id}",
        )
        notes = []
        for item in (safe_get(result, 0) or []):
            notes.append({
                "noteId": safe_get(item, 0),
                "title": safe_get(item, 1),
                "content": safe_get(item, 2),
            })
        return {"notes": notes}

    async def note_update(
        self, notebook_id: str, note_id: str, content: str, title: str
    ) -> dict:
        await self._c().call(
            R.RPC_NOTE_UPDATE, [[2], notebook_id, note_id, title, content],
            source_path=f"/notebook/{notebook_id}",
        )
        return {"noteId": note_id, "title": title}

    async def note_delete(self, notebook_id: str, note_id: str) -> dict:
        await self._c().call(
            R.RPC_NOTE_DELETE, [[2], notebook_id, note_id],
            source_path=f"/notebook/{notebook_id}",
        )
        return {"deleted": note_id}

    # ── Export / Download ─────────────────────────────────────────────────────

    async def export_artifact(
        self, notebook_id: str, artifact_id: str, export_type: str, title: str
    ) -> dict:
        type_code = 1 if export_type == "docs" else 2
        result = await self._c().call(
            R.RPC_EXPORT,
            [[2], notebook_id, artifact_id, type_code, title or None],
            source_path=f"/notebook/{notebook_id}",
        )
        url = safe_get(result, 0, default="")
        return {"url": url}

    async def download_artifact(
        self,
        notebook_id: str,
        artifact_type: str,
        output_path: str,
        artifact_id: str | None,
    ) -> dict:
        # Web режим: артефакты загружаются через ссылки из studio_status
        status = await self.studio_status(notebook_id)
        for art in status.get("artifacts", []):
            if artifact_id and art.get("artifactId") != artifact_id:
                continue
            url = art.get("url")
            if not url:
                continue
            client = get_web_client()
            data = await client._http.get(url)
            data.raise_for_status()
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(path, "wb") as f:
                await f.write(data.content)
            return {"path": str(path.resolve()), "artifactId": art.get("artifactId")}
        raise RuntimeError(f"Артефакт не найден или URL недоступен")

    # Podcast не поддерживается в web режиме (нет нужного API без Enterprise)
    async def podcast_create(self, *args, **kwargs) -> dict:
        raise NotImplementedError(
            "podcast_create доступен только в Enterprise режиме. "
            "Используйте audio_overview_create для генерации аудио в web режиме."
        )

    async def podcast_download(self, *args, **kwargs) -> str:
        raise NotImplementedError(
            "podcast_download доступен только в Enterprise режиме."
        )


# ── Вспомогательные функции ───────────────────────────────────────────────────

def _web_role_code(role: str) -> int:
    return {"PROJECT_ROLE_WRITER": 2, "PROJECT_ROLE_READER": 1, "PROJECT_ROLE_NOT_SHARED": 0}.get(role, 1)


def _build_source_param(content: dict) -> list:
    kind = content.get("kind")
    name = content.get("display_name", "")

    if kind == "web":
        url = content["url"]
        return [None, None, [url], None, None, None, None, None, None, None, 1]

    if kind == "text":
        return [None, [name, content["text"]], None, 2, None, None, None, None, None, None, 1]

    if kind == "drive":
        doc_id = content["document_id"]
        mime = R.DRIVE_MIME.get(content.get("doc_type", "doc"), R.DRIVE_MIME["doc"])
        return [[doc_id, mime, 1, name or doc_id], None, None, None, None, None, None, None, None, None, 1]

    if kind == "youtube":
        url = content["youtube_url"]
        return [None, None, None, None, None, None, None, [url], None, None, 1]

    raise ValueError(f"Неизвестный тип источника: {kind}")


def _build_studio_params(
    artifact_type: str, notebook_id: str, sources_nested: list, opts
) -> list:
    type_code = R.STUDIO_TYPE[artifact_type]

    if artifact_type == "audio":
        type_opts = [
            None,
            [
                opts.focus_prompt,
                R.AUDIO_LENGTH_CODE[opts.audio_length],
                None,
                sources_nested or None,
                opts.language_code,
                None,
                R.AUDIO_FORMAT_CODE[opts.audio_format],
            ],
        ]
    elif artifact_type == "video":
        type_opts = [None, [
            R.VIDEO_FORMAT_CODE[opts.video_format],
            R.VIDEO_STYLE_CODE[opts.visual_style],
        ]]
    elif artifact_type == "slide_deck":
        type_opts = [None, [
            R.SLIDE_FORMAT_CODE[opts.slide_format],
            R.SLIDE_LENGTH_CODE[opts.slide_length],
        ]]
    elif artifact_type == "report":
        type_opts = [None, [
            R.REPORT_FORMAT_CODE[opts.report_format],
            opts.custom_prompt or None,
        ]]
    elif artifact_type in ("flashcards", "quiz"):
        type_opts = [None, [R.DIFFICULTY_CODE[opts.difficulty], opts.question_count]]
    elif artifact_type == "infographic":
        type_opts = [None, [opts.orientation, opts.detail_level, opts.infographic_style]]
    elif artifact_type == "data_table":
        type_opts = [None, [opts.description]]
    else:
        type_opts = None

    return [
        [2],
        notebook_id,
        [None, None, type_code, sources_nested, None, None, type_opts],
    ]


def _parse_notebook(result: list, notebook_id: str) -> dict:
    return {
        "notebookId": notebook_id,
        "title": safe_get(result, 0, 1, default=""),
        "sourceCount": safe_get(result, 0, 3, default=0),
        "isShared": bool(safe_get(result, 0, 5)),
    }
