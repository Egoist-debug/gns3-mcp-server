#!/usr/bin/env bash
# Oh My Pi / MCP stdio launcher for gns3-mcp-server
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
LOG="${GNS3_MCP_LAUNCH_LOG:-/tmp/gns3-mcp-omp-launch.log}"
PY="${ROOT}/.venv/bin/python"

{
  echo "$(date -Is) launcher pid=$$ root=$ROOT py=$PY"
  echo "  GNS3_SERVER_URL=${GNS3_SERVER_URL:-}"
  echo "  GNS3_USERNAME=${GNS3_USERNAME:-}"
  echo "  has_password=$([ -n "${GNS3_PASSWORD:-}" ] && echo yes || echo no)"
  ls -la "$PY" 2>&1 || true
} >>"$LOG" 2>&1

if [[ ! -x "$PY" ]]; then
  echo "gns3-mcp: missing venv python at $PY" >&2
  echo "Run: cd $ROOT && uv sync" >&2
  exit 127
fi

export PYTHONUNBUFFERED=1
export FASTMCP_SHOW_CLI_BANNER=false
export GNS3_MCP_LAUNCH_LOG="$LOG"

# Ensure local package is importable even if env is sparse
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:$PYTHONPATH}"

exec "$PY" "$ROOT/omp_stdio_entry.py"
