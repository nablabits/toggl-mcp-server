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
# Workspace not found
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_get_clients_workspace_not_found():
    result = await get_clients(workspace_name="NonExistentWS")
    assert isinstance(result, str)
    assert result == "Workspace with name 'NonExistentWS' doesn't exist"


# ---------------------------------------------------------------------------
# Client not found
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_update_client_not_found():
    result = await update_client(client_name="NonExistent Client", new_name="x")
    assert isinstance(result, str)
    assert result == "Client with name 'NonExistent Client' doesn't exist"


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_delete_client_not_found():
    result = await delete_client(client_name="NonExistent Client")
    assert isinstance(result, str)
    assert result == "Client with name 'NonExistent Client' doesn't exist"


# ---------------------------------------------------------------------------
# Workspace not found — create / update / delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_create_client_workspace_not_found():
    result = await create_client(name="Acme", workspace_name="NonExistentWS")
    assert result == "Workspace with name 'NonExistentWS' doesn't exist"


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_update_client_workspace_not_found():
    result = await update_client(
        client_name="Acme", new_name="Acme2", workspace_name="NonExistentWS"
    )
    assert result == "Workspace with name 'NonExistentWS' doesn't exist"


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_delete_client_workspace_not_found():
    result = await delete_client(client_name="Acme", workspace_name="NonExistentWS")
    assert result == "Workspace with name 'NonExistentWS' doesn't exist"


# ---------------------------------------------------------------------------
# API error paths — get_client_id / delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_client_id_by_name_helper_error():
    with patch("clients.toggl_request", new_callable=AsyncMock, return_value="503 error"):
        from clients import _get_client_id_by_name

        result = await _get_client_id_by_name("Acme", 12345)
    assert result == "Error fetching clients: 503 error"


@pytest.mark.asyncio
async def test_delete_client_api_error():
    with (
        patch("clients._get_default_workspace_id", new_callable=AsyncMock, return_value=12345),
        patch("clients._get_client_id_by_name", new_callable=AsyncMock, return_value=42),
        patch("clients._delete_client_helper", new_callable=AsyncMock, return_value="503 error"),
    ):
        result = await delete_client(client_name="Acme")
    assert result == "Failed to delete client 'Acme': 503 error"
