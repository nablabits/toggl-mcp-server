from datetime import timezone
from typing import List, Optional, Tuple, Union

from tzlocal import get_localzone

from app import Endpoints, mcp
from helpers.http import toggl_request
from helpers.time import (
    _convert_utc_to_local,
    _get_current_utc_time,
    _get_date_range,
    _iso_timestamp,
)
from resources import (
    _get_default_workspace_id,
)
from resources import _get_time_entries_for_range as _fetch_time_entries_for_range
from resources import (
    _get_time_entry_id_by_name,
    _get_workspace_id_by_name,
)


async def _new_time_entry_helper(
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    project_id: Optional[int] = None,
    start: Optional[str] = None,
    stop: Optional[str] = None,
    duration: Optional[int] = -1,
    billable: Optional[bool] = False,
    workspace_id: Optional[int] = None,
) -> Union[Tuple[dict, str], str]:
    if workspace_id is None:
        return "Error: workspace_id must be provided to _new_time_entry_helper."

    ep = Endpoints(workspace_id)
    url = ep.time_entries
    current_iso_time = _get_current_utc_time()
    current_local_time = _convert_utc_to_local(current_iso_time)

    payload = {
        "created_with": "toggl_mcp_server",
        "description": description,
        "tags": tags,
        "project_id": project_id,
        "start": start if start else current_iso_time,
        "stop": stop,
        "duration": duration,
        "billable": billable,
        "workspace_id": workspace_id,
    }
    payload = {k: v for k, v in payload.items() if v is not None}

    result = await toggl_request("post", url, json=payload)
    if isinstance(result, str):
        return result
    return result, current_local_time


async def _stopping_time_entry_helper(time_entry_id: int, workspace_id: int) -> Union[dict, str]:
    return await toggl_request("patch", Endpoints(workspace_id).time_entry_stop(time_entry_id))


async def _deleting_time_entry_helper(time_entry_id: int, workspace_id: int) -> Union[int, str]:
    return await toggl_request("delete", Endpoints(workspace_id).time_entry(time_entry_id))


async def _get_current_time_entry_helper() -> Union[dict, str]:
    return await toggl_request("get", Endpoints.ME_TIME_ENTRY_CURRENT)


async def _update_time_entry_helper(
    time_entry_id: int,
    workspace_id: int,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    project_id: Optional[int] = None,
    start: Optional[str] = None,
    stop: Optional[str] = None,
    duration: Optional[int] = None,
    billable: Optional[bool] = None,
) -> Union[dict, str]:
    payload = {
        k: v
        for k, v in {
            "created_with": "toggl_mcp_server",
            "description": description,
            "tags": tags,
            "project_id": project_id,
            "start": start,
            "stop": stop,
            "duration": duration,
            "billable": billable,
        }.items()
        if v is not None
    }
    return await toggl_request(
        "put", Endpoints(workspace_id).time_entry(time_entry_id), json=payload
    )


