from __future__ import annotations
from ..backends.base import NotebookLMBackend
from ..models.common import ExportType


async def export_artifact(
    backend: NotebookLMBackend,
    notebook_id: str,
    artifact_id: str,
    export_type: ExportType,
    title: str = "",
) -> dict:
    backend.require("exports", "export_artifact")
    return await backend.export_artifact(notebook_id, artifact_id, export_type, title)


async def download_artifact(
    backend: NotebookLMBackend,
    notebook_id: str,
    artifact_type: str,
    output_path: str,
    artifact_id: str | None = None,
) -> dict:
    backend.require("downloads", "download_artifact")
    return await backend.download_artifact(
        notebook_id, artifact_type, output_path, artifact_id
    )
