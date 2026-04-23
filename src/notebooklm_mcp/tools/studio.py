from __future__ import annotations
from ..backends.base import NotebookLMBackend
from ..models.common import StudioOptions, StudioArtifactType


async def studio_create(
    backend: NotebookLMBackend,
    notebook_id: str,
    artifact_type: StudioArtifactType,
    opts: StudioOptions,
) -> dict:
    backend.require("studio", "studio_create")
    return await backend.studio_create(notebook_id, artifact_type, **opts.model_dump())


async def studio_status(backend: NotebookLMBackend, notebook_id: str) -> dict:
    backend.require("studio", "studio_status")
    return await backend.studio_status(notebook_id)


async def studio_delete(
    backend: NotebookLMBackend, notebook_id: str, artifact_id: str
) -> dict:
    backend.require("studio", "studio_delete")
    return await backend.studio_delete(notebook_id, artifact_id)


async def studio_revise(
    backend: NotebookLMBackend,
    notebook_id: str,
    artifact_id: str,
    slide_instructions: list[dict],
) -> dict:
    backend.require("studio", "studio_revise")
    return await backend.studio_revise(notebook_id, artifact_id, slide_instructions)