@mcp.tool()
async def create_time_entry(
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    project_id: Optional[int] = None,
    start: Optional[str] = None,
    stop: Optional[str] = None,
    duration: Optional[int] = -1,
    billable: Optional[bool] = False,
    workspace_name: Optional[str] = None,
) -> dict:
    """
    Create a Toggl Track time entry with flexible options for live or past tracking.

    If `workspace_name` is not provided, set it as None.
    Use `get_all_projects` first to discover project IDs.

    Duration is in seconds. Set to -1 for live tracking.

    Args:
        description (str, optional): What the time entry is about.
        tags (List[str], optional): List of tags (names only).
        project_id (int, optional): ID of the associated project.
        start (str, optional): ISO 8601 UTC start time.
        stop (str, optional): ISO 8601 UTC stop time.
        duration (int, optional): Duration in seconds. Set to -1 for live tracking.
        billable (bool, optional): Whether this is billable time.
        workspace_name (str, optional): Name of the workspace. Defaults to user's default workspace.

    Returns:
        dict: Toggl API response on success, or error dict on failure.
    """
    workspace_id = (
        await _get_default_workspace_id()
        if workspace_name is None
        else await _get_workspace_id_by_name(workspace_name)
    )
    if isinstance(workspace_id, str):
        return {"error": workspace_id}
    if workspace_id is None:
        return {"error": "Could not determine workspace ID."}

    final_start_for_api = start
    final_stop_for_api = stop
    debug_info = {
        "correction_applied_start": False,
        "original_start_input": start,
        "correction_applied_stop": False,
        "original_stop_input": stop,
        "system_timezone": None,
    }
    local_tz = None

    if start:
        try:
            import datetime

            naive_time_str = start.split(".")[0].replace("Z", "")
            assumed_local_naive_dt = datetime.datetime.fromisoformat(naive_time_str)
            if local_tz is None:
                local_tz = get_localzone()
                if not local_tz:
                    raise ValueError("Failed to get local timezone")
                debug_info["system_timezone"] = getattr(local_tz, "key", str(local_tz))
            if hasattr(local_tz, "localize"):
                assumed_local_dt = local_tz.localize(assumed_local_naive_dt, is_dst=None)
            else:
                assumed_local_dt = assumed_local_naive_dt.replace(tzinfo=local_tz)
            corrected_utc_dt = assumed_local_dt.astimezone(timezone.utc)
            final_start_for_api = _iso_timestamp(corrected_utc_dt)
            debug_info["correction_applied_start"] = True
            debug_info["corrected_utc_start"] = final_start_for_api
        except Exception as e:
            print(
                f"WARNING: Timezone correction failed for start='{start}': {e}. Using original value."
            )
            final_start_for_api = start
            debug_info["correction_error_start"] = str(e)
            debug_info["correction_applied_start"] = False

    if stop:
        try:
            import datetime

            naive_time_str = stop.split(".")[0].replace("Z", "")
            assumed_local_naive_dt = datetime.datetime.fromisoformat(naive_time_str)
            if local_tz is None:
                local_tz = get_localzone()
                if not local_tz:
                    raise ValueError("Failed to get local timezone")
                if debug_info["system_timezone"] is None:
                    debug_info["system_timezone"] = getattr(local_tz, "key", str(local_tz))
            if hasattr(local_tz, "localize"):
                assumed_local_dt = local_tz.localize(assumed_local_naive_dt, is_dst=None)
            else:
                assumed_local_dt = assumed_local_naive_dt.replace(tzinfo=local_tz)
            corrected_utc_dt = assumed_local_dt.astimezone(timezone.utc)
            final_stop_for_api = _iso_timestamp(corrected_utc_dt)
            debug_info["correction_applied_stop"] = True
            debug_info["corrected_utc_stop"] = final_stop_for_api
        except Exception as e:
            print(
                f"WARNING: Timezone correction failed for stop='{stop}': {e}. Using original value."
            )
            final_stop_for_api = stop
            debug_info["correction_error_stop"] = str(e)
            debug_info["correction_applied_stop"] = False

    toggl_time_entry = await _new_time_entry_helper(
        description=description,
        tags=tags,
        project_id=project_id,
        start=final_start_for_api,
        stop=final_stop_for_api,
        duration=duration if start else -1,
        billable=billable,
        workspace_id=workspace_id,
    )

    if isinstance(toggl_time_entry, str) and toggl_time_entry.startswith("Error:"):
        return {"error": toggl_time_entry, "debug_info": debug_info}
    if not isinstance(toggl_time_entry, tuple) or len(toggl_time_entry) != 2:
        return {
            "error": f"Unexpected response format from _new_time_entry_helper: {toggl_time_entry}",
            "debug_info": debug_info,
        }

    toggl_time_entry_response, api_call_local_time = toggl_time_entry
    debug_info["final_start_passed_to_helper"] = final_start_for_api
    debug_info["final_stop_passed_to_helper"] = final_stop_for_api

    return {
        "toggle_time_entry_response": toggl_time_entry_response,
        "api_call_local_time": api_call_local_time,
        "debug_info": debug_info,
    }


