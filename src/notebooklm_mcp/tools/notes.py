from __future__ import annotations
from ..backends.base import NotebookLMBackend


async def note_create(
    backend: NotebookLMBackend, notebook_id: str, content: str, title: str = ""
) -> dict:
    backend.require("notes", "note_create")
    return await backend.note_create(notebook_id, content, title)


async def note_list(backend: NotebookLMBackend, notebook_id: str) -> dict:
    backend.require("notes", "note_list")
    return await backend.note_list(notebook_id)


async def note_update(
    backend: NotebookLMBackend,
    notebook_id: str,
    note_id: str,
    content: str,
    title: str = "",
) -> dict:
    backend.require("notes", "note_update")
    return await backend.note_update(notebook_id, note_id, content, title)


async def note_delete(
    backend: NotebookLMBackend, notebook_id: str, note_id: str
) -> dict:
    backend.require("notes", "note_delete")
    return await backend.note_delete(notebook_id, note_id)
