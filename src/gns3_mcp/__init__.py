"""
GNS3 MCP Server - Model Context Protocol server for GNS3 network simulation.

Version: 2.0.0
"""

from __future__ import annotations

__version__ = "2.0.0"
__author__ = "GNS3 MCP Server Team"
__license__ = "MIT"

# Lazy re-exports: avoid importing the FastMCP server graph at package import
# time (prevents double-import warnings with `python -m gns3_mcp.server`).

__all__ = [
    "mcp",
    "GNS3APIClient",
    "GNS3Config",
    "TelnetClient",
    "ConfigTemplates",
    "TopologyTemplates",
]


def __getattr__(name: str):
    if name == "mcp":
        from .server import mcp

        return mcp
    if name in {"GNS3APIClient", "GNS3Config"}:
        from . import gns3_client

        return getattr(gns3_client, name)
    if name == "TelnetClient":
        from .telnet_client import TelnetClient

        return TelnetClient
    if name in {"ConfigTemplates", "TopologyTemplates"}:
        from . import config_templates

        return getattr(config_templates, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
