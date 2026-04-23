from __future__ import annotations
import base64
import mimetypes
from pathlib import Path

import aiofiles

from ..backends.base import NotebookLMBackend
from ..models.common import PodcastContextItem, PodcastLength


async def _build_contexts(
    texts: list[str] | None,
    file_paths: list[str] | None,
) -> list[dict]:
    contexts: list[dict] = []
    for t in (texts or []):
        contexts.append({"text": t})
    for fp in (file_paths or []):
        path = Path(fp)
        if not path.exists():
            raise FileNotFoundError(f"Файл не найден: {fp}")
        async with aiofiles.open(path, "rb") as f:
            raw = await f.read()
        mime, _ = mimetypes.guess_type(str(path))
        contexts.append({
            "inlineData": {
                "mimeType": mime or "application/octet-stream",
                "data": base64.b64encode(raw).decode(),
            }
        })
    return contexts


async def podcast_create(
    backend: NotebookLMBackend,
    focus: str,
    length: PodcastLength = "STANDARD",
    texts: list[str] | None = None,
    file_paths: list[str] | None = None,
    title: str = "",
    description: str = "",
    language_code: str = "en",
) -> dict:
    backend.require("podcast", "podcast_create")
    contexts = await _build_contexts(texts, file_paths)
    if not contexts:
        raise ValueError("Укажите хотя бы один texts или file_paths")
    return await backend.podcast_create(
        focus, length, contexts, title, description, language_code
    )


async def podcast_create_from_items(
    backend: NotebookLMBackend,
    focus: str,
    items: list[PodcastContextItem],
    length: PodcastLength = "STANDARD",
    title: str = "",
    description: str = "",
    language_code: str = "en",
) -> dict:
    backend.require("podcast", "podcast_create")
    texts = [i.text for i in items if i.kind == "text"]
    files = [i.file_path for i in items if i.kind == "file"]
    contexts = await _build_contexts(texts, files)
    return await backend.podcast_create(
        focus, length, contexts, title, description, language_code
    )


async def podcast_download(
    backend: NotebookLMBackend, operation_name: str, output_path: str
) -> str:
    backend.require("podcast", "podcast_download")
    return await backend.podcast_download(operation_name, output_path)
