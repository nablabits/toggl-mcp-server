import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import resources
from resources import (
    _get_default_workspace_id,
    _get_project_id_by_name,
    _get_time_entry_id_by_name,
    _get_workspace_id_by_name,
)
from toggl_mcp_server import _get_projects, _get_time_entries, _get_workspaces, get_tasks

WORKSPACE_ID = int(os.environ["TOGGL_WORKSPACE_ID"])

SEEDED_PROJECTS = {"Alpha", "Beta", "Gamma"}
SEEDED_TAGS = {"dev", "review", "meeting", "docs"}
SEEDED_TASKS = {"Research", "Implementation"}  # tasks seeded under Alpha
SEEDED_ENTRIES = {
    "Planning session",
    "Implementation work",
    "Code review",
    "Documentation",
    "Bug investigation",
    "Team sync",
    "Feature work",
    "Testing",
    "Weekly review",
}


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_get_projects(vcr):
    result = await _get_projects(WORKSPACE_ID)

    assert "projects" in result
    names = {p["name"] for p in result["projects"]}
    assert SEEDED_PROJECTS.issubset(names)

    # Each project has expected fields
    for project in result["projects"]:
        assert "id" in project
        assert "name" in project
        assert project["active"] is True


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_get_time_entries(vcr):
    result = await _get_time_entries()

    assert isinstance(result, list)
    assert len(result) >= len(SEEDED_ENTRIES)

    descriptions = {e["description"] for e in result}
    assert SEEDED_ENTRIES.issubset(descriptions)

    # Each entry has expected fields
    for entry in result:
        assert "id" in entry
        assert "start" in entry
        assert "workspace_id" in entry


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_get_time_entries_tags(vcr):
    result = await _get_time_entries()

    all_tags = {tag for entry in result for tag in (entry.get("tags") or [])}
    assert SEEDED_TAGS.issubset(all_tags)


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_get_workspaces(vcr):
    result = await _get_workspaces()

    assert isinstance(result, list)
    assert len(result) >= 1

    workspace_ids = {w["id"] for w in result}
    assert WORKSPACE_ID in workspace_ids


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_get_tasks(vcr):
    result = await get_tasks(project_name="Alpha")

    assert isinstance(result, list), f"Expected list, got: {result}"
    names = {t["name"] for t in result}
    assert SEEDED_TASKS.issubset(names)

    for task in result:
        assert "id" in task
        assert "name" in task
        assert task["active"] is True


# ---------------------------------------------------------------------------
# _get_default_workspace_id — fallback to /me when env var is unset
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_get_default_workspace_id_from_api(monkeypatch):
    monkeypatch.delitem(os.environ, "TOGGL_WORKSPACE_ID", raising=False)
    result = await _get_default_workspace_id()
    assert isinstance(result, int)


@pytest.mark.asyncio
async def test_get_default_workspace_id_api_error(monkeypatch):
    monkeypatch.delitem(os.environ, "TOGGL_WORKSPACE_ID", raising=False)
    with patch("resources.toggl_request", new_callable=AsyncMock, return_value="503 error"):
        result = await _get_default_workspace_id()
    assert result == "Failed to fetch default workspace ID: 503 error"


# ---------------------------------------------------------------------------
# _get_project_id_by_name — _get_projects returns an error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_project_id_by_name_projects_error():
    with patch(
        "resources._get_projects",
        new_callable=AsyncMock,
        return_value={"error": "upstream failure"},
    ):
        result = await _get_project_id_by_name("Alpha", 12345)
    assert result == "Error fetching projects: upstream failure"


# ---------------------------------------------------------------------------
# _get_time_entry_id_by_name — _get_time_entries returns an error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_time_entry_id_by_name_entries_error():
    with patch(
        "resources._get_time_entries",
        new_callable=AsyncMock,
        return_value={"error": "upstream failure"},
    ):
        result = await _get_time_entry_id_by_name("My entry", 12345)
    assert result == "Error fetching time_entries: upstream failure"


# ---------------------------------------------------------------------------
# _get_workspace_id_by_name — error and success paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_workspace_id_by_name_workspaces_error():
    with patch(
        "resources._get_workspaces",
        new_callable=AsyncMock,
        return_value={"error": "upstream failure"},
    ):
        result = await _get_workspace_id_by_name("MyWorkspace")
    assert result == "Error fetching workspaces: upstream failure"


@pytest.mark.asyncio
async def test_get_workspace_id_by_name_found():
    fake_workspaces = [{"id": 42, "name": "MyWorkspace"}, {"id": 99, "name": "Other"}]
    with patch("resources._get_workspaces", new_callable=AsyncMock, return_value=fake_workspaces):
        result = await _get_workspace_id_by_name("MyWorkspace")
    assert result == 42


# ---------------------------------------------------------------------------
# _get_workspaces — cache behaviour
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_workspaces_caches_result():
    fake_workspaces = [{"id": 42, "name": "MyWorkspace"}]
    resources._workspaces_cache = None
    try:
        with patch(
            "resources.toggl_request", new_callable=AsyncMock, return_value=fake_workspaces
        ) as mock_req:
            await resources._get_workspaces()
            await resources._get_workspaces()
        mock_req.assert_called_once()
    finally:
        resources._workspaces_cache = None


@pytest.mark.asyncio
async def test_get_workspaces_does_not_cache_errors():
    resources._workspaces_cache = None
    try:
        with patch(
            "resources.toggl_request", new_callable=AsyncMock, return_value="upstream failure"
        ) as mock_req:
            await resources._get_workspaces()
            await resources._get_workspaces()
        assert mock_req.call_count == 2
        assert resources._workspaces_cache is None
    finally:
        resources._workspaces_cache = None
