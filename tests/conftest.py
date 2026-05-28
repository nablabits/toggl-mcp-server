import os
from pathlib import Path

import pytest
from dotenv import dotenv_values

# Push test credentials into os.environ before any module import.
# dotenv_values + os.environ.update guarantees precedence over the
# module-level load_dotenv() in toggl_mcp_server.py.
_test_env = Path(__file__).parent / ".env-test"
os.environ.update(dotenv_values(_test_env))


@pytest.fixture(scope="session")
def vcr_config():
    """Configure pytest-vcr for recording/replaying HTTP interactions."""
    cassettes_dir = Path(__file__).parent / "cassettes"
    cassettes_dir.mkdir(exist_ok=True)

    return {
        "filter_headers": [
            "authorization",  # Hide auth headers for safety
            "Authorization",
        ],
        "cassette_library_dir": str(cassettes_dir),
        "record_mode": "once",  # Record once, replay thereafter
        "decode_compressed_response": True,
    }


@pytest.fixture
def vcr_cassette_name(request):
    """Generate cassette names from test function names."""
    return f"{request.node.name}.yaml"
