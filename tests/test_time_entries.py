import datetime
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from time_entries import (
    _new_time_entry_helper,
    create_time_entry,
    delete_time_entry,
    get_current_time_entry,
    get_time_entries_for_range,
    stop_time_entry,
    update_time_entry,
)

_FAKE_ENTRY = {"id": 1, "description": "test"}
_FAKE_LOCAL_TIME = "2025-05-01 10:00:00 UTC"


def _fixed_tz(offset_hours: int) -> datetime.timezone:
    return datetime.timezone(datetime.timedelta(hours=offset_hours))


@pytest.fixture
def mock_workspace():
    with patch(
        "time_entries._get_default_workspace_id",
        new_callable=AsyncMock,
        return_value=12345,
    ):
        yield


@pytest.fixture
def mock_helper():
    with patch(
        "time_entries._new_time_entry_helper",
        new_callable=AsyncMock,
        return_value=(_FAKE_ENTRY, _FAKE_LOCAL_TIME),
    ) as m:
        yield m


# ---------------------------------------------------------------------------
# Timezone correction — start
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_naive_local_time_converted_to_utc(mock_workspace, mock_helper):
    with patch("time_entries.get_localzone", return_value=_fixed_tz(2)):
        await create_time_entry(start="2025-05-01T10:00:00", duration=3600)

    # local 10:00 UTC+2 → UTC 08:00
    assert mock_helper.call_args.kwargs["start"] == "2025-05-01T08:00:00.000Z"


@pytest.mark.asyncio
async def test_start_z_suffix_stripped_before_conversion(mock_workspace, mock_helper):
    with patch("time_entries.get_localzone", return_value=_fixed_tz(3)):
        await create_time_entry(start="2025-05-01T10:00:00Z", duration=3600)

    # local 10:00 UTC+3 → UTC 07:00
    assert mock_helper.call_args.kwargs["start"] == "2025-05-01T07:00:00.000Z"


@pytest.mark.asyncio
async def test_start_fractional_seconds_stripped_before_conversion(mock_workspace, mock_helper):
    with patch("time_entries.get_localzone", return_value=_fixed_tz(1)):
        await create_time_entry(start="2025-05-01T10:00:00.123456", duration=3600)

    # local 10:00 UTC+1 → UTC 09:00
    assert mock_helper.call_args.kwargs["start"] == "2025-05-01T09:00:00.000Z"


@pytest.mark.asyncio
async def test_start_fallback_to_original_when_localzone_fails(mock_workspace, mock_helper):
    with patch("time_entries.get_localzone", side_effect=Exception("tz unavailable")):
        await create_time_entry(start="2025-05-01T10:00:00", duration=3600)

    assert mock_helper.call_args.kwargs["start"] == "2025-05-01T10:00:00"


# ---------------------------------------------------------------------------
# Timezone correction — stop
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stop_naive_local_time_converted_to_utc(mock_workspace, mock_helper):
    with patch("time_entries.get_localzone", return_value=_fixed_tz(2)):
        await create_time_entry(
            start="2025-05-01T10:00:00", stop="2025-05-01T11:00:00", duration=3600
        )

    assert mock_helper.call_args.kwargs["stop"] == "2025-05-01T09:00:00.000Z"


@pytest.mark.asyncio
async def test_stop_fallback_to_original_when_localzone_fails(mock_workspace, mock_helper):
    with patch("time_entries.get_localzone", side_effect=Exception("tz unavailable")):
        await create_time_entry(
            start="2025-05-01T10:00:00", stop="2025-05-01T11:00:00", duration=3600
        )

    assert mock_helper.call_args.kwargs["stop"] == "2025-05-01T11:00:00"


# ---------------------------------------------------------------------------
# Timezone correction — shared state
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_localzone_called_once_for_both_timestamps(mock_workspace, mock_helper):
    with patch("time_entries.get_localzone", return_value=_fixed_tz(1)) as mock_tz:
        await create_time_entry(
            start="2025-05-01T10:00:00", stop="2025-05-01T11:00:00", duration=3600
        )

    mock_tz.assert_called_once()


# ---------------------------------------------------------------------------
# No start → no timezone correction
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_start_skips_timezone_correction(mock_workspace, mock_helper):
    with patch("time_entries.get_localzone") as mock_tz:
        await create_time_entry(description="live entry")

    mock_tz.assert_not_called()


# ---------------------------------------------------------------------------
# stop_time_entry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_stop_time_entry_not_found():
    result = await stop_time_entry(entry_id=99999999999)
    assert isinstance(result, str)


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_stop_time_entry_by_entry_id():
    # Create a live timer, then stop it by the returned entry_id.
    created = await create_time_entry(description="Stop-by-id test entry")
    assert isinstance(created, dict)
    entry_id = created["toggle_time_entry_response"]["id"]

    result = await stop_time_entry(entry_id=entry_id)
    assert isinstance(result, dict)
    assert result["stop"] is not None
    assert result["id"] == entry_id


# ---------------------------------------------------------------------------
# get_current_time_entry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_get_current_time_entry():
    # Cassette was recorded with no timer running; API returns null → None.
    result = await get_current_time_entry()
    assert result is None


