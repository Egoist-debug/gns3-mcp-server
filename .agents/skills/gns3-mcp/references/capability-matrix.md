# GNS3 MCP capability matrix

Legend:

| Color | Meaning |
|-------|---------|
| **Green** | Fully doable with MCP tools. No escape. |
| **Yellow** | Partial MCP path. Finish only via escape ritual (name gap → user allow → minimum non-MCP). |
| **Red** | Not an agent ops path via this MCP. Human / external process. |

Tool names below are canonical `gns3_*`. Apply host prefixes as needed.

## Green — MCP-only

| Job | Primary tools |
|-----|----------------|
| Probe / auto-start local GNS3 | `gns3_ensure_server`, `gns3_get_server_info`, `gns3_list_computes` |
| Project lifecycle | `gns3_list_projects`, `gns3_create_project`, `gns3_get_project`, `gns3_update_project`, `gns3_open_project`, `gns3_close_project`, `gns3_duplicate_project`, `gns3_save_project` |
| List / add / control nodes | `gns3_list_nodes`, `gns3_add_node`, `gns3_get_node`, `gns3_update_node`, `gns3_delete_node`, start/stop/suspend/reload/duplicate, start/stop all |
| Links | `gns3_list_links`, `gns3_add_link`, `gns3_delete_link` |
| Topology overview / validation | `gns3_get_topology`, `gns3_validate_topology` |
| Device CLI | `gns3_send_console_commands`, `gns3_get_node_config` |
| Built-in config templates | `gns3_apply_config_template` (ospf, eigrp, bgp, vlan, dhcp, ssh, …) |
| Bulk CLI push | `gns3_bulk_configure_nodes` |
| Guest shell over SSH | `gns3_ssh_exec` |
| List device templates / appliances | `gns3_list_templates`, `gns3_list_appliances` |
| Image store list / upload | `gns3_list_images`, `gns3_import_image` |
| Compute Idle-PC on a node | `gns3_get_idle_pc_values` |
| Snapshots | `gns3_list_snapshots`, `gns3_create_snapshot`, `gns3_restore_snapshot`, `gns3_delete_snapshot` |
| Packet capture | `gns3_start_capture`, `gns3_stop_capture` |
| Canvas annotations | `gns3_add_text_annotation`, `gns3_add_shape` |
| Export project archive | `gns3_export_project` (confirm with user first) |

## Yellow — MCP + possible escape

| Job | MCP can | Gap | Escape only after ritual |
|-----|---------|-----|---------------------------|
| Dynamips / IOS **template create** | Upload image (`gns3_import_image`); list images/templates | No MCP tool for `create_template` (client has REST helper) | Create template via allowed non-MCP **after user allow**, or human uses GNS3 GUI |
| **Densify** template slots (fill WIC/NM/PA) | `gns3_update_node` for **instances**; list templates | No MCP tool to update **template** properties / slot maps | Persist densify on template only with allow; prefer densifying documented defaults in GUI/template JSON with allow |
| **Idle-PC on template** | `gns3_get_idle_pc_values` on a running Dynamips **node** | No MCP tool to write idle-pc onto the **template** record | Apply computed value to template with allow, or leave on node only |
| Appliance install from `.gns3a` | List appliances | No dedicated “install appliance file” MCP tool | Install via GNS3 UI/CLI with allow if required for the task |
| Docker image pull | N/A | `gns3_import_image` rejects docker | Use Docker tooling with allow if the lab needs it |

Policy for yellow: still **ask once** (escape ritual). Do not treat yellow as silent permission.

## Red — not MCP agent ops

| Job | Notes |
|-----|--------|
| Drive lab by running `examples/*.py` or ad-hoc REST scripts | Forbidden as ops path (see skill hard rules) |
| Reverse-engineer GNS3 GUI automation | Out of scope |
| Change GNS3 server source / reinstall GNS3 OS packages | Human / infra |
| Non-GNS3 networks (physical lab, cloud VPC) | Different tools |

## Densify / Idle-PC (agent-facing)

From workspace policy (also in root `AGENTS.md`):

- Prefer best practical RAM/NVRAM; sparsemem/mmap on where applicable.
- Fill every usable Dynamips-supported slot with high-density lab modules.
- After import, compute Idle-PC and **save it on the template** when possible.

**MCP-green portion:** `gns3_import_image` → add node from an **existing** template → `gns3_get_idle_pc_values`.  
**Yellow portion:** creating/updating the template document itself (slots + idle-pc field) until MCP grows those tools.

## When a green tool fails

That is not “yellow.” Run the escape ritual with the **error text**, or fix preconditions via other green tools (ensure server, open project, start node, correct ports). Do not invent a Python client because one call failed.
