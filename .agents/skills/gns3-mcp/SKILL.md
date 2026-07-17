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

1. **MCP-first.** Every GNS3 control-plane or device-access action goes through a `gns3_*` MCP tool (host may prefix it; see mapping below).
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
4. **IDs are provenance-only.** `project_id`, `node_id`, `link_id`, `template_id`, `snapshot_id`, adapter/port numbers, and similar must come from a prior MCP result in this session or from the user. Never invent UUIDs. User says “R1” → `gns3_list_nodes` (or topology) and match by name before acting. Refresh with list/get tools if state may be stale. For links, take adapter/port from `gns3_get_node` when needed.
5. **Session open.** The first GNS3 action in a conversation is `gns3_ensure_server`. Later GNS3 calls may skip a separate ensure.
6. **Secrets.** Use env / host MCP config. Document variable **names** only. Never print `GNS3_PASSWORD`, console passwords, or SSH passwords. Never commit secrets into skill or repo files. Examples use placeholders only.
7. **Destructive ops.**
   - Confirm with the user before: `gns3_delete_project`, `gns3_restore_snapshot`, `gns3_export_project`
   - Node/link delete is OK when the user asked for that topology change
   - Before `gns3_restore_snapshot`, create a safety snapshot when possible

## Escape ritual (only path around MCP)

Use only when a required `gns3_*` tool is missing or returns a hard failure, or the path is **yellow** in the capability matrix:

1. Name the missing/broken tool and the error (or the matrix gap).
2. Ask the user for explicit allow for **this** action.
3. After allow, do the **minimum** non-MCP work and state that in the reply.

No silent fallback. No session-wide “I may use Python now” without a fresh allow for the action. Yellow ≠ auto-escape.

## Standard lab loop

Use this spine for topology work:

1. `gns3_ensure_server`
2. `gns3_list_projects` → `gns3_open_project` or `gns3_create_project`
3. `gns3_list_templates` / `gns3_list_nodes` / `gns3_get_topology` as needed
4. Mutate via MCP (`gns3_add_node`, `gns3_add_link`, start/stop, configure, …)
5. `gns3_validate_topology` when the shape should be checked
6. Optional: `gns3_create_snapshot` / `gns3_save_project`

Completion criterion for a lab change: every intended node/link/config step was done with MCP tools (or an explicit allowed escape), and IDs used were resolved—not guessed.

## Configure preference

- Prefer `gns3_apply_config_template` when a built-in template fits (ospf, vlan, dhcp, ssh, …).
- If the user pastes CLI, send it with `gns3_send_console_commands` (do not rewrite into a different design unless asked).
- For ≥3 similar devices, prefer `gns3_bulk_configure_nodes`.

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
