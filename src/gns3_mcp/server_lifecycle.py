"""GNS3 server probe / auto-start lifecycle helpers."""

from __future__ import annotations

import asyncio
import logging
import os
import shlex
import time
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

import httpx

from .gns3_client import GNS3Config, _env_bool

logger = logging.getLogger(__name__)

# Keep a single default owner: GNS3Config.server_url Field default.
DEFAULT_SERVER_URL = "http://localhost:3080"
DEFAULT_START_CMD = "gns3server"
DEFAULT_START_TIMEOUT = 30.0
DEFAULT_HEALTHY_CACHE_SECONDS = 30.0
DEFAULT_PROBE_TIMEOUT = 3.0

_lock = asyncio.Lock()
# url -> (monotonic_ts, server_info)
_healthy_cache: Dict[str, Tuple[float, Any]] = {}


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def normalize_server_url(server_url: Optional[str]) -> str:
    """Normalize server URL; share default/env fallback with GNS3Config."""
    if server_url is not None and str(server_url).strip():
        return str(server_url).strip().rstrip("/")
    # GNS3Config owns GNS3_SERVER_URL + default base URL
    return GNS3Config.from_env().server_url.rstrip("/")


def is_local_server_url(server_url: str) -> bool:
    """Return True if server_url targets this machine's loopback interface."""
    parsed = urlparse(server_url if "://" in server_url else f"http://{server_url}")
    host = (parsed.hostname or "").lower()
    if not host:
        return True
    return host in {"localhost", "127.0.0.1", "::1"}


def _parse_host_port(server_url: str) -> Tuple[str, int]:
    parsed = urlparse(server_url if "://" in server_url else f"http://{server_url}")
    host = parsed.hostname or "127.0.0.1"
    if host == "localhost":
        host = "127.0.0.1"
    port = parsed.port or 3080
    return host, port


def build_start_command(server_url: str) -> list[str]:
    """Build argv for starting gns3server.

    Custom GNS3_SERVER_START_CMD is never rewritten.
    Bare default ``gns3server`` gets --host/--port from server_url.
    """
    raw = os.environ.get("GNS3_SERVER_START_CMD")
    custom = raw is not None and raw.strip() != ""
    if custom:
        return shlex.split(raw.strip())

    argv = shlex.split(DEFAULT_START_CMD)
    host, port = _parse_host_port(server_url)
    if len(argv) == 1 and os.path.basename(argv[0]) == DEFAULT_START_CMD:
        argv.extend(["--host", host, "--port", str(port)])
    return argv


async def probe_server(
    server_url: str,
    *,
    username: Optional[str] = None,
    password: Optional[str] = None,
    timeout: float = DEFAULT_PROBE_TIMEOUT,
) -> Tuple[bool, Any]:
    """Probe GNS3 ``/v2/version``.

    Returns (ok, payload_or_error_str).

    Any HTTP response (including 401/403) means the process is up and listening.
    Connection errors mean the server is down.
    """
    base = normalize_server_url(server_url)
    url = f"{base}/v2/version"
    auth = None
    if username and password:
        auth = (username, password)
    try:
        async with httpx.AsyncClient(
            timeout=timeout, verify=_env_bool("GNS3_VERIFY_SSL", True)
        ) as client:
            resp = await client.get(url, auth=auth)
            if resp.status_code == 200:
                try:
                    return True, resp.json()
                except Exception:
                    return True, {"raw": resp.text}
            # Server is reachable but rejected the request (auth, etc.)
            return True, {
                "reachable": True,
                "http_status": resp.status_code,
                "detail": (resp.text or "")[:200],
            }
    except Exception as e:
        return False, str(e)


def _cache_ttl() -> float:
    return _env_float("GNS3_SERVER_HEALTHY_CACHE_SECONDS", DEFAULT_HEALTHY_CACHE_SECONDS)


def _start_timeout() -> float:
    return _env_float("GNS3_SERVER_START_TIMEOUT", DEFAULT_START_TIMEOUT)


