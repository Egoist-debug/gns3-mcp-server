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
    split_at_first_prompt,
)


class CleanAndPromptTests(unittest.TestCase):
    def test_clean_normalizes_crlf_and_controls(self):
        raw = "line1\r\nline2\rline3\x00\x07\tkeep\n"
        out = clean_console_text(raw)
        self.assertEqual(out, "line1\nline2\nline3\tkeep\n")

    def test_clean_strips_ansi_color_sequences(self):
        raw = "\x1b[01;36mcolored\x1b[0m text"
        self.assertEqual(clean_console_text(raw), "colored text")

    def test_clean_strips_ansi_and_osc_without_residue(self):
        raw = (
            "\x1b[1;32mOK\x1b[0m "
            "\x1b[?1h\x1b=\x1b[H\x1b[2Jclear "
            "\x1b]0;title\x07"
            "R1# \x1b[7m--More--\x1b[m"
        )
        out = clean_console_text(raw)
        self.assertEqual(out, "OK clear R1# ")
        self.assertNotIn("[01", out)
        self.assertNotIn("[0m", out)
        self.assertNotIn("[7m", out)
        self.assertNotIn("]0;title", out)

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

    def test_split_at_first_prompt_keeps_remainder(self):
        buf = "show ver\nCisco IOS\nR1#\nshow ip\nEth0 up\nR1#"
        split = split_at_first_prompt(buf, wait_for=["#", ">"])
        self.assertIsNotNone(split)
        complete, remainder = split
        self.assertIn("Cisco IOS", complete)
        self.assertTrue(complete.rstrip().endswith("R1#"))
        self.assertNotIn("Eth0", complete)
        self.assertIn("show ip", remainder)
        self.assertIn("Eth0", remainder)

    def test_prompt_complete_true_on_first_of_many(self):
        buf = "body1\nR1#\nbody2\nR1#"
        self.assertTrue(prompt_complete(buf, wait_for=["#"]))

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



class TelnetMultiCommandPairingTests(unittest.TestCase):
    """Command/response pairing: residual buffer + first-prompt framing."""

    def _client(self, reads, timeout: float = 2.0) -> TelnetClient:
        c = TelnetClient("127.0.0.1", 5000, timeout=timeout)
        c.sock = FakeSock(reads)
        c.connected = True
        return c

    def test_residual_prompt_does_not_shift_pairing(self):
        # Leftover prompt after login/boot must not become cmd1's response.
        c = self._client(
            [
                "R1#",
                "show ver\nCisco IOS Software\nR1#",
                "show ip\nEth0 is up\nR1#",
            ]
        )
        r1, _ = c.send_cmd("show ver", wait_for=["#", ">"], return_meta=True)
        r2, _ = c.send_cmd("show ip", wait_for=["#", ">"], return_meta=True)
        self.assertIn("Cisco IOS", r1)
        self.assertNotIn("Eth0", r1)
        self.assertIn("Eth0", r2)
        self.assertNotIn("Cisco IOS", r2)

    def test_multi_prompt_chunk_split_across_commands(self):
        # One socket chunk holds two full command cycles.
        c = self._client(
            [
                "show ver\nCisco IOS\nR1#\nshow ip\nEth0 up\nR1#",
            ]
        )
        r1, _ = c.send_cmd("show ver", wait_for=["#", ">"], return_meta=True)
        r2, _ = c.send_cmd("show ip", wait_for=["#", ">"], return_meta=True)
        self.assertIn("Cisco IOS", r1)
        self.assertTrue(r1.rstrip().endswith("R1#") or "R1#" in r1.splitlines()[-1])
        self.assertNotIn("Eth0", r1)
        self.assertIn("Eth0", r2)
        self.assertNotIn("Cisco IOS", r2)

    def test_three_command_sequence_stays_ordered(self):
        c = self._client(
            [
                "cmd-a\nAAA\nR1#",
                "cmd-b\nBBB\nR1#",
                "cmd-c\nCCC\nR1#",
            ]
        )
        ra, _ = c.send_cmd("a", wait_for=["#"], return_meta=True)
        rb, _ = c.send_cmd("b", wait_for=["#"], return_meta=True)
        rc, _ = c.send_cmd("c", wait_for=["#"], return_meta=True)
        self.assertIn("AAA", ra)
        self.assertIn("BBB", rb)
        self.assertIn("CCC", rc)
        self.assertNotIn("BBB", ra)
        self.assertNotIn("CCC", ra)
        self.assertNotIn("AAA", rb)
        self.assertNotIn("CCC", rb)
        self.assertNotIn("AAA", rc)
        self.assertNotIn("BBB", rc)

    def test_read_until_leaves_remainder_in_residual(self):
        c = self._client(
            [
                "line1\nR1#\nline2\nR2#",
            ]
        )
        first = c.read_until(["#", ">"], timeout=2.0)
        self.assertIn("line1", first)
        self.assertNotIn("line2", first)
        self.assertIn("line2", c._rx_buf)


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
