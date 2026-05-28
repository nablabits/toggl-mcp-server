import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import app as server
from tasks import create_task, delete_task, get_tasks, update_task

# ---------------------------------------------------------------------------
# Workspace not found
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_get_tasks_workspace_not_found():
    result = await get_tasks(project_name="Alpha", workspace_name="NonExistentWS")
    assert isinstance(result, str)
    assert result == "Workspace with name 'NonExistentWS' doesn't exist"


# ---------------------------------------------------------------------------
# Project not found
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_get_tasks_project_not_found():
    result = await get_tasks(project_name="NonExistent Project")
    assert isinstance(result, str)
    assert result == "Project with name 'NonExistent Project' doesn't exist"


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_create_task_project_not_found():
    result = await create_task(name="My Task", project_name="NonExistent Project")
    assert isinstance(result, str)
    assert result == "Project with name 'NonExistent Project' doesn't exist"


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_update_task_project_not_found():
    result = await update_task(task_name="Research", project_name="NonExistent Project")
    assert isinstance(result, str)
    assert result == "Project with name 'NonExistent Project' doesn't exist"


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_delete_task_project_not_found():
    result = await delete_task(task_name="Research", project_name="NonExistent Project")
    assert isinstance(result, str)
    assert result == "Project with name 'NonExistent Project' doesn't exist"


# ---------------------------------------------------------------------------
# Task not found
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_update_task_not_found():
    result = await update_task(task_name="NonExistent Task", project_name="Alpha")
    assert isinstance(result, str)
    assert result == "Task with name 'NonExistent Task' doesn't exist in the project"


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_delete_task_not_found():
    result = await delete_task(task_name="NonExistent Task", project_name="Alpha")
    assert isinstance(result, str)
    assert result == "Task with name 'NonExistent Task' doesn't exist in the project"


# ---------------------------------------------------------------------------
# Workspace not found — create / update / delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_create_task_workspace_not_found():
    result = await create_task(
        name="My Task", project_name="Alpha", workspace_name="NonExistentWS"
    )
    assert result == "Workspace with name 'NonExistentWS' doesn't exist"


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_update_task_workspace_not_found():
    result = await update_task(
        task_name="Research", project_name="Alpha", workspace_name="NonExistentWS"
    )
    assert result == "Workspace with name 'NonExistentWS' doesn't exist"


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_delete_task_workspace_not_found():
    result = await delete_task(
        task_name="Research", project_name="Alpha", workspace_name="NonExistentWS"
    )
    assert result == "Workspace with name 'NonExistentWS' doesn't exist"


# ---------------------------------------------------------------------------
# API error paths — get / create / update / delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_tasks_api_error():
    with (
        patch("tasks._get_default_workspace_id", new_callable=AsyncMock, return_value=12345),
        patch("tasks._get_project_id_by_name", new_callable=AsyncMock, return_value=99),
        patch("tasks._get_tasks_helper", new_callable=AsyncMock, return_value="503 error"),
    ):
        result = await get_tasks(project_name="Alpha")
    assert result == "Failed to fetch tasks: 503 error"


@pytest.mark.asyncio
async def test_create_task_api_error():
    with (
        patch("tasks._get_default_workspace_id", new_callable=AsyncMock, return_value=12345),
        patch("tasks._get_project_id_by_name", new_callable=AsyncMock, return_value=99),
        patch("tasks._create_task_helper", new_callable=AsyncMock, return_value="503 error"),
    ):
        result = await create_task(name="My Task", project_name="Alpha")
    assert result == "Failed to create task: 503 error"


@pytest.mark.asyncio
async def test_update_task_api_error():
    with (
        patch("tasks._get_default_workspace_id", new_callable=AsyncMock, return_value=12345),
        patch("tasks._get_project_id_by_name", new_callable=AsyncMock, return_value=99),
        patch("tasks._get_task_id_by_name", new_callable=AsyncMock, return_value=42),
        patch("tasks._update_task_helper", new_callable=AsyncMock, return_value="503 error"),
    ):
        result = await update_task(task_name="Research", project_name="Alpha")
    assert result == "Failed to update task: 503 error"


@pytest.mark.asyncio
async def test_delete_task_api_error():
    with (
        patch("tasks._get_default_workspace_id", new_callable=AsyncMock, return_value=12345),
        patch("tasks._get_project_id_by_name", new_callable=AsyncMock, return_value=99),
        patch("tasks._get_task_id_by_name", new_callable=AsyncMock, return_value=42),
        patch("tasks._delete_task_helper", new_callable=AsyncMock, return_value="503 error"),
    ):
        result = await delete_task(task_name="Research", project_name="Alpha")
    assert result == "Failed to delete task 'Research': 503 error"


@pytest.mark.asyncio
async def test_get_task_id_by_name_helper_error():
    with patch("tasks.toggl_request", new_callable=AsyncMock, return_value="503 error"):
        from tasks import _get_task_id_by_name

        result = await _get_task_id_by_name("Research", 12345, 99)
    assert result == "Error fetching tasks: 503 error"
