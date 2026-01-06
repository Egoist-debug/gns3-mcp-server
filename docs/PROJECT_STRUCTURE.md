# GNS3 MCP Server v2.0 - Project Structure

## 📁 Directory Structure

```
gns3-mcp-server3/
│
├── 📄 Core Files
│   ├── server.py                      # Main MCP server with 40+ tools
│   ├── gns3_client.py                 # Complete GNS3 API client
│   ├── telnet_client.py               # Enhanced Telnet console access
│   ├── config_templates.py            # Pre-built configuration templates
│   └── server_old.py                  # Backup of v1.0 server
│
├── 📄 Configuration
│   ├── mcp-server.json                # MCP server metadata for Gemini
│   ├── pyproject.toml                 # Python project configuration
│   ├── requirements.txt               # Python dependencies
│   ├── run.bat                        # Windows launcher
│   └── run.sh                         # Linux/Mac launcher
│
├── 📄 Documentation
│   ├── README.md                      # Main project documentation
│   ├── TOOL_REFERENCE.md              # Complete tool documentation (40+ tools)
│   ├── CHANGELOG.md                   # Version history and roadmap
│   ├── MIGRATION.md                   # v1.0 → v2.0 migration guide
│   └── PROJECT_STRUCTURE.md           # This file
│
├── 📄 Examples & Tests
│   ├── example_complete_network.py    # Complete enterprise network example
│   ├── configure_topology.py          # Topology configuration example
│   ├── test_api.py                    # Basic API testing
│   ├── test_connectivity_step_by_step.py  # Connectivity testing
│   ├── check_gns3_info.py             # GNS3 server info check
│   ├── verify_mcp_features.py         # MCP features verification
│   ├── add_laptop2.py                 # Add laptop example
│   ├── bounce_interface.py            # Interface bounce example
│   ├── cleanup_test.py                # Cleanup utilities
│   ├── configure_and_ping.py          # Config and connectivity test
│   ├── debug_router.py                # Router debugging
│   ├── fix_router_ram.py              # Router RAM fix
│   ├── fix_topology.py                # Topology fix utilities
│   ├── inspect_r1.py                  # Router inspection
│   ├── recreate_links.py              # Link recreation
│   ├── replace_switch1.py             # Switch replacement
│   ├── restart_router.py              # Router restart
│   └── restart_switch1.py             # Switch restart
│
└── 📁 Runtime
    └── __pycache__/                   # Python bytecode cache
```

## 📋 File Descriptions

### Core Components

#### `server.py` (Main Server)
**Purpose:** MCP server with 40+ tools for GNS3 automation

**Key Features:**
- FastMCP integration
- 40+ comprehensive tools covering all GNS3 operations
- Async operation support
- Comprehensive error handling
- Tool categories:
  - Server & Compute (2 tools)
  - Project Management (8 tools)
  - Node Management (13 tools)
  - Link Management (3 tools)
  - Topology (1 tool)
  - Console & Configuration (3 tools)
  - Templates & Appliances (2 tools)
  - Snapshots (4 tools)
  - Packet Capture (2 tools)
  - Drawing & Annotation (2 tools)
  - Advanced Utilities (3 tools)

**Dependencies:** gns3_client, telnet_client, config_templates, fastmcp

#### `gns3_client.py` (API Client)
**Purpose:** Comprehensive HTTP client for GNS3 REST API v2

**Features:**
- Complete API coverage
- Async HTTP operations
- Authentication support
- SSL/TLS verification
- Error handling with detailed messages
- Connection pooling
- Timeout configuration

**API Categories:**
- Server operations
- Project CRUD
- Node CRUD
- Link CRUD
- Capture operations
- Snapshot operations
- Template operations
- Appliance operations
- Drawing operations
- Symbol operations

#### `telnet_client.py` (Console Client)
**Purpose:** Enhanced Telnet client for device console access

**Features:**
- Auto-detection of device prompts
- Boot wait functionality
- Config mode entry/exit
- Config save automation
- Handle various device types
- Error handling and logging

**Methods:**
- connect() - Establish connection
- close() - Close connection
- read_until() - Read until specific chars
- send_cmd() - Send command and wait
- wait_for_boot() - Wait for device boot
- enter_config_mode() - Enter Cisco config mode
- exit_config_mode() - Exit config mode
- save_config() - Save configuration
- send_config_commands() - Send multiple configs
- get_running_config() - Retrieve configuration

#### `config_templates.py` (Templates)
**Purpose:** Pre-built configuration templates for common scenarios

**Template Categories:**

1. **Basic Setup:**
   - basic_router_config()
   - interface_config()

2. **Routing Protocols:**
   - ospf_config()
   - eigrp_config()
   - bgp_config()
   - static_route()
   - default_route()

3. **Switching:**
   - vlan_config()
   - trunk_port_config()
   - access_port_config()

4. **Services:**
   - dhcp_pool_config()
   - nat_overload_config()

5. **Security:**
   - standard_acl()
   - extended_acl()
   - security_hardening_basic()
   - ssh_config()

