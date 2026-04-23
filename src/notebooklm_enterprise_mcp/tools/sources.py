import mimetypes
from pathlib import Path

import aiofiles

from ..client import get_client
from ..config import get_settings
from ..models import DriveDocType, SourceBatchItem

_DRIVE_MIME = {
    "doc": "application/vnd.google-apps.document",
    "slide": "application/vnd.google-apps.presentation",
}


def _build_user_content(item: SourceBatchItem) -> dict:
    if item.kind == "drive":
        content: dict = {
            "documentId": item.document_id,
            "mimeType": _DRIVE_MIME[item.doc_type],
        }
        if item.display_name:
            content["sourceName"] = item.display_name
        return {"googleDriveContent": content}

    if item.kind == "text":
        content = {"content": item.text}
        if item.display_name:
            content["sourceName"] = item.display_name
        return {"textContent": content}

    if item.kind == "web":
        content = {"url": item.url}
        if item.display_name:
            content["sourceName"] = item.display_name
        return {"webContent": content}

    if item.kind == "youtube":
        return {"videoContent": {"youtubeUrl": item.youtube_url}}

    raise ValueError(f"Unsupported source kind: {item.kind}")


async def source_batch_create(
    notebook_id: str,
    items: list[SourceBatchItem],
) -> dict:
    """Add one or more mixed source types in a single batchCreate call."""
    if not items:
        raise ValueError("At least one source item is required.")

    cfg = get_settings()
    endpoint = f"{cfg.sources_url(notebook_id)}:batchCreate"
    return await get_client().post(
        endpoint,
        {"userContents": [_build_user_content(item) for item in items]},
    )


async def source_add_url(
    notebook_id: str,
    url: str,
    display_name: str = "",
) -> dict:
    """Add a web page URL as a source."""
    item = SourceBatchItem(kind="web", url=url, display_name=display_name)
    return await source_batch_create(notebook_id, [item])


async def source_add_urls(
    notebook_id: str,
    urls: list[str],
) -> dict:
    """Add multiple web page URLs as sources in one request."""
    items = [SourceBatchItem(kind="web", url=url) for url in urls]
    return await source_batch_create(notebook_id, items)


async def source_add_text(
    notebook_id: str,
    text: str,
    title: str = "",
) -> dict:
    """Add plain text as a source."""
    item = SourceBatchItem(kind="text", text=text, display_name=title)
    return await source_batch_create(notebook_id, [item])


async def source_add_drive(
    notebook_id: str,
    document_id: str,
    doc_type: DriveDocType = "doc",
    display_name: str = "",
) -> dict:
    """Add a Google Docs or Google Slides file as a source."""
    item = SourceBatchItem(
        kind="drive",
        document_id=document_id,
        doc_type=doc_type,
        display_name=display_name,
    )
    return await source_batch_create(notebook_id, [item])


async def source_add_youtube(notebook_id: str, youtube_url: str) -> dict:
    """Add a YouTube video as a source."""
    item = SourceBatchItem(kind="youtube", youtube_url=youtube_url)
    return await source_batch_create(notebook_id, [item])


async def source_upload_file(
    notebook_id: str,
    file_path: str,
    display_name: str = "",
) -> dict:
    """Upload a local file (PDF, DOCX, MP3, PNG, etc.) as a source."""
    cfg = get_settings()
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    mime_type, _ = mimetypes.guess_type(str(path))
    if not mime_type:
        mime_type = "application/octet-stream"

    name = display_name or path.name
    url = cfg.source_upload_url(notebook_id)

    async with aiofiles.open(path, "rb") as f:
        data = await f.read()

    return await get_client().post_raw(
        url,
        data=data,
        content_type=mime_type,
        extra_headers={"X-Goog-Upload-File-Name": name, "X-Goog-Upload-Protocol": "raw"},
    )


async def source_get(notebook_id: str, source_id: str) -> dict:
    """Get source details including word count and status."""
    cfg = get_settings()
    return await get_client().get(cfg.source_url(notebook_id, source_id))


async def source_delete(notebook_id: str, source_ids: list[str]) -> dict:
    """Batch delete sources from a notebook."""
    cfg = get_settings()
    endpoint = f"{cfg.sources_url(notebook_id)}:batchDelete"
    names = [cfg.source_name(notebook_id, sid) for sid in source_ids]
    return await get_client().post(endpoint, {"names": names})
