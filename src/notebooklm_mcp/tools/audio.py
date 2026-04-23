from __future__ import annotations
from ..backends.base import NotebookLMBackend


async def audio_overview_create(
    backend: NotebookLMBackend,
    notebook_id: str,
    source_ids: list[str] | None = None,
    episode_focus: str = "",
    language_code: str = "en",
) -> dict:
    return await backend.audio_overview_create(
        notebook_id, source_ids, episode_focus, language_code
    )


async def audio_overview_delete(
    backend: NotebookLMBackend, notebook_id: str
) -> dict:
    return await backend.audio_overview_delete(notebook_id)
