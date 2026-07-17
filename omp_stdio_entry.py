#!/usr/bin/env python3
"""Quiet STDIO entrypoint for Oh My Pi / MCP clients.

Avoids FastMCP rich banner and noisy INFO logs that can confuse stdio clients.
Also writes a small launch breadcrumb for diagnosing spawn failures.
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Unbuffered stdio for MCP JSON-RPC
os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("FASTMCP_SHOW_CLI_BANNER", "false")

# Breadcrumb so we can confirm OMP actually launched the process
try:
    log_path = Path(os.environ.get("GNS3_MCP_LAUNCH_LOG", "/tmp/gns3-mcp-omp-launch.log"))
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(
            f"{datetime.now(timezone.utc).isoformat()} pid={os.getpid()} "
            f"argv={sys.argv!r} cwd={os.getcwd()!r} "
            f"url={os.environ.get('GNS3_SERVER_URL')!r} "
            f"user={os.environ.get('GNS3_USERNAME')!r}\n"
        )
except Exception:
    pass

# Quiet logging before importing FastMCP server
logging.basicConfig(
    level=logging.WARNING,
    stream=sys.stderr,
    format="%(levelname)s %(name)s: %(message)s",
)

# FastMCP / MCP SDK loggers are chatty on INFO
for _name in (
    "mcp",
    "mcp.server",
    "mcp.server.lowlevel",
    "mcp.server.lowlevel.server",
    "fastmcp",
    "httpx",
    "httpcore",
    "uvicorn",
    "asyncio",
):
    logging.getLogger(_name).setLevel(logging.WARNING)

from gns3_mcp.server import mcp  # noqa: E402

# Re-assert after import (server.basicConfig may reconfigure)
logging.getLogger().setLevel(logging.WARNING)
for _name in ("mcp", "mcp.server", "mcp.server.lowlevel.server", "fastmcp"):
    logging.getLogger(_name).setLevel(logging.ERROR)


if __name__ == "__main__":
    mcp.run(show_banner=False, transport="stdio")
