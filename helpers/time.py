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
