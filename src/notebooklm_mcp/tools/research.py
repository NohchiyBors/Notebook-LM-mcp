from __future__ import annotations
from ..backends.base import NotebookLMBackend
from ..models.common import ResearchSource, ResearchMode


async def research_start(
    backend: NotebookLMBackend,
    notebook_id: str,
    query: str,
    source: ResearchSource = "web",
    mode: ResearchMode = "fast",
) -> dict:
    backend.require("research", "research_start")
    return await backend.research_start(notebook_id, query, source, mode)


async def research_status(
    backend: NotebookLMBackend, notebook_id: str, task_id: str
) -> dict:
    backend.require("research", "research_status")
    return await backend.research_status(notebook_id, task_id)


async def research_import(
    backend: NotebookLMBackend,
    notebook_id: str,
    task_id: str,
    source_indices: list[int] | None = None,
) -> dict:
    backend.require("research", "research_import")
    return await backend.research_import(notebook_id, task_id, source_indices)
