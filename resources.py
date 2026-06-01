import os
from typing import List, Optional, Union

from app import Endpoints, mcp
from helpers.http import toggl_request

_workspaces_cache: Optional[List[dict]] = None


@mcp.resource("toggl:://entities/{workspace_id}/projects")
async def _get_projects(workspace_id: int) -> dict:
    """Retrieve all projects in a workspace."""
    result = await toggl_request("get", Endpoints(workspace_id).projects)
    if isinstance(result, str):
        return {"error": result}
    return {"projects": result}


@mcp.resource("toggl:://me/time_entries")
async def _get_time_entries() -> dict:
    """Retrieve the most recent time entries for the authenticated user.

    Limited to a 90-day rolling window by the Toggl API — entries older than
    ~3 months are not accessible through this endpoint.
    """
    result = await toggl_request("get", Endpoints.ME_TIME_ENTRIES)
    return {"error": result} if isinstance(result, str) else result


async def _get_time_entries_for_range(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Union[list, dict]:
    """Fetch time entries filtered server-side by date range.

    start_date / end_date accept YYYY-MM-DD or RFC3339.
    The Toggl API enforces a hard 90-day rolling window — dates older than
    ~3 months from today will be rejected with a 400 error.
    """
    params = {
        k: v for k, v in {"start_date": start_date, "end_date": end_date}.items() if v is not None
    }
    result = await toggl_request("get", Endpoints.ME_TIME_ENTRIES, params=params or None)
    return {"error": result} if isinstance(result, str) else result


@mcp.resource("toggl:://me/workspaces")
async def _get_workspaces() -> dict:
    """Retrieve all workspaces for the authenticated user."""
    global _workspaces_cache
    if _workspaces_cache is not None:
        return _workspaces_cache
    result = await toggl_request("get", Endpoints.ME_WORKSPACES)
    if isinstance(result, str):
        return {"error": result}
    _workspaces_cache = result
    return result


async def _get_default_workspace_id() -> Union[int, str]:
    if workspace_id := os.getenv("TOGGL_WORKSPACE_ID"):
        return int(workspace_id)
    result = await toggl_request("get", Endpoints.ME)
    if isinstance(result, str):
        return f"Failed to fetch default workspace ID: {result}"
    return result.get("default_workspace_id")


async def _get_time_entry_id_by_name(time_entry_name: str, workspace_id: int) -> Union[int, str]:
    time_entries_response = await _get_time_entries()
    if "error" in time_entries_response:
        return f"Error fetching time_entries: {time_entries_response['error']}"
    for time_entry in time_entries_response:
        if time_entry.get("description") == time_entry_name:
            return time_entry.get("id")
    return f"Time entry with name '{time_entry_name}' doesn't exist"


async def _get_workspace_id_by_name(workspace_name: str) -> Union[int, str]:
    workspaces_response = await _get_workspaces()
    if isinstance(workspaces_response, dict) and "error" in workspaces_response:
        return f"Error fetching workspaces: {workspaces_response['error']}"
    for workspace in workspaces_response:
        if workspace.get("name") == workspace_name:
            return workspace.get("id")
    return f"Workspace with name '{workspace_name}' doesn't exist"
