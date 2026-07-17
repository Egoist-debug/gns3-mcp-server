# GNS3 MCP Server - Complete Tool Reference

## 🎯 Quick Start

```bash
# Start the MCP server
run.bat  # Windows
./run.sh # Linux/Mac

# Add to Gemini CLI
gemini mcp add gns3 "path/to/gns3-mcp-server3/run.bat"
```

## 📚 Available Tools (40+ Tools)

### 🖥️ Server & Compute Management (5 tools)

#### `gns3_ensure_server`
Probe the GNS3 server and auto-start it when the target is **localhost**.
```
Args:
  - server_url: GNS3 REST base URL (default http://localhost:3080)
  - username/password: Optional GNS3 API auth
  - force: Bypass healthy cache and re-probe (default: false)

Behavior:
  - Localhost/127.0.0.1/::1 down → run GNS3_SERVER_START_CMD or `gns3server`
    (default binary gets --host/--port from server_url)
  - Remote URL down → error only (never spawns local process)
  - Spawned process is detached and left running
  - Process-wide lock + 30s healthy cache

Returns:
  status, already_running, started, server_url, server_info,
  start_command, wait_seconds, error?

Env:
  GNS3_SERVER_URL, GNS3_SERVER_START_CMD, GNS3_SERVER_START_TIMEOUT,
  GNS3_SERVER_HEALTHY_CACHE_SECONDS
```

#### `gns3_stop_server`
Stop a **localhost** GNS3 server process listening on the URL port.
```
Args:
  - server_url: GNS3 REST base URL (port used for PID discovery)
  - username/password: Unused (signature consistency only)

Behavior:
  - Discover TCP LISTEN PIDs on the URL port (ss → fuser → lsof)
  - SIGTERM all PIDs, wait (default 10s, GNS3_SERVER_STOP_TIMEOUT), then SIGKILL survivors
  - Remote URLs are refused (never killed over the network)
  - No listen PIDs → already_stopped success
  - Clears healthy cache for the URL

Returns:
  status, server_url, stopped, already_stopped, pids, signal_steps,
  wait_seconds, error?

Env:
  GNS3_SERVER_STOP_TIMEOUT
```

#### `gns3_cleanup_session`
Optional multi-step lab cleanup. All flags default **false** (inert until set).
```
Args:
  - project_id: Optional; required for node/project steps
  - stop_nodes: Stop all nodes in the project (default false)
  - close_project: Close project (default false)
  - stop_server: Stop localhost gns3server (default false)
  - server_url / username / password: Standard API connection args

Order (when flags true):
  1. stop_nodes
  2. close_project
  3. stop_server

Rules:
  - Missing project_id with stop_nodes/close_project → that step skipped
  - Step failure is recorded; later steps still run
  - stop_server-only path does NOT call ensure (avoids restart-then-kill)
  - Does not delete projects

Returns:
  status (success|partial|error), server_url, project_id, steps[]
```

#### `gns3_get_server_info`
Get GNS3 server version and capabilities.
```
Returns: Server version, user, supported features
```

#### `gns3_list_computes`
List all available compute servers (local, VM, remote).
```
Returns: Compute ID, name, host, port, status
```

---

### 📁 Project Management (8 tools)

#### `gns3_list_projects`
List all projects with status and statistics.

#### `gns3_create_project`
Create new project.
```
Args:
  - name: Project name (required)
  - auto_close: Auto-close on server stop (default: false)
  - auto_open: Auto-open on server start (default: false)
  - auto_start: Auto-start all nodes (default: false)
  - path: Custom project path (optional)
```

#### `gns3_get_project`
Get detailed project information.

#### `gns3_update_project`
Update project settings.

#### `gns3_open_project`
Open a project for editing.

#### `gns3_close_project`
Close a project (stops all nodes).

#### `gns3_delete_project`
Permanently delete a project.
**⚠️ WARNING: Cannot be undone!**

