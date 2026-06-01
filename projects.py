from typing import Any, List, Optional, Union

from app import TOGGL_COLORS, Endpoints, mcp
from helpers.http import toggl_request
from resources import (
    _get_default_workspace_id,
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
    payload = {
        k: v
        for k, v in {
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
        }.items()
        if v is not None
    }
    return await toggl_request("post", Endpoints(workspace_id).projects, json=payload)


async def _delete_project_helper(project_id: int, workspace_id: int) -> Union[int, str]:
    return await toggl_request("delete", Endpoints(workspace_id).project(project_id))


async def _update_projects_helper(
    workspace_id: int,
    project_ids: List[int],
    operations: List[dict],
) -> Union[dict, str]:
    project_ids_str = ",".join(str(pid) for pid in project_ids)
    return await toggl_request(
        "patch", Endpoints(workspace_id).project(project_ids_str), json=operations
    )


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

    If color is not in TOGGL_COLORS, choose the closest color from TOGGL_COLORS.

    Args:
        name (str): Name of the project to create.
        workspace_name (str, optional): Name of the workspace. Defaults to user's default workspace.
        active (bool, optional): Whether project is active. Defaults to True.
        billable (bool, optional): Whether project is billable. Defaults to False.
        client_id (int, optional): Associated client ID.
        color (str, optional): Project color hex code. Must be one of TOGGL_COLORS.
        is_private (bool, optional): Whether project is private. Defaults to True.
        start_date (str, optional): Project start date in ISO format.
        end_date (str, optional): Project end date in ISO format.
        estimated_hours (int, optional): Estimated project hours.
        template (bool, optional): Whether this is a template. Defaults to False.
        template_id (int, optional): ID of template to use.

    Returns:
        dict: Project data on success.
        str: Error message on failure.
    """
    workspace_id = (
        await _get_default_workspace_id()
        if workspace_name is None
        else await _get_workspace_id_by_name(workspace_name)
    )
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
async def delete_project(project_id: int, workspace_name: Optional[str] = None) -> str:
    """
    Deletes a Toggl project by its ID.

    If `workspace_name` is not provided, set it as None.
    Use `get_all_projects` first to discover project IDs.

    Args:
        project_id (int): The ID of the project to delete.
        workspace_name (str, optional): Name of the workspace. Defaults to user's default workspace.

    Returns:
        str: Success or error message.
    """
    workspace_id = (
        await _get_default_workspace_id()
        if workspace_name is None
        else await _get_workspace_id_by_name(workspace_name)
    )
    if isinstance(workspace_id, str):
        return workspace_id

    delete_status = await _delete_project_helper(project_id, workspace_id)
    if isinstance(delete_status, int):
        return f"Successfully deleted the project with project_id: {project_id}"
    elif delete_status == "Project not found/accessible":
        return f"Project with project_id {project_id} was not found or is inaccessible."
    return f"Failed to delete project {project_id}. Details: {delete_status}"


@mcp.tool()
async def update_project(
    project_id: int,
    workspace_name: Optional[str] = None,
    operations: Optional[List[Any]] = None,
) -> Union[dict, str]:
    """
    Update a project using JSON Patch operations (RFC 6902).

    If `workspace_name` is not provided, set it as None.
    Use `get_all_projects` first to discover project IDs.

    Args:
        project_id (int): ID of the project to update.
        workspace_name (str, optional): Name of the workspace. Defaults to user's default workspace.
        operations (List[Any], optional): List of patch operations with op, path, value keys.

    Returns:
        dict: Response containing success/failure info for the project.
        str: Error message if the operation fails.
    """
    if operations is None:
        return "Error: No operations provided for update."

    workspace_id = (
        await _get_default_workspace_id()
        if workspace_name is None
        else await _get_workspace_id_by_name(workspace_name)
    )
    if isinstance(workspace_id, str):
        return workspace_id

    response = await _update_projects_helper(
        workspace_id=workspace_id, project_ids=[project_id], operations=operations
    )
    if isinstance(response, str):
        return f"Failed to update project: {response}"
    return response


@mcp.tool()
async def get_all_projects(workspace_name: Optional[str] = None) -> Union[dict, str]:
    """
    Retrieve all projects in the user's Toggl workspace.

    If `workspace_name` is not provided, the default workspace will be used.

    Args:
        workspace_name (str, optional): Name of the workspace. Defaults to user's default workspace.

    Returns:
        dict: JSON response containing all projects.
        str: Error message if the request fails.
    """
    workspace_id = (
        await _get_default_workspace_id()
        if workspace_name is None
        else await _get_workspace_id_by_name(workspace_name)
    )
    if isinstance(workspace_id, str):
        return workspace_id

    projects_response = await _get_projects(workspace_id)
    if isinstance(projects_response, dict) and "error" in projects_response:
        return f"Error fetching projects for workspace ID {workspace_id}: {projects_response['error']}"
    if not isinstance(projects_response, dict) or "projects" not in projects_response:
        return f"Error: Unexpected response format when fetching projects for workspace ID {workspace_id}."
    return projects_response
