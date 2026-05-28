import datetime
from datetime import timezone
from typing import List, Optional, Tuple, Union

import httpx
from tzlocal import get_localzone

from app import headers, mcp
from helpers.time import (
    _convert_utc_to_local,
    _get_current_utc_time,
    _get_date_range,
    _iso_timestamp,
)
from resources import (
    _get_default_workspace_id,
    _get_project_id_by_name,
    _get_time_entries,
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

    url = f"https://api.track.toggl.com/api/v9/workspaces/{workspace_id}/time_entries"

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

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json(), current_local_time
        except Exception as e:
            return f"Error: {e}"


async def _stopping_time_entry_helper(time_entry_id: int, workspace_id: int) -> Union[dict, str]:
    url = f"https://api.track.toggl.com/api/v9/workspaces/{workspace_id}/time_entries/{time_entry_id}/stop"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.patch(url, headers=headers)

            if 200 <= response.status_code < 300:
                try:
                    return response.json()
                except Exception as json_e:
                    return f"Error parsing successful response: {json_e}"
            else:
                if response.status_code == 404:
                    return f"Stop failed: Time entry not found or already stopped (HTTP 404). Response: {response.text}"
                elif response.status_code == 400:
                    return f"Stop failed: Bad Request (HTTP 400). Possibly already stopped or invalid state. Response: {response.text}"
                else:
                    return f"HTTP error {response.status_code}: {response.text}"

        except httpx.RequestError as req_e:
            return f"Request failed: {req_e}"
        except Exception as e:
            return f"An unexpected error occurred: {e}"


async def _deleting_time_entry_helper(time_entry_id: int, workspace_id: int) -> Union[dict, str]:
    url = f"https://api.track.toggl.com/api/v9/workspaces/{workspace_id}/time_entries/{time_entry_id}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.delete(url, headers=headers)
            response.raise_for_status()
            return response.status_code
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                return "User does not have access to this resource."
            elif e.response.status_code == 500:
                return "Internal Server Error"
            return f"HTTP error: {e.response.status_code}"
        except Exception as e:
            return f"Unknown error: {str(e)}"


async def _get_current_time_entry_helper() -> Union[dict, str]:
    url = "https://api.track.toggl.com/api/v9/me/time_entries/current"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                return "User does not have access to this resource."
            elif e.response.status_code == 404:
                return "Resource can not be found"
            elif e.response.status_code == 500:
                return "Internal Server Error"
            return f"HTTP error: {e.response.status_code}"
        except Exception as e:
            return f"Unknown error: {str(e)}"


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
    url = f"https://api.track.toggl.com/api/v9/workspaces/{workspace_id}/time_entries/{time_entry_id}"

    payload = {
        "created_with": "toggl_mcp_server",
        "description": description,
        "tags": tags,
        "project_id": project_id,
        "start": start,
        "stop": stop,
        "duration": duration,
        "billable": billable,
    }
    payload = {key: value for key, value in payload.items() if value is not None}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(url, json=payload, headers=headers)
            response.raise_for_status()
            print(f"Response json: {response.json}")
            return response.json()
        except Exception as e:
            return f"Error: {e}"


@mcp.tool()
async def new_time_entry(
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    project_name: Optional[str] = None,
    start: Optional[str] = None,
    stop: Optional[str] = None,
    duration: Optional[int] = -1,
    billable: Optional[bool] = False,
    workspace_name: Optional[str] = None,
) -> dict:
    """
    Create a Toggl Track time entry with flexible options for live or past tracking.

    If `workspace_name` is not provided, set it as None.

    Duration is in seconds. Set to -1 for live tracking for the current time entry.

    Use this tool to start a new entry (live tracking) or log a completed activity with precise timing.

    Examples:
    - "Track 'Writing docs' starting now"
    - "Log 2 hours spent on 'MCP Server' yesterday tagged ['Toggl', 'backend']"

    Args:
        description (str, optional): What the time entry is about.
        tags (List[str], optional): List of tags (names only).
        project_name (str, optional): Name of the associated project.
        start (str, optional): ISO 8601 UTC start time.
        stop (str, optional): ISO 8601 UTC stop time.
        duration (int, optional): Duration in seconds. Set to -1 for live tracking.
        billable (bool, optional): Whether this is billable time.
        workspace_name (str, optional): Name of the workspace. Defaults to user's default workspace if omitted.

    Returns:
        dict: Toggl API response on success.
        dict: Error message on failure.
    """
    if workspace_name is None:
        workspace_id = await _get_default_workspace_id()
    else:
        workspace_id = await _get_workspace_id_by_name(workspace_name)

    if isinstance(workspace_id, str):
        return {"error": workspace_id}
    if workspace_id is None:
        return {"error": "Could not determine workspace ID."}

    project_id = None
    if project_name is not None:
        project_id_or_error = await _get_project_id_by_name(project_name, workspace_id)
        if isinstance(project_id_or_error, str):
            return {"error": project_id_or_error}
        else:
            project_id = project_id_or_error

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
            naive_time_str = start.split(".")[0].replace("Z", "")
            assumed_local_naive_dt = datetime.datetime.fromisoformat(naive_time_str)
            if local_tz is None:
                local_tz = get_localzone()
                if not local_tz:
                    raise ValueError("Failed to get local timezone")
                debug_info["system_timezone"] = getattr(local_tz, "key", str(local_tz))

            if hasattr(local_tz, "localize"):
                assumed_local_dt = local_tz.localize(assumed_local_naive_dt, is_dst=None)
            elif hasattr(assumed_local_naive_dt, "replace"):
                assumed_local_dt = assumed_local_naive_dt.replace(tzinfo=local_tz)
            else:
                raise TypeError("Unsupported timezone object from get_localzone()")

            corrected_utc_dt = assumed_local_dt.astimezone(timezone.utc)
            final_start_for_api = _iso_timestamp(corrected_utc_dt)
            debug_info["correction_applied_start"] = True
            debug_info["corrected_utc_start"] = final_start_for_api

        except Exception as e:
            print(f"WARNING: Timezone correction failed for start='{start}': {e}. Using original value.")
            final_start_for_api = start
            debug_info["correction_error_start"] = str(e)
            debug_info["correction_applied_start"] = False

    if stop:
        try:
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
            elif hasattr(assumed_local_naive_dt, "replace"):
                assumed_local_dt = assumed_local_naive_dt.replace(tzinfo=local_tz)
            else:
                raise TypeError("Unsupported timezone object from get_localzone()")

            corrected_utc_dt = assumed_local_dt.astimezone(timezone.utc)
            final_stop_for_api = _iso_timestamp(corrected_utc_dt)
            debug_info["correction_applied_stop"] = True
            debug_info["corrected_utc_stop"] = final_stop_for_api

        except Exception as e:
            print(f"WARNING: Timezone correction failed for stop='{stop}': {e}. Using original value.")
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
async def stopping_time_entry(
    time_entry_name: str, workspace_name: Optional[str] = None
) -> Union[dict, str]:
    """
    Stop a currently running time entry by name.

    This function looks up the time entry by its description, retrieves its ID, and then calls the Toggl API to stop it.

    If `workspace_name` is not provided, set it as None.

    Args:
        time_entry_name (str): Description of the currently running time entry to stop.
        workspace_name (str, optional): Name of the workspace. Defaults to the user's default workspace.

    Returns:
        dict: JSON response from the Toggl API if successful.
        str: An error message if the request fails or no matching time entry is found.
    """
    if workspace_name is None:
        workspace_id = await _get_default_workspace_id()
    else:
        workspace_id = await _get_workspace_id_by_name(workspace_name)

    if isinstance(workspace_id, str):
        return workspace_id

    time_entry_id = await _get_time_entry_id_by_name(time_entry_name, workspace_id)

    if isinstance(time_entry_id, str):
        return time_entry_id

    stopping_time_entry_response = await _stopping_time_entry_helper(time_entry_id, workspace_id)

    if isinstance(stopping_time_entry_response, str) and stopping_time_entry_response == "Time entry not found":
        return "Time entry not found!"
    elif isinstance(stopping_time_entry_response, dict):
        return stopping_time_entry_response
    else:
        return "ERROR"


@mcp.tool()
async def delete_time_entry(
    time_entry_name: str, workspace_name: Optional[str] = None
) -> str:
    """
    Deletes a time entry by its description.

    This permanently removes the time entry from the workspace, so use with caution.

    If `workspace_name` is not provided, set it as None.

    Args:
        time_entry_name (str): Description of the time entry to delete.
        workspace_name (str, optional): Name of the workspace. Defaults to the user's default workspace.

    Returns:
        str: A success message if deleted, or an error string if it fails.
    """
    if workspace_name is None:
        workspace_id = await _get_default_workspace_id()
    else:
        workspace_id = await _get_workspace_id_by_name(workspace_name)

    if isinstance(workspace_id, str):
        return workspace_id

    time_entry_id = await _get_time_entry_id_by_name(time_entry_name, workspace_id)

    if isinstance(time_entry_id, str):
        return time_entry_id

    delete_status = await _deleting_time_entry_helper(time_entry_id, workspace_id)

    if isinstance(delete_status, int):
        return f"Successfully deleted the time entry with time_entry_id: {time_entry_id}"
    elif isinstance(delete_status, str) and delete_status == "Time Entry not found/accessible":
        return f"Time entry with time_entry_id {time_entry_id} was not found or is inaccessible."
    else:
        return f"Failed to delete time_entry {time_entry_id}. Details: {delete_status}"


@mcp.tool()
async def get_current_time_entry() -> Union[dict, str]:
    """
    Fetch the currently running time entry for the authenticated Toggl user.

    Returns:
        dict: JSON object describing the currently running time entry, or containing `data: None` if none is active.
        str: Descriptive error message if the request fails.
    """
    current_time_entry_data = await _get_current_time_entry_helper()

    if isinstance(current_time_entry_data, str):
        return current_time_entry_data

    return current_time_entry_data


@mcp.tool()
async def updating_time_entry(
    time_entry_name: str,
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
    Update one or more attributes of an existing time entry in the Toggl Track workspace.

    If `workspace_name` is not provided, set it as None.

    Args:
        time_entry_name (str): Description of the time entry to update.
        workspace_name (str, optional): Name of the workspace. Defaults to the user's default.
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
    if workspace_name is None:
        workspace_id = await _get_default_workspace_id()
    else:
        workspace_id = await _get_workspace_id_by_name(workspace_name)

    if isinstance(workspace_id, str):
        return workspace_id

    time_entry_id = await _get_time_entry_id_by_name(time_entry_name, workspace_id)

    if isinstance(time_entry_id, str):
        return time_entry_id

    response = await _update_time_entry_helper(
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

    return response


@mcp.tool()
async def get_time_entries_for_range(
    from_day_offset: Optional[int] = 0,
    to_day_offset: Optional[int] = 0,
) -> Union[List[dict], str]:
    """
    Retrieves time entries for the authenticated Toggl user within a specific UTC day range.

    This tool allows you to query all entries from a specific day or over multiple days,
    using day offsets from today.

    Examples:
    - To get entries for today: `from_day_offset=0`, `to_day_offset=0`
    - For yesterday only: `from_day_offset=-1`, `to_day_offset=-1`
    - For the last two days: `from_day_offset=-1`, `to_day_offset=0`

    Args:
        from_day_offset (int, optional): Days offset before today for the start of the range. Defaults to 0 (today).
        to_day_offset (int, optional): Days offset before today for the end of the range. Defaults to 0 (today).

    Returns:
        List[dict]: Filtered time entries that fall within the given date range.
        str: Error message if retrieval or filtering fails.
    """
    from_day_offset = from_day_offset if from_day_offset is not None else 0
    to_day_offset = to_day_offset if to_day_offset is not None else 0

    all_entries = await _get_time_entries()

    if isinstance(all_entries, dict) and "error" in all_entries:
        return f"Failed to retrieve entries: {all_entries['error']}"

    start_time, _ = _get_date_range(from_day_offset)
    _, end_time = _get_date_range(to_day_offset)

    def _in_range(entry: dict) -> bool:
        entry_start = entry.get("start")
        if entry_start is None:
            return False
        return start_time <= entry_start <= end_time

    filtered = [entry for entry in all_entries if _in_range(entry)]
    return filtered
