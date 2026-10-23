import datetime
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from zoneinfo import ZoneInfo

from helpers.time import _convert_utc_to_local, _normalize_timestamp


def test_convert_utc_to_local_without_milliseconds():
    with patch("helpers.time.get_localzone", return_value=datetime.timezone.utc):
        result = _convert_utc_to_local("2025-05-01T10:00:00Z")
    assert "2025-05-01" in result
    assert "10:00:00" in result


def test_convert_utc_to_local_invalid_format():
    result = _convert_utc_to_local("not-a-timestamp")
    assert result.startswith("Invalid timestamp format:")


# ---------------------------------------------------------------------------
# _normalize_timestamp
# ---------------------------------------------------------------------------

_MADRID = ZoneInfo("Europe/Madrid")


@pytest.fixture
def madrid():
    with patch("helpers.time.get_localzone", return_value=_MADRID):
        yield


@pytest.mark.parametrize(
    "value",
    [
        "2026-10-23T06:21:50Z",
        "2026-10-23T06:21:50z",
        " 2026-10-23T06:21:50Z ",
        "2026-10-23T06:21:50.123Z",
    ],
)
def test_normalize_z_is_utc_and_ignores_local_zone(madrid, value):
    assert _normalize_timestamp(value) == "2026-10-23T06:21:50.000Z"


def test_normalize_naive_is_local_time(madrid):
    # Madrid is UTC+2 in October (CEST).
    assert _normalize_timestamp("2026-10-23T08:21:50") == "2026-10-23T06:21:50.000Z"


def test_normalize_naive_winter_uses_standard_offset(madrid):
    assert _normalize_timestamp("2026-01-15T08:00:00") == "2026-01-15T07:00:00.000Z"


@pytest.mark.parametrize(
    "value, expected",
    [
        ("2026-10-23T08:21:50+02:00", "2026-10-23T06:21:50.000Z"),
        ("2026-10-23T01:21:50-05:00", "2026-10-23T06:21:50.000Z"),
    ],
)
def test_normalize_explicit_offset_is_honoured(madrid, value, expected):
    assert _normalize_timestamp(value) == expected


@pytest.mark.parametrize("value", ["not-a-timestamp", "", "tomorrow 9am", "2026-13-45T00:00:00"])
def test_normalize_invalid_raises(madrid, value):
    with pytest.raises(ValueError, match="Invalid timestamp"):
        _normalize_timestamp(value)


def test_normalize_dst_gap_raises(madrid):
    # 2026-03-29 02:30 does not exist in Madrid (clocks jump 02:00 -> 03:00).
    with pytest.raises(ValueError, match="does not exist"):
        _normalize_timestamp("2026-03-29T02:30:00")


def test_normalize_dst_fold_raises(madrid):
    # 2026-10-25 02:30 happens twice in Madrid (clocks go back 03:00 -> 02:00).
    with pytest.raises(ValueError, match="ambiguous"):
        _normalize_timestamp("2026-10-25T02:30:00")


def test_normalize_dst_ambiguity_resolved_by_explicit_offset(madrid):
    assert _normalize_timestamp("2026-10-25T02:30:00+02:00") == "2026-10-25T00:30:00.000Z"
