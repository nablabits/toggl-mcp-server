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
    A naive value (no suffix) is interpreted as system-local time.

    Raises ValueError if the value cannot be parsed, or if a naive value falls in a
    DST gap (does not exist locally) or fold (occurs twice) and so has no single UTC
    equivalent. Callers surface the message; pass an explicit offset to resolve it.
    """
    text = value.strip()
    if text[-1:] == "z":
        text = text[:-1] + "Z"
    try:
        dt = datetime.datetime.fromisoformat(text)
    except ValueError as e:
        raise ValueError(
            f"Invalid timestamp '{value}': expected ISO 8601, e.g. '2026-10-23T08:21:50' "
            f"(local), '2026-10-23T06:21:50Z' (UTC) or '2026-10-23T08:21:50+02:00'."
        ) from e

    if dt.tzinfo is None:
        local_tz = get_localzone()
        first = dt.replace(tzinfo=local_tz, fold=0)
        second = dt.replace(tzinfo=local_tz, fold=1)
        if first.utcoffset() != second.utcoffset():
            roundtrip = first.astimezone(timezone.utc).astimezone(local_tz).replace(tzinfo=None)
            problem = "does not exist" if roundtrip != dt else "is ambiguous"
            raise ValueError(
                f"Local time '{value}' {problem} in {local_tz} because of a DST change. "
                f"Pass an explicit offset (e.g. '+01:00') or 'Z' instead."
            )
        dt = first
    return _iso_timestamp(dt.astimezone(timezone.utc))
