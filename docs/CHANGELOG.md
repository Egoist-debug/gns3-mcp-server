# Changelog

All notable changes to GNS3 MCP Server will be documented in this file.

## [2.0.0] - 2026-01-06

### 🎉 Major Release - Complete Rewrite

#### Added
- **37 New Tools** bringing total to 40+ comprehensive tools
- **Modular Architecture** - Separated into logical modules:
  - `gns3_client.py` - Complete GNS3 API client
  - `telnet_client.py` - Enhanced Telnet console access
  - `config_templates.py` - Pre-built configuration templates
  - `server.py` - Main MCP server with all tools

- **Server & Compute Management**
  - `gns3_get_server_info` - Server version and capabilities
  - `gns3_list_computes` - List compute servers

- **Enhanced Project Management**
  - `gns3_get_project` - Get project details
  - `gns3_update_project` - Update project settings
  - `gns3_close_project` - Close projects
  - `gns3_delete_project` - Delete projects permanently
  - `gns3_duplicate_project` - Copy projects

- **Complete Node Management**
  - `gns3_list_nodes` - List all devices
  - `gns3_get_node` - Get device details
  - `gns3_update_node` - Update device settings
  - `gns3_delete_node` - Remove devices
  - `gns3_suspend_node` - Suspend devices
  - `gns3_reload_node` - Reload devices
  - `gns3_duplicate_node` - Clone devices
  - `gns3_start_all_nodes` - Bulk start
  - `gns3_stop_all_nodes` - Bulk stop

- **Link Management**
  - `gns3_list_links` - List all connections
  - `gns3_delete_link` - Remove connections

- **Console & Configuration**
  - `gns3_get_node_config` - Get device configuration
  - `gns3_apply_config_template` - Apply pre-built configs
  - Enhanced `gns3_send_console_commands` with:
    - Auto config mode entry
    - Auto save configuration
    - Boot wait support
    - Enable password support

- **Configuration Templates (15+)**
  - Routing: OSPF, EIGRP, BGP, Static Routes
  - Switching: VLANs, Trunk Ports, Access Ports
  - Services: DHCP, NAT/PAT, SSH
  - Security: ACLs, Basic Hardening
  - Management: NTP, Logging, SNMP, Banners
  - QoS: Basic marking configuration

- **Template & Appliance Management**
  - `gns3_list_templates` - List device templates
  - `gns3_list_appliances` - List available appliances

- **Snapshot & Version Control**
  - `gns3_list_snapshots` - List snapshots
  - `gns3_create_snapshot` - Create backups
  - `gns3_restore_snapshot` - Restore from backups
  - `gns3_delete_snapshot` - Delete snapshots

- **Packet Capture**
  - `gns3_start_capture` - Start packet capture
  - `gns3_stop_capture` - Stop packet capture

- **Drawing & Annotation**
  - `gns3_add_text_annotation` - Add text labels
  - `gns3_add_shape` - Add shapes (rectangle, ellipse)

- **Advanced Utilities**
  - `gns3_get_idle_pc_values` - Optimize Dynamips routers
  - `gns3_bulk_configure_nodes` - Configure multiple devices
  - `gns3_validate_topology` - Check for common issues

#### Enhanced
- **Telnet Client**
  - Better prompt detection (>, #, $, %, various device types)
  - Auto-detection of config dialogs
  - Config mode entry/exit automation
  - Config save automation
  - Better error handling and logging

- **API Client**
  - Comprehensive error messages
  - Support for all HTTP methods (GET, POST, PUT, DELETE, PATCH)
  - Better connection handling
  - Configurable timeouts
  - SSL verification support

- **Error Handling**
  - Detailed error messages
  - Status indicators in all responses
  - Proper exception handling throughout

#### Changed
- Renamed tools for consistency:
  - `gns3_start_simulation` → `gns3_start_all_nodes`
  - `gns3_stop_simulation` → `gns3_stop_all_nodes`
  - `gns3_configure_device` → Merged into `gns3_update_node`
  - `gns3_capture_traffic` → `gns3_start_capture`
- Standardized return format: All tools return `{"status": "success|error", ...}`
- Improved parameter names for clarity

#### Documentation
- Added `TOOL_REFERENCE.md` - Complete tool documentation
- Updated `README.md` with v2.0 features
- Added `example_complete_network.py` - Comprehensive example
- Enhanced docstrings for all tools
- Added workflow examples

#### Performance
- Async operations throughout
- Better connection pooling
- Reduced redundant API calls

### Backward Compatibility Notes
- Old tool names still work but are deprecated
- Response format changed to include "status" field
- Some parameter names changed for clarity
- Migration guide: Check TOOL_REFERENCE.md for new names

---

## [1.0.0] - 2025-12-XX

### Initial Release
- Basic project management (list, create, open)
- Node management (add, configure)
- Link creation
- Simulation control (start/stop)
- Traffic capture
- Topology retrieval
- Console command sending
- 12 initial tools
- Gemini CLI integration

---

## Future Roadmap

### [2.1.0] - Planned
- [ ] Template creation and management tools
- [ ] Image management (upload, delete IOS images)
- [ ] More drawing types (lines, polygons)
- [ ] Advanced ACL builder
- [ ] Route map configuration templates
- [ ] BGP advanced features (communities, filters)
- [ ] WebSocket support for real-time updates

### [2.2.0] - Planned
- [ ] Multi-project operations
- [ ] Project import/export tools
- [ ] Automated testing frameworks
- [ ] Network documentation generator
- [ ] Compliance checking (best practices)
- [ ] Performance monitoring integration

### [3.0.0] - Planned
- [ ] AI-powered topology optimization
- [ ] Automatic configuration generation from requirements
- [ ] Network simulation scenarios
- [ ] Integration with external monitoring tools
- [ ] Cloud GNS3 server support
- [ ] Collaborative features
