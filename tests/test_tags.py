import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import app as server
from tags import create_tag, delete_tag, get_tags, update_tag

# ---------------------------------------------------------------------------
# API error codes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_create_tag_bad_request():
    result = await create_tag(name="")
    assert isinstance(result, str)
    assert result == "Failed to create tag: tag name can't be blank"


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_get_tags_unauthorized(monkeypatch):
    monkeypatch.setitem(server.headers, "Authorization", "Basic aW52YWxpZA==")
    result = await get_tags()
    assert isinstance(result, str)
    assert result == "Failed to fetch tags: 401 Unauthorized"


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_get_tags_forbidden(monkeypatch):
    async def foreign_workspace():
        return 1

    monkeypatch.setattr("tags._get_default_workspace_id", foreign_workspace)
    result = await get_tags()
    assert isinstance(result, str)
    assert result == "Failed to fetch tags: workspace not found/accessible"


# ---------------------------------------------------------------------------
# Workspace not found
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_get_tags_workspace_not_found():
    result = await get_tags(workspace_name="NonExistentWS")
    assert isinstance(result, str)
    assert result == "Workspace with name 'NonExistentWS' doesn't exist"


# ---------------------------------------------------------------------------
# Tag not found
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_update_tag_not_found():
    result = await update_tag(tag_name="NonExistent Tag", new_name="x")
    assert isinstance(result, str)
    assert result == "Tag with name 'NonExistent Tag' doesn't exist"


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_delete_tag_not_found():
    result = await delete_tag(tag_name="NonExistent Tag")
    assert isinstance(result, str)
    assert result == "Tag with name 'NonExistent Tag' doesn't exist"


# ---------------------------------------------------------------------------
# Workspace not found — create / update / delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_create_tag_workspace_not_found():
    result = await create_tag(name="my-tag", workspace_name="NonExistentWS")
    assert result == "Workspace with name 'NonExistentWS' doesn't exist"


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_update_tag_workspace_not_found():
    result = await update_tag(tag_name="dev", new_name="dev2", workspace_name="NonExistentWS")
    assert result == "Workspace with name 'NonExistentWS' doesn't exist"


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_delete_tag_workspace_not_found():
    result = await delete_tag(tag_name="dev", workspace_name="NonExistentWS")
    assert result == "Workspace with name 'NonExistentWS' doesn't exist"


# ---------------------------------------------------------------------------
# API error paths — get_tag_id / update / delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_tag_id_by_name_helper_error():
    with patch("tags.toggl_request", new_callable=AsyncMock, return_value="503 error"):
        from tags import _get_tag_id_by_name

        result = await _get_tag_id_by_name("dev", 12345)
    assert result == "Error fetching tags: 503 error"


@pytest.mark.asyncio
async def test_update_tag_api_error():
    with (
        patch("tags._get_default_workspace_id", new_callable=AsyncMock, return_value=12345),
        patch("tags._get_tag_id_by_name", new_callable=AsyncMock, return_value=42),
        patch("tags._update_tag_helper", new_callable=AsyncMock, return_value="503 error"),
    ):
        result = await update_tag(tag_name="dev", new_name="dev2")
    assert result == "Failed to update tag: 503 error"


@pytest.mark.asyncio
async def test_delete_tag_api_error():
    with (
        patch("tags._get_default_workspace_id", new_callable=AsyncMock, return_value=12345),
        patch("tags._get_tag_id_by_name", new_callable=AsyncMock, return_value=42),
        patch("tags._delete_tag_helper", new_callable=AsyncMock, return_value="503 error"),
    ):
        result = await delete_tag(tag_name="dev")
    assert result == "Failed to delete tag 'dev': 503 error"
