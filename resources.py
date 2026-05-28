from typing import Union

import httpx

from app import headers, mcp


@mcp.resource("toggl:://entities/{workspace_id}/projects")
async def _get_projects(workspace_id: int) -> dict:
    """
    Retrieve a full list of all projects within the user's Toggl workspace, including detailed metadata for each project.
    """
    url = f"https://api.track.toggl.com/api/v9/workspaces/{workspace_id}/projects"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return {"projects": response.json()}
        except Exception as e:
            return {"error": e}


@mcp.resource("toggl:://me/time_entries")
async def _get_time_entries() -> dict:
    """
    Retrieve all time entries associated with the authenticated Toggl user.
    """
    url = "https://api.track.toggl.com/api/v9/me/time_entries"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                return {"error": "User does not have access to this resource"}
            elif e.response.status_code == 500:
                return {"error": "Internal Server Error"}
            else:
                return {"error": f"Unknown Error Code: {e.response.status_code}"}
        except Exception as e:
            return {"error": e}


@mcp.resource("toggl:://me/workspaces")
async def _get_workspaces() -> dict:
    """
    Retrieve all workspaces associated with the authenticated Toggl user.
    """
    url = "https://api.track.toggl.com/api/v9/me/workspaces"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                return {"error": "User does not have access to this resource"}
            elif e.response.status_code == 500:
                return {"error": "Internal Server Error"}
            else:
                return {"error": f"Unknown Error Code: {e.response.status_code}"}
        except Exception as e:
            return {"error": e}


async def _get_default_workspace_id() -> Union[int, str]:
    url = "https://api.track.toggl.com/api/v9/me"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json().get("default_workspace_id")
        except Exception as e:
            return f"Failed to fetch default workspace ID: {str(e)}"


async def _get_project_id_by_name(project_name: str, workspace_id: int) -> Union[int, str]:
    projects_response = await _get_projects(workspace_id)

    if "error" in projects_response:
        return f"Error fetching projects: {projects_response['error']}"

    for project in projects_response.get("projects", []):
        if project.get("name") == project_name:
            return project.get("id")

    return f"Project with name '{project_name}' doesn't exist"


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

    if "error" in workspaces_response:
        return f"Error fetching workspaces: {workspaces_response['error']}"

    for workspace in workspaces_response:
        if workspace.get("name") == workspace_name:
            return workspace.get("id")

    return f"Workspace with name '{workspace_name}' doesn't exist"
