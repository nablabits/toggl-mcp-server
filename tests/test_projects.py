import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import app as server
from projects import (
    create_project,
    delete_project,
    get_all_projects,
    get_project_by_id,
    update_project,
)

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
# No operations
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_project_no_operations():
    result = await update_project(project_id=999)
    assert isinstance(result, str)
    assert result == "Error: No operations provided for update."


# ---------------------------------------------------------------------------
# Workspace error propagation — create / delete / update / get_all
# ---------------------------------------------------------------------------

_WS_ERROR = "Failed to fetch default workspace ID: 503 error"


@pytest.mark.asyncio
async def test_create_project_workspace_error():
    with patch(
        "projects._get_default_workspace_id", new_callable=AsyncMock, return_value=_WS_ERROR
    ):
        result = await create_project(name="My Project")
    assert result == _WS_ERROR


@pytest.mark.asyncio
async def test_delete_project_workspace_error():
    with patch(
        "projects._get_default_workspace_id", new_callable=AsyncMock, return_value=_WS_ERROR
    ):
        result = await delete_project(project_id=999)
    assert result == _WS_ERROR


@pytest.mark.asyncio
async def test_update_project_workspace_error():
    with patch(
        "projects._get_default_workspace_id", new_callable=AsyncMock, return_value=_WS_ERROR
    ):
        result = await update_project(
            project_id=999,
            operations=[{"op": "replace", "path": "/color", "value": "#bc85e6"}],
        )
    assert result == _WS_ERROR


@pytest.mark.asyncio
async def test_get_all_projects_workspace_error():
    with patch(
        "projects._get_default_workspace_id", new_callable=AsyncMock, return_value=_WS_ERROR
    ):
        result = await get_all_projects()
    assert result == _WS_ERROR


# ---------------------------------------------------------------------------
# delete_project — API error paths (lines 158–160)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_project_not_found_sentinel():
    with (
        patch("projects._get_default_workspace_id", new_callable=AsyncMock, return_value=12345),
        patch(
            "projects._delete_project_helper",
            new_callable=AsyncMock,
            return_value="Project not found/accessible",
        ),
    ):
        result = await delete_project(project_id=99999)

    assert result == "Project with project_id 99999 was not found or is inaccessible."


@pytest.mark.asyncio
async def test_delete_project_generic_api_error():
    with (
        patch("projects._get_default_workspace_id", new_callable=AsyncMock, return_value=12345),
        patch(
            "projects._delete_project_helper",
            new_callable=AsyncMock,
            return_value="503 Service Unavailable",
        ),
    ):
        result = await delete_project(project_id=99999)

    assert result == "Failed to delete project 99999. Details: 503 Service Unavailable"


# ---------------------------------------------------------------------------
# update_project — API error path (line 202)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_project_api_error():
    with (
        patch("projects._get_default_workspace_id", new_callable=AsyncMock, return_value=12345),
        patch(
            "projects._update_projects_helper",
            new_callable=AsyncMock,
            return_value="503 Service Unavailable",
        ),
    ):
        result = await update_project(
            project_id=99999,
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
            "projects._fetch_projects",
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
        patch(
            "projects._fetch_projects", new_callable=AsyncMock, return_value=["not", "a", "dict"]
        ),
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


# ---------------------------------------------------------------------------
# get_project_by_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_project_by_id_workspace_error():
    with patch(
        "projects._get_default_workspace_id", new_callable=AsyncMock, return_value=_WS_ERROR
    ):
        result = await get_project_by_id(project_id=999)
    assert result == _WS_ERROR


@pytest.mark.asyncio
async def test_get_project_by_id_api_error():
    with (
        patch("projects._get_default_workspace_id", new_callable=AsyncMock, return_value=12345),
        patch("projects.toggl_request", new_callable=AsyncMock, return_value="404 Not Found"),
    ):
        result = await get_project_by_id(project_id=99999)
    assert result == "Failed to fetch project 99999: 404 Not Found"


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_get_project_by_id_success():
    result = await get_project_by_id(project_id=219958848)
    assert isinstance(result, dict)
    assert result["id"] == 219958848
    assert result["name"] == "Alpha"
