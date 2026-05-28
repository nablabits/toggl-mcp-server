import os
from base64 import b64encode
from typing import Literal

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

mcp = FastMCP("toggl")

auth_credentials = f"{os.getenv('TOGGL_EMAIL')}:{os.getenv('TOGGL_PASSWORD')}".encode("utf-8")
auth_header = f"Basic {b64encode(auth_credentials).decode('ascii')}"

headers = {
    "Content-Type": "application/json",
    "Authorization": auth_header,
}

BASE_URL = "https://api.track.toggl.com/api/v9"


class Endpoints:
    # /me — no workspace needed, kept as class constants
    ME = f"{BASE_URL}/me"
    ME_TIME_ENTRIES = f"{BASE_URL}/me/time_entries"
    ME_TIME_ENTRY_CURRENT = f"{BASE_URL}/me/time_entries/current"
    ME_WORKSPACES = f"{BASE_URL}/me/workspaces"

    def __init__(self, ws: int):
        self._base = f"{BASE_URL}/workspaces/{ws}"

    # /workspaces/{ws}/...
    @property
    def projects(self) -> str:
        return f"{self._base}/projects"

    def project(self, proj: int | str) -> str:
        return f"{self._base}/projects/{proj}"

    def tasks(self, proj: int) -> str:
        return f"{self._base}/projects/{proj}/tasks"

    def task(self, proj: int, task: int) -> str:
        return f"{self._base}/projects/{proj}/tasks/{task}"

    @property
    def time_entries(self) -> str:
        return f"{self._base}/time_entries"

    def time_entry(self, te: int) -> str:
        return f"{self._base}/time_entries/{te}"

    def time_entry_stop(self, te: int) -> str:
        return f"{self._base}/time_entries/{te}/stop"

    @property
    def tags(self) -> str:
        return f"{self._base}/tags"

    def tag(self, tag: int) -> str:
        return f"{self._base}/tags/{tag}"

    @property
    def clients(self) -> str:
        return f"{self._base}/clients"

    def client(self, c: int) -> str:
        return f"{self._base}/clients/{c}"


TOGGL_COLORS = Literal[
    "#4dc3ff",  # Light Blue
    "#bc85e6",  # Lavender
    "#df7baa",  # Pink
    "#f68d38",  # Orange
    "#b27636",  # Brown
    "#8ab734",  # Lime Green
    "#14a88e",  # Teal
    "#268bb5",  # Medium Blue
    "#6668b4",  # Purple
    "#a4506c",  # Rose
    "#67412c",  # Dark Brown
    "#3c6526",  # Forest Green
    "#094558",  # Navy Blue
    "#bc2d07",  # Red
    "#999999",  # Gray
]
