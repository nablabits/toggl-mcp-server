from typing import Any, List, Optional, Union

import httpx

from app import TOGGL_COLORS, headers, mcp
from resources import (
    _get_default_workspace_id,
    _get_project_id_by_name,
    _get_projects,
    _get_workspace_id_by_name,
)


async def _create_project_helper(
    name: str,
    workspace_id: int,
    active: Optional[bool] = True,
    billable: Optional[bool] = False,
    client_id: Optional[int] = None,
    color: Optional[str] = None,
    is_private: Optional[bool] = True,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    estimated_hours: Optional[int] = None,
    template: Optional[bool] = False,
    template_id: Optional[int] = None,
) -> Union[dict, str]:
    url = f"https://api.track.toggl.com/api/v9/workspaces/{workspace_id}/projects"

    payload = {
        "name": name,
        "active": active,
        "billable": billable,
        "client_id": client_id,
        "color": color,
        "is_private": is_private,
        "start_date": start_date,
        "end_date": end_date,
        "estimated_hours": estimated_hours,
        "template": template,
        "template_id": template_id,
    }
    payload = {k: v for k, v in payload.items() if v is not None}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                return "User does not have access to this resource"
            elif e.response.status_code == 500:
                return "Internal Server Error"
            return f"HTTP error: {e.response.status_code}"
        except Exception as e:
            return f"Error: {str(e)}"


async def _delete_project_helper(project_id: int, workspace_id: int) -> Union[int, str]:
    url = f"https://api.track.toggl.com/api/v9/workspaces/{workspace_id}/projects/{project_id}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.delete(url, headers=headers)
            response.raise_for_status()
            return response.status_code
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                return "Invalid project_id"
            elif e.response.status_code == 403:
                return f"Error: {e}"
            elif e.response.status_code == 500:
                return "Internal Server Error"
            return f"HTTP error: {e.response.status_code}"
        except Exception as e:
            return f"Unknown error: {str(e)}"


async def _update_projects_helper(
    workspace_id: int,
    project_ids: List[int],
    operations: List[dict],
) -> Union[dict, str]:
    project_ids_str = ",".join(str(pid) for pid in project_ids)
    url = f"https://api.track.toggl.com/api/v9/workspaces/{workspace_id}/projects/{project_ids_str}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.patch(url, json=operations, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 500:
                return "Internal Server Error"
            return f"HTTP error: {e.response.status_code}"
        except Exception as e:
            return f"Error: {str(e)}"


@mcp.tool()
async def create_project(
    name: str,
    workspace_name: Optional[str] = None,
    active: Optional[bool] = True,
    billable: Optional[bool] = False,
    client_id: Optional[int] = None,
    color: Optional[TOGGL_COLORS] = None,
    is_private: Optional[bool] = True,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    estimated_hours: Optional[int] = None,
    template: Optional[bool] = False,
    template_id: Optional[int] = None,
) -> Union[dict, str]:
    """
    Creates a new project in a Toggl workspace.

    If `workspace_name` is not provided, set it as None.

    If color is not in TOGGL_COLORS, choose color from TOGGL_COLORS which is
    most similar to the given color.

    Args:
        name (str): Name of the project to create
        workspace_name (str, optional): Name of the workspace. Defaults to user's default workspace.
        active (bool, optional): Whether project is active. Defaults to True
        billable (bool, optional): Whether project is billable. Defaults to False
        client_id (int, optional): Associated client ID
        color (str, optional): Project color hex code. Must be one of:
            - "#4dc3ff" (Light Blue)
            - "#bc85e6" (Lavender)
            - "#df7baa" (Pink)
            - "#f68d38" (Orange)
            - "#b27636" (Brown)
            - "#8ab734" (Lime Green)
            - "#14a88e" (Teal)
            - "#268bb5" (Medium Blue)
            - "#6668b4" (Purple)
            - "#a4506c" (Rose)
            - "#67412c" (Dark Brown)
            - "#3c6526" (Forest Green)
            - "#094558" (Navy Blue)
            - "#bc2d07" (Red)
            - "#999999" (Gray)
        is_private (bool, optional): Whether project is private. Defaults to True
        start_date (str, optional): Project start date in ISO format
        end_date (str, optional): Project end date in ISO format
        estimated_hours (int, optional): Estimated project hours
        template (bool, optional): Whether this is a template. Defaults to False
        template_id (int, optional): ID of template to use

    Returns:
        dict: Project data on success
        str: Error message on failure
    """
    if workspace_name is None:
        workspace_id = await _get_default_workspace_id()
    else:
        workspace_id = await _get_workspace_id_by_name(workspace_name)

    if isinstance(workspace_id, str):
        return workspace_id

    response = await _create_project_helper(
        name=name,
        workspace_id=workspace_id,
        active=active,
        billable=billable,
        client_id=client_id,
        color=color,
        is_private=is_private,
        start_date=start_date,
        end_date=end_date,
        estimated_hours=estimated_hours,
        template=template,
        template_id=template_id,
    )

    if isinstance(response, str):
        return f"Failed to create project: {response}"
    return response