#### `gns3_duplicate_project`
Create a copy of a project.
```
Args:
  - project_id: Source project
  - new_name: Name for duplicate
  - path: Optional custom path
```

---

### 🔧 Node Management (13 tools)

#### `gns3_list_nodes`
List all nodes in a project with details.

#### `gns3_add_node`
Add a device to the topology.
```
Args:
  - project_id: Target project
  - node_name: Device name
  - template_id: Template to use (see gns3_list_templates)
  - x, y: Position coordinates
  - compute_id: Compute server (default: "local")
```

#### `gns3_get_node`
Get detailed node information.

#### `gns3_update_node`
Update node name, position, or properties.

#### `gns3_delete_node`
Remove a node (deletes connected links too).

#### `gns3_start_node`
Start a specific node.

#### `gns3_stop_node`
Stop a specific node.

#### `gns3_suspend_node`
Suspend node (pause, save state).

#### `gns3_reload_node`
Reload node (restart without stopping).

#### `gns3_duplicate_node`
Create a copy of a node.

#### `gns3_start_all_nodes`
Start all nodes in a project at once.

#### `gns3_stop_all_nodes`
Stop all nodes in a project at once.

---

### 🔗 Link Management (3 tools)

#### `gns3_list_links`
List all connections with endpoint details.

#### `gns3_add_link`
Connect two nodes.
```
Args:
  - project_id: Target project
  - node_a_id, node_b_id: Nodes to connect
  - adapter_a, port_a: Port on node A (default: 0, 0)
  - adapter_b, port_b: Port on node B (default: 0, 0)
```

#### `gns3_delete_link`
Remove a connection.

---

### 🗺️ Topology Tools (1 tool)

#### `gns3_get_topology`
Get complete topology overview.
```
Returns:
  - Project info
  - All nodes with details
  - All links with connections
  - Summary statistics
```

---

### 💻 Console & Configuration (3 tools)

#### `gns3_send_console_commands`
Send CLI commands to a device console via Telnet.
```
Args:
  - project_id, node_id: Target device (must be started)
  - commands: List of commands
  - wait_for_boot: Wait for device boot (default: true)
  - boot_timeout: Boot wait timeout in seconds (default: 120)
  - enter_config_mode: Auto enter config mode (default: false)
  - save_config: Save after commands (default: false)
  - enable_password: Enable password if needed
  - login_username: Console login user (or GNS3_CONSOLE_USER)
  - login_password: Console login password (or GNS3_CONSOLE_PASSWORD)
  - ready_timeout: Login readiness budget seconds after connect/boot
      (default 30 / GNS3_CONSOLE_READY_TIMEOUT)

Notes:
  - username/password on this tool are GNS3 API auth, not console login
  - Login handles Username:/login:/Password: heuristics with settle/retry
  - Command completion uses line-oriented shell prompts (avoids mid-output
    truncation on interior '#' / '>')
  - Auto-pages --More-- and cleans CR/control noise from responses
  - Per-command response cap: 512 KiB (GNS3_CONSOLE_MAX_RESPONSE_BYTES);
    over-cap results set truncated=true + length metadata
  - Does not auto-start the node; use gns3_start_node first

Example:
{
  "commands": [
    "interface GigabitEthernet0/0",
    "ip address 192.168.1.1 255.255.255.0",
    "no shutdown"
  ],
  "enter_config_mode": true,
  "save_config": true,
  "login_username": "admin",
  "login_password": "cisco"
}
```

#### `gns3_get_node_config`
Retrieve device configuration.
```
Args:
  - config_type: "running" or "startup"
```

