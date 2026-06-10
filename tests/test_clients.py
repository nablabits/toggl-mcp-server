import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import app as server
from clients import create_client, delete_client, get_clients, update_client

# ---------------------------------------------------------------------------
# API error codes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_create_client_bad_request():
    result = await create_client(name="")
    assert isinstance(result, str)
    assert result == "Client name cannot be empty"


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_get_clients_unauthorized(monkeypatch):
    monkeypatch.setitem(server.headers, "Authorization", "Basic aW52YWxpZA==")
    result = await get_clients()
    assert isinstance(result, str)
    assert result == "401 Unauthorized"


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_get_clients_forbidden(monkeypatch):
    async def foreign_workspace():
        return 1  # workspace that exists in Toggl but we don't own

    monkeypatch.setattr("clients._get_default_workspace_id", foreign_workspace)
    result = await get_clients()
    assert isinstance(result, str)
    assert result == "workspace not found/accessible"


# ---------------------------------------------------------------------------
# Workspace error propagation — get / create / update / delete
# ---------------------------------------------------------------------------

_WS_ERROR = "Failed to fetch default workspace ID: 503 error"


@pytest.mark.asyncio
async def test_get_clients_workspace_error():
    with patch(
        "clients._get_default_workspace_id", new_callable=AsyncMock, return_value=_WS_ERROR
    ):
        result = await get_clients()
    assert result == _WS_ERROR


@pytest.mark.asyncio
async def test_create_client_workspace_error():
    with patch(
        "clients._get_default_workspace_id", new_callable=AsyncMock, return_value=_WS_ERROR
    ):
        result = await create_client(name="Acme")
    assert result == _WS_ERROR


@pytest.mark.asyncio
async def test_update_client_workspace_error():
    with patch(
        "clients._get_default_workspace_id", new_callable=AsyncMock, return_value=_WS_ERROR
    ):
        result = await update_client(client_id=42, new_name="Acme2")
    assert result == _WS_ERROR


@pytest.mark.asyncio
async def test_delete_client_workspace_error():
    with patch(
        "clients._get_default_workspace_id", new_callable=AsyncMock, return_value=_WS_ERROR
    ):
        result = await delete_client(client_id=42)
    assert result == _WS_ERROR


# ---------------------------------------------------------------------------
# API error paths — delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_client_api_error():
    with (
        patch("clients._get_default_workspace_id", new_callable=AsyncMock, return_value=12345),
        patch("clients._delete_client_helper", new_callable=AsyncMock, return_value="503 error"),
    ):
        result = await delete_client(client_id=42)
    assert result == "Failed to delete client (id: 42): 503 error"
