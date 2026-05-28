"""
Seed script for the Toggl sandbox account.

Creates generic projects, tasks, and time entries so cassettes have realistic fixtures.
Run once after setting up the sandbox account:

    cd toggl-mcp-server
    python tests/seed_sandbox.py
"""

import asyncio
import datetime
import os
from base64 import b64encode
from pathlib import Path

import httpx
from dotenv import dotenv_values

TIMEOUT = httpx.Timeout(30.0)
REQUEST_DELAY = 0.5  # seconds between requests

# Load sandbox credentials
_env = dotenv_values(Path(__file__).parent / ".env-test")
os.environ.update(_env)

TOGGL_EMAIL = os.environ["TOGGL_EMAIL"]
TOGGL_PASSWORD = os.environ["TOGGL_PASSWORD"]
WORKSPACE_ID = int(os.environ["TOGGL_WORKSPACE_ID"])

BASE_URL = "https://api.track.toggl.com/api/v9"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Basic {b64encode(f'{TOGGL_EMAIL}:{TOGGL_PASSWORD}'.encode()).decode()}",
}

PROJECTS = [
    {"name": "Alpha", "color": "#4dc3ff"},
    {"name": "Beta", "color": "#8ab734"},
    {"name": "Gamma", "color": "#f68d38"},
]

# Tasks: (name, project_name)
TASKS = [
    ("Research", "Alpha"),
    ("Implementation", "Alpha"),
    ("Code Review", "Beta"),
    ("Documentation", "Beta"),
    ("Sprint Planning", "Gamma"),
]

# Time entries: (description, project_name, tags, day_offset, start_hour, duration_min)
TIME_ENTRIES = [
    ("Planning session", "Alpha", ["meeting"], -3, 9, 45),
    ("Implementation work", "Alpha", ["dev"], -3, 10, 90),
    ("Code review", "Beta", ["review"], -3, 14, 30),
    ("Documentation", "Beta", ["docs"], -2, 9, 60),
    ("Bug investigation", "Alpha", ["dev", "review"], -2, 11, 75),
    ("Team sync", "Gamma", ["meeting"], -2, 15, 30),
    ("Feature work", "Gamma", ["dev"], -1, 9, 120),
    ("Testing", "Alpha", ["dev"], -1, 11, 50),
    ("Weekly review", "Beta", ["docs", "review"], -1, 15, 40),
]


def _iso(dt: datetime.datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


async def create_project(client: httpx.AsyncClient, name: str, color: str) -> int:
    resp = await client.post(
        f"{BASE_URL}/workspaces/{WORKSPACE_ID}/projects",
        json={"name": name, "color": color, "is_private": True, "active": True},
        headers=HEADERS,
    )
    resp.raise_for_status()
    project_id = resp.json()["id"]
    print(f"  Created project '{name}' (id={project_id})")
    return project_id


async def create_time_entry(
    client: httpx.AsyncClient,
    description: str,
    project_id: int,
    tags: list[str],
    day_offset: int,
    start_hour: int,
    duration_min: int,
) -> None:
    today = datetime.datetime.utcnow().date()
    target = today + datetime.timedelta(days=day_offset)
    start = datetime.datetime(
        target.year, target.month, target.day, start_hour, 0, 0, tzinfo=datetime.timezone.utc
    )
    stop = start + datetime.timedelta(minutes=duration_min)

    resp = await client.post(
        f"{BASE_URL}/workspaces/{WORKSPACE_ID}/time_entries",
        json={
            "description": description,
            "project_id": project_id,
            "tags": tags,
            "start": _iso(start),
            "stop": _iso(stop),
            "created_with": "seed_sandbox",
            "workspace_id": WORKSPACE_ID,
        },
        headers=HEADERS,
    )
    if not resp.is_success:
        raise RuntimeError(f"HTTP {resp.status_code} creating '{description}': {resp.text}")
    print(f"  Created entry '{description}' ({day_offset}d, {duration_min}min, tags={tags})")
    await asyncio.sleep(REQUEST_DELAY)


async def create_task(client: httpx.AsyncClient, name: str, project_id: int) -> None:
    resp = await client.post(
        f"{BASE_URL}/workspaces/{WORKSPACE_ID}/projects/{project_id}/tasks",
        json={"name": name, "active": True},
        headers=HEADERS,
    )
    if not resp.is_success:
        raise RuntimeError(f"HTTP {resp.status_code} creating task '{name}': {resp.text}")
    print(f"  Created task '{name}' (project_id={project_id})")
    await asyncio.sleep(REQUEST_DELAY)


async def main() -> None:
    print(f"Seeding workspace {WORKSPACE_ID} as {TOGGL_EMAIL}\n")

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        print("Creating projects...")
        project_ids = {}
        for p in PROJECTS:
            project_ids[p["name"]] = await create_project(client, p["name"], p["color"])

        print("\nCreating tasks...")
        for task_name, project_name in TASKS:
            await create_task(client, task_name, project_ids[project_name])

        print("\nCreating time entries...")
        for description, project_name, tags, day_offset, start_hour, duration_min in TIME_ENTRIES:
            await create_time_entry(
                client,
                description=description,
                project_id=project_ids[project_name],
                tags=tags,
                day_offset=day_offset,
                start_hour=start_hour,
                duration_min=duration_min,
            )

    print("\nDone. Re-record cassettes with:")
    print("  rm tests/cassettes/*.yaml && python -m pytest tests/ -v")


if __name__ == "__main__":
    asyncio.run(main())