#### `gns3_apply_config_template`
Apply pre-built configuration templates.
```
Supported templates:
  - basic_router: Hostname, domain setup
  - interface: Configure interface with IP
  - ospf: OSPF routing protocol
  - eigrp: EIGRP routing protocol
  - bgp: BGP routing protocol
  - static_route: Static routing
  - vlan: VLAN creation
  - trunk_port: Trunk port configuration
  - access_port: Access port configuration
  - dhcp_pool: DHCP server setup
  - nat_overload: NAT/PAT configuration
  - ssh: SSH access configuration

Example - Configure OSPF:
{
  "template_name": "ospf",
  "template_params": {
    "process_id": 1,
    "router_id": "1.1.1.1",
    "networks": [
      {"network": "192.168.1.0", "wildcard": "0.0.0.255", "area": 0},
      {"network": "10.0.0.0", "wildcard": "0.0.0.3", "area": 0}
    ]
  },
  "save_config": true
}
```


### 🔐 SSH Guest Access (1 tool)

#### `gns3_ssh_exec`
Run shell commands on a guest VM/host over SSH (password auth).
```
Args:
  - commands: List of shell commands (one SSH connection)
  - host: Guest IP/hostname (preferred)
  - port: SSH port (default 22)
  - project_id, node_id: Optional; best-effort IP from GNS3 node metadata if host omitted
  - ssh_username: Guest user (or GNS3_SSH_USER)
  - ssh_password: Guest password (or GNS3_SSH_PASSWORD)
  - stop_on_error: Stop after first non-zero exit (default true)
  - host_key_policy: accept_new (accept any key) | strict (default known_hosts) | warn (accept + log fingerprint)
  - connect_timeout: Total connect readiness budget seconds (default 30 /
      GNS3_SSH_CONNECT_TIMEOUT). Retries transient failures (refused/timeout);
      does not retry PermissionDenied.
  - username/password: GNS3 API auth for metadata lookup only

Returns per command: {command, stdout, stderr, exit_code}
Also may include connect_attempts. Passwords are never returned in the payload.

Env:
  GNS3_SSH_USER, GNS3_SSH_PASSWORD, GNS3_SSH_HOST_KEY_POLICY, GNS3_SSH_CONNECT_TIMEOUT
```

---

### 📦 Template & Appliance Management (2 tools)

#### `gns3_list_templates`
List all device templates available.
```
Returns: Template name, ID, type, category
Use template_id when adding nodes
```

#### `gns3_list_appliances`
List all available appliances.
```
Returns: Appliance name, category, vendor
```

---

### 📸 Snapshot & Version Control (4 tools)

#### `gns3_list_snapshots`
List all snapshots for a project.

#### `gns3_create_snapshot`
Create a backup snapshot.
```
Args:
  - snapshot_name: Name for the snapshot
```

#### `gns3_restore_snapshot`
Restore project to a previous snapshot.
**⚠️ WARNING: Current state will be lost!**

#### `gns3_delete_snapshot`
Delete a snapshot permanently.

---

### 📊 Packet Capture (2 tools)

#### `gns3_start_capture`
Start capturing packets on a link.
```
Args:
  - link_id: Link to capture
  - capture_file_name: Name for pcap file
  - data_link_type: Link layer type (default: "DLT_EN10MB")
```

#### `gns3_stop_capture`
Stop packet capture.

---

### ✏️ Drawing & Annotation (2 tools)

#### `gns3_add_text_annotation`
Add text labels to topology.
```
Args:
  - text: Text content
  - x, y: Position
  - rotation: Rotation angle (default: 0)
```

#### `gns3_add_shape`
Add shapes (rectangle or ellipse).
```
Args:
  - shape_type: "rectangle" or "ellipse"
  - x, y: Position
  - width, height: Dimensions
  - color: Border color (hex)
  - fill_color: Fill color (hex, optional)
```

---

### 🔧 Advanced & Utilities (3 tools)

#### `gns3_get_idle_pc_values`
Get idle-pc values for Dynamips routers (reduces CPU usage).
```
Args:
  - auto_compute: Auto-compute best value (default: true)
```

