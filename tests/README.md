# Tests

This directory contains test scripts and utilities for the GNS3 MCP Server.

## Directory Contents

### Old v1.0 Scripts (Archived)
These scripts were used during development and are kept for reference:
- `server_old.py` - Original v1.0 server implementation (backup)
- `test_api.py` - Basic GNS3 API connectivity tests
- `test_connectivity_step_by_step.py` - Step-by-step connection testing
- `verify_mcp_features.py` - Feature verification script

### Debug & Development Scripts
Various scripts used during topology testing and development:
- `add_laptop2.py`, `bounce_interface.py`, `check_gns3_info.py`
- `cleanup_test.py`, `configure_and_ping.py`, `configure_topology.py`
- `debug_router.py`, `fix_router_ram.py`, `fix_topology.py`
- `inspect_r1.py`, `recreate_links.py`, `replace_switch1.py`
- `restart_router.py`, `restart_switch1.py`

## Running Tests

### Manual Testing
For manual testing of the MCP server:

```bash
# 1. Start GNS3 server
# 2. From project root, run:
python -m gns3_mcp.server

# 3. In another terminal, use Gemini CLI:
gemini "List all GNS3 projects"
gemini "Get GNS3 server info"
```

### API Testing
Test direct API connectivity:

```bash
cd tests
python test_api.py
```

### Feature Verification
Verify all MCP features:

```bash
cd tests
python verify_mcp_features.py
```

## Test Environment Setup

Required for testing:
1. GNS3 server running on http://localhost:3080
2. At least one project created in GNS3
3. Some device templates installed

## Future Development

TODO:
- [ ] Add pytest-based unit tests
- [ ] Add integration tests
- [ ] Add CI/CD pipeline tests
- [ ] Add coverage reporting
- [ ] Add performance benchmarks

## Notes

The scripts in this directory are primarily for development and debugging purposes. For production use, see the main server in `src/gns3_mcp/` and examples in `examples/`.

For proper testing framework setup, install dev dependencies:

```bash
pip install -e ".[dev]"
pytest
```

See [docs/PROJECT_STRUCTURE.md](../docs/PROJECT_STRUCTURE.md) for development workflow information.
