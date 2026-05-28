import os
from base64 import b64encode
from typing import Literal

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

mcp = FastMCP("toggl")

auth_credentials = f"{os.getenv('EMAIL')}:{os.getenv('PASSWORD')}".encode("utf-8")
auth_header = f"Basic {b64encode(auth_credentials).decode('ascii')}"

headers = {
    "Content-Type": "application/json",
    "Authorization": auth_header,
}

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
