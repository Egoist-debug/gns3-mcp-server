"""
GNS3 MCP Server - Model Context Protocol server for GNS3 network simulation.

This package provides a comprehensive MCP server that allows AI assistants
to interact with GNS3 through natural language commands.

Version: 2.0.0
Author: GNS3 MCP Server Team
License: MIT
"""

__version__ = "2.0.0"
__author__ = "GNS3 MCP Server Team"
__license__ = "MIT"

from .server import mcp
from .gns3_client import GNS3APIClient, GNS3Config
from .telnet_client import TelnetClient
from .config_templates import ConfigTemplates, TopologyTemplates

__all__ = [
    "mcp",
    "GNS3APIClient",
    "GNS3Config",
    "TelnetClient",
    "ConfigTemplates",
    "TopologyTemplates",
]
