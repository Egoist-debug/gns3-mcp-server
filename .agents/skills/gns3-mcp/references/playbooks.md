# GNS3 MCP playbooks

Canonical tool names: `gns3_*`. On Oh My Pi this lab maps to `mcp__gns_*` / `xd://mcp__gns_*`.

**Prefer the goal tool** for each playbook. Expert tools remain for partial/custom work.
IDs only from prior MCP results or user paste when using expert tools. Goal tools resolve names.

---

## 1. Bootstrap lab / project

**Goal tool:** `gns3_prepare_lab` (`project_name` or `project_id`)

**Expert fallback:**

1. `gns3_ensure_server`
2. `gns3_get_server_info` (optional sanity)
3. `gns3_list_projects`
4. If project exists: `gns3_open_project` with its `project_id`
5. Else: `gns3_create_project` with the agreed name → open if required by host state
6. `gns3_list_templates` (cache names → template_id for later add_node)

**Done when:** Server healthy and a `project_id` is known from a tool result.

---

## 2. Build topology (nodes + links)

**Goal tool:** `gns3_build_topology` (`project_*`, `nodes`, `links`, optional `start`/`validate`)

**Expert fallback:**

1. Complete playbook 1 if needed
2. `gns3_list_templates` — pick `template_id` by name/type (never invent)
3. For each device: `gns3_add_node` (`project_id`, `node_name`, `template_id`, position as needed)
4. `gns3_list_nodes` — map name → `node_id`
5. For each link:
   - `gns3_get_node` on endpoints if adapter/port unknown
   - `gns3_add_link` with real node ids and ports
6. `gns3_list_links` or `gns3_get_topology` to verify
7. `gns3_start_node` / `gns3_start_all_nodes` when the user wants power-on
8. `gns3_validate_topology`

**Done when:** Requested nodes and links appear in list/topology results.

---

## 3. Configure devices

**Goal tool:** `gns3_configure_devices` (`targets` with `node_name` + `commands` or `template_name`). Console bodies are pure text + `completed`.

**Expert fallback:**

1. Resolve `node_id` via `gns3_list_nodes` (by name)
2. Ensure node is started if console needs it (`gns3_start_node` / status from list)
3. Choose path:
   - **Template-first:** `gns3_apply_config_template` when a built-in fits
   - **Pasted CLI:** `gns3_send_console_commands` with the user’s commands (`enter_config_mode` / `save_config` as appropriate; console login via `login_username` / `login_password` or env defaults — do not print secrets)
   - **Bulk (≥3 similar):** `gns3_bulk_configure_nodes`
4. Verify: `gns3_get_node_config` and/or show commands via console

**Done when:** Verification output matches the requested config intent.

---

## 4. Diagnose connectivity

**Goal tool:** `gns3_diagnose_connectivity` (validate + optional `suspect_nodes` probes). Findings cite MCP evidence only; no auto-remediation.

**Expert fallback:**

1. `gns3_ensure_server` if not yet this session
2. `gns3_validate_topology`
3. `gns3_list_nodes` / `gns3_get_topology` — status, missing links, wrong ports
4. On suspects: `gns3_send_console_commands` (`show ip interface brief`, `show ip route`, `ping`, vendor-appropriate)
5. Optional: `gns3_start_capture` on a link → user/Wireshark analysis → `gns3_stop_capture`
6. Fix with green tools (start interface via console, add missing link, start node, re-apply config)
7. Re-check with the same probes

**Done when:** Root cause is stated with evidence from MCP outputs, and fix (if requested) is applied via MCP.

---

## 5. Guest SSH / host-style ops (e.g. SONiC VS)

**Goal tool:** `gns3_run_guest_commands` (`host` or project+node; never returns passwords).

**Expert fallback:**

1. Resolve node; ensure it is started and has management reachability
2. Prefer `gns3_ssh_exec` with explicit `host` when known; else `project_id` + `node_id` for metadata IP discovery
3. Pass `ssh_username` / `ssh_password` or rely on `GNS3_SSH_*` env — never echo passwords
4. Use console (`gns3_send_console_commands`) only if SSH is the wrong plane for that image

**Done when:** Command results from the goal tool or `gns3_ssh_exec` (or justified console path) answer the ask.

---

## 6. Image import + densify + Idle-PC

**Goal tool:** `gns3_prepare_image` (idempotent import; optional Idle-PC; densify stays yellow + escape note).

**Expert green path:**

1. `gns3_ensure_server`
2. `gns3_import_image` (`source_path`, `emulator`: `qemu` | `dynamips` | `iou`)
3. `gns3_list_images` to confirm
4. `gns3_list_templates` — if a suitable template already exists, use it with `gns3_add_node`
5. Start Dynamips node when needed → `gns3_get_idle_pc_values` (`auto_compute` true)

### Densify policy (always)

- Best practical RAM/NVRAM; sparsemem/mmap on when applicable
- Fill every usable Dynamips-supported slot (switch + routed FE + multi-serial where supported; full PA set on c7200)
- Prefer denser adapters; no empty supported slots
- After import, compute Idle-PC and save on the **template** when possible

### Yellow path (template CRUD / idle-pc on template)

MCP does **not** yet expose create/update template tools (see `capability-matrix.md`). To create a new dense template or write idle-pc onto the template:

1. State the gap (yellow)
2. Ask user allow for this action
3. Minimum non-MCP (or human GUI) only after allow

**Done when:** Image is listed; node can be instantiated from a template; Idle-PC computed; template densify/idle-pc either done green, completed under escape, or explicitly deferred with user agreement.

---

## 7. Snapshot / reset clean state

**Goal tool:** `gns3_manage_snapshot` (`operation` create|list|restore|delete_snapshot|delete_project). Destructive ops: preview → user confirm → `confirmation_token`.

**Expert fallback:**

1. Resolve `project_id`
2. **Create:** `gns3_create_snapshot` with a clear name (e.g. `Clean_State`, `Before_OSPF`)
3. **List:** `gns3_list_snapshots`
4. **Restore:**
   - Confirm with user
   - Prefer `gns3_create_snapshot` safety checkpoint first (name like `pre_restore_<timestamp>`)
   - `gns3_restore_snapshot`
5. **Delete snapshot:** only when user asked; use delete tool for snapshots (not project delete)
6. **Delete project:** confirm first → `gns3_delete_project`

**Done when:** Snapshot list reflects the request; restore only after confirm (+ safety snap when possible).

---

## 8. Session cleanup (ask first)

**Goal tool:** `gns3_finish_lab` (defaults all false; destructive flags need token after user yes).

**Expert fallback:**

1. Confirm the lab goal for this turn is done (topology/config/verify complete).
2. **Ask the user** two questions (can be one message):
   - Close the current project?
   - Stop the GNS3 server?
3. Only after explicit answers, act via MCP:
   - Close only: `gns3_close_project(project_id)` **or** `gns3_cleanup_session(project_id=…, close_project=true)`
   - Stop server only: `gns3_stop_server` **or** `gns3_cleanup_session(stop_server=true)`
   - Both / plus stop nodes: `gns3_cleanup_session` with flags matching consent
4. Remote `server_url`: stop_server is refused by the tool — report that; only close_project may apply.
5. Never delete the project as part of “cleanup” unless the user separately confirmed `gns3_delete_project`.

**Done when:** User was asked; accepted actions ran via MCP; declines are respected with no silent close/stop.
