"""SSH client helpers for guest VM command execution."""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List, Optional

import asyncssh

logger = logging.getLogger(__name__)

_IPV4_RE = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
)


def resolve_ssh_credentials(
    ssh_username: Optional[str] = None,
    ssh_password: Optional[str] = None,
) -> tuple[Optional[str], Optional[str]]:
    user = ssh_username if ssh_username is not None else os.environ.get("GNS3_SSH_USER")
    password = ssh_password if ssh_password is not None else os.environ.get("GNS3_SSH_PASSWORD")
    return user, password


def resolve_host_key_policy(policy: Optional[str] = None) -> str:
    raw = policy if policy is not None else os.environ.get("GNS3_SSH_HOST_KEY_POLICY")
    value = (raw or "accept_new").strip().lower()
    if value not in {"accept_new", "strict", "warn"}:
        return "accept_new"
    return value


def _known_hosts_for_policy(policy: str):
    """Map policy name to asyncssh known_hosts argument.

    asyncssh: ``None`` = default known_hosts files; ``()`` = disable checking.
    """
    if policy == "strict":
        return None  # use system/user known_hosts
    # accept_new / warn: lab default — do not enforce known_hosts
    if policy == "warn":
        logger.warning("SSH host_key_policy=warn: host key checking disabled (lab mode)")
    return ()


def extract_ips_from_node(node: Dict[str, Any]) -> List[str]:
    """Best-effort IPv4 harvest from a GNS3 node document."""
    found: List[str] = []
    seen = set()

    def add(text: str) -> None:
        for m in _IPV4_RE.findall(text or ""):
            if m.startswith("127.") or m.startswith("0."):
                continue
            if m not in seen:
                seen.add(m)
                found.append(m)

    props = node.get("properties") or {}
    if isinstance(props, dict):
        for key, val in props.items():
            if val is None:
                continue
            if isinstance(val, (str, int, float)):
                add(str(val))
            elif isinstance(val, dict):
                add(str(val))
            elif isinstance(val, list):
                for item in val:
                    add(str(item))

    for key in ("name", "console_host", "node_type"):
        if key in node and node[key] is not None:
            # Prefer not to treat console_host as guest IP unless it looks non-loopback;
            # still collect via add() filters.
            if key == "console_host":
                add(str(node[key]))

    # Nested common keys
    for key in ("ip_address", "ip", "management_ip", "hostname"):
        if key in node and node[key]:
            add(str(node[key]))
        if isinstance(props, dict) and props.get(key):
            add(str(props[key]))

    return found


async def exec_commands(
    host: str,
    commands: List[str],
    *,
    port: int = 22,
    username: Optional[str] = None,
    password: Optional[str] = None,
    stop_on_error: bool = True,
    host_key_policy: str = "accept_new",
    connect_timeout: float = 30.0,
) -> Dict[str, Any]:
    """Run commands over SSH on one connection.

    Passwords are never included in the returned structure.
    """
    if not host:
        return {"status": "error", "error": "host is required"}
    if not username:
        return {"status": "error", "error": "ssh_username is required (or set GNS3_SSH_USER)"}
    if password is None:
        return {"status": "error", "error": "ssh_password is required (or set GNS3_SSH_PASSWORD)"}
    if not commands:
        return {"status": "error", "error": "commands must be a non-empty list"}

    policy = resolve_host_key_policy(host_key_policy)
    known_hosts = _known_hosts_for_policy(policy)
    results: List[Dict[str, Any]] = []

    try:
        conn_kwargs: Dict[str, Any] = {
            "host": host,
            "port": port,
            "username": username,
            "password": password,
            "known_hosts": known_hosts,
            "login_timeout": connect_timeout,
        }
        async with asyncssh.connect(**conn_kwargs) as conn:
            for cmd in commands:
                try:
                    result = await conn.run(cmd, check=False)
                    exit_code = int(result.exit_status if result.exit_status is not None else -1)
                    entry = {
                        "command": cmd,
                        "stdout": result.stdout or "",
                        "stderr": result.stderr or "",
                        "exit_code": exit_code,
                    }
                    results.append(entry)
                    if stop_on_error and exit_code != 0:
                        return {
                            "status": "error",
                            "host": host,
                            "authenticated": True,
                            "username": username,
                            "results": results,
                            "error": f"Command failed with exit_code={exit_code}: {cmd}",
                        }
                except Exception as e:
                    results.append(
                        {
                            "command": cmd,
                            "stdout": "",
                            "stderr": str(e),
                            "exit_code": -1,
                        }
                    )
                    if stop_on_error:
                        return {
                            "status": "error",
                            "host": host,
                            "authenticated": True,
                            "username": username,
                            "results": results,
                            "error": f"Command execution failed: {e}",
                        }
    except asyncssh.PermissionDenied:
        logger.error("SSH authentication failed for user %s@%s", username, host)
        return {
            "status": "error",
            "host": host,
            "authenticated": False,
            "username": username,
            "results": results,
            "error": "SSH authentication failed",
        }
    except Exception as e:
        logger.error("SSH connection failed to %s: %s", host, e)
        return {
            "status": "error",
            "host": host,
            "authenticated": False,
            "username": username,
            "results": results,
            "error": f"SSH connection failed: {e}",
        }

    return {
        "status": "success",
        "host": host,
        "authenticated": True,
        "username": username,
        "results": results,
    }
