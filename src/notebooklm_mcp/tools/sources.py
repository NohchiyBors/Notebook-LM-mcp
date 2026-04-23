from __future__ import annotations
from ..backends.base import NotebookLMBackend
from ..models.common import SourceBatchItem, DriveDocType


def _item_to_dict(item: SourceBatchItem) -> dict:
    return {
        "kind": item.kind,
        "url": item.url,
        "text": item.text,
        "document_id": item.document_id,
        "doc_type": item.doc_type,
        "youtube_url": item.youtube_url,
        "display_name": item.display_name,
    }


async def source_add_url(
    backend: NotebookLMBackend, notebook_id: str, url: str, display_name: str = ""
) -> dict:
    return await backend.source_add(
        notebook_id, [{"kind": "web", "url": url, "display_name": display_name}]
    )


async def source_add_urls(
    backend: NotebookLMBackend, notebook_id: str, urls: list[str]
) -> dict:
    contents = [{"kind": "web", "url": u, "display_name": ""} for u in urls]
    return await backend.source_add(notebook_id, contents)


async def source_add_text(
    backend: NotebookLMBackend, notebook_id: str, text: str, title: str = ""
) -> dict:
    return await backend.source_add(
        notebook_id, [{"kind": "text", "text": text, "display_name": title}]
    )


async def source_add_drive(
    backend: NotebookLMBackend,
    notebook_id: str,
    document_id: str,
    doc_type: DriveDocType = "doc",
    display_name: str = "",
) -> dict:
    return await backend.source_add(
        notebook_id,
        [{"kind": "drive", "document_id": document_id, "doc_type": doc_type, "display_name": display_name}],
    )


async def source_add_youtube(
    backend: NotebookLMBackend, notebook_id: str, youtube_url: str
) -> dict:
    return await backend.source_add(
        notebook_id, [{"kind": "youtube", "youtube_url": youtube_url}]
    )


async def source_add_batch(
    backend: NotebookLMBackend, notebook_id: str, items: list[SourceBatchItem]
) -> dict:
    return await backend.source_add(notebook_id, [_item_to_dict(i) for i in items])


async def source_upload_file(
    backend: NotebookLMBackend,
    notebook_id: str,
    file_path: str,
    display_name: str = "",
) -> dict:
    return await backend.source_upload_file(notebook_id, file_path, display_name)


async def source_get(
    backend: NotebookLMBackend, notebook_id: str, source_id: str
) -> dict:
    return await backend.source_get(notebook_id, source_id)


async def source_delete(
    backend: NotebookLMBackend, notebook_id: str, source_ids: list[str]
) -> dict:
    return await backend.source_delete(notebook_id, source_ids)


async def source_rename(
    backend: NotebookLMBackend, notebook_id: str, source_id: str, new_title: str
) -> dict:
    backend.require("source_rename", "source_rename")
    return await backend.source_rename(notebook_id, source_id, new_title)


async def source_sync_drive(
    backend: NotebookLMBackend, source_ids: list[str]
) -> dict:
    backend.require("source_sync_drive", "source_sync_drive")
    return await backend.source_sync_drive(source_ids)


async def source_describe(backend: NotebookLMBackend, source_id: str) -> dict:
    backend.require("source_describe", "source_describe")
    return await backend.source_describe(source_id)