# ---------------------------------------------------------------------------
# create_time_entry — workspace / project not found
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_time_entry_workspace_error():
    _WS_ERROR = "Failed to fetch default workspace ID: 503 error"
    with patch(
        "time_entries._get_default_workspace_id", new_callable=AsyncMock, return_value=_WS_ERROR
    ):
        result = await create_time_entry()
    assert result == {"error": _WS_ERROR}


# ---------------------------------------------------------------------------
# delete_time_entry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_delete_time_entry_not_found():
    result = await delete_time_entry(entry_id=99999999999)
    assert isinstance(result, str)


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_delete_time_entry_by_entry_id():
    # Create a completed entry, then delete it by the returned entry_id.
    created = await create_time_entry(description="Delete-by-id test entry", duration=60)
    assert isinstance(created, dict)
    entry_id = created["toggle_time_entry_response"]["id"]

    result = await delete_time_entry(entry_id=entry_id)
    assert isinstance(result, str)
    assert "Successfully" in result
    assert str(entry_id) in result


# ---------------------------------------------------------------------------
# update_time_entry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_update_time_entry_not_found():
    result = await update_time_entry(entry_id=99999999999, description="new desc")
    assert isinstance(result, str)


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_update_time_entry_by_entry_id():
    # Create a completed entry, then update it by the returned entry_id.
    created = await create_time_entry(description="Update-by-id test entry", duration=60)
    assert isinstance(created, dict)
    entry_id = created["toggle_time_entry_response"]["id"]

    result = await update_time_entry(entry_id=entry_id, description="Updated description")
    assert isinstance(result, dict)
    assert result["id"] == entry_id
    assert result["description"] == "Updated description"


# ---------------------------------------------------------------------------
# get_time_entries_for_range
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_get_time_entries_for_range_by_explicit_dates():
    # Sandbox has 3 entries on 2026-05-19: "Weekly review", "Testing", "Feature work"
    result = await get_time_entries_for_range(start_date="2026-05-19", end_date="2026-05-20")
    assert isinstance(result, list)
    assert len(result) == 3
    assert {e["description"] for e in result} == {"Weekly review", "Testing", "Feature work"}


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_get_time_entries_for_range_multi_day():
    # Sandbox has 6 entries on 2026-05-18 and 2026-05-19
    result = await get_time_entries_for_range(start_date="2026-05-18", end_date="2026-05-20")
    assert isinstance(result, list)
    assert len(result) == 6
    assert {e["description"] for e in result} == {
        "Weekly review",
        "Testing",
        "Feature work",
        "Team sync",
        "Bug investigation",
        "Documentation",
    }


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_get_time_entries_for_range_by_day_offsets(monkeypatch):
    # Pin _get_date_range so the cassette captures deterministic query params
    # (replay works regardless of what today's date is)
    monkeypatch.setattr(
        "time_entries._get_date_range",
        lambda _: ("2026-05-19T00:00:00.000Z", "2026-05-20T00:00:00.000Z"),
    )
    result = await get_time_entries_for_range(from_day_offset=0, to_day_offset=0)
    assert isinstance(result, list)
    assert len(result) == 3
    assert {e["description"] for e in result} == {"Weekly review", "Testing", "Feature work"}


@pytest.mark.asyncio
async def test_get_time_entries_for_range_fetch_error(monkeypatch):
    async def _fail(start_date=None, end_date=None):
        return {"error": "Connection error"}

    monkeypatch.setattr("time_entries._fetch_time_entries_for_range", _fail)
    result = await get_time_entries_for_range()
    assert result == "Failed to retrieve entries: Connection error"


# ---------------------------------------------------------------------------
# _new_time_entry_helper — guard and API error paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_new_time_entry_helper_missing_workspace_id():
    result = await _new_time_entry_helper()
    assert result == "Error: workspace_id must be provided to _new_time_entry_helper."


@pytest.mark.asyncio
async def test_new_time_entry_helper_api_error():
    with patch("time_entries.toggl_request", new_callable=AsyncMock, return_value="503 error"):
        result = await _new_time_entry_helper(workspace_id=12345)
    assert result == "503 error"


# ---------------------------------------------------------------------------
# create_time_entry — workspace_id None and project success path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_time_entry_workspace_id_none(mock_helper):
    with patch(
        "time_entries._get_default_workspace_id", new_callable=AsyncMock, return_value=None
    ):
        result = await create_time_entry()
    assert result == {"error": "Could not determine workspace ID."}


@pytest.mark.asyncio
async def test_create_time_entry_with_project_id(mock_workspace, mock_helper):
    result = await create_time_entry(project_id=99)
    assert "toggle_time_entry_response" in result
    assert mock_helper.call_args.kwargs["project_id"] == 99


# ---------------------------------------------------------------------------
# create_time_entry — timezone edge cases (start block)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_localzone_returns_falsy_falls_back(mock_workspace, mock_helper):
    with patch("time_entries.get_localzone", return_value=None):
        await create_time_entry(start="2025-05-01T10:00:00", duration=3600)
    assert mock_helper.call_args.kwargs["start"] == "2025-05-01T10:00:00"


