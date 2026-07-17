"""Unit tests for console output capture, cleaning, pager, cap, and ready login."""

from __future__ import annotations

import socket
import unittest
from unittest.mock import patch

from gns3_mcp.telnet_client import (
    TelnetClient,
    apply_response_cap,
    clean_console_text,
    looks_like_shell_prompt,
    prompt_complete,
)


class CleanAndPromptTests(unittest.TestCase):
    def test_clean_normalizes_crlf_and_controls(self):
        raw = "line1\r\nline2\rline3\x00\x07\tkeep\n"
        out = clean_console_text(raw)
        self.assertEqual(out, "line1\nline2\nline3\tkeep\n")

    def test_interior_hash_not_prompt(self):
        body = "!\n! Last configuration change at 12:00\ninterface Gi0/0\n ip address 1.1.1.1 255.255.255.0\n"
        self.assertFalse(prompt_complete(body + "comment with # inside\n"))
        self.assertTrue(prompt_complete(body + "R1#"))

    def test_looks_like_shell_prompt(self):
        self.assertTrue(looks_like_shell_prompt("R1#"))
        self.assertTrue(looks_like_shell_prompt("R1(config-if)#"))
        self.assertTrue(looks_like_shell_prompt("user@host$"))
        self.assertFalse(looks_like_shell_prompt("Password:"))
        self.assertFalse(looks_like_shell_prompt("--More--"))
        self.assertFalse(looks_like_shell_prompt("! comment #"))

    def test_apply_cap_marks_truncated(self):
        text = "a" * 200
        clipped, meta = apply_response_cap(text, max_bytes=50)
        self.assertTrue(meta["truncated"])
        self.assertLessEqual(len(clipped.encode("utf-8")), 50)
        self.assertEqual(meta["response_bytes_raw"], 200)


class FakeSock:
    def __init__(self, scripted_reads):
        self.scripted = list(scripted_reads)
        self.sent = []

    def send(self, data: bytes):
        self.sent.append(data)
        return len(data)

    def recv(self, _n: int) -> bytes:
        if not self.scripted:
            raise socket.timeout("no more data")
        item = self.scripted.pop(0)
        if isinstance(item, Exception):
            raise item
        if item is None:
            raise socket.timeout("idle")
        return item if isinstance(item, bytes) else item.encode()

    def settimeout(self, _t):
        pass

    def close(self):
        pass


class TelnetOutputTests(unittest.TestCase):
    def _client(self, reads, timeout: float = 2.0) -> TelnetClient:
        c = TelnetClient("127.0.0.1", 5000, timeout=timeout)
        c.sock = FakeSock(reads)
        c.connected = True
        return c

    def test_read_until_does_not_stop_on_interior_hash(self):
        # Chunks with interior '#' then final prompt.
        c = self._client(
            [
                "!\n! config # note\ninterface Gi0/0\n",
                " description has > and #\n",
                "R1#",
            ]
        )
        out = c.read_until(["#", ">"], timeout=2.0)
        self.assertIn("config # note", out)
        self.assertTrue(out.rstrip().endswith("R1#") or "R1#" in out.splitlines()[-1])

    def test_multi_chunk_assembly(self):
        c = self._client(["part-one-", "part-two-", "\nR1>"])
        out = c.read_until([">", "#"], timeout=2.0)
        self.assertIn("part-one-part-two-", out)
        self.assertIn("R1>", out)

    def test_pager_is_advanced(self):
        c = self._client(
            [
                "line1\n--More--",
                "line2\nR1#",
            ]
        )
        out = c.read_until(["#"], timeout=2.0)
        # space sent to advance pager
        self.assertTrue(any(s == b" " for s in c.sock.sent))
        self.assertIn("line1", out)
        self.assertIn("line2", out)

    def test_send_cmd_cleans_and_caps(self):
        c = self._client(["show me\r\nvalue\r\nR1#"])
        c.max_response_bytes = 512 * 1024
        text, meta = c.send_cmd("show version", wait_for=["#"], return_meta=True)
        self.assertNotIn("\r", text)
        self.assertIn("value", text)
        self.assertFalse(meta["truncated"])

    def test_send_cmd_truncated_meta(self):
        big = ("x" * 100) + "\nR1#"
        c = self._client([big])
        c.max_response_bytes = 40
        text, meta = c.send_cmd("show", wait_for=["#"], return_meta=True)
        self.assertTrue(meta["truncated"])
        self.assertLessEqual(len(text.encode("utf-8")), 40)


class TelnetLoginReadyTests(unittest.TestCase):
    def _client_with_read_until(self, side_effect):
        c = TelnetClient("127.0.0.1", 5000, timeout=1.0)
        c.sock = FakeSock([])
        c.connected = True
        return c, side_effect

    def test_delayed_login_prompt_succeeds(self):
        c = TelnetClient("127.0.0.1", 5000, timeout=1.0)
        c.sock = FakeSock([])
        c.connected = True
        # First probes empty/not ready; then username/password/shell.
        reads = ["", "", "Username:", "Password:", "R1#"]
        with patch.object(c, "read_until", side_effect=reads), patch(
            "gns3_mcp.telnet_client.time.sleep", return_value=None
        ):
            ok = c.login("admin", "secret", ready_timeout=5.0, settle=0.0)
        self.assertTrue(ok)
        sent = b"".join(c.sock.sent)
        self.assertIn(b"admin\r", sent)
        self.assertIn(b"secret\r", sent)

    def test_auth_failure_no_endless_retry(self):
        c = TelnetClient("127.0.0.1", 5000, timeout=1.0)
        c.sock = FakeSock([])
        c.connected = True
        # Always Username -> Password -> Username after password.
        seq = ["Username:", "Password:", "Username:"]
        with patch.object(c, "read_until", side_effect=seq * 3), patch(
            "gns3_mcp.telnet_client.time.sleep", return_value=None
        ):
            ok = c.login("admin", "bad", ready_timeout=5.0, settle=0.0)
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
