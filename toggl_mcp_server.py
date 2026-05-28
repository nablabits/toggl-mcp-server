from app import mcp
from projects import create_project, delete_project, get_all_projects, update_projects
from resources import _get_projects, _get_time_entries, _get_workspaces
from time_entries import (
    delete_time_entry,
    get_current_time_entry,
    get_time_entries_for_range,
    new_time_entry,
    stopping_time_entry,
    updating_time_entry,
)

if __name__ == "__main__":
    mcp.run()
