---
name: gns3-mcp
description: "MCP-first GNS3 lab operations. Use when the user works with GNS3 projects, topologies, nodes, links, Dynamips/QEMU/SONiC labs, device console, guest SSH, image import, Idle-PC, or when the agent is about to call GNS3 REST, write Python against GNS3, or curl port 3080. Load this skill and drive the lab only through gns3_* MCP tools."
---

# GNS3 MCP (MCP-first)

GNS3 work is executed **only** through this package’s MCP tools. Hand-rolled REST, telnet, SSH, or Python clients are not an ops path.

## When this skill applies

Load and follow this skill for any of:

- GNS3 project / topology / node / link work
- Device console or guest SSH inside GNS3
- Image import, Dynamips densify, Idle-PC
- Any impulse to hit GNS3 via REST, `curl`, `httpx`, `requests`, raw telnet/SSH, or a new Python script

## Hard rules

1. **MCP-first.** Prefer the **8 goal tools** for standard lab playbooks; use expert `gns3_*` tools when goals do not fit. Every GNS3 action still goes through MCP (host may prefix names; see mapping).
2. **Forbidden without the escape ritual:**
   - HTTP to GNS3 (`:3080`, `/v2/...`) via curl/httpx/requests/fetch/etc.
   - Raw telnet/console when `gns3_send_console_commands` can do the job
   - Raw guest SSH when `gns3_ssh_exec` can do the job
   - Agent-written scripts that import or wrap `gns3_mcp` / GNS3 REST as a lab driver
   - Running `examples/` or package tests as a substitute for MCP lab ops
3. **Allowed without escape:**
   - `gns3_*` MCP tools
   - Reading this skill, `references/*`, package docs, `AGENTS.md`
   - Local filesystem for image paths, export destinations, reading capture files
   - Non-GNS3 work (git, unrelated code, general shell)
   - Editing `gns3-mcp-server` source when the **task is developing the MCP server** (tests of the server are fine; still do not drive a live lab around MCP tools)
4. **IDs are provenance-only.** Goal tools resolve names internally; for expert tools, `project_id` / `node_id` / etc. must come from a prior MCP result or the user. Never invent UUIDs.
5. **Session open.** Prefer `gns3_prepare_lab` (includes ensure). If using expert tools only, first GNS3 action is `gns3_ensure_server`.
6. **Session close (ask first).** Prefer `gns3_finish_lab` after user intent: defaults all false; destructive flags require a one-time `confirmation_token` from a preview call. Expert path: ask close/stop, then `gns3_cleanup_session` / discrete tools. Never auto-close or auto-stop without explicit yes.
7. **Secrets.** Use env / host MCP config. Document variable **names** only. Never print passwords. Console `results[].response` is **pure command body** (no completion prompt / username); completion is `completed` bool when first-prompt framing succeeded.
8. **Destructive ops + tokens.** `gns3_manage_snapshot` / `gns3_finish_lab` (and other destructive goal actions) return `status: confirmation_required` with `confirmation_token` bound to action+target. Re-call with the token only after **user** confirms. Bare `confirm=true` is not authorization. Expert delete/restore still needs user confirm in chat.

## Escape ritual (only path around MCP)

Use only when a required `gns3_*` tool is missing or returns a hard failure, or the path is **yellow** in the capability matrix:

1. Name the missing/broken tool and the error (or the matrix gap).
2. Ask the user for explicit allow for **this** action.
3. After allow, do the **minimum** non-MCP work and state that in the reply.

No silent fallback. No session-wide “I may use Python now” without a fresh allow for the action. Yellow ≠ auto-escape.

## Preferred: goal tools (playbook entry points)

| Goal tool | Playbook |
|-----------|----------|
| `gns3_prepare_lab` | Bootstrap lab / project |
| `gns3_build_topology` | Build topology |
| `gns3_configure_devices` | Configure devices |
| `gns3_diagnose_connectivity` | Diagnose connectivity |
| `gns3_run_guest_commands` | Guest SSH / host-style ops |
| `gns3_prepare_image` | Image import + Idle-PC (densify yellow) |
| `gns3_manage_snapshot` | Snapshot / reset |
| `gns3_finish_lab` | Session cleanup |

Shared behavior: observe-converge (reuse exact natural keys; `conflict` if same key different spec), fail-stop with step trace, statuses `success|error|partial|confirmation_required|conflict`. Expert `gns3_*` tools remain available.

## Standard lab loop

Preferred spine:

1. `gns3_prepare_lab` (ensure + resolve/create + open)
2. `gns3_build_topology` (nodes/links; optional start/validate)
3. `gns3_configure_devices` / `gns3_run_guest_commands` as needed
4. `gns3_diagnose_connectivity` when verifying path
5. `gns3_manage_snapshot` for checkpoints
6. **On completion:** ask user → `gns3_finish_lab` with flags + token after preview

Expert multi-step loop (when goals insufficient): ensure → list/open → resolve → mutate → validate → ask cleanup.

## Configure preference

- Prefer `gns3_configure_devices` (goal) for multi-node playbook work.
- Expert: `gns3_apply_config_template` when a built-in fits; pasted CLI via `gns3_send_console_commands` (pure-body responses); bulk via `gns3_bulk_configure_nodes`.

## Tool name mapping

Playbooks and this skill use **canonical** names: `gns3_<action>`.

| Host | Surface |
|------|---------|
| Logical / docs | `gns3_list_projects` |
| Oh My Pi (this lab) | `mcp__gns_list_projects` or write JSON to `xd://mcp__gns_list_projects` |
| Other clients | Server-prefixed names (`mcp_gns3_*`, etc.) — same tool, different wrapper |

Never reimplement a tool because the host prefix looks different. Discover the bound GNS3 MCP tools and call them.

## Progressive disclosure

| Need | Load |
|------|------|
| Install / register MCP on a host | `references/setup.md` |
| What MCP can vs cannot do | `references/capability-matrix.md` |
| Recipe for a common lab job | `references/playbooks.md` |

## Anti-patterns

- Writing `scripts/fix_lab.py` that talks to GNS3 because “it’s faster”
- Curl-ing `http://127.0.0.1:3080/v2/projects` after a tool error instead of running the escape ritual
- Guessing a `project_id` from memory or a previous chat
- Running `examples/example_complete_network.py` to build the user’s lab
- Printing API passwords from `.omp/mcp.json` into the transcript
- Stopping gns3server or closing a project without asking after lab work
