from typing import Literal

from fastmcp import FastMCP

from .models import (
    DriveDocType,
    NotebookRole,
    NotebookShareGrant,
    PodcastContextInput,
    SourceBatchItem,
)
from .tools.audio import audio_overview_create, audio_overview_delete
from .tools.notebooks import (
    notebook_create,
    notebook_delete,
    notebook_get,
    notebook_list,
    notebook_share,
    notebook_share_batch,
)
from .tools.operations import operation_get, operation_wait
from .tools.podcast import podcast_create, podcast_create_from_contexts, podcast_download
from .tools.sources import (
    source_add_drive,
    source_add_text,
    source_add_url,
    source_add_urls,
    source_add_youtube,
    source_batch_create,
    source_delete,
    source_get,
    source_upload_file,
)

mcp = FastMCP(
    name="notebooklm-enterprise",
    instructions=(
        "MCP server for NotebookLM Enterprise REST API. "
        "Requires NOTEBOOKLM_PROJECT_NUMBER for NotebookLM Enterprise notebook APIs. "
        "Standalone Podcast API follows the current Google docs and can additionally use "
        "NOTEBOOKLM_PROJECT_ID. "
        "Auth uses ADC, NOTEBOOKLM_GOOGLE_APPLICATION_CREDENTIALS, or "
        "NOTEBOOKLM_USE_GCLOUD_ACCESS_TOKEN=true. "
        "Google Drive sources require Google user credentials with Drive access, as documented by Google."
    ),
)

# ---------------------------------------------------------------------------
# Notebooks
# ---------------------------------------------------------------------------


@mcp.tool()
async def create_notebook(title: str) -> dict:
    """Create a new NotebookLM Enterprise notebook."""
    return await notebook_create(title)


@mcp.tool()
async def get_notebook(notebook_id: str) -> dict:
    """Get notebook details (title, sources, metadata, sharing status)."""
    return await notebook_get(notebook_id)


@mcp.tool()
async def list_notebooks(page_size: int = 500) -> dict:
    """List recently viewed notebooks. Max 500."""
    return await notebook_list(page_size)


@mcp.tool()
async def delete_notebooks(notebook_ids: list[str]) -> dict:
    """Permanently delete one or more notebooks by their IDs."""
    return await notebook_delete(notebook_ids)


@mcp.tool()
async def share_notebook(
    notebook_id: str,
    email: str,
    role: NotebookRole,
) -> dict:
    """
    Share a notebook with a user.

    Roles:
    - PROJECT_ROLE_OWNER: full control
    - PROJECT_ROLE_WRITER: edit (cannot delete/share)
    - PROJECT_ROLE_READER: view and interact only
    - PROJECT_ROLE_NOT_SHARED: revoke access
    """
    return await notebook_share(notebook_id, email, role)


@mcp.tool()
async def share_notebook_batch(
    notebook_id: str,
    grants: list[NotebookShareGrant],
) -> dict:
    """Share or revoke access for multiple users in one API call."""
    return await notebook_share_batch(notebook_id, grants)


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------


@mcp.tool()
async def add_source_url(
    notebook_id: str,
    url: str,
    display_name: str = "",
) -> dict:
    """Add a web page URL as a source to a notebook."""
    return await source_add_url(notebook_id, url, display_name)


@mcp.tool()
async def add_source_urls(
    notebook_id: str,
    urls: list[str],
) -> dict:
    """Add multiple web page URLs as sources in a single request."""
    return await source_add_urls(notebook_id, urls)


@mcp.tool()
async def add_sources_batch(
    notebook_id: str,
    sources: list[SourceBatchItem],
) -> dict:
    """Add mixed source types in a single batchCreate call."""
    return await source_batch_create(notebook_id, sources)


@mcp.tool()
async def add_source_text(
    notebook_id: str,
    text: str,
    title: str = "",
) -> dict:
    """Add plain text as a source to a notebook."""
    return await source_add_text(notebook_id, text, title)


@mcp.tool()
async def add_source_drive(
    notebook_id: str,
    document_id: str,
    doc_type: DriveDocType = "doc",
    display_name: str = "",
) -> dict:
    """
    Add a Google Drive document as a source.

    doc_type: 'doc' (Google Docs) or 'slide' (Google Slides)
    document_id: the ID from the Drive document URL
    """
    return await source_add_drive(notebook_id, document_id, doc_type, display_name)


