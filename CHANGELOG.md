# Changelog

## v2.0.0

ID-first parameter model across all tools. All name-based lookups have been removed in favour of explicit IDs, eliminating an entire class of ambiguity errors and reducing round-trips to the Toggl API.

### Breaking changes

- Every CRUD tool (`create_*`, `update_*`, `delete_*`, `get_*`) now requires `workspace_id` instead of `workspace_name`. The server no longer resolves workspace names at call time.
- `stop_time_entry`, `delete_time_entry`, and `update_time_entry` no longer accept `time_entry_name` as a fallback. `entry_id` is the only identifier.
- `get_tasks` requires `project_id` instead of `project_name`.
- All `*_not_found` workspace-name cassettes have been removed; the corresponding error paths no longer exist.

### Internals

- Name-to-ID lookup helpers (`_get_workspace_id_by_name`, `_get_project_id_by_name`, etc.) deleted entirely.
- `TOGGL_WORKSPACE_ID` env var remains the recommended way to avoid passing `workspace_id` on every call.
- Test suite updated throughout; cassettes re-recorded to reflect the new parameter shapes.

---

## v1.0.0

First release of this fork. Substantial rework of the upstream codebase, adding new tool domains, a modular structure, a full test suite, and several reliability improvements.

### New tool domains

- **Tag Management** — `get_tags`, `create_tag`, `update_tag`, `delete_tag`
- **Client Management** — `get_clients`, `create_client`, `update_client`, `delete_client`
- **Task Management** — `get_tasks`, `create_task`, `update_task`, `delete_task`

### Improvements to existing tools

- `stop_time_entry`, `delete_time_entry`, and `update_time_entry` now accept an optional `entry_id` — no more ambiguity when multiple entries share a description
- `get_time_entries_for_range` accepts explicit `start_date`/`end_date` ISO params alongside the original day-offset approach

### Reliability & performance

- `toggl_request` retries on 429 and surfaces quota headers on 402 instead of treating all 4xx errors the same
- Workspace list is cached for the lifetime of the server process, eliminating repeat `/me/workspaces` calls within a session
- `TOGGL_WORKSPACE_ID` env var short-circuits all `/me` lookups — important given Toggl's 30 req/h cap on that endpoint
- Test coverage went from zero (upstream had no tests) to 163 tests at 100% coverage against the real Toggl API, using pytest-vcr for offline cassette replay

### Architecture

- Monolith split into domain modules: `projects.py`, `tasks.py`, `time_entries.py`, `tags.py`, `clients.py`, `resources.py`

---

## v0.0.1

Upstream fork baseline — [abhinav24jha/toggl-mcp-server](https://github.com/abhinav24jha/toggl-mcp-server) as received, with minor README fixes and a default value for `workspace_name`.