#### `gns3_bulk_configure_nodes`
Configure multiple nodes in one operation.
```
Args:
  - configurations: List of node configs
    Each config:
      - node_id: Target node
      - commands: Command list
      - enter_config_mode: Auto config mode (default: true)
      - save_config: Save after (default: false)

Example:
{
  "configurations": [
    {
      "node_id": "router1-id",
      "commands": ["hostname R1", "interface g0/0", "ip address 10.1.1.1 255.255.255.0"],
      "save_config": true
    },
    {
      "node_id": "router2-id",
      "commands": ["hostname R2", "interface g0/0", "ip address 10.1.1.2 255.255.255.0"],
      "save_config": true
    }
  ]
}
```

#### `gns3_validate_topology`
Validate topology for common issues.
```
Checks:
  - Disconnected nodes
  - Stopped critical nodes
  - Overlapping nodes
  - Configuration problems
```

---

## 🎨 Common Workflows

### Creating a Simple Network

```
1. Create project
   gns3_create_project(name="My_Network")

2. List available templates
   gns3_list_templates()

3. Add devices
   gns3_add_node(node_name="R1", template_id="router-template-id", x=0, y=0)
   gns3_add_node(node_name="SW1", template_id="switch-template-id", x=0, y=100)
   gns3_add_node(node_name="PC1", template_id="vpcs-template-id", x=-100, y=200)

4. Connect devices
   gns3_add_link(node_a_id="r1-id", node_b_id="sw1-id")
   gns3_add_link(node_a_id="sw1-id", node_b_id="pc1-id")

5. Start simulation
   gns3_start_all_nodes()

6. Configure devices
   gns3_apply_config_template(
     node_id="r1-id",
     template_name="interface",
     template_params={
       "interface": "GigabitEthernet0/0",
       "ip_address": "192.168.1.1",
       "subnet_mask": "255.255.255.0"
     }
   )
```

### Configuring OSPF Between Routers

```
# Configure R1
gns3_apply_config_template(
  node_id="r1-id",
  template_name="ospf",
  template_params={
    "process_id": 1,
    "router_id": "1.1.1.1",
    "networks": [
      {"network": "192.168.1.0", "wildcard": "0.0.0.255", "area": 0},
      {"network": "10.0.0.0", "wildcard": "0.0.0.3", "area": 0}
    ]
  },
  save_config=true
)

# Configure R2
gns3_apply_config_template(
  node_id="r2-id",
  template_name="ospf",
  template_params={
    "process_id": 1,
    "router_id": "2.2.2.2",
    "networks": [
      {"network": "192.168.2.0", "wildcard": "0.0.0.255", "area": 0},
      {"network": "10.0.0.0", "wildcard": "0.0.0.3", "area": 0}
    ]
  },
  save_config=true
)
```

### Setting Up VLANs on Switch

```
# Create VLANs
gns3_send_console_commands(
  node_id="switch-id",
  commands=[
    "vlan 10",
    "name Sales",
    "vlan 20",
    "name Engineering"
  ],
  enter_config_mode=true,
  save_config=true
)

# Configure trunk port
gns3_apply_config_template(
  node_id="switch-id",
  template_name="trunk_port",
  template_params={
    "interface": "GigabitEthernet0/1",
    "allowed_vlans": "10,20"
  },
  save_config=true
)

# Configure access ports
gns3_apply_config_template(
  node_id="switch-id",
  template_name="access_port",
  template_params={
    "interface": "FastEthernet0/1",
    "vlan": 10,
    "portfast": true
  },
  save_config=true
)
```

### Backing Up Configuration

```
1. Create snapshot before changes
   gns3_create_snapshot(snapshot_name="Before_Changes")

2. Make changes...

3. If something goes wrong:
   gns3_restore_snapshot(snapshot_id="snapshot-id")

4. Or get current config:
   gns3_get_node_config(node_id="router-id", config_type="running")
```

### Troubleshooting

```
1. Validate topology
   gns3_validate_topology()

2. Check all nodes status
   gns3_list_nodes()

3. Check connectivity
   gns3_list_links()

4. Capture traffic
   gns3_start_capture(link_id="link-id", capture_file_name="debug")

5. View device config
   gns3_get_node_config(node_id="device-id")

6. Send diagnostic commands
   gns3_send_console_commands(
     node_id="router-id",
     commands=["show ip interface brief", "show ip route", "ping 192.168.1.1"]
   )
```

