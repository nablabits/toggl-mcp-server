from typing import Optional, Union

from app import Endpoints, mcp
from helpers.http import toggl_request
from resources import _get_default_workspace_id


async def _get_clients_helper(
    workspace_id: int,
    status: Optional[str] = None,
    name: Optional[str] = None,
) -> Union[list, str]:
    params = {k: v for k, v in {"status": status, "name": name}.items() if v is not None}
    return await toggl_request("get", Endpoints(workspace_id).clients, params=params)


async def _create_client_helper(
    workspace_id: int, name: str, notes: Optional[str] = None
) -> Union[dict, str]:
    payload = {k: v for k, v in {"name": name, "notes": notes}.items() if v is not None}
    return await toggl_request("post", Endpoints(workspace_id).clients, json=payload)


async def _update_client_helper(
    workspace_id: int,
    client_id: int,
    name: Optional[str] = None,
    notes: Optional[str] = None,
) -> Union[dict, str]:
    payload = {k: v for k, v in {"name": name, "notes": notes}.items() if v is not None}
    return await toggl_request("put", Endpoints(workspace_id).client(client_id), json=payload)


async def _delete_client_helper(workspace_id: int, client_id: int) -> Union[int, str]:
    return await toggl_request("delete", Endpoints(workspace_id).client(client_id))


@mcp.tool()
async def get_clients(
    workspace_id: Optional[int] = None,
    status: Optional[str] = None,
) -> Union[list, str]:
    """
    List clients in the workspace. Optionally filter by status ('active', 'archived', 'both').

    Args:
        workspace_id (int, optional): Workspace ID. If omitted, uses the TOGGL_WORKSPACE_ID env
            var or your Toggl default workspace.
        status (str, optional): Filter by 'active', 'archived', or 'both'.

    Returns:
        list: Client objects on success.
        str: Error message on failure.
    """
    if workspace_id is None:
        workspace_id = await _get_default_workspace_id()
    if isinstance(workspace_id, str):
        return workspace_id
    return await _get_clients_helper(workspace_id, status=status)


@mcp.tool()
async def create_client(
    name: str,
    notes: Optional[str] = None,
    workspace_id: Optional[int] = None,
) -> Union[dict, str]:
    """
    Create a new client in the workspace.

    Args:
        name (str): Name of the client to create.
        notes (str, optional): Additional notes about the client.
        workspace_id (int, optional): Workspace ID. If omitted, uses the TOGGL_WORKSPACE_ID env
            var or your Toggl default workspace.

    Returns:
        dict: Created client object on success.
        str: Error message on failure.
    """
    if workspace_id is None:
        workspace_id = await _get_default_workspace_id()
    if isinstance(workspace_id, str):
        return workspace_id
    return await _create_client_helper(workspace_id, name=name, notes=notes)


@mcp.tool()
async def update_client(
    client_id: int,
    new_name: Optional[str] = None,
    notes: Optional[str] = None,
    workspace_id: Optional[int] = None,
) -> Union[dict, str]:
    """
    Update an existing client by ID.

    Use `get_clients` first to discover client IDs.

    Args:
        client_id (int): ID of the client to update.
        new_name (str, optional): New name for the client.
        notes (str, optional): Updated notes.
        workspace_id (int, optional): Workspace ID. If omitted, uses the TOGGL_WORKSPACE_ID env
            var or your Toggl default workspace.

    Returns:
        dict: Updated client object on success.
        str: Error message on failure.
    """
    if workspace_id is None:
        workspace_id = await _get_default_workspace_id()
    if isinstance(workspace_id, str):
        return workspace_id
    return await _update_client_helper(workspace_id, client_id, name=new_name, notes=notes)


@mcp.tool()
async def delete_client(
    client_id: int,
    workspace_id: Optional[int] = None,
) -> str:
    """
    Delete a client by ID.

    Use `get_clients` first to discover client IDs.

    Args:
        client_id (int): ID of the client to delete.
        workspace_id (int, optional): Workspace ID. If omitted, uses the TOGGL_WORKSPACE_ID env
            var or your Toggl default workspace.

    Returns:
        str: Success message on deletion, or error message on failure.
    """
    if workspace_id is None:
        workspace_id = await _get_default_workspace_id()
    if isinstance(workspace_id, str):
        return workspace_id
    status = await _delete_client_helper(workspace_id, client_id)
    if isinstance(status, int):
        return f"Successfully deleted client (id: {client_id})"
    return f"Failed to delete client (id: {client_id}): {status}"
