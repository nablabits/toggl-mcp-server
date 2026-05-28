import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.http import toggl_request

_URL = "https://api.track.toggl.com/api/v9/me"


def _make_client_mock(responses):
    """Return a patched AsyncClient whose .get returns `responses` in order."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(side_effect=responses)
    return mock_client


@pytest.mark.asyncio
async def test_toggl_request_connect_error():
    with patch("helpers.http.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        mock_client_cls.return_value = mock_client

        result = await toggl_request("get", _URL)

    assert isinstance(result, str)
    assert result.startswith("Connection error:")


@pytest.mark.asyncio
async def test_toggl_request_success_non_json_body():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.side_effect = ValueError("no JSON")

    with patch("helpers.http.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        result = await toggl_request("get", _URL)

    assert result == []


@pytest.mark.asyncio
async def test_toggl_request_429_retries_and_succeeds():
    """A single 429 triggers one retry; if the retry succeeds the result is returned."""
    r429 = MagicMock()
    r429.status_code = 429

    r200 = MagicMock()
    r200.status_code = 200
    r200.json.return_value = {"id": 1}

    with patch("helpers.http.httpx.AsyncClient") as mock_client_cls:
        with patch("helpers.http.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_client_cls.return_value = _make_client_mock([r429, r200])
            result = await toggl_request("get", _URL)

    mock_sleep.assert_awaited_once_with(1)
    assert result == {"id": 1}


@pytest.mark.asyncio
async def test_toggl_request_429_twice_returns_error():
    """Two consecutive 429s return the rate-limit error string."""
    r429 = MagicMock()
    r429.status_code = 429

    with patch("helpers.http.httpx.AsyncClient") as mock_client_cls:
        with patch("helpers.http.asyncio.sleep", new_callable=AsyncMock):
            mock_client_cls.return_value = _make_client_mock([r429, r429])
            result = await toggl_request("get", _URL)

    assert isinstance(result, str)
    assert "429" in result
    assert "Rate limit" in result


@pytest.mark.asyncio
async def test_toggl_request_402_surfaces_quota_headers():
    r402 = MagicMock()
    r402.status_code = 402
    r402.headers = {
        "X-Toggl-Quota-Remaining": "0",
        "X-Toggl-Quota-Resets-In": "1800",
    }

    with patch("helpers.http.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=r402)
        mock_client_cls.return_value = mock_client

        result = await toggl_request("get", _URL)

    assert isinstance(result, str)
    assert "402" in result
    assert "0" in result       # remaining
    assert "1800" in result    # resets_in


@pytest.mark.asyncio
async def test_toggl_request_402_missing_headers_uses_unknown():
    r402 = MagicMock()
    r402.status_code = 402
    r402.headers = {}

    with patch("helpers.http.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=r402)
        mock_client_cls.return_value = mock_client

        result = await toggl_request("get", _URL)

    assert "unknown" in result