6. **Management:**
   - banner_config()
   - ntp_config()
   - logging_config()
   - snmp_config()

7. **QoS:**
   - qos_basic_marking()

8. **VPCS:**
   - vpcs_basic_config()
   - vpcs_dhcp_config()

**Topology Templates:**
- simple_lan() - Basic LAN setup
- dual_router_topology() - Two routers with PCs
- hub_and_spoke() - Central hub with spokes

### Configuration Files

#### `mcp-server.json`
**Purpose:** MCP server metadata for AI assistant integration

**Contains:**
- Server name and description
- Launch command (run.bat)
- Environment variables
- User parameters

#### `pyproject.toml`
**Purpose:** Python project configuration (PEP 518)

**Contains:**
- Project metadata
- Dependencies
- Build system
- Development tools configuration

#### `requirements.txt`
**Purpose:** Python package dependencies

**Dependencies:**
- fastmcp>=2.0.0 - MCP framework
- httpx>=0.25.0 - HTTP client
- pydantic>=2.0.0 - Data validation

#### `run.bat` / `run.sh`
**Purpose:** Platform-specific launchers

**Features:**
- Auto-create virtual environment
- Install dependencies
- Activate environment
- Start MCP server

### Documentation

#### `README.md`
Comprehensive project overview with:
- Feature matrix
- Installation guide
- Tool categories overview
- Usage examples
- Real-world scenarios

#### `TOOL_REFERENCE.md`
Complete documentation for all 40+ tools:
- Tool descriptions
- Parameters
- Return values
- Usage examples
- Workflow guides
- Pro tips

#### `CHANGELOG.md`
Version history:
- v2.0 features and changes
- v1.0 initial release
- Future roadmap

#### `MIGRATION.md`
Guide for upgrading from v1.0:
- Breaking changes
- New features
- Migration steps
- Testing checklist

### Examples

#### `example_complete_network.py`
**Comprehensive demonstration showing:**
1. Project creation
2. Template listing
3. Device addition
4. Link creation
5. Simulation start
6. Configuration (OSPF, DHCP)
7. Snapshot creation
8. Topology validation
9. Final topology overview

**Use Case:** Learn all major features in one script

#### Other Example Scripts
Various focused examples for specific operations:
- Topology configuration
- Connectivity testing
- API testing
- Router debugging
- Interface management
- Device replacement

## 🔧 Development Workflow

### Adding a New Tool

1. **Add function to `server.py`:**
```python
@mcp.tool
async def gns3_my_new_tool(
    project_id: str,
    server_url: str = "http://localhost:3080",
    username: Optional[str] = None,
    password: Optional[str] = None,
    # your parameters
) -> Dict[str, Any]:
    """
    Tool description for AI assistant.
    
    Args:
        project_id: Project ID
        # your parameters
    
    Returns:
        Dictionary with status and results
    """
    try:
        client = create_client(server_url, username, password)
        # your implementation
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"Failed: {e}")
        return {"status": "error", "error": str(e)}
```

2. **Add to API client if needed (`gns3_client.py`):**
```python
async def my_new_api_method(self, ...) -> Dict[str, Any]:
    """API method description."""
    return await self._request("GET", f"/endpoint")
```

3. **Document in `TOOL_REFERENCE.md`:**
```markdown
#### `gns3_my_new_tool`
Description and usage example.
```

4. **Add to CHANGELOG.md**

5. **Test thoroughly**

### Testing Changes

```bash
# Syntax check
python -m py_compile server.py

# Import test
python -c "import server; print('OK')"

# Run examples
python example_complete_network.py
```

## 🚀 Deployment

### For End Users
```bash
# Clone repository
git clone <repo-url>
cd gns3-mcp-server3

# Add to Gemini CLI
gemini mcp add gns3 "$(pwd)/run.bat"  # Windows
gemini mcp add gns3 "$(pwd)/run.sh"   # Linux/Mac

# Test
gemini "List GNS3 projects"
```

### For Developers
```bash
# Clone and setup dev environment
git clone <repo-url>
cd gns3-mcp-server3
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black server.py
isort server.py

# Type check
mypy server.py
```

## 📊 Statistics

- **Total Files:** 30+
- **Lines of Code:** ~3,500+ (core modules)
- **Tools:** 40+
- **Configuration Templates:** 15+
- **Documentation Pages:** 5
- **Example Scripts:** 15+

## 🔄 Version Control

### Important Files to Track
- ✅ Core modules (server.py, gns3_client.py, etc.)
- ✅ Configuration files
- ✅ Documentation
- ✅ Examples

### Files to Ignore (.gitignore)
```
__pycache__/
*.pyc
*.pyo
.venv/
*.egg-info/
dist/
build/
.pytest_cache/
.mypy_cache/
*.log
```

## 📞 Support

For questions about project structure:
1. Review this document
2. Check README.md for overview
3. See TOOL_REFERENCE.md for tool details
4. Review example scripts for usage patterns

---

**Last Updated:** January 6, 2026  
**Version:** 2.0.0  
**Maintainer:** GNS3 MCP Server Team
