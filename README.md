# Toggl MCP Server

Allows MCP clients to interact with Toggl Track, enabling time tracking, project management, and workspace operations through natural language.

## Features

This was forked from [abhinav24jha/toggl-mcp-server](https://github.com/abhinav24jha/toggl-mcp-server) and double checked against the toggl official docs:

<https://engineering.toggl.com/docs/track/>

**Additional features for this fork:**

- **Three new tool domains:** Tag Management, Client Management, and Task Management (12 new tools)
- **Smarter time entry targeting:** `stop_time_entry`, `delete_time_entry`, and `update_time_entry` now accept an optional `entry_id` parameter — no more ambiguity when multiple entries share a description
- **Historical range queries:** `get_time_entries_for_range` accepts explicit `start_date`/`end_date` ISO params alongside the original day-offset approach
- **Rate limit handling:** `toggl_request` retries on 429 and surfaces quota headers on 402 instead of treating all 4xx errors the same
- **Workspace cache:** the workspace list is cached for the lifetime of the server process, eliminating repeat `/me/workspaces` calls within a session
- **`TOGGL_WORKSPACE_ID` env var:** short-circuits all `/me` lookups when set — important given Toggl's 30 req/h cap on that endpoint
- **Modular structure:** split from a single file into domain modules (`projects.py`, `tasks.py`, `time_entries.py`, `tags.py`, `clients.py`, `resources.py`)
- **Full test suite:** 182 tests, 100% coverage, using pytest-vcr for offline replay

### Tools

#### Project Management

| Tool | Description |
| --- | --- |
| `create_project` | Create a new project (name, color, billable, dates, etc.) |
| `delete_project` | Delete a project by name |
| `update_project` | Update a project via JSON Patch operations |
| `get_all_projects` | List all projects in the workspace |

#### Task Management

| Tool | Description |
| --- | --- |
| `get_tasks` | List tasks for a given project |
| `create_task` | Create a task inside a project |
| `update_task` | Rename or change a task's status/estimate |
| `delete_task` | Delete a task by name |

#### Time Entry Management

| Tool | Description |
| --- | --- |
| `create_time_entry` | Start a live timer or log a completed entry |
| `stop_time_entry` | Stop a running time entry by name or `entry_id` |
| `delete_time_entry` | Permanently delete a time entry by name or `entry_id` |
| `get_current_time_entry` | Fetch the currently running entry |
| `update_time_entry` | Update description, tags, project, or timestamps |
| `get_time_entries_for_range` | List entries by day-offset range or explicit `start_date`/`end_date` |

#### Tag Management

| Tool | Description |
| --- | --- |
| `get_tags` | List all tags in the workspace |
| `create_tag` | Create a new tag |
| `update_tag` | Rename a tag |
| `delete_tag` | Delete a tag by name |

#### Client Management

| Tool | Description |
| --- | --- |
| `get_clients` | List clients (optionally filter by `active`/`archived`/`both`) |
| `create_client` | Create a new client |
| `update_client` | Rename a client or update its notes |
| `delete_client` | Delete a client by name |


## Getting Started

### Prerequisites

- Python 3.11+
- Toggl Track account
- uv installed for dependency management

### Environment Variables

Copy the template and fill in your credentials:

```bash
cp toggl-mcp-server/env-template toggl-mcp-server/.env
```

The `.env` file goes inside the `toggl-mcp-server` directory and should contain:

```bash
TOGGL_EMAIL=your_toggl_email
TOGGL_PASSWORD=your_toggl_password
```

If you are using Toggl API tokens (<https://track.toggl.com/profile>):

```bash
TOGGL_EMAIL=your-actual-api-token
TOGGL_PASSWORD="api_token"
```

Where `"api_token"` is the literal string Toggl expects as the password field when authenticating with a token

**Strongly recommended:** set your workspace ID directly to avoid hitting the `/me` endpoint on every tool invocation:

```bash
TOGGL_WORKSPACE_ID=your_workspace_id
```

### Installation

**First install uv:**

- For Unix:
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```
- For Windows:
    ```bash
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```

Make sure to restart your terminal afterwards to ensure that the uv command gets picked up.

Now let's clone the repository and set up the project:

```bash
git clone https://github.com/nablabits/toggl-mcp-server
cd toggl-mcp-server
uv venv
uv sync
```

### Integration with Development Tools

#### Claude Code

```bash
cd /ABSOLUTE/PATH/TO/toggl-mcp-server
```

```bash
source .env && \
claude mcp add \
--transport stdio \
--scope user \
--env TOGGL_EMAIL=$TOGGL_EMAIL \
--env TOGGL_PASSWORD=$TOGGL_PASSWORD \
--env TOGGL_WORKSPACE_ID=$TOGGL_WORKSPACE_ID \
-- toggl \
uv --directory "$(pwd)" run toggl_mcp_server.py
```

#### VS Code + GitHub Copilot Setup

1. Configure the MCP Server in `.vscode/mcp.json`:

```json
"servers": {
  "toggl": {
    "type": "stdio",
    "command": "uv",
    "args": [
      "--directory",
      "/ABSOLUTE/PATH/TO/toggl-mcp-server",
      "run",
      "toggl_mcp_server.py"],
    "envFile": "${workspaceFolder}/.env"
  }
}
```

2. Update the configuration:
   - Replace `/ABSOLUTE/PATH/TO/toggl-mcp-server` with the absolute path to the server
   - You may need to put the full path to the uv executable in the command field. You can get this by running which uv on MacOS/Linux or where uv on Windows

3. Enable the server:
   - Look for the start button when hovering over the server configuration `/.vscode/mcp.json`
   - Click start to let Copilot discover available tools
   - Switch to agent mode in Copilot

For detailed setup instructions, see:

- [MCP Servers in VS Code](https://code.visualstudio.com/docs/copilot/chat/mcp-servers)
- [Copilot Agent Mode](https://code.visualstudio.com/docs/copilot/chat/chat-agent-mode)

### Additional MCP Client Integration

The Toggl MCP Server works with any MCP-compatible client. For integration steps:

1. For Claude Desktop, visit the [MCP Quick Start Guide](https://modelcontextprotocol.io/quickstart/user)
2. For other MCP clients, consult their respective documentation for server configuration

Note: Configuration typically involves specifying the server path and environment variables similar to the VS Code setup above.

## Technicalities

### Limitations

- **Time entries limit:** `get_time_entries_for_range` is capped at a **90-day rolling window** by the Toggl API — dates older than ~3 months are rejected. Toggl exposes Reports endpoints for historical data, but those do not return `time_entry_id` values, so individual historical entries cannot be addressed, updated, or deleted through this MCP server.

- **Throttling:**
  - **429 Too Many Requests** — leaky bucket rate limiter (≈1 req/s per token/IP); back off for a few minutes
  - **402 Payment Required** — sliding window quota per user per org (30 req/h on free, 240 on Starter, 600 on Premium); headers `X-Toggl-Quota-Remaining` and `X-Toggl-Quota-Resets-In` indicate remaining budget.
  - The `/me` endpoint is subject to a hard limit of 30 requests/hour regardless of plan ([docs](https://engineering.toggl.com/docs/track/)). A couple of guardrails have been added to mitigate this limitation: 
    - Set `TOGGL_WORKSPACE_ID` — without it, every tool call that needs a workspace ID consumes one of those 30 requests. If you use a single workspace, always set this.
    - Tools that accept an explicit `workspace_name` resolve it via `/me/workspaces`, which is cached for the lifetime of the server process — so only the first lookup in a session hits the API.


### Code Structure

The server is organised by domain. Each module owns its low-level API helpers and the `@mcp.tool()` functions for that domain:

```text
toggl-mcp-server/
├── toggl_mcp_server.py   # entry point — mcp.run()
├── app.py                # FastMCP instance, auth headers, Endpoints, TOGGL_COLORS
├── helpers/
│   ├── http.py           # toggl_request — authenticated HTTP with rate-limit handling
│   └── time.py           # _get_current_utc_time, _iso_timestamp, _get_date_range, …
├── projects.py           # helpers + tools: create/delete/update/get_all_projects
├── tasks.py              # helpers + tools: get/create/update/delete_task
├── time_entries.py       # helpers + tools: new/stop/delete/update/get time entries
├── tags.py               # helpers + tools: get/create/update/delete_tag
├── clients.py            # helpers + tools: get/create/update/delete_client
└── resources.py          # MCP resources + name→ID lookup helpers (workspace cache)
```

**Key conventions:**

- `_` prefix = low-level helper (ID-based, internal). No prefix = `@mcp.tool()` (name-based, user-facing).
- Helpers return `str` on error; callers check `isinstance(result, str)` before proceeding.
- All HTTP calls use `httpx.AsyncClient` via `async`/`await`.

### Automated Testing

Tests live in `toggl-mcp-server/tests/` and use [pytest-vcr](https://pytest-vcr.readthedocs.io/) to record and replay real Toggl API responses (cassettes), so tests run without network access after the first recording.

**Creating a Sandbox Environment:**

Tests rely on a dedicated Toggl sandbox account with a known set of fixtures. `tests/seed_sandbox.py` creates them in one shot:

- 3 projects: `Alpha`, `Beta`, `Gamma`
- 5 tasks spread across those projects
- 9 time entries across the last 3 days with realistic tags

To seed a fresh sandbox:

1. Create a free Toggl account, copy the template, and fill in its credentials and workspace ID:

```bash
cp tests/env-test-template tests/.env-test
```

```bash
uv sync --extra test --extra dev
```

1. Run the script:

```bash
cd toggl-mcp-server
python tests/seed_sandbox.py
```

1. Delete any existing cassettes and re-record them:

```bash
rm tests/cassettes/*.yaml
uv run pytest -v
```

**Run the suite:**

```bash
uv run pytest -v
```

**Adding tests for a new tool:**

1. Write the test with `@pytest.mark.vcr` — on first run pytest-vcr will call the real API and save the response to `tests/cassettes/<test_name>.yaml`.
2. Re-run: the cassette is replayed, no network needed.
3. Always run the full suite before committing cassettes — `test_cassette_has_no_sensitive_data` will auto-scrub any `api_token` or `email` values that leaked into a cassette and fail to flag what was fixed.

**Re-recording a cassette** (e.g. after an API change): delete the `.yaml` file and re-run the test with a live network connection.

**Test coverage:** 100% coverage across all files (182 tests). Updated 2026-05-28.


## License

This MCP server is licensed under the MIT License.
