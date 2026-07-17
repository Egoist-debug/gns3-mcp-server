"""Unit tests for SSH guest exec helper."""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from gns3_mcp import ssh_client


class ExtractIpTests(unittest.TestCase):
    def test_from_properties(self):
        node = {
            "name": "vm1",
            "properties": {"ip_address": "10.1.1.50", "adapters": 1},
            "console_host": "127.0.0.1",
        }
        ips = ssh_client.extract_ips_from_node(node)
        self.assertIn("10.1.1.50", ips)
        self.assertNotIn("127.0.0.1", ips)


class HostKeyPolicyTests(unittest.TestCase):
    def test_accept_new_disables_known_hosts(self):
        # asyncssh: () disables checking; None uses default files
        self.assertEqual(ssh_client._known_hosts_for_policy("accept_new"), ())

    def test_strict_uses_default_known_hosts(self):
        self.assertIsNone(ssh_client._known_hosts_for_policy("strict"))


class ExecCommandsTests(unittest.IsolatedAsyncioTestCase):
    async def test_requires_host_and_creds(self):
        r = await ssh_client.exec_commands("", ["id"], username="u", password="p")
        self.assertEqual(r["status"], "error")
        r = await ssh_client.exec_commands("10.0.0.1", ["id"], username=None, password="p")
        self.assertEqual(r["status"], "error")

    async def test_runs_commands_stop_on_error(self):
        conn = MagicMock()
        result_ok = MagicMock(stdout="ok\n", stderr="", exit_status=0)
        result_bad = MagicMock(stdout="", stderr="fail", exit_status=1)
        conn.run = AsyncMock(side_effect=[result_ok, result_bad])
        conn.__aenter__ = AsyncMock(return_value=conn)
        conn.__aexit__ = AsyncMock(return_value=None)

        with patch("gns3_mcp.ssh_client.asyncssh.connect", return_value=conn):
            out = await ssh_client.exec_commands(
                "10.0.0.1",
                ["echo ok", "false", "echo never"],
                username="user",
                password="pass",
                stop_on_error=True,
            )
        self.assertEqual(out["status"], "error")
        self.assertTrue(out["authenticated"])
        self.assertEqual(len(out["results"]), 2)
        # password must not appear in payload
        self.assertNotIn("pass", str(out))

    async def test_success_all_commands(self):
        conn = MagicMock()
        conn.run = AsyncMock(
            side_effect=[
                MagicMock(stdout="a", stderr="", exit_status=0),
                MagicMock(stdout="b", stderr="", exit_status=0),
            ]
        )
        conn.__aenter__ = AsyncMock(return_value=conn)
        conn.__aexit__ = AsyncMock(return_value=None)

        with patch("gns3_mcp.ssh_client.asyncssh.connect", return_value=conn):
            out = await ssh_client.exec_commands(
                "10.0.0.1",
                ["a", "b"],
                username="user",
                password="pass",
            )
        self.assertEqual(out["status"], "success")
        self.assertEqual(len(out["results"]), 2)
        self.assertEqual(out["username"], "user")


if __name__ == "__main__":
    unittest.main()