@mcp.tool()
async def stop_time_entry(
    time_entry_name: Optional[str] = None,
    entry_id: Optional[int] = None,
    workspace_name: Optional[str] = None,
) -> Union[dict, str]:
    """
    Stop a currently running time entry.

    Provide either `entry_id` (unambiguous) or `time_entry_name` (matched by description).
    When multiple entries share the same description, prefer `entry_id`.

    If `workspace_name` is not provided, set it as None.

    Args:
        time_entry_name (str, optional): Description of the running time entry to stop.
        entry_id (int, optional): Exact ID of the time entry to stop.
        workspace_name (str, optional): Name of the workspace. Defaults to user's default workspace.

    Returns:
        dict: JSON response from the Toggl API if successful.
        str: Error message on failure.
    """
    if entry_id is None and time_entry_name is None:
        return "Either time_entry_name or entry_id must be provided."

    workspace_id = (
        await _get_default_workspace_id()
        if workspace_name is None
        else await _get_workspace_id_by_name(workspace_name)
    )
    if isinstance(workspace_id, str):
        return workspace_id

    if entry_id is not None:
        time_entry_id = entry_id
    else:
        time_entry_id = await _get_time_entry_id_by_name(time_entry_name, workspace_id)
        if isinstance(time_entry_id, str):
            return time_entry_id

    return await _stopping_time_entry_helper(time_entry_id, workspace_id)


@mcp.tool()
async def delete_time_entry(
    time_entry_name: Optional[str] = None,
    entry_id: Optional[int] = None,
    workspace_name: Optional[str] = None,
) -> str:
    """
    Deletes a time entry.

    Provide either `entry_id` (unambiguous) or `time_entry_name` (matched by description).
    When multiple entries share the same description, prefer `entry_id`.

    If `workspace_name` is not provided, set it as None.

    Args:
        time_entry_name (str, optional): Description of the time entry to delete.
        entry_id (int, optional): Exact ID of the time entry to delete.
        workspace_name (str, optional): Name of the workspace. Defaults to user's default workspace.

    Returns:
        str: Success or error message.
    """
    if entry_id is None and time_entry_name is None:
        return "Either time_entry_name or entry_id must be provided."

    workspace_id = (
        await _get_default_workspace_id()
        if workspace_name is None
        else await _get_workspace_id_by_name(workspace_name)
    )
    if isinstance(workspace_id, str):
        return workspace_id

    if entry_id is not None:
        time_entry_id = entry_id
    else:
        time_entry_id = await _get_time_entry_id_by_name(time_entry_name, workspace_id)
        if isinstance(time_entry_id, str):
            return time_entry_id

    delete_status = await _deleting_time_entry_helper(time_entry_id, workspace_id)
    if isinstance(delete_status, int):
        return f"Successfully deleted the time entry with time_entry_id: {time_entry_id}"
    elif delete_status == "Time Entry not found/accessible":
        return f"Time entry with time_entry_id {time_entry_id} was not found or is inaccessible."
    return f"Failed to delete time_entry {time_entry_id}. Details: {delete_status}"


@mcp.tool()
async def get_current_time_entry() -> Union[dict, str]:
    """
    Fetch the currently running time entry for the authenticated Toggl user.

    Returns:
        dict: JSON object describing the currently running time entry.
        str: Error message on failure.
    """
    return await _get_current_time_entry_helper()


