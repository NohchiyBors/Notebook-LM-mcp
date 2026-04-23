from __future__ import annotations
from ..backends.base import NotebookLMBackend
from ..models.common import NotebookShareGrant, WebShareRole


async def notebook_create(backend: NotebookLMBackend, title: str) -> dict:
    return await backend.notebook_create(title)


async def notebook_get(backend: NotebookLMBackend, notebook_id: str) -> dict:
    return await backend.notebook_get(notebook_id)


async def notebook_list(backend: NotebookLMBackend, page_size: int = 100) -> dict:
    return await backend.notebook_list(page_size)


async def notebook_delete(
    backend: NotebookLMBackend, notebook_ids: list[str]
) -> dict:
    return await backend.notebook_delete(notebook_ids)


async def notebook_rename(
    backend: NotebookLMBackend, notebook_id: str, new_title: str
) -> dict:
    backend.require("notebook_rename", "notebook_rename")
    return await backend.notebook_rename(notebook_id, new_title)


async def notebook_describe(backend: NotebookLMBackend, notebook_id: str) -> dict:
    backend.require("notebook_describe", "notebook_describe")
    return await backend.notebook_describe(notebook_id)


async def notebook_share(
    backend: NotebookLMBackend,
    notebook_id: str,
    grants: list[dict],
) -> dict:
    return await backend.notebook_share(notebook_id, grants)


async def notebook_share_public(
    backend: NotebookLMBackend, notebook_id: str, is_public: bool
) -> dict:
    backend.require("share_public", "notebook_share_public")
    return await backend.notebook_share_public(notebook_id, is_public)


async def notebook_share_status(
    backend: NotebookLMBackend, notebook_id: str
) -> dict:
    backend.require("share_public", "notebook_share_status")
    return await backend.notebook_share_status(notebook_id)
