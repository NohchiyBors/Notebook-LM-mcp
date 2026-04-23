from ..client import get_client
from ..config import get_settings


async def audio_overview_create(
    notebook_id: str,
    source_ids: list[str] | None = None,
    episode_focus: str = "",
    language_code: str = "en",
) -> dict:
    """
    Create an audio overview for a notebook.

    If source_ids is empty or None, all notebook sources are used.
    Poll the returned audioOverviewId for completion status.
    """
    cfg = get_settings()
    url = cfg.audio_overviews_url(notebook_id)

    body: dict = {"languageCode": language_code}
    if source_ids:
        body["sourceIds"] = [{"id": sid} for sid in source_ids]
    if episode_focus:
        body["episodeFocus"] = episode_focus

    return await get_client().post(url, body)


async def audio_overview_delete(notebook_id: str) -> dict:
    """Delete the default audio overview of a notebook."""
    cfg = get_settings()
    url = f"{cfg.audio_overviews_url(notebook_id)}/default"
    return await get_client().delete(url)
