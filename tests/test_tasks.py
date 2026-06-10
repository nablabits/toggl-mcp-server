import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import app as server
from tasks import create_task, delete_task, get_tasks, update_task

# ---------------------------------------------------------------------------
# Workspace error propagation — get / create / update / delete
# ---------------------------------------------------------------------------

_WS_ERROR = "Failed to fetch default workspace ID: 503 error"


@pytest.mark.asyncio
async def test_get_tasks_workspace_error():
    with patch("tasks._get_default_workspace_id", new_callable=AsyncMock, return_value=_WS_ERROR):
        result = await get_tasks(project_id=99)
    assert result == _WS_ERROR


@pytest.mark.asyncio
async def test_create_task_workspace_error():
    with patch("tasks._get_default_workspace_id", new_callable=AsyncMock, return_value=_WS_ERROR):
        result = await create_task(name="My Task", project_id=99)
    assert result == _WS_ERROR


@pytest.mark.asyncio
async def test_update_task_workspace_error():
    with patch("tasks._get_default_workspace_id", new_callable=AsyncMock, return_value=_WS_ERROR):
        result = await update_task(task_id=42, project_id=99)
    assert result == _WS_ERROR


@pytest.mark.asyncio
async def test_delete_task_workspace_error():
    with patch("tasks._get_default_workspace_id", new_callable=AsyncMock, return_value=_WS_ERROR):
        result = await delete_task(task_id=42, project_id=99)
    assert result == _WS_ERROR


# ---------------------------------------------------------------------------
# API error paths — get / create / update / delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_tasks_api_error():
    with (
        patch("tasks._get_default_workspace_id", new_callable=AsyncMock, return_value=12345),
        patch("tasks._get_tasks_helper", new_callable=AsyncMock, return_value="503 error"),
    ):
        result = await get_tasks(project_id=99)
    assert result == "Failed to fetch tasks: 503 error"


@pytest.mark.asyncio
async def test_create_task_api_error():
    with (
        patch("tasks._get_default_workspace_id", new_callable=AsyncMock, return_value=12345),
        patch("tasks._create_task_helper", new_callable=AsyncMock, return_value="503 error"),
    ):
        result = await create_task(name="My Task", project_id=99)
    assert result == "Failed to create task: 503 error"


@pytest.mark.asyncio
async def test_update_task_api_error():
    with (
        patch("tasks._get_default_workspace_id", new_callable=AsyncMock, return_value=12345),
        patch("tasks._update_task_helper", new_callable=AsyncMock, return_value="503 error"),
    ):
        result = await update_task(task_id=42, project_id=99)
    assert result == "Failed to update task: 503 error"


@pytest.mark.asyncio
async def test_delete_task_api_error():
    with (
        patch("tasks._get_default_workspace_id", new_callable=AsyncMock, return_value=12345),
        patch("tasks._delete_task_helper", new_callable=AsyncMock, return_value="503 error"),
    ):
        result = await delete_task(task_id=42, project_id=99)
    assert result == "Failed to delete task (id: 42): 503 error"
