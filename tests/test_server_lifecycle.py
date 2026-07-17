"""Unit tests for GNS3 server lifecycle (probe/auto-start)."""

from __future__ import annotations

import asyncio
import os
import unittest
from unittest.mock import AsyncMock, patch

from gns3_mcp.server_lifecycle import (
    build_start_command,
    clear_healthy_cache,
    ensure_gns3_server,
    is_local_server_url,
    normalize_server_url,
)


class LocalUrlTests(unittest.TestCase):
    def test_local_hosts(self):
        self.assertTrue(is_local_server_url("http://localhost:3080"))
        self.assertTrue(is_local_server_url("http://127.0.0.1:3080"))
        self.assertTrue(is_local_server_url("http://[::1]:3080"))
        self.assertFalse(is_local_server_url("http://192.168.1.10:3080"))
        self.assertFalse(is_local_server_url("http://gns3.lab.example:3080"))

    def test_normalize(self):
        self.assertEqual(normalize_server_url("http://localhost:3080/"), "http://localhost:3080")


class BuildStartCommandTests(unittest.TestCase):
    def test_default_injects_host_port(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GNS3_SERVER_START_CMD", None)
            argv = build_start_command("http://127.0.0.1:3081")
            self.assertEqual(argv[:1], ["gns3server"])
            self.assertIn("--host", argv)
            self.assertIn("127.0.0.1", argv)
            self.assertIn("--port", argv)
            self.assertIn("3081", argv)

    def test_custom_cmd_not_rewritten(self):
        with patch.dict(os.environ, {"GNS3_SERVER_START_CMD": "mywrapper --foo"}):
            argv = build_start_command("http://127.0.0.1:3081")
            self.assertEqual(argv, ["mywrapper", "--foo"])


class EnsureServerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        clear_healthy_cache()
        os.environ.pop("GNS3_SERVER_START_CMD", None)

    async def test_already_running_no_start(self):
        with patch(
            "gns3_mcp.server_lifecycle.probe_server",
            new=AsyncMock(return_value=(True, {"version": "2.2"})),
        ) as probe, patch(
            "gns3_mcp.server_lifecycle._spawn_server",
            new=AsyncMock(),
        ) as spawn:
            result = await ensure_gns3_server("http://127.0.0.1:3080", force=True)
            self.assertEqual(result["status"], "success")
            self.assertTrue(result["already_running"])
            self.assertFalse(result["started"])
            spawn.assert_not_called()
            self.assertGreaterEqual(probe.await_count, 1)

    async def test_cache_skips_probe(self):
        with patch(
            "gns3_mcp.server_lifecycle.probe_server",
            new=AsyncMock(return_value=(True, {"version": "2.2"})),
        ) as probe:
            r1 = await ensure_gns3_server("http://127.0.0.1:3080", force=True)
            self.assertEqual(r1["status"], "success")
            r2 = await ensure_gns3_server("http://127.0.0.1:3080", force=False)
            self.assertEqual(r2["status"], "success")
            self.assertTrue(r2["already_running"])
            # second call uses cache → no extra probe
            self.assertEqual(probe.await_count, 1)

    async def test_remote_unreachable_no_spawn(self):
        with patch(
            "gns3_mcp.server_lifecycle.probe_server",
            new=AsyncMock(return_value=(False, "connection refused")),
        ), patch(
            "gns3_mcp.server_lifecycle._spawn_server",
            new=AsyncMock(),
        ) as spawn:
            result = await ensure_gns3_server("http://10.0.0.5:3080", force=True)
            self.assertEqual(result["status"], "error")
            self.assertIn("Remote", result["error"])
            spawn.assert_not_called()

    async def test_local_down_starts_and_waits(self):
        probes = [
            (False, "down"),
            (False, "down"),
            (True, {"version": "2.2"}),
        ]

        async def probe_side_effect(*_a, **_k):
            return probes.pop(0) if probes else (True, {"version": "2.2"})

        with patch(
            "gns3_mcp.server_lifecycle.probe_server",
            new=AsyncMock(side_effect=probe_side_effect),
        ), patch(
            "gns3_mcp.server_lifecycle._spawn_server",
            new=AsyncMock(return_value=(12345, "")),
        ) as spawn, patch(
            "gns3_mcp.server_lifecycle._start_timeout",
            return_value=5.0,
        ), patch(
            "gns3_mcp.server_lifecycle.asyncio.sleep",
            new=AsyncMock(),
        ):
            result = await ensure_gns3_server("http://127.0.0.1:3080", force=True)
            self.assertEqual(result["status"], "success")
            self.assertTrue(result["started"])
            self.assertFalse(result["already_running"])
            spawn.assert_awaited_once()

    async def test_http_401_counts_as_reachable(self):
        with patch(
            "gns3_mcp.server_lifecycle.probe_server",
            new=AsyncMock(
                return_value=(True, {"reachable": True, "http_status": 401, "detail": ""})
            ),
        ), patch(
            "gns3_mcp.server_lifecycle._spawn_server",
            new=AsyncMock(),
        ) as spawn:
            result = await ensure_gns3_server("http://127.0.0.1:3080", force=True)
            self.assertEqual(result["status"], "success")
            self.assertTrue(result["already_running"])
            spawn.assert_not_called()


if __name__ == "__main__":
    unittest.main()