@mcp.tool()
async def update_time_entry(
    time_entry_name: Optional[str] = None,
    entry_id: Optional[int] = None,
    workspace_name: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    project_id: Optional[int] = None,
    start: Optional[str] = None,
    stop: Optional[str] = None,
    duration: Optional[int] = None,
    billable: Optional[bool] = None,
) -> Union[dict, str]:
    """
    Update one or more attributes of an existing time entry.

    Provide either `entry_id` (unambiguous) or `time_entry_name` (matched by description).
    When multiple entries share the same description, prefer `entry_id`.

    If `workspace_name` is not provided, set it as None.

    Args:
        time_entry_name (str, optional): Description of the time entry to update.
        entry_id (int, optional): Exact ID of the time entry to update.
        workspace_name (str, optional): Name of the workspace. Defaults to user's default workspace.
        description (str, optional): New description.
        tags (List[str], optional): New list of tags.
        project_id (int, optional): New project ID.
        start (str, optional): New start timestamp (ISO 8601).
        stop (str, optional): New stop timestamp.
        duration (int, optional): Duration in seconds.
        billable (bool, optional): Whether the entry is billable.

    Returns:
        dict: JSON response from Toggl if update is successful.
        str: Error message on failure.
    """
    if entry_id is None and time_entry_name is None:
        return "Either time_entry_name or entry_id must be provided."

    workspace_id = (
        await _get_default_workspace_id()
        if workspace_name is None
        else await _get_workspace_id_by_name(workspace_name)
    )
    if isinstance(workspace_id, str):
        return workspace_id

    if entry_id is not None:
        time_entry_id = entry_id
    else:
        time_entry_id = await _get_time_entry_id_by_name(time_entry_name, workspace_id)
        if isinstance(time_entry_id, str):
            return time_entry_id

    return await _update_time_entry_helper(
        time_entry_id=time_entry_id,
        workspace_id=workspace_id,
        description=description,
        tags=tags,
        project_id=project_id,
        start=start,
        stop=stop,
        duration=duration,
        billable=billable,
    )


@mcp.tool()
async def get_time_entries_for_range(
    from_day_offset: Optional[int] = 0,
    to_day_offset: Optional[int] = 0,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Union[List[dict], str]:
    """
    Retrieves time entries within a date range.

    **API limit:** Toggl enforces a hard 90-day rolling window. Dates older
    than ~3 months from today will be rejected by the API. For older data,
    Toggl exposes Reports endpoints (not implemented in this MCP), but those
    do not return `time_entry_id` values, making individual entries
    unaddressable from there.

    Two ways to specify the range (explicit dates take precedence):

    1. Explicit ISO dates — `start_date` and/or `end_date` as YYYY-MM-DD or RFC3339.
       Examples:
       - "2025-05-20" to "2025-05-22"
       - "2025-05-20T00:00:00Z" to "2025-05-23T00:00:00Z"

    2. Day offsets from today (default) — `from_day_offset` / `to_day_offset`.
       Examples:
       - Today: `from_day_offset=0`, `to_day_offset=0`
       - Yesterday: `from_day_offset=-1`, `to_day_offset=-1`
       - Last 7 days: `from_day_offset=-6`, `to_day_offset=0`

    Args:
        from_day_offset (int, optional): Start day offset from today. Defaults to 0.
        to_day_offset (int, optional): End day offset from today. Defaults to 0.
        start_date (str, optional): Explicit range start (YYYY-MM-DD or RFC3339).
        end_date (str, optional): Explicit range end (YYYY-MM-DD or RFC3339).

    Returns:
        List[dict]: Time entries within the given date range.
        str: Error message on failure.
    """
    if start_date is not None or end_date is not None:
        api_start = start_date
        api_end = end_date
    else:
        from_day_offset = from_day_offset if from_day_offset is not None else 0
        to_day_offset = to_day_offset if to_day_offset is not None else 0
        api_start, _ = _get_date_range(from_day_offset)
        _, api_end = _get_date_range(to_day_offset)

    entries = await _fetch_time_entries_for_range(start_date=api_start, end_date=api_end)
    if isinstance(entries, dict) and "error" in entries:
        return f"Failed to retrieve entries: {entries['error']}"
    return entries
