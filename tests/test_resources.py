import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import resources
from resources import _fetch_projects, _get_default_workspace_id
from toggl_mcp_server import _get_projects, _get_time_entries, _get_workspaces, get_tasks

WORKSPACE_ID = int(os.environ["TOGGL_WORKSPACE_ID"])

SEEDED_PROJECTS = {"Alpha", "Beta", "Gamma"}
SEEDED_ARCHIVED_PROJECTS = {"Archived sample project"}
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
    projects = await _get_projects(WORKSPACE_ID)
    alpha_id = next(p["id"] for p in projects["projects"] if p["name"] == "Alpha")
    result = await get_tasks(project_id=alpha_id)

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


# ---------------------------------------------------------------------------
# _fetch_projects — pagination
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_projects_empty_workspace():
    with patch("resources.toggl_request", new_callable=AsyncMock, return_value=[]) as mock_req:
        result = await _fetch_projects(WORKSPACE_ID)

    assert result == {"projects": []}
    mock_req.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_projects_multiple_pages():
    page1 = [{"id": i, "name": f"P{i}", "active": True} for i in range(200)]
    page2 = [{"id": 200, "name": "P200", "active": True}]

    with patch(
        "resources.toggl_request", new_callable=AsyncMock, side_effect=[page1, page2]
    ) as mock_req:
        result = await _fetch_projects(WORKSPACE_ID)

    assert result == {"projects": page1 + page2}
    assert mock_req.call_count == 2


# ---------------------------------------------------------------------------
# _fetch_projects — active filter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_fetch_projects_active_only():
    result = await _fetch_projects(WORKSPACE_ID, active=True)

    assert "projects" in result
    names = {p["name"] for p in result["projects"]}
    assert SEEDED_PROJECTS.issubset(names)
    assert not SEEDED_ARCHIVED_PROJECTS.intersection(names)
    assert all(p["active"] is True for p in result["projects"])


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_fetch_projects_inactive_only():
    result = await _fetch_projects(WORKSPACE_ID, active=False)

    assert "projects" in result
    names = {p["name"] for p in result["projects"]}
    assert SEEDED_ARCHIVED_PROJECTS.issubset(names)
    assert not SEEDED_PROJECTS.intersection(names)
    assert all(p["active"] is False for p in result["projects"])


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_fetch_projects_both():
    result = await _fetch_projects(WORKSPACE_ID, active="both")

    assert "projects" in result
    names = {p["name"] for p in result["projects"]}
    assert SEEDED_PROJECTS.issubset(names)
    assert SEEDED_ARCHIVED_PROJECTS.issubset(names)
    statuses = {p["active"] for p in result["projects"]}
    assert statuses == {True, False}
