import datetime
from datetime import timedelta, timezone
from typing import Tuple

from tzlocal import get_localzone


def _get_current_utc_time() -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _convert_utc_to_local(utc_iso_time: str) -> str:
    try:
        if "." in utc_iso_time:
            utc_time = datetime.datetime.strptime(utc_iso_time, "%Y-%m-%dT%H:%M:%S.%fZ")
        else:
            utc_time = datetime.datetime.strptime(utc_iso_time, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as e:
        return f"Invalid timestamp format: {e}"

    utc_time = utc_time.replace(tzinfo=datetime.timezone.utc)
    local_tz = get_localzone()
    local_time = utc_time.astimezone(local_tz)
    return local_time.strftime("%Y-%m-%d %H:%M:%S %Z")


def _iso_timestamp(dt: datetime.datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _get_date_range(days_offset: int) -> Tuple[str, str]:
    today_utc = datetime.datetime.now(datetime.timezone.utc).date()
    target_date = today_utc + timedelta(days=days_offset)
    start_dt = datetime.datetime.combine(target_date, datetime.time.min, tzinfo=timezone.utc)
    end_dt = start_dt + timedelta(days=1)
    return _iso_timestamp(start_dt), _iso_timestamp(end_dt)


def _normalize_timestamp(value: str) -> str:
    """Return `value` as a UTC ISO timestamp ending in 'Z'.

    A trailing 'Z' or an explicit offset (e.g. '+02:00') is honoured as given.
    A naive value (no suffix) is interpreted as system-local time. If the value
    cannot be parsed it is returned unchanged so the API can report the error.
    """
    try:
        dt = datetime.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=get_localzone())
        return _iso_timestamp(dt.astimezone(timezone.utc))
    except Exception as e:
        print(f"WARNING: Timestamp normalization failed for '{value}': {e}. Using original value.")
        return value
