# 🏗️ GNS3 MCP Server - Project Structure

```
gns3-mcp-server/
│
├── 📄 README.md                    # Main project documentation
├── 📄 LICENSE                      # MIT License
├── 📄 pyproject.toml               # Python project configuration
├── 📄 requirements.txt             # Python dependencies
├── 📄 .gitignore                   # Git ignore rules
├── 📄 mcp-server.json              # MCP server configuration (for Gemini)
├── 📄 run.bat                      # Windows launcher
├── 📄 run.sh                       # Linux/Mac launcher
│
├── 📁 src/gns3_mcp/                # Main source code (Python package)
│   ├── __init__.py                 # Package initialization
│   ├── __main__.py                 # Entry point (python -m gns3_mcp.server)
│   ├── server.py                   # Main MCP server (42 tools)
│   ├── gns3_client.py              # GNS3 REST API client
│   ├── telnet_client.py            # Enhanced Telnet console client
│   └── config_templates.py         # Pre-built configuration templates
│
├── 📁 docs/                        # Documentation
│   ├── START_HERE.md               # Quick start guide
│   ├── TOOL_REFERENCE.md           # Complete tool documentation
│   ├── CHANGELOG.md                # Version history
│   ├── MIGRATION.md                # v1.0 to v2.0 migration guide
│   ├── PROJECT_STRUCTURE.md        # Architecture documentation
│   └── UPGRADE_SUMMARY.md          # Upgrade summary
│
├── 📁 examples/                    # Usage examples
│   ├── README.md                   # Examples documentation
│   └── example_complete_network.py # Comprehensive network demo
│
├── 📁 tests/                       # Test scripts
│   ├── README.md                   # Testing documentation
│   ├── server_old.py               # v1.0 backup
│   ├── test_api.py                 # API connectivity tests
│   ├── test_connectivity_step_by_step.py
│   ├── verify_mcp_features.py
│   └── [various debug scripts...]
│
└── 📁 scripts/                     # Utility scripts (future use)
```

## 📊 Statistics

- **Total Lines of Code**: ~4,000+
- **Core Package**: 2,319 lines
  - `server.py`: 1,333 lines (42 tools)
  - `gns3_client.py`: 342 lines
  - `config_templates.py`: 385 lines
  - `telnet_client.py`: 259 lines
- **Documentation**: 2,063 lines (6 guides)
- **Examples**: 400+ lines

## 🔧 Key Files

### Core Package (`src/gns3_mcp/`)

| File | Purpose | Lines | Key Features |
|------|---------|-------|--------------|
| `server.py` | Main MCP server | 1,333 | 42 tools, FastMCP integration |
| `gns3_client.py` | GNS3 API client | 342 | Complete REST API v2 coverage |
| `telnet_client.py` | Console access | 259 | Auto-detection, config modes |
| `config_templates.py` | Templates | 385 | 15+ routing/switching configs |
| `__init__.py` | Package init | 27 | Version info, exports |
| `__main__.py` | Entry point | 10 | Module execution |

### Documentation (`docs/`)

| File | Purpose | Lines |
|------|---------|-------|
| `TOOL_REFERENCE.md` | Complete tool docs | 532 |
| `README.md` (root) | Project overview | 449 |
| `PROJECT_STRUCTURE.md` | Architecture | 344 |
| `UPGRADE_SUMMARY.md` | Upgrade summary | 338 |
| `MIGRATION.md` | Migration guide | 258 |
| `CHANGELOG.md` | Version history | 142 |
| `START_HERE.md` | Quick start | Various |

### Configuration

| File | Purpose |
|------|---------|
| `pyproject.toml` | Python project metadata, dependencies |
| `requirements.txt` | Pip-compatible dependencies |
| `mcp-server.json` | Gemini MCP configuration |
| `.gitignore` | Git ignore patterns |
| `LICENSE` | MIT License text |

### Launchers

| File | Purpose |
|------|---------|
| `run.bat` | Windows launcher (auto-installs deps) |
| `run.sh` | Linux/Mac launcher (uses uv) |

## 🎯 Import Structure

```python
# Package can be imported as:
from gns3_mcp import (
    mcp,                    # FastMCP server instance
    GNS3APIClient,          # API client class
    GNS3Config,             # Configuration model
    TelnetClient,           # Telnet client class
    ConfigTemplates,        # Configuration templates
    TopologyTemplates       # Topology templates
)

# Or run directly:
python -m gns3_mcp.server
```

## 🚀 Usage Patterns

### As MCP Server (Primary Use)
```bash
# Via Gemini CLI
gemini "List all GNS3 projects"
gemini "Create project and add 3 routers"
```

### As Python Package
```python
from gns3_mcp import GNS3APIClient, GNS3Config

config = GNS3Config(base_url="http://localhost:3080")
client = GNS3APIClient(config)
projects = await client.list_projects()
```

### Direct Execution
```bash
# Run the server directly
python -m gns3_mcp.server

# Or use launchers
./run.bat  # Windows
./run.sh   # Linux/Mac
```

## 📦 Installation

### For End Users
```bash
git clone https://github.com/wael-rd/gns3-mcp-server.git
cd gns3-mcp-server
pip install -e .
```

### For Development
```bash
git clone https://github.com/wael-rd/gns3-mcp-server.git
cd gns3-mcp-server
pip install -e ".[dev]"
```

## 🏛️ Architecture

### Modular Design
- **Separation of Concerns**: API client, Telnet client, config templates, MCP server
- **Clean Interfaces**: Each module has clear responsibilities
- **Extensible**: Easy to add new tools or templates

### Package Structure
- **Proper Python Package**: Installable via pip
- **Type Hints**: Full type annotations throughout
- **Documentation**: Comprehensive docstrings

### Production Ready
- **Error Handling**: Robust error catching and reporting
- **Async Support**: Fully async with httpx and FastMCP
- **Logging**: Structured logging throughout
- **Configuration**: Environment-based configuration

## 📝 Development Workflow

1. **Clone Repository**: `git clone ...`
2. **Install Dependencies**: `pip install -e ".[dev]"`
3. **Make Changes**: Edit files in `src/gns3_mcp/`
4. **Test**: Run examples or use Gemini CLI
5. **Document**: Update relevant docs in `docs/`
6. **Commit**: Follow conventional commits
7. **Push**: Push to GitHub

## 🎓 Learning Resources

- **Start Here**: [docs/START_HERE.md](docs/START_HERE.md)
- **Tool Reference**: [docs/TOOL_REFERENCE.md](docs/TOOL_REFERENCE.md)
- **Examples**: [examples/example_complete_network.py](examples/example_complete_network.py)
- **Migration**: [docs/MIGRATION.md](docs/MIGRATION.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Update documentation
6. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) file

## 🔗 Links

- **GitHub**: https://github.com/wael-rd/gns3-mcp-server
- **Issues**: https://github.com/wael-rd/gns3-mcp-server/issues
- **GNS3**: https://gns3.com/
- **MCP Protocol**: https://modelcontextprotocol.io/
- **FastMCP**: https://github.com/anselmholden/fastmcp

---

**Version**: 2.0.0  
**Status**: Production Ready ✅  
**Last Updated**: January 6, 2026
