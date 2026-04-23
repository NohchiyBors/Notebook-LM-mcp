import base64
import mimetypes
from pathlib import Path
from typing import Literal

import aiofiles

from ..client import get_client
from ..config import get_settings
from ..models import PodcastContextInput

_PODCAST_BASE = "https://discoveryengine.googleapis.com/v1"


async def _inline_data_from_file_path(file_path: str) -> dict:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    async with aiofiles.open(path, "rb") as f:
        raw = await f.read()

    mime_type, _ = mimetypes.guess_type(str(path))
    return {
        "inlineData": {
            "mimeType": mime_type or "application/octet-stream",
            "data": base64.b64encode(raw).decode(),
        }
    }


async def _build_contexts_from_texts_and_files(
    texts: list[str] | None = None,
    file_paths: list[str] | None = None,
) -> list[dict]:
    contexts = [{"text": text} for text in (texts or [])]
    for file_path in file_paths or []:
        contexts.append(await _inline_data_from_file_path(file_path))
    return contexts


async def _build_contexts_from_inputs(
    contexts: list[PodcastContextInput],
) -> list[dict]:
    if not contexts:
        raise ValueError("At least one podcast context is required.")

    payloads: list[dict] = []
    for item in contexts:
        if item.kind == "text":
            payloads.append({"text": item.text})
        else:
            payloads.append(await _inline_data_from_file_path(item.file_path))
    return payloads


def _build_podcast_body(
    focus: str,
    contexts: list[dict],
    length: Literal["SHORT", "STANDARD"] = "STANDARD",
    title: str = "",
    description: str = "",
    language_code: str = "en",
) -> dict:
    if not contexts:
        raise ValueError("At least one podcast context is required.")

    body: dict = {
        "podcastConfig": {
            "focus": focus,
            "length": length,
        },
        "contexts": contexts,
    }
    if language_code:
        body["podcastConfig"]["languageCode"] = language_code
    if title:
        body["title"] = title
    if description:
        body["description"] = description
    return body


async def _podcast_create_raw(
    focus: str,
    contexts: list[dict],
    length: Literal["SHORT", "STANDARD"] = "STANDARD",
    title: str = "",
    description: str = "",
    language_code: str = "en",
) -> dict:
    cfg = get_settings()
    body = _build_podcast_body(focus, contexts, length, title, description, language_code)
    return await get_client().post(cfg.podcasts_url, body)


async def podcast_create(
    focus: str,
    length: Literal["SHORT", "STANDARD"] = "STANDARD",
    texts: list[str] | None = None,
    file_paths: list[str] | None = None,
    title: str = "",
    description: str = "",
    language_code: str = "en",
) -> dict:
    """
    Generate a podcast (audio overview without a notebook).

    - texts: list of plain-text strings to include as context
    - file_paths: list of local file paths (PDF, DOCX, MP3, etc.) encoded as base64
    - Total context must be < 100,000 tokens
    - Does NOT support CMEK
    """
    contexts = await _build_contexts_from_texts_and_files(texts, file_paths)
    return await _podcast_create_raw(
        focus,
        contexts,
        length=length,
        title=title,
        description=description,
        language_code=language_code,
    )


async def podcast_create_from_contexts(
    focus: str,
    contexts: list[PodcastContextInput],
    length: Literal["SHORT", "STANDARD"] = "STANDARD",
    title: str = "",
    description: str = "",
    language_code: str = "en",
) -> dict:
    """Generate a podcast from an ordered list of text/file context items."""
    payload_contexts = await _build_contexts_from_inputs(contexts)
    return await _podcast_create_raw(
        focus,
        payload_contexts,
        length=length,
        title=title,
        description=description,
        language_code=language_code,
    )


async def podcast_download(operation_name: str, output_path: str) -> str:
    """
    Download a completed podcast MP3 to a local file.

    operation_name: the 'name' field from podcast_create response,
                    e.g. 'projects/.../locations/global/operations/OP_ID'
    Returns the absolute path of the saved file.
    """
    url = f"{_PODCAST_BASE}/{operation_name}:download?alt=media"
    data = await get_client().download(url)

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(path, "wb") as f:
        await f.write(data)

    return str(path.resolve())
