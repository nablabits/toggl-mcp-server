import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import app as server
from projects import create_project, delete_project, get_all_projects, update_project

# ---------------------------------------------------------------------------
# API error codes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_create_project_bad_request():
    result = await create_project(name="")
    assert isinstance(result, str)
    assert result == "Failed to create project: project name must not be empty"


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_get_all_projects_unauthorized(monkeypatch):
    monkeypatch.setitem(server.headers, "Authorization", "Basic aW52YWxpZA==")
    result = await get_all_projects()
    assert isinstance(result, str)
    assert result == "Error fetching projects for workspace ID 21407567: 401 Unauthorized"


# ---------------------------------------------------------------------------
# Workspace not found
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_create_project_workspace_not_found():
    result = await create_project(name="My Project", workspace_name="NonExistentWS")
    assert isinstance(result, str)
    assert result == "Workspace with name 'NonExistentWS' doesn't exist"


# ---------------------------------------------------------------------------
# No operations
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_project_no_operations():
    result = await update_project(project_name="Alpha")
    assert isinstance(result, str)
    assert result == "Error: No operations provided for update."


# ---------------------------------------------------------------------------
# Project not found
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_delete_project_not_found():
    result = await delete_project(project_name="NonExistent Project")
    assert isinstance(result, str)
    assert result == "Project with name 'NonExistent Project' doesn't exist"


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_update_project_not_found():
    result = await update_project(
        project_name="NonExistent Project",
        operations=[{"op": "replace", "path": "/color", "value": "#bc85e6"}],
    )
    assert isinstance(result, str)
    assert (
        result
        == "Error with project 'NonExistent Project': Project with name 'NonExistent Project' doesn't exist"
    )


# ---------------------------------------------------------------------------
# Workspace not found — delete / update / get_all
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_delete_project_workspace_not_found():
    result = await delete_project(project_name="Alpha", workspace_name="NonExistentWS")
    assert isinstance(result, str)
    assert result == "Workspace with name 'NonExistentWS' doesn't exist"


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_update_project_workspace_not_found():
    result = await update_project(
        project_name="Alpha",
        workspace_name="NonExistentWS",
        operations=[{"op": "replace", "path": "/color", "value": "#bc85e6"}],
    )
    assert isinstance(result, str)
    assert result == "Workspace with name 'NonExistentWS' doesn't exist"


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_get_all_projects_workspace_not_found():
    result = await get_all_projects(workspace_name="NonExistentWS")
    assert isinstance(result, str)
    assert result == "Workspace with name 'NonExistentWS' doesn't exist"


# ---------------------------------------------------------------------------
# delete_project — API error paths (lines 158–160)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_project_not_found_sentinel():
    with (
        patch("projects._get_default_workspace_id", new_callable=AsyncMock, return_value=12345),
        patch("projects._get_project_id_by_name", new_callable=AsyncMock, return_value=99999),
        patch(
            "projects._delete_project_helper",
            new_callable=AsyncMock,
            return_value="Project not found/accessible",
        ),
    ):
        result = await delete_project(project_name="Alpha")

    assert result == "Project with project_id 99999 was not found or is inaccessible."


@pytest.mark.asyncio
async def test_delete_project_generic_api_error():
    with (
        patch("projects._get_default_workspace_id", new_callable=AsyncMock, return_value=12345),
        patch("projects._get_project_id_by_name", new_callable=AsyncMock, return_value=99999),
        patch(
            "projects._delete_project_helper",
            new_callable=AsyncMock,
            return_value="503 Service Unavailable",
        ),
    ):
        result = await delete_project(project_name="Alpha")

    assert result == "Failed to delete project 99999. Details: 503 Service Unavailable"


# ---------------------------------------------------------------------------
# update_project — API error path (line 202)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_project_api_error():
    with (
        patch("projects._get_default_workspace_id", new_callable=AsyncMock, return_value=12345),
        patch("projects._get_project_id_by_name", new_callable=AsyncMock, return_value=99999),
        patch(
            "projects._update_projects_helper",
            new_callable=AsyncMock,
            return_value="503 Service Unavailable",
        ),
    ):
        result = await update_project(
            project_name="Alpha",
            operations=[{"op": "replace", "path": "/color", "value": "#bc85e6"}],
        )

    assert result == "Failed to update project: 503 Service Unavailable"


# ---------------------------------------------------------------------------
# get_all_projects — unexpected response format (lines 231–233)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_all_projects_error_in_response():
    with (
        patch("projects._get_default_workspace_id", new_callable=AsyncMock, return_value=12345),
        patch(
            "projects._get_projects",
            new_callable=AsyncMock,
            return_value={"error": "upstream failure"},
        ),
    ):
        result = await get_all_projects()

    assert result == "Error fetching projects for workspace ID 12345: upstream failure"


@pytest.mark.asyncio
async def test_get_all_projects_unexpected_format():
    with (
        patch("projects._get_default_workspace_id", new_callable=AsyncMock, return_value=12345),
        patch("projects._get_projects", new_callable=AsyncMock, return_value=["not", "a", "dict"]),
    ):
        result = await get_all_projects()

    assert (
        result
        == "Error: Unexpected response format when fetching projects for workspace ID 12345."
    )


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_get_all_projects_success():
    result = await get_all_projects()
    assert isinstance(result, dict)
    assert "projects" in result
    assert isinstance(result["projects"], list)
