from typing import Optional, Union

from app import Endpoints, mcp
from helpers.http import toggl_request
from resources import _get_default_workspace_id


async def _get_tags_helper(workspace_id: int) -> Union[list, str]:
    return await toggl_request("get", Endpoints(workspace_id).tags)


async def _create_tag_helper(workspace_id: int, name: str) -> Union[dict, str]:
    return await toggl_request("post", Endpoints(workspace_id).tags, json={"name": name})


async def _update_tag_helper(workspace_id: int, tag_id: int, name: str) -> Union[dict, str]:
    return await toggl_request("put", Endpoints(workspace_id).tag(tag_id), json={"name": name})


async def _delete_tag_helper(workspace_id: int, tag_id: int) -> Union[int, str]:
    return await toggl_request("delete", Endpoints(workspace_id).tag(tag_id))


@mcp.tool()
async def get_tags(workspace_id: Optional[int] = None) -> Union[list, str]:
    """
    List all tags in the workspace.

    Args:
        workspace_id (int, optional): Workspace ID. If omitted, uses the TOGGL_WORKSPACE_ID env
            var or your Toggl default workspace.

    Returns:
        list: Tag objects with id, name, workspace_id, creator_id, at.
        str: Error message on failure.
    """
    if workspace_id is None:
        workspace_id = await _get_default_workspace_id()
    if isinstance(workspace_id, str):
        return workspace_id

    result = await _get_tags_helper(workspace_id)
    if isinstance(result, str):
        return f"Failed to fetch tags: {result}"
    return result


@mcp.tool()
async def create_tag(name: str, workspace_id: Optional[int] = None) -> Union[dict, str]:
    """
    Create a new tag in the workspace.

    Args:
        name (str): Name of the tag to create.
        workspace_id (int, optional): Workspace ID. If omitted, uses the TOGGL_WORKSPACE_ID env
            var or your Toggl default workspace.

    Returns:
        dict: Created tag object on success.
        str: Error message on failure.
    """
    if workspace_id is None:
        workspace_id = await _get_default_workspace_id()
    if isinstance(workspace_id, str):
        return workspace_id

    result = await _create_tag_helper(workspace_id, name)
    if isinstance(result, str):
        return f"Failed to create tag: {result}"
    return result


@mcp.tool()
async def update_tag(
    tag_id: int,
    new_name: str,
    workspace_id: Optional[int] = None,
) -> Union[dict, str]:
    """
    Rename an existing tag.

    Use `get_tags` first to discover tag IDs.

    Args:
        tag_id (int): ID of the tag to update.
        new_name (str): New name for the tag.
        workspace_id (int, optional): Workspace ID. If omitted, uses the TOGGL_WORKSPACE_ID env
            var or your Toggl default workspace.

    Returns:
        dict: Updated tag object on success.
        str: Error message on failure.
    """
    if workspace_id is None:
        workspace_id = await _get_default_workspace_id()
    if isinstance(workspace_id, str):
        return workspace_id

    result = await _update_tag_helper(workspace_id, tag_id, new_name)
    if isinstance(result, str):
        return f"Failed to update tag: {result}"
    return result


@mcp.tool()
async def delete_tag(tag_id: int, workspace_id: Optional[int] = None) -> str:
    """
    Delete a tag by ID.

    Use `get_tags` first to discover tag IDs.

    Args:
        tag_id (int): ID of the tag to delete.
        workspace_id (int, optional): Workspace ID. If omitted, uses the TOGGL_WORKSPACE_ID env
            var or your Toggl default workspace.

    Returns:
        str: Success message on deletion, or error message on failure.
    """
    if workspace_id is None:
        workspace_id = await _get_default_workspace_id()
    if isinstance(workspace_id, str):
        return workspace_id

    status = await _delete_tag_helper(workspace_id, tag_id)
    if isinstance(status, int):
        return f"Successfully deleted tag (id: {tag_id})"
    return f"Failed to delete tag (id: {tag_id}): {status}"