@mcp.tool()
async def add_source_youtube(notebook_id: str, youtube_url: str) -> dict:
    """Add a YouTube video as a source to a notebook."""
    return await source_add_youtube(notebook_id, youtube_url)


@mcp.tool()
async def upload_source_file(
    notebook_id: str,
    file_path: str,
    display_name: str = "",
) -> dict:
    """
    Upload a local file as a source (PDF, DOCX, PPTX, XLSX, MP3, MP4, PNG, etc.).

    file_path: absolute or relative path to the file on disk.
    """
    return await source_upload_file(notebook_id, file_path, display_name)


@mcp.tool()
async def get_source(notebook_id: str, source_id: str) -> dict:
    """Get source details including word count, token count, and processing status."""
    return await source_get(notebook_id, source_id)


@mcp.tool()
async def delete_sources(notebook_id: str, source_ids: list[str]) -> dict:
    """Permanently delete one or more sources from a notebook."""
    return await source_delete(notebook_id, source_ids)


# ---------------------------------------------------------------------------
# Audio Overviews
# ---------------------------------------------------------------------------


@mcp.tool()
async def create_audio_overview(
    notebook_id: str,
    source_ids: list[str] | None = None,
    episode_focus: str = "",
    language_code: str = "en",
) -> dict:
    """
    Create an audio overview from notebook sources.

    - source_ids: specific sources to use; if empty, all sources are used
    - episode_focus: topic description to highlight
    - language_code: BCP47 code, e.g. 'en', 'ru', 'de'

    Returns audioOverviewId and initial status (IN_PROGRESS).
    Google docs currently document create/delete only; final verification happens in the NotebookLM UI.
    """
    return await audio_overview_create(notebook_id, source_ids, episode_focus, language_code)


@mcp.tool()
async def delete_audio_overview(notebook_id: str) -> dict:
    """Delete the audio overview of a notebook."""
    return await audio_overview_delete(notebook_id)


# ---------------------------------------------------------------------------
# Podcast API (standalone, no notebook required)
# ---------------------------------------------------------------------------


@mcp.tool()
async def create_podcast(
    focus: str,
    length: Literal["SHORT", "STANDARD"] = "STANDARD",
    texts: list[str] | None = None,
    file_paths: list[str] | None = None,
    title: str = "",
    description: str = "",
    language_code: str = "en",
) -> dict:
    """
    Generate a standalone podcast without a notebook.

    - focus: topic description for the podcast
    - length: 'SHORT' (~4-5 min) or 'STANDARD' (~10 min)
    - texts: list of text strings as context
    - file_paths: list of local files to include as context (documents, images, audio, video)
    - Returns a long-running operation name for polling and download
    """
    return await podcast_create(focus, length, texts, file_paths, title, description, language_code)


@mcp.tool()
async def create_podcast_from_contexts(
    focus: str,
    contexts: list[PodcastContextInput],
    length: Literal["SHORT", "STANDARD"] = "STANDARD",
    title: str = "",
    description: str = "",
    language_code: str = "en",
) -> dict:
    """
    Generate a standalone podcast from an ordered list of text/file context items.

    This is the closest MCP wrapper to the official Podcast API 'contexts' array.
    """
    return await podcast_create_from_contexts(
        focus,
        contexts,
        length=length,
        title=title,
        description=description,
        language_code=language_code,
    )


@mcp.tool()
async def get_operation(operation_name: str) -> dict:
    """Get the latest state of a Google long-running operation."""
    return await operation_get(operation_name)


@mcp.tool()
async def wait_operation(
    operation_name: str,
    timeout_seconds: int = 300,
    poll_interval_seconds: int = 5,
) -> dict:
    """Poll a Google long-running operation until it completes or times out."""
    return await operation_wait(operation_name, timeout_seconds, poll_interval_seconds)


@mcp.tool()
async def download_podcast(operation_name: str, output_path: str) -> str:
    """
    Download a completed podcast MP3 to a local file.

    - operation_name: the 'name' field from create_podcast response
    - output_path: local path to save the MP3 file

    Returns the absolute path of the saved file.
    """
    return await podcast_download(operation_name, output_path)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
