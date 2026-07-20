---
name: gns3-mcp
description: "MCP-first GNS3 lab operations. Use when the user works with GNS3 projects, topologies, nodes, links, Dynamips/QEMU/SONiC labs, device console, guest SSH, image import, Idle-PC, or when the agent is about to call GNS3 REST, write Python against GNS3, or curl port 3080. Load this skill and drive the lab only through gns3_* MCP tools."
---

# GNS3 MCP (MCP-first)

GNS3 work is executed **only** through this package’s MCP tools. Hand-rolled REST, telnet, SSH, or Python clients are not an ops path.

Current server surface: **58** `@mcp.tool` entries in `src/gns3_mcp/server.py` — **8 goal tools** + **50 expert tools**. Prefer goals for playbooks; use expert tools for partial/custom work.

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
   - Raw guest SSH when `gns3_ssh_exec` / `gns3_run_guest_commands` can do the job
   - Agent-written scripts that import or wrap `gns3_mcp` / GNS3 REST as a lab driver
   - Running `examples/` or package tests as a substitute for MCP lab ops
3. **Allowed without escape:**
   - `gns3_*` MCP tools
   - Reading this skill, `references/*`, package docs, `AGENTS.md`
   - Local filesystem for image paths, export destinations, reading capture files
   - Non-GNS3 work (git, unrelated code, general shell)
   - Editing `gns3-mcp-server` source when the **task is developing the MCP server** (tests of the server are fine; still do not drive a live lab around MCP tools)
4. **IDs are provenance-only.** Goal tools resolve names (`project_name`, `node_name`, `template_name`, `snapshot_name`) internally. For expert tools, `project_id` / `node_id` / `link_id` / `template_id` / `snapshot_id` / adapter+port must come from a prior MCP result or the user. Never invent UUIDs.
5. **Session open.** Prefer `gns3_prepare_lab` (ensure + resolve/create + open). Expert-only path: first GNS3 action is `gns3_ensure_server`.
6. **Session close (ask first).** Prefer `gns3_finish_lab` after user intent. Defaults are all false (inert). Any true `stop_nodes` / `close_project` / `stop_server` needs a preview → user yes → `confirmation_token` re-call. Expert path: ask close/stop, then `gns3_cleanup_session` or discrete tools. Never auto-close or auto-stop without explicit yes.
7. **Secrets.** Use env / host MCP config. Document variable **names** only. Never print passwords. Console `results[].response` is **pure command body** (no completion prompt / username); completion is `completed` bool when first-prompt framing succeeded.
8. **Destructive ops + tokens.** Goal tools only:
   - `gns3_manage_snapshot`: destructive ops = `restore` | `delete_snapshot` | `delete_project` (create/list are not token-gated)
   - `gns3_finish_lab`: any true cleanup flag
   - Response: `status: confirmation_required` with `result.confirmation_token` bound to **action + target** (resolved project/snapshot ids, flags, server_url). Tokens are one-shot, process-local, default TTL 600s (`GNS3_CONFIRM_TOKEN_TTL_SECONDS`).
   - After **user** confirms, re-call with the **same** resolved target fields + token. Changing project/snapshot/flags invalidates the token (`target mismatch`). Bare `confirm=true` is not a field and is not authorization.
   - Expert delete/restore/export still needs user confirm in chat (no token system on expert tools).

## Escape ritual (only path around MCP)

Use only when a required `gns3_*` tool is missing or returns a hard failure, or the path is **yellow** in the capability matrix:

1. Name the missing/broken tool and the error (or the matrix gap).
2. Ask the user for explicit allow for **this** action.
3. After allow, do the **minimum** non-MCP work and state that in the reply.

No silent fallback. No session-wide “I may use Python now” without a fresh allow for the action. Yellow ≠ auto-escape.

## Preferred: goal tools (playbook entry points)

| Goal tool | Playbook | Key inputs |
|-----------|----------|------------|
| `gns3_prepare_lab` | Bootstrap lab / project | `project_name` or `project_id`; `create_if_missing` / `open_project` (default true); `force_ensure` |
| `gns3_build_topology` | Build topology | `project_*`; `nodes[]` (`name` + `template_id`\|`template_name`, optional `x`/`y`/`compute_id`); `links[]` endpoints `a`/`b` or `node_a`/`node_b` with `node_name` + optional `adapter`/`port` **together**; `start`; `validate` (default true) |
| `gns3_configure_devices` | Configure devices | `project_*`; `targets[]` with `node_name`\|`node_id` + `commands` **or** `template_name`+`params`; optional `enter_config_mode` (default true), `save_config`, `verify_commands`, console login fields |
| `gns3_diagnose_connectivity` | Diagnose connectivity | `project_*`; optional `suspect_nodes[]`, `probe_commands` — findings only, no auto-fix |
| `gns3_run_guest_commands` | Guest SSH / host-style ops | `commands`; `host` **or** project+node; never returns passwords |
| `gns3_prepare_image` | Image import + Idle-PC | `source_path` + `emulator` (`qemu`\|`dynamips`\|`iou`; docker rejected); optional Idle-PC node; `densify_template` stays **yellow** (skipped + escape note) |
| `gns3_manage_snapshot` | Snapshot / reset | `operation`: `create`\|`list`\|`restore`\|`delete_snapshot`\|`delete_project`; destructive need token |
| `gns3_finish_lab` | Session cleanup | flags default false; any true flag → token after user yes |