@mcp.tool()
async def delete_project(project_name: str, workspace_name: Optional[str] = None) -> str:
    """
    Deletes a Toggl project by its name.

    If `workspace_name` is not provided, set it as None.

    Args:
        project_name (str): The name of the project to delete.
        workspace_name (str, optional): Name of the Toggl workspace. If not provided, defaults to the user's default workspace.

    Returns:
        str: Success message if the project is deleted, or an error message if it fails.
    """
    if workspace_name is None:
        workspace_id = await _get_default_workspace_id()
    else:
        workspace_id = await _get_workspace_id_by_name(workspace_name)

    if isinstance(workspace_id, str):
        return workspace_id

    project_id = await _get_project_id_by_name(project_name, workspace_id)

    if isinstance(project_id, str):
        return project_id

    delete_status = await _delete_project_helper(project_id, workspace_id)

    if isinstance(delete_status, int):
        return f"Successfully deleted the project with project_id: {project_id}"
    elif isinstance(delete_status, str) and delete_status == "Project not found/accessible":
        return f"Project with project_id {project_id} was not found or is inaccessible."
    else:
        return f"Failed to delete project {project_id}. Details: {delete_status}"


@mcp.tool()
async def update_projects(
    project_names: List[str],
    workspace_name: Optional[str] = None,
    operations: Optional[List[Any]] = None,
) -> Union[dict, str]:
    """
    Update multiple projects in bulk using PATCH operations.

    If `workspace_name` is not provided, set it as None.

    Args:
        project_names (List[str]): List of project names to update
        workspace_name (str, optional): Name of the workspace. Defaults to user's default workspace.
        operations (List[Any], optional): List of patch operations, each containing:
            - op (str): Operation type ("add", "remove", "replace")
            - path (str): Path to field (e.g., "/color")
            - value (Any): New value for the field

    Returns:
        dict: Response containing success/failure info for each project
        str: Error message if the operation fails
    """
    if operations is None:
        return "Error: No operations provided for update."

    if workspace_name is None:
        workspace_id = await _get_default_workspace_id()
    else:
        workspace_id = await _get_workspace_id_by_name(workspace_name)

    if isinstance(workspace_id, str):
        return workspace_id

    project_ids = []
    for name in project_names:
        project_id = await _get_project_id_by_name(name, workspace_id)
        if isinstance(project_id, str):
            return f"Error with project '{name}': {project_id}"
        project_ids.append(project_id)

    response = await _update_projects_helper(
        workspace_id=workspace_id,
        project_ids=project_ids,
        operations=operations,
    )

    if isinstance(response, str):
        return f"Failed to update projects: {response}"
    return response


@mcp.tool()
async def get_all_projects(workspace_name: Optional[str] = None) -> Union[dict, str]:
    """
    Retrieve all projects in the user's Toggl workspace.

    If `workspace_name` is not provided, the default workspace will be used.

    Args:
        workspace_name (str, optional): Name of the workspace to fetch projects from.
                                        Defaults to the user's default workspace if None.
    Returns:
        dict: JSON response containing all projects in the user's workspace.
        str: Error message if the request fails.
    """
    if workspace_name is None:
        workspace_id = await _get_default_workspace_id()
        if isinstance(workspace_id, str):
            return f"Error fetching default workspace ID: {workspace_id}"
        if workspace_id is None:
            return "Error: Could not determine default workspace ID."
    else:
        workspace_id = await _get_workspace_id_by_name(workspace_name)

    if isinstance(workspace_id, str):
        return workspace_id

    projects_response = await _get_projects(workspace_id)

    if isinstance(projects_response, dict) and "error" in projects_response:
        return f"Error fetching projects for workspace ID {workspace_id}: {projects_response['error']}"
    elif not isinstance(projects_response, dict) or "projects" not in projects_response:
        return f"Error: Unexpected response format when fetching projects for workspace ID {workspace_id}."

    return projects_response
