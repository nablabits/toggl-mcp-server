import asyncio
from typing import Union

import httpx

from app import headers


async def toggl_request(
    method: str,
    url: str,
    *,
    json=None,
    params=None,
) -> Union[dict, list, int, str]:
    """Make an authenticated request to the Toggl API.

    `method` must be one of: "get", "post", "put", "patch", "delete".

    Returns the parsed JSON body on success, or an error string on failure.
    DELETE endpoints return no body, so the HTTP status code is returned
    instead — callers check `isinstance(result, int)` to detect success.

    429 responses are retried once after a 1-second back-off (leaky-bucket
    rate limiter runs at ~1 req/s). 402 responses surface the quota headers
    so callers know how long to wait before the budget resets.
    """
    kwargs = {k: v for k, v in {"json": json, "params": params}.items() if v is not None}
    try:
        async with httpx.AsyncClient() as client:
            response = await getattr(client, method)(url, headers=headers, **kwargs)
            if response.status_code == 429:
                await asyncio.sleep(1)
                response = await getattr(client, method)(url, headers=headers, **kwargs)
    except httpx.ConnectError as e:
        return f"Connection error: {e}"

    if response.status_code == 429:
        return "Rate limit exceeded (429). Please wait a moment before retrying."

    if response.status_code == 402:
        remaining = response.headers.get("X-Toggl-Quota-Remaining", "unknown")
        resets_in = response.headers.get("X-Toggl-Quota-Resets-In", "unknown")
        return (
            f"Toggl API quota exhausted (402). "
            f"Quota remaining: {remaining}, resets in: {resets_in} seconds."
        )

    if response.status_code >= 400:
        try:
            return str(response.json())
        except ValueError:
            return response.text or f"{response.status_code} {response.reason_phrase}"

    if method == "delete":
        return response.status_code
    try:
        return response.json()
    except ValueError:
        return []
