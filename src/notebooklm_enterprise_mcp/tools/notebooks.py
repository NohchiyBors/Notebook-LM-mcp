from ..client import get_client
from ..config import get_settings
from ..models import NotebookRole, NotebookShareGrant


async def notebook_create(title: str) -> dict:
    """Create a new notebook."""
    cfg = get_settings()
    return await get_client().post(cfg.notebooks_url, {"title": title})


async def notebook_get(notebook_id: str) -> dict:
    """Get notebook details including sources and metadata."""
    cfg = get_settings()
    return await get_client().get(cfg.notebook_url(notebook_id))


async def notebook_list(page_size: int = 500) -> dict:
    """List recently viewed notebooks (up to 500)."""
    cfg = get_settings()
    url = f"{cfg.notebooks_url}:listRecentlyViewed"
    return await get_client().get(url, params={"pageSize": min(page_size, 500)})


async def notebook_delete(notebook_ids: list[str]) -> dict:
    """Batch delete notebooks by their IDs."""
    cfg = get_settings()
    url = f"{cfg.notebooks_url}:batchDelete"
    names = [cfg.notebook_name(nid) for nid in notebook_ids]
    return await get_client().post(url, {"names": names})


def _share_body(grants: list[NotebookShareGrant]) -> dict:
    if not grants:
        raise ValueError("At least one share grant is required.")
    return {"accountAndRoles": [grant.model_dump() for grant in grants]}


async def notebook_share(
    notebook_id: str,
    email: str,
    role: NotebookRole,
) -> dict:
    """Share a notebook with a single user."""
    grant = NotebookShareGrant(email=email, role=role)
    return await notebook_share_batch(notebook_id, [grant])


async def notebook_share_batch(
    notebook_id: str,
    grants: list[NotebookShareGrant],
) -> dict:
    """Share a notebook with one or more users in a single API call."""
    cfg = get_settings()
    url = f"{cfg.notebook_url(notebook_id)}:share"
    return await get_client().post(url, _share_body(grants))