### Goal envelope contract

All goals return a shared envelope:

- `status`: `success` \| `error` \| `partial` \| `confirmation_required` \| `conflict`
- `goal`: short name (e.g. `prepare_lab`)
- `steps[]`: `{step, status, detail?, error?}` with step statuses `success` \| `skipped` \| `changed` \| `failed`
- `result` / `error` / `next` (hint) as applicable

Shared behavior:

- **Observe-converge:** reuse existing objects when natural keys match; do not recreate blindly.
  - Nodes: natural key = **name**. Same name + different template → `conflict` / fail (not silent replace).
  - Links: endpoints by node name + adapter/port (implicit free ports when omitted; adapter and port must both be set or both omitted).
  - Snapshots create: same name → reuse, not duplicate.
- **Fail-stop:** first hard failure stops further mutations in that goal; earlier `changed` steps may yield `partial`.
- Expert `gns3_*` tools remain available for one-off control.

## Standard lab loop

Preferred spine:

1. `gns3_prepare_lab` (ensure + resolve/create + open)
2. `gns3_build_topology` (nodes/links; optional start/validate)
3. `gns3_configure_devices` / `gns3_run_guest_commands` as needed
4. `gns3_diagnose_connectivity` when verifying path
5. `gns3_manage_snapshot` for checkpoints (`create` / `list` free; restore/delete need token)
6. **On completion:** ask user which of stop_nodes / close_project / stop_server → `gns3_finish_lab` preview → user yes → re-call with `confirmation_token`

Expert multi-step loop (when goals insufficient): `gns3_ensure_server` → list/open → resolve IDs → mutate → `gns3_validate_topology` → ask cleanup.

## Configure preference

- Prefer `gns3_configure_devices` (goal) for multi-node playbook work.
- Goal `template_name` values are the **workflow** set: `basic_router`, `interface`, `vlan`, `ospf` (plus `params`). For broader built-ins (eigrp, bgp, dhcp, ssh, …) use expert `gns3_apply_config_template`.
- Expert: pasted CLI via `gns3_send_console_commands` (pure-body responses); bulk via `gns3_bulk_configure_nodes`.

## Expert tool inventory (50)

| Area | Tools |
|------|--------|
| Server / session | `gns3_ensure_server`, `gns3_stop_server`, `gns3_cleanup_session`, `gns3_get_server_info`, `gns3_list_computes` |
| Projects | `gns3_list_projects`, `gns3_create_project`, `gns3_get_project`, `gns3_update_project`, `gns3_open_project`, `gns3_close_project`, `gns3_delete_project`, `gns3_duplicate_project`, `gns3_save_project`, `gns3_export_project` |
| Nodes | `gns3_list_nodes`, `gns3_add_node`, `gns3_get_node`, `gns3_update_node`, `gns3_delete_node`, `gns3_start_node`, `gns3_stop_node`, `gns3_suspend_node`, `gns3_reload_node`, `gns3_duplicate_node`, `gns3_start_all_nodes`, `gns3_stop_all_nodes` |
| Links | `gns3_list_links`, `gns3_add_link`, `gns3_delete_link` |
| Topology | `gns3_get_topology`, `gns3_validate_topology` |
| Console / config | `gns3_send_console_commands`, `gns3_get_node_config`, `gns3_apply_config_template`, `gns3_bulk_configure_nodes` |
| Templates / appliances / images | `gns3_list_templates`, `gns3_list_appliances`, `gns3_list_images`, `gns3_import_image`, `gns3_get_idle_pc_values` |
| Snapshots | `gns3_list_snapshots`, `gns3_create_snapshot`, `gns3_restore_snapshot`, `gns3_delete_snapshot` |
| Capture / canvas | `gns3_start_capture`, `gns3_stop_capture`, `gns3_add_text_annotation`, `gns3_add_shape` |
| Guest SSH | `gns3_ssh_exec` |

Yellow gaps (no MCP tool yet): template **create/update**, densify-on-template, idle-pc write to template, appliance file install, docker image pull. See `references/capability-matrix.md`.

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
- Treating `gns3_finish_lab` / destructive snapshot preview as “already done” — preview only issues a token
- Reusing a confirmation token after changing project, snapshot, or flags
