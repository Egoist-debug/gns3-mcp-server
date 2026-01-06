# Migration Guide: v1.0 → v2.0

## Overview
Version 2.0 is a major update that expands from 12 to 40+ tools with enhanced capabilities. While we've maintained backward compatibility where possible, some changes require attention.

## Breaking Changes

### 1. Tool Renames

| v1.0 Name | v2.0 Name | Status |
|-----------|-----------|--------|
| `gns3_start_simulation` | `gns3_start_all_nodes` | Recommended to update |
| `gns3_stop_simulation` | `gns3_stop_all_nodes` | Recommended to update |
| `gns3_configure_device` | `gns3_update_node` | Replaced |
| `gns3_capture_traffic` | `gns3_start_capture` | Renamed for clarity |

**Old tools still work** but will show deprecation warnings. Update your code to use new names.

### 2. Response Format Changes

**v1.0 Response:**
```json
{
  "project": {...},
  "other_data": ...
}
```

**v2.0 Response:**
```json
{
  "status": "success",
  "project": {...},
  "other_data": ...
}
```

All tools now return a `"status"` field (`"success"` or `"error"`).

**Migration:**
```python
# v1.0
result = await gns3_create_project(name="Test")
if result.get("project"):
    # Success

# v2.0
result = await gns3_create_project(name="Test")
if result["status"] == "success":
    # Success
```

### 3. Parameter Changes

#### `gns3_add_node`
```python
# v1.0
gns3_add_node(
    project_id, node_name, node_type="ethernet_switch",
    template_id=None, ...
)

# v2.0 - template_id now required
gns3_add_node(
    project_id, node_name, template_id,  # Required
    x=0, y=0, compute_id="local"
)
```

#### `gns3_send_console_commands`
```python
# v1.0
gns3_send_console_commands(
    project_id, node_id, commands,
    wait_for_prompts=True, timeout=30
)

# v2.0 - Enhanced parameters
gns3_send_console_commands(
    project_id, node_id, commands,
    wait_for_boot=True,
    boot_timeout=120,
    enter_config_mode=False,  # New!
    save_config=False,        # New!
    enable_password=None      # New!
)
```

## New Features to Adopt

### 1. Configuration Templates

**Before (v1.0):**
```python
await gns3_send_console_commands(
    project_id, node_id,
    commands=[
        "router ospf 1",
        "router-id 1.1.1.1",
        "network 192.168.1.0 0.0.0.255 area 0",
        "exit"
    ]
)
```

**After (v2.0):**
```python
await gns3_apply_config_template(
    project_id, node_id,
    template_name="ospf",
    template_params={
        "process_id": 1,
        "router_id": "1.1.1.1",
        "networks": [
            {"network": "192.168.1.0", "wildcard": "0.0.0.255", "area": 0}
        ]
    },
    save_config=True
)
```

### 2. Bulk Operations

**Before (v1.0):**
```python
nodes = await gns3_list_nodes(project_id)
for node in nodes:
    await gns3_send_console_commands(
        project_id, node["node_id"],
        commands=["hostname Router"]
    )
```

**After (v2.0):**
```python
nodes = await gns3_list_nodes(project_id)
configurations = [
    {
        "node_id": node["node_id"],
        "commands": [f"hostname {node['name']}"],
        "save_config": True
    }
    for node in nodes["nodes"]
]
await gns3_bulk_configure_nodes(project_id, configurations)
```

### 3. Topology Validation

**New in v2.0:**
```python
# Check topology for issues
result = await gns3_validate_topology(project_id)
if not result["validation"]["is_valid"]:
    print("Issues found:", result["validation"]["issues"])
    print("Warnings:", result["validation"]["warnings"])
```

### 4. Snapshot Management

**New in v2.0:**
```python
# Create backup before changes
await gns3_create_snapshot(project_id, "Before_Changes")

# Make changes...

# Restore if needed
snapshots = await gns3_list_snapshots(project_id)
await gns3_restore_snapshot(project_id, snapshot_id)
```

### 5. Project Management Enhancements

**New operations:**
```python
# Close project (stops all nodes)
await gns3_close_project(project_id)

# Duplicate project
await gns3_duplicate_project(project_id, "Copy_Of_Project")

# Delete project permanently
await gns3_delete_project(project_id)

# Update project settings
await gns3_update_project(
    project_id,
    name="New_Name",
    auto_start=True
)
```

### 6. Node Management Enhancements

**New operations:**
```python
# Get detailed node info
node = await gns3_get_node(project_id, node_id)

# Update node properties
await gns3_update_node(
    project_id, node_id,
    name="New_Name",
    x=100, y=200,
    properties={"ram": 512}
)

# Suspend node (save state)
await gns3_suspend_node(project_id, node_id)

# Reload node
await gns3_reload_node(project_id, node_id)

# Duplicate node
await gns3_duplicate_node(project_id, node_id, x=50, y=50)

# Delete node
await gns3_delete_node(project_id, node_id)
```

### 7. Drawing & Annotations

**New in v2.0:**
```python
# Add text labels
await gns3_add_text_annotation(
    project_id,
    text="Core Network",
    x=0, y=-50
)

# Add shapes for documentation
await gns3_add_shape(
    project_id,
    shape_type="rectangle",
    x=0, y=0, width=200, height=100,
    color="#0000FF",
    fill_color="#E0E0FF"
)
```

## Migration Checklist

- [ ] Update tool names in your code
- [ ] Add `status` field checks to response handling
- [ ] Update parameter names where changed
- [ ] Test with new response format
- [ ] Consider using configuration templates
- [ ] Implement bulk operations where applicable
- [ ] Add topology validation to workflows
- [ ] Use snapshot management for safety
- [ ] Update documentation/comments

## Testing Your Migration

1. **Test Basic Operations:**
```python
# List projects (should work immediately)
result = await gns3_list_projects()
assert result["status"] == "success"
```

2. **Test Node Creation:**
```python
# Get templates first
templates = await gns3_list_templates()
template_id = templates["templates"][0]["template_id"]

# Create node
result = await gns3_add_node(
    project_id, "Test_Node", template_id
)
assert result["status"] == "success"
```

3. **Test Configuration:**
```python
# Try new template system
result = await gns3_apply_config_template(
    project_id, node_id,
    template_name="basic_router",
    template_params={"hostname": "R1", "domain": "test.local"}
)
assert result["status"] == "success"
```

## Getting Help

1. Check [TOOL_REFERENCE.md](TOOL_REFERENCE.md) for complete tool documentation
2. Review [example_complete_network.py](example_complete_network.py) for usage examples
3. See [CHANGELOG.md](CHANGELOG.md) for all changes

## Rollback

If you need to rollback to v1.0:

```bash
# The old server is backed up
cd gns3-mcp-server3
mv server.py server_v2.py
mv server_old.py server.py
```

## Benefits of Migrating

- **40+ tools** vs 12 tools
- **Configuration templates** - Faster, error-free configs
- **Bulk operations** - Configure multiple devices efficiently
- **Validation** - Catch errors before they cause problems
- **Snapshots** - Safety net for changes
- **Better error handling** - Clear, actionable error messages
- **Enhanced console** - Auto-detection and config mode support
- **Comprehensive API** - Every GNS3 feature accessible

## Questions?

For migration assistance, review the complete documentation or check the examples provided.