def _cache_get(server_url: str) -> Optional[Any]:
    key = normalize_server_url(server_url)
    entry = _healthy_cache.get(key)
    if not entry:
        return None
    ts, info = entry
    if time.monotonic() - ts <= _cache_ttl():
        return info
    _healthy_cache.pop(key, None)
    return None


def _cache_set(server_url: str, info: Any) -> None:
    _healthy_cache[normalize_server_url(server_url)] = (time.monotonic(), info)


def clear_healthy_cache() -> None:
    """Test helper: drop the process-wide healthy cache."""
    _healthy_cache.clear()


async def _spawn_server(argv: list[str]) -> Tuple[Optional[int], str]:
    """Spawn detached gns3server. Returns (pid_or_none, start_note).

    Stdio is fully detached (DEVNULL) so a chatty child cannot fill a pipe
    buffer and block while we wait for health.
    """
    logger.warning("Starting GNS3 server: %s", " ".join(argv))
    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
            stdin=asyncio.subprocess.DEVNULL,
            start_new_session=True,
        )
    except FileNotFoundError as e:
        return None, str(e)
    except Exception as e:
        return None, str(e)

    # Detached: do not wait on stdio. Caller polls health separately.
    return proc.pid, f"spawned pid={proc.pid}"


async def ensure_gns3_server(
    server_url: Optional[str] = None,
    *,
    username: Optional[str] = None,
    password: Optional[str] = None,
    force: bool = False,
) -> Dict[str, Any]:
    """Ensure GNS3 REST API is reachable; auto-start on localhost if needed.

    Returns a structured dict suitable for the ``gns3_ensure_server`` tool.
    """
    url = normalize_server_url(server_url)
    start_timeout = _start_timeout()
    t0 = time.monotonic()

    async with _lock:
        if not force:
            cached = _cache_get(url)
            if cached is not None:
                return {
                    "status": "success",
                    "already_running": True,
                    "started": False,
                    "server_url": url,
                    "server_info": cached,
                    "start_command": None,
                    "wait_seconds": round(time.monotonic() - t0, 3),
                }

        ok, payload = await probe_server(url, username=username, password=password)
        if ok:
            _cache_set(url, payload)
            return {
                "status": "success",
                "already_running": True,
                "started": False,
                "server_url": url,
                "server_info": payload,
                "start_command": None,
                "wait_seconds": round(time.monotonic() - t0, 3),
            }

        if not is_local_server_url(url):
            return {
                "status": "error",
                "already_running": False,
                "started": False,
                "server_url": url,
                "server_info": None,
                "start_command": None,
                "wait_seconds": round(time.monotonic() - t0, 3),
                "error": (
                    f"GNS3 server unreachable at {url} ({payload}). "
                    "Remote URLs are not auto-started; start the server on that host."
                ),
            }

        argv = build_start_command(url)
        start_cmd_str = " ".join(shlex.quote(a) for a in argv)
        pid, stderr_tail = await _spawn_server(argv)
        if pid is None:
            return {
                "status": "error",
                "already_running": False,
                "started": False,
                "server_url": url,
                "server_info": None,
                "start_command": start_cmd_str,
                "wait_seconds": round(time.monotonic() - t0, 3),
                "error": f"Failed to spawn GNS3 server: {stderr_tail}",
            }

        deadline = time.monotonic() + start_timeout
        last_err = payload
        while time.monotonic() < deadline:
            ok, payload = await probe_server(url, username=username, password=password)
            if ok:
                _cache_set(url, payload)
                return {
                    "status": "success",
                    "already_running": False,
                    "started": True,
                    "server_url": url,
                    "server_info": payload,
                    "start_command": start_cmd_str,
                    "wait_seconds": round(time.monotonic() - t0, 3),
                }
            last_err = payload
            await asyncio.sleep(0.5)

        err_bits = [f"Timed out after {start_timeout}s waiting for GNS3 at {url}: {last_err}"]
        if stderr_tail:
            err_bits.append(f"start stderr: {stderr_tail[:500]}")
        return {
            "status": "error",
            "already_running": False,
            "started": True,
            "server_url": url,
            "server_info": None,
            "start_command": start_cmd_str,
            "wait_seconds": round(time.monotonic() - t0, 3),
            "error": " ".join(err_bits),
        }