@pytest.mark.asyncio
async def test_start_pytz_style_localize_used(mock_workspace, mock_helper):
    aware_dt = datetime.datetime(2025, 5, 1, 8, 0, 0, tzinfo=datetime.timezone.utc)
    mock_tz = MagicMock()
    mock_tz.localize.return_value = aware_dt
    with patch("time_entries.get_localzone", return_value=mock_tz):
        await create_time_entry(start="2025-05-01T10:00:00", duration=3600)
    mock_tz.localize.assert_called_once()
    assert mock_helper.call_args.kwargs["start"] == "2025-05-01T08:00:00.000Z"


# ---------------------------------------------------------------------------
# create_time_entry — timezone edge cases (stop block, no start provided)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stop_only_fetches_localzone(mock_workspace, mock_helper):
    with patch("time_entries.get_localzone", return_value=_fixed_tz(2)) as mock_tz:
        await create_time_entry(stop="2025-05-01T11:00:00")
    mock_tz.assert_called_once()
    assert mock_helper.call_args.kwargs["stop"] == "2025-05-01T09:00:00.000Z"


@pytest.mark.asyncio
async def test_stop_only_localzone_returns_falsy_falls_back(mock_workspace, mock_helper):
    with patch("time_entries.get_localzone", return_value=None):
        await create_time_entry(stop="2025-05-01T11:00:00")
    assert mock_helper.call_args.kwargs["stop"] == "2025-05-01T11:00:00"


@pytest.mark.asyncio
async def test_stop_only_pytz_style_localize_used(mock_workspace, mock_helper):
    aware_dt = datetime.datetime(2025, 5, 1, 9, 0, 0, tzinfo=datetime.timezone.utc)
    mock_tz = MagicMock()
    mock_tz.localize.return_value = aware_dt
    with patch("time_entries.get_localzone", return_value=mock_tz):
        await create_time_entry(stop="2025-05-01T11:00:00")
    mock_tz.localize.assert_called_once()
    assert mock_helper.call_args.kwargs["stop"] == "2025-05-01T09:00:00.000Z"


# ---------------------------------------------------------------------------
# create_time_entry — helper returns unexpected values
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_time_entry_helper_returns_error_string(mock_workspace):
    with patch(
        "time_entries._new_time_entry_helper",
        new_callable=AsyncMock,
        return_value="Error: something went wrong",
    ):
        result = await create_time_entry()
    assert "error" in result
    assert result["error"] == "Error: something went wrong"


@pytest.mark.asyncio
async def test_create_time_entry_helper_returns_unexpected_format(mock_workspace):
    with patch(
        "time_entries._new_time_entry_helper",
        new_callable=AsyncMock,
        return_value=["not", "a", "valid", "tuple"],
    ):
        result = await create_time_entry()
    assert "error" in result
    assert "Unexpected response format" in result["error"]


# ---------------------------------------------------------------------------
# stop_time_entry / delete_time_entry / update_time_entry — workspace failure
# ---------------------------------------------------------------------------


_WS_ERROR = "Failed to fetch default workspace ID: 503 error"


@pytest.mark.asyncio
async def test_stop_time_entry_workspace_error():
    with patch(
        "time_entries._get_default_workspace_id", new_callable=AsyncMock, return_value=_WS_ERROR
    ):
        result = await stop_time_entry(entry_id=99)
    assert result == _WS_ERROR


@pytest.mark.asyncio
async def test_delete_time_entry_workspace_error():
    with patch(
        "time_entries._get_default_workspace_id", new_callable=AsyncMock, return_value=_WS_ERROR
    ):
        result = await delete_time_entry(entry_id=99)
    assert result == _WS_ERROR


@pytest.mark.asyncio
async def test_update_time_entry_workspace_error():
    with patch(
        "time_entries._get_default_workspace_id", new_callable=AsyncMock, return_value=_WS_ERROR
    ):
        result = await update_time_entry(entry_id=99)
    assert result == _WS_ERROR


# ---------------------------------------------------------------------------
# delete_time_entry — API error paths (sentinel and generic)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_time_entry_not_found_sentinel():
    with (
        patch(
            "time_entries._get_default_workspace_id", new_callable=AsyncMock, return_value=12345
        ),
        patch(
            "time_entries._deleting_time_entry_helper",
            new_callable=AsyncMock,
            return_value="Time Entry not found/accessible",
        ),
    ):
        result = await delete_time_entry(entry_id=99999)
    assert result == "Time entry with time_entry_id 99999 was not found or is inaccessible."


@pytest.mark.asyncio
async def test_delete_time_entry_generic_api_error():
    with (
        patch(
            "time_entries._get_default_workspace_id", new_callable=AsyncMock, return_value=12345
        ),
        patch(
            "time_entries._deleting_time_entry_helper",
            new_callable=AsyncMock,
            return_value="503 Service Unavailable",
        ),
    ):
        result = await delete_time_entry(entry_id=99999)
    assert result == "Failed to delete time_entry 99999. Details: 503 Service Unavailable"
