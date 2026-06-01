import datetime
import os
import sys
from pathlib import Path

import pytest


def _utc_offset(days: int, hour: int = 10) -> str:
    """Return an ISO 8601 UTC timestamp for a given day offset and hour."""
    dt = datetime.datetime.now(datetime.timezone.utc).replace(
        hour=hour, minute=0, second=0, microsecond=0
    ) + datetime.timedelta(days=days)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


sys.path.insert(0, str(Path(__file__).parent.parent))

from toggl_mcp_server import (
    create_client,
    create_project,
    create_tag,
    create_task,
    create_time_entry,
    delete_client,
    delete_project,
    delete_tag,
    delete_task,
    delete_time_entry,
    get_clients,
    get_tags,
    get_tasks,
    update_client,
    update_project,
    update_tag,
    update_task,
    update_time_entry,
)

WORKSPACE_ID = int(os.environ["TOGGL_WORKSPACE_ID"])


# ---------------------------------------------------------------------------
# Project lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_project_lifecycle(vcr):
    # --- Create ---
    result = await create_project(name="Delta", color="#4dc3ff")

    assert isinstance(result, dict), f"Expected dict, got: {result}"
    assert result["name"] == "Delta"
    assert result["active"] is True
    assert "id" in result

    project_id = result["id"]

    # --- Update ---
    updated = await update_project(
        project_id=project_id,
        operations=[{"op": "replace", "path": "/color", "value": "#bc2d07"}],
    )

    assert isinstance(updated, dict), f"Expected dict, got: {updated}"
    successes = updated.get("success", [])
    assert len(successes) >= 1

    # --- Delete ---
    deleted = await delete_project(project_id=project_id)

    assert isinstance(deleted, str)
    assert "Successfully" in deleted


# ---------------------------------------------------------------------------
# Time entry lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_time_entry_lifecycle(vcr):
    start = _utc_offset(-2, hour=10)
    stop = _utc_offset(-2, hour=11)

    # --- Create ---
    result = await create_time_entry(
        description="Lifecycle test entry",
        start=start,
        stop=stop,
        duration=3600,
    )

    assert isinstance(result, dict), f"Expected dict, got: {result}"
    assert "toggle_time_entry_response" in result
    entry = result["toggle_time_entry_response"]
    assert entry["description"] == "Lifecycle test entry"
    assert "id" in entry

    # --- Update ---
    updated = await update_time_entry(
        time_entry_name="Lifecycle test entry",
        description="Lifecycle test entry (updated)",
        tags=["dev"],
    )

    assert isinstance(updated, dict), f"Expected dict, got: {updated}"
    assert updated["description"] == "Lifecycle test entry (updated)"
    assert "dev" in updated.get("tags", [])

    # --- Delete ---
    deleted = await delete_time_entry(time_entry_name="Lifecycle test entry (updated)")

    assert isinstance(deleted, str)
    assert "Successfully" in deleted


# ---------------------------------------------------------------------------
# Task lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_task_lifecycle(vcr):
    # --- Resolve project ---
    from toggl_mcp_server import get_all_projects

    projects_resp = await get_all_projects()
    alpha = next(p for p in projects_resp["projects"] if p["name"] == "Alpha")
    project_id = alpha["id"]

    # --- Create ---
    result = await create_task(name="Lifecycle task", project_id=project_id)

    assert isinstance(result, dict), f"Expected dict, got: {result}"
    assert result["name"] == "Lifecycle task"
    assert result["active"] is True
    assert "id" in result

    task_id = result["id"]

    # --- Read (verify it appears in listing) ---
    tasks = await get_tasks(project_id=project_id)

    assert isinstance(tasks, list), f"Expected list, got: {tasks}"
    names = {t["name"] for t in tasks}
    assert "Lifecycle task" in names

    # --- Update ---
    updated = await update_task(
        task_id=task_id,
        project_id=project_id,
        name="Lifecycle task (updated)",
    )

    assert isinstance(updated, dict), f"Expected dict, got: {updated}"
    assert updated["name"] == "Lifecycle task (updated)"

    # --- Delete ---
    deleted = await delete_task(task_id=task_id, project_id=project_id)

    assert isinstance(deleted, str)
    assert "Successfully" in deleted


# ---------------------------------------------------------------------------
# Tag lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_tag_lifecycle(vcr):
    # --- Create ---
    result = await create_tag(name="lifecycle-tag")

    assert isinstance(result, dict), f"Expected dict, got: {result}"
    assert result["name"] == "lifecycle-tag"
    assert "id" in result

    tag_id = result["id"]

    # --- Read (verify it appears in listing) ---
    tags = await get_tags()

    assert isinstance(tags, list), f"Expected list, got: {tags}"
    names = {t["name"] for t in tags}
    assert "lifecycle-tag" in names

    # --- Update ---
    updated = await update_tag(tag_id=tag_id, new_name="lifecycle-tag-updated")

    assert isinstance(updated, dict), f"Expected dict, got: {updated}"
    assert updated["name"] == "lifecycle-tag-updated"

    # --- Delete ---
    deleted = await delete_tag(tag_id=tag_id)

    assert isinstance(deleted, str)
    assert "Successfully" in deleted


# ---------------------------------------------------------------------------
# Client lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_client_lifecycle(vcr):
    # --- Create ---
    result = await create_client(name="Lifecycle client", notes="test notes")

    assert isinstance(result, dict), f"Expected dict, got: {result}"
    assert result["name"] == "Lifecycle client"
    assert "id" in result

    client_id = result["id"]

    # --- Read (verify it appears in listing) ---
    clients = await get_clients()

    assert isinstance(clients, list), f"Expected list, got: {clients}"
    names = {c["name"] for c in clients}
    assert "Lifecycle client" in names

    # --- Update ---
    updated = await update_client(client_id=client_id, new_name="Lifecycle client (updated)")

    assert isinstance(updated, dict), f"Expected dict, got: {updated}"
    assert updated["name"] == "Lifecycle client (updated)"

    # --- Delete ---
    deleted = await delete_client(client_id=client_id)

    assert isinstance(deleted, str)
    assert "Successfully" in deleted
