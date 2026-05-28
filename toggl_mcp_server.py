from app import mcp
from clients import create_client, delete_client, get_clients, update_client
from projects import create_project, delete_project, get_all_projects, update_project
from resources import _get_projects, _get_time_entries, _get_workspaces
from tags import create_tag, delete_tag, get_tags, update_tag
from tasks import create_task, delete_task, get_tasks, update_task
from time_entries import (
    create_time_entry,
    delete_time_entry,
    get_current_time_entry,
    get_time_entries_for_range,
    stop_time_entry,
    update_time_entry,
)

if __name__ == "__main__":
    mcp.run()  # pragma: no cover
