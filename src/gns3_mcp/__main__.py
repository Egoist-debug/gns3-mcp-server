"""
Main entry point for the GNS3 MCP Server.
This module is executed when running: python -m gns3_mcp.server
"""

from .server import mcp

if __name__ == "__main__":
    # Start the FastMCP server
    mcp.run()
