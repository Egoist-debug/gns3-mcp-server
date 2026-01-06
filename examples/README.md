# Examples

This directory contains comprehensive examples demonstrating the capabilities of the GNS3 MCP Server.

## Available Examples

### `example_complete_network.py`
A comprehensive demonstration of building a complete enterprise network using the GNS3 MCP Server. This example covers:

- Project creation and management
- Device deployment (routers, switches, PCs)
- Link creation and topology building
- OSPF configuration across routers
- DHCP server setup
- Snapshot management
- Topology validation

### Running the Examples

```bash
# From the project root
cd examples
python example_complete_network.py
```

**Prerequisites:**
- GNS3 server running on http://localhost:3080
- Required templates installed in GNS3:
  - Cisco routers (IOSv or similar)
  - Ethernet switches
  - VPCS (Virtual PC Simulator)

### What You'll Learn

1. **Project Management**: Create and configure projects
2. **Device Deployment**: Add routers, switches, and PCs
3. **Topology Building**: Connect devices with links
4. **Configuration**: Apply routing protocols and services
5. **Validation**: Check topology health
6. **Backup**: Create and manage snapshots

### Example Output

The example script provides detailed output showing:
- Each step of the network build process
- Device configurations being applied
- Validation results
- Success/failure status for each operation

### Customization

You can modify the example to:
- Use different device templates
- Change IP addressing schemes
- Add additional routing protocols (BGP, EIGRP)
- Implement VLANs and trunking
- Add security features (ACLs, SSH)

### Need Help?

- See [docs/TOOL_REFERENCE.md](../docs/TOOL_REFERENCE.md) for complete API documentation
- Check [docs/START_HERE.md](../docs/START_HERE.md) for quick start guide
- Review [README.md](../README.md) for feature overview