---

## 🔍 Pro Tips

### 1. Always List First
Before adding nodes, use `gns3_list_templates()` to see available templates.

### 2. Use Snapshots
Create snapshots before major changes. They're your safety net!

### 3. Bulk Operations
Use `gns3_bulk_configure_nodes()` to configure multiple devices efficiently.

### 4. Validation
Run `gns3_validate_topology()` after building to catch issues early.

### 5. Configuration Templates
Use pre-built templates instead of raw commands - they're tested and reliable.

### 6. Console Access
The console tools support auto-detection of prompts and config modes.

### 7. Error Handling
All tools return `{"status": "success"}` or `{"status": "error", "error": "message"}`.

---

## 📖 Configuration Template Examples

### Basic Router Setup
```json
{
  "template_name": "basic_router",
  "template_params": {
    "hostname": "R1",
    "domain": "lab.local"
  }
}
```

### Interface Configuration
```json
{
  "template_name": "interface",
  "template_params": {
    "interface": "GigabitEthernet0/0",
    "ip_address": "192.168.1.1",
    "subnet_mask": "255.255.255.0",
    "description": "LAN Interface"
  }
}
```

### DHCP Server
```json
{
  "template_name": "dhcp_pool",
  "template_params": {
    "pool_name": "LAN_POOL",
    "network": "192.168.1.0",
    "mask": "255.255.255.0",
    "default_router": "192.168.1.1",
    "dns_servers": ["8.8.8.8", "8.8.4.4"],
    "excluded_addresses": [["192.168.1.1", "192.168.1.10"]]
  }
}
```

### NAT Configuration
```json
{
  "template_name": "nat_overload",
  "template_params": {
    "inside_interfaces": ["GigabitEthernet0/0", "GigabitEthernet0/1"],
    "outside_interface": "GigabitEthernet0/2",
    "acl_number": 1,
    "allowed_networks": ["192.168.1.0 0.0.0.255", "192.168.2.0 0.0.0.255"]
  }
}
```

### SSH Access
```json
{
  "template_name": "ssh",
  "template_params": {
    "domain": "lab.local",
    "username": "admin",
    "password": "cisco123",
    "crypto_key_size": 2048,
    "vty_lines": "0 15"
  }
}
```

---

## 🚨 Important Notes

1. **Project IDs**: Use `gns3_list_projects()` to get project IDs
2. **Node IDs**: Use `gns3_list_nodes()` to get node IDs
3. **Link IDs**: Use `gns3_list_links()` to get link IDs
4. **Template IDs**: Use `gns3_list_templates()` to get template IDs
5. **Console Access**: Node must be started to access console
6. **Compute Servers**: "local" is default, use `gns3_list_computes()` for others

---

## 🆘 Troubleshooting

### Connection Issues
```
Error: "Failed to connect to GNS3 server"
Solution: 
  - Check GNS3 server is running
  - Verify server_url (default: http://localhost:3080)
  - Check firewall settings
```

### Template Not Found
```
Error: "Template not found"
Solution:
  - Use gns3_list_templates() to get valid template IDs
  - Ensure template is installed in GNS3
```

### Console Timeout
```
Error: "Timeout waiting for device boot"
Solution:
  - Increase boot_timeout parameter
  - Check device is starting correctly
  - Verify sufficient RAM/CPU in device properties
```

### Configuration Failed
```
Error: "Failed to send console commands"
Solution:
  - Ensure device is started (status: "started")
  - Check enable_password if device requires it
  - Verify commands are valid for device type
```

---

## 📞 Support

For issues or questions:
1. Check this reference guide
2. Review README.md for examples
3. Check GNS3 server logs
4. Verify GNS3 server is accessible

---

**Version**: 2.0.0  
**Last Updated**: January 2026  
**Total Tools**: 40+  
**Supported GNS3 API**: v2
