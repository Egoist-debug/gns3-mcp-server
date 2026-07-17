# Import GNS3 MCP into real agent hosts

This package exposes a stdio MCP server. Agents must **call tools**, not reimplement the API. After install, load the `gns3-mcp` skill and follow its hard rules.

Secrets: set via environment or host MCP config. Examples use **placeholders only**. Never commit real passwords.

## Prerequisites

- GNS3 server reachable (default `http://127.0.0.1:3080`)
- Python 3.10+ and project deps (`uv sync` or `pip install -e .` in `gns3-mcp-server/`)
- For Oh My Pi launcher: `.venv` with package importable (`run-omp.sh` uses `.venv/bin/python`)

## Environment variables

| Variable | Purpose |
|----------|---------|
| `GNS3_SERVER_URL` | REST base URL (default `http://localhost:3080`) |
| `GNS3_USERNAME` / `GNS3_PASSWORD` | GNS3 API auth |
| `GNS3_VERIFY_SSL` | TLS verify (`true`/`false`) |
| `GNS3_SERVER_START_CMD` | Custom localhost start command (optional) |
| `GNS3_SERVER_START_TIMEOUT` | Wait for auto-start (default `30`) |
| `GNS3_SERVER_HEALTHY_CACHE_SECONDS` | Skip re-probe window (default `30`) |
| `GNS3_CONSOLE_USER` / `GNS3_CONSOLE_PASSWORD` | Default device console login |
| `GNS3_CONSOLE_READY_TIMEOUT` | Console login readiness budget seconds (default `30`) |
| `GNS3_CONSOLE_MAX_RESPONSE_BYTES` | Per-command console output cap (default `524288`) |
| `GNS3_SSH_USER` / `GNS3_SSH_PASSWORD` | Default guest SSH |
| `GNS3_SSH_HOST_KEY_POLICY` | `accept_new` (default) / `strict` / `warn` |
| `GNS3_SSH_CONNECT_TIMEOUT` | SSH connect readiness budget with retries (default `30`) |
| `GNS3_MCP_LAUNCH_LOG` | Optional launcher log path (OMP script) |

API `username`/`password` tool fields are **not** guest console/SSH credentials.

## Install skill (this monorepo layout)

Canonical skill:

```text
gns3-mcp-server/.agents/skills/gns3-mcp/
```

Workspace hosts should symlink (not copy) so content does not drift:

```bash
# from gns3-test workspace root
ln -sfn ../../gns3-mcp-server/.agents/skills/gns3-mcp .agents/skills/gns3-mcp
ln -sfn ../../gns3-mcp-server/.agents/skills/gns3-mcp .omp/skills/gns3-mcp
```

Confirm:

```bash
ls -la .agents/skills/gns3-mcp .omp/skills/gns3-mcp
readlink -f .agents/skills/gns3-mcp
```

## Oh My Pi (OMP)

1. Build venv in the package: `cd gns3-mcp-server && uv sync`
2. Register stdio server in `.omp/mcp.json`:

```json
{
  "mcpServers": {
    "gns3": {
      "type": "stdio",
      "command": "/ABS/PATH/gns3-mcp-server/run-omp.sh",
      "cwd": "/ABS/PATH/gns3-mcp-server",
      "env": {
        "PYTHONUNBUFFERED": "1",
        "FASTMCP_SHOW_CLI_BANNER": "false",
        "GNS3_SERVER_URL": "http://127.0.0.1:3080",
        "GNS3_USERNAME": "YOUR_USER",
        "GNS3_PASSWORD": "YOUR_PASSWORD",
        "GNS3_VERIFY_SSL": "false"
      },
      "timeout": 120000
    }
  }
}
```

3. Symlink skill into `.omp/skills/gns3-mcp` (above)
4. Restart OMP / reload MCP
5. Tools appear as `mcp__gns_*` / `xd://mcp__gns_*`

Launcher: `run-omp.sh` → `omp_stdio_entry.py` with `PYTHONPATH=src`.

## Gemini CLI

Package ships `mcp-server.json` and `run.sh` / `run.bat`.

```bash
# Linux/macOS example
gemini mcp add gns3 "/ABS/PATH/gns3-mcp-server/run.sh"
```

Or point Gemini at a server config that runs:

```bash
/ABS/PATH/gns3-mcp-server/run.sh
```

Set the same env vars as above in the host’s MCP env block. Install/copy the skill into the agent skill path your Gemini workflow uses (or rely on project `AGENTS.md` + workspace skills).

## Claude Desktop

Add to Claude MCP config (paths vary by OS), concept:

```json
{
  "mcpServers": {
    "gns3": {
      "command": "/ABS/PATH/gns3-mcp-server/run.sh",
      "args": [],
      "env": {
        "GNS3_SERVER_URL": "http://127.0.0.1:3080",
        "GNS3_USERNAME": "YOUR_USER",
        "GNS3_PASSWORD": "YOUR_PASSWORD",
        "GNS3_VERIFY_SSL": "false"
      }
    }
  }
}
```

Windows: use `run.bat` as `command` or `python` with module entry after install.

Place the `gns3-mcp` skill where Claude loads project/user skills, or paste the hard rules into project instructions.

## Cursor

Cursor MCP settings (UI or `mcp.json`):

```json
{
  "mcpServers": {
    "gns3": {
      "command": "/ABS/PATH/gns3-mcp-server/run.sh",
      "env": {
        "GNS3_SERVER_URL": "http://127.0.0.1:3080",
        "GNS3_USERNAME": "YOUR_USER",
        "GNS3_PASSWORD": "YOUR_PASSWORD"
      }
    }
  }
}
```

Point project rules at this skill (or symlink into the project’s skill directory).

## Generic MCP stdio

Any client that can spawn:

```bash
# preferred after editable install
python -m gns3_mcp.server

# or package launchers
./run.sh          # POSIX
./run-omp.sh      # OMP-oriented venv entry
./run.bat         # Windows
```

Must be **stdio** MCP, not a random HTTP sidecar the agent curls.

## Verify checklist

Run in order after wiring:

1. Host shows GNS3 MCP tools (names contain `gns3` / `gns_`)
2. Call **`gns3_ensure_server`** (or host-prefixed equivalent) → success / healthy
3. Call **`gns3_list_projects`** → JSON list (may be empty)
4. Optional: `gns3_list_templates`
5. Confirm skill is loadable (`gns3-mcp`) and root `AGENTS.md` points at MCP-first policy
6. Negative check: agent must **not** need `curl http://127.0.0.1:3080/v2/projects` for the same job

## Failure triage

| Symptom | Check |
|---------|--------|
| No tools listed | MCP config path, command executable, restart client |
| `run-omp.sh` exit 127 | `uv sync` / missing `.venv/bin/python` |
| Connection errors | `GNS3_SERVER_URL`, GNS3 running, auth env, `GNS3_VERIFY_SSL` |
| Tools work but agent uses Python | Skill not loaded; reinforce `AGENTS.md`; reject scripts and re-run via MCP |
| Console/SSH auth fails | Guest creds vs API creds; set `GNS3_CONSOLE_*` / `GNS3_SSH_*` or per-call login fields |

## Related files

- `mcp-server.json` — exhibit / Gemini-oriented server metadata
- `README.md`, `docs/START_HERE.md`, `docs/TOOL_REFERENCE.md` — package docs
- Skill core: `../SKILL.md`
