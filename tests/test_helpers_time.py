import datetime
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.time import _convert_utc_to_local


def test_convert_utc_to_local_without_milliseconds():
    with patch("helpers.time.get_localzone", return_value=datetime.timezone.utc):
        result = _convert_utc_to_local("2025-05-01T10:00:00Z")
    assert "2025-05-01" in result
    assert "10:00:00" in result


def test_convert_utc_to_local_invalid_format():
    result = _convert_utc_to_local("not-a-timestamp")
    assert result.startswith("Invalid timestamp format:")
