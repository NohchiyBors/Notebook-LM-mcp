import asyncio
import time

from ..client import get_client

_OPERATIONS_BASE = "https://discoveryengine.googleapis.com/v1"


def _operation_url(operation_name: str) -> str:
    normalized = operation_name.lstrip("/")
    if normalized.startswith("https://"):
        return normalized
    return f"{_OPERATIONS_BASE}/{normalized}"


async def operation_get(operation_name: str) -> dict:
    """Fetch a Google long-running operation by name."""
    return await get_client().get(_operation_url(operation_name))


async def operation_wait(
    operation_name: str,
    timeout_seconds: int = 300,
    poll_interval_seconds: int = 5,
) -> dict:
    """Poll a Google long-running operation until it completes or times out."""
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be greater than 0.")
    if poll_interval_seconds <= 0:
        raise ValueError("poll_interval_seconds must be greater than 0.")

    deadline = time.monotonic() + timeout_seconds
    while True:
        operation = await operation_get(operation_name)
        if operation.get("done"):
            return operation
        if time.monotonic() >= deadline:
            raise TimeoutError(
                f"Operation did not complete within {timeout_seconds} seconds: {operation_name}"
            )
        await asyncio.sleep(poll_interval_seconds)
