from typing import Optional, Union

from app import Endpoints, mcp
from helpers.http import toggl_request
from resources import (
    _get_default_workspace_id,
    _get_project_id_by_name,
    _get_workspace_id_by_name,
)


async def _get_tasks_helper(
    workspace_id: int,
    project_id: int,
    active: Optional[bool] = None,
) -> Union[list, str]:
    params = {k: v for k, v in {"active": active}.items() if v is not None}
    return await toggl_request("get", Endpoints(workspace_id).tasks(project_id), params=params)


async def _create_task_helper(
    workspace_id: int,
    project_id: int,
    name: str,
    active: Optional[bool] = None,
    estimated_seconds: Optional[int] = None,
    user_id: Optional[int] = None,
) -> Union[dict, str]:
    payload = {
        k: v
        for k, v in {
            "name": name,
            "active": active,
            "estimated_seconds": estimated_seconds,
            "user_id": user_id,
        }.items()
        if v is not None
    }
    return await toggl_request("post", Endpoints(workspace_id).tasks(project_id), json=payload)


async def _update_task_helper(
    workspace_id: int,
    project_id: int,
    task_id: int,
    name: Optional[str] = None,
    active: Optional[bool] = None,
    estimated_seconds: Optional[int] = None,
    user_id: Optional[int] = None,
) -> Union[dict, str]:
    payload = {
        k: v
        for k, v in {
            "name": name,
            "active": active,
            "estimated_seconds": estimated_seconds,
            "user_id": user_id,
        }.items()
        if v is not None
    }
    return await toggl_request(
        "put", Endpoints(workspace_id).task(project_id, task_id), json=payload
    )


async def _delete_task_helper(workspace_id: int, project_id: int, task_id: int) -> Union[int, str]:
    return await toggl_request("delete", Endpoints(workspace_id).task(project_id, task_id))


async def _get_task_id_by_name(
    task_name: str, workspace_id: int, project_id: int
) -> Union[int, str]:
    tasks = await _get_tasks_helper(workspace_id, project_id)
    if isinstance(tasks, str):
        return f"Error fetching tasks: {tasks}"
    for task in tasks:
        if task.get("name") == task_name:
            return task.get("id")
    return f"Task with name '{task_name}' doesn't exist in the project"


@mcp.tool()
async def get_tasks(
    project_name: str,
    workspace_name: Optional[str] = None,
    active: Optional[bool] = None,
) -> Union[list, str]:
    """
    List all tasks for a given project.

    If `workspace_name` is not provided, set it as None.

    Args:
        project_name (str): Name of the project to fetch tasks from.
        workspace_name (str, optional): Name of the workspace. Defaults to user's default workspace.
        active (bool, optional): If True, return only active tasks. If False, only inactive. Omit for all.

    Returns:
        list: Task objects.
        str: Error message on failure.
    """
    workspace_id = (
        await _get_default_workspace_id()
        if workspace_name is None
        else await _get_workspace_id_by_name(workspace_name)
    )
    if isinstance(workspace_id, str):
        return workspace_id

    project_id = await _get_project_id_by_name(project_name, workspace_id)
    if isinstance(project_id, str):
        return project_id

    result = await _get_tasks_helper(workspace_id, project_id, active=active)
    if isinstance(result, str):
        return f"Failed to fetch tasks: {result}"
    return result


@mcp.tool()
async def create_task(
    name: str,
    project_name: str,
    workspace_name: Optional[str] = None,
    active: Optional[bool] = None,
    estimated_seconds: Optional[int] = None,
) -> Union[dict, str]:
    """
    Create a new task inside a project.

    If `workspace_name` is not provided, set it as None.

    Args:
        name (str): Name of the task.
        project_name (str): Name of the project.
        workspace_name (str, optional): Name of the workspace. Defaults to user's default workspace.
        active (bool, optional): Whether the task is active.
        estimated_seconds (int, optional): Estimated time in seconds.

    Returns:
        dict: Created task object on success.
        str: Error message on failure.
    """
    workspace_id = (
        await _get_default_workspace_id()
        if workspace_name is None
        else await _get_workspace_id_by_name(workspace_name)
    )
    if isinstance(workspace_id, str):
        return workspace_id

    project_id = await _get_project_id_by_name(project_name, workspace_id)
    if isinstance(project_id, str):
        return project_id

    result = await _create_task_helper(
        workspace_id=workspace_id,
        project_id=project_id,
        name=name,
        active=active,
        estimated_seconds=estimated_seconds,
    )
    if isinstance(result, str):
        return f"Failed to create task: {result}"
    return result


@mcp.tool()
async def update_task(
    task_name: str,
    project_name: str,
    workspace_name: Optional[str] = None,
    name: Optional[str] = None,
    active: Optional[bool] = None,
    estimated_seconds: Optional[int] = None,
) -> Union[dict, str]:
    """
    Update an existing task by name.

    If `workspace_name` is not provided, set it as None.

    Args:
        task_name (str): Current name of the task to update.
        project_name (str): Name of the project the task belongs to.
        workspace_name (str, optional): Name of the workspace. Defaults to user's default workspace.
        name (str, optional): New name for the task.
        active (bool, optional): Set False to mark the task as done.
        estimated_seconds (int, optional): Updated estimate in seconds.

    Returns:
        dict: Updated task object on success.
        str: Error message on failure.
    """
    workspace_id = (
        await _get_default_workspace_id()
        if workspace_name is None
        else await _get_workspace_id_by_name(workspace_name)
    )
    if isinstance(workspace_id, str):
        return workspace_id

    project_id = await _get_project_id_by_name(project_name, workspace_id)
    if isinstance(project_id, str):
        return project_id

    task_id = await _get_task_id_by_name(task_name, workspace_id, project_id)
    if isinstance(task_id, str):
        return task_id

    result = await _update_task_helper(
        workspace_id=workspace_id,
        project_id=project_id,
        task_id=task_id,
        name=name,
        active=active,
        estimated_seconds=estimated_seconds,
    )
    if isinstance(result, str):
        return f"Failed to update task: {result}"
    return result


@mcp.tool()
async def delete_task(
    task_name: str,
    project_name: str,
    workspace_name: Optional[str] = None,
) -> str:
    """
    Delete a task by name.

    If `workspace_name` is not provided, set it as None.

    Args:
        task_name (str): Name of the task to delete.
        project_name (str): Name of the project the task belongs to.
        workspace_name (str, optional): Name of the workspace. Defaults to user's default workspace.

    Returns:
        str: Success message on deletion, or error message on failure.
    """
    workspace_id = (
        await _get_default_workspace_id()
        if workspace_name is None
        else await _get_workspace_id_by_name(workspace_name)
    )
    if isinstance(workspace_id, str):
        return workspace_id

    project_id = await _get_project_id_by_name(project_name, workspace_id)
    if isinstance(project_id, str):
        return project_id

    task_id = await _get_task_id_by_name(task_name, workspace_id, project_id)
    if isinstance(task_id, str):
        return task_id

    status = await _delete_task_helper(workspace_id, project_id, task_id)
    if isinstance(status, int):
        return f"Successfully deleted task '{task_name}' (id: {task_id})"
    return f"Failed to delete task '{task_name}': {status}"
