#!/usr/bin/env python3
"""
Telnet Client for GNS3 Console Access
Provides robust telnet connection to network device consoles.
"""

import logging
import socket
import time
from typing import List, Optional

logger = logging.getLogger(__name__)


class TelnetClient:
    """Enhanced Telnet client for GNS3 console interaction."""
    
    def __init__(self, host: str, port: int, timeout: float = 10.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock: Optional[socket.socket] = None
        self.connected = False

    def connect(self) -> bool:
        """Connect to the Telnet server."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(self.timeout)
            self.sock.connect((self.host, self.port))
            self.connected = True
            logger.info(f"Telnet connected to {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Telnet connection failed to {self.host}:{self.port}: {e}")
            self.connected = False
            return False

    def close(self):
        """Close the connection."""
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None
            self.connected = False
            logger.info(f"Telnet connection closed to {self.host}:{self.port}")

    def read_until(self, valid_end_chars: List[str], timeout: Optional[float] = None) -> str:
        """Read from socket until one of valid_end_chars is seen."""
        if not self.sock or not self.connected:
            return ""
        
        timeout = timeout or self.timeout
        start_time = time.time()
        buf = ""
        
        while time.time() - start_time < timeout:
            try:
                chunk = self.sock.recv(1024).decode('utf-8', errors='ignore')
                if not chunk:
                    time.sleep(0.1)
                    continue
                buf += chunk
                
                # Check for end chars in the buffer
                for end_char in valid_end_chars:
                    if end_char in buf:
                        return buf
            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"Read error: {e}")
                break
                
        return buf

    def read_available(self, wait_time: float = 0.5) -> str:
        """Read whatever is available in the buffer."""
        if not self.sock or not self.connected:
            return ""
        
        time.sleep(wait_time)
        try:
            self.sock.settimeout(0.5)
            data = self.sock.recv(4096).decode('utf-8', errors='ignore')
            self.sock.settimeout(self.timeout)
            return data
        except socket.timeout:
            return ""
        except Exception as e:
            logger.error(f"Read error: {e}")
            return ""

    def send_cmd(self, cmd: str, wait_for: Optional[List[str]] = None, wait_time: float = 0.5) -> str:
        """Send a command and wait for response."""
        if not self.sock or not self.connected:
            logger.error("Not connected")
            return ""
        
        try:
            full_cmd = f"{cmd}\r"
            self.sock.send(full_cmd.encode())
            logger.debug(f"Sent command: {cmd}")
            
            if wait_for:
                return self.read_until(wait_for)
            else:
                return self.read_available(wait_time)
                
        except Exception as e:
            logger.error(f"Send error: {e}")
            return ""

    def wait_for_boot(
        self,
        timeout: int = 120,
        additional_prompts: Optional[List[str]] = None,
        accept_login_prompts: bool = True,
    ) -> bool:
        """Wait for device to boot and show a prompt or login screen."""
        if not self.sock or not self.connected:
            return False

        start_time = time.time()
        # Common prompts across different device types
        prompts = [
            ">",
            "#",  # Cisco/IOS
            "PC1>",
            "PC2>",
            "PC3>",
            "PC4>",  # VPCS
            "Laptop1>",
            "Laptop2>",  # VPCS laptops
            "Router>",
            "Router#",  # Generic routers
            "Switch>",
            "Switch#",  # Generic switches
            "$",
            "%",  # Linux/Unix
            "[yes/no]:",
            "[confirm]",  # Cisco prompts
        ]
        login_markers = [
            "Username:",
            "username:",
            "login:",
            "Login:",
            "Password:",
            "password:",
        ]
        if accept_login_prompts:
            prompts = prompts + login_markers

        if additional_prompts:
            prompts.extend(additional_prompts)

        while time.time() - start_time < timeout:
            try:
                self.sock.send(b"\r")
                res = self.read_until(prompts, timeout=2)

                # Handle initial config dialog
                if "[yes/no]:" in res or "yes/no" in res.lower():
                    logger.info("Initial Config Dialog detected. Sending 'no'.")
                    self.sock.send(b"no\r")
                    time.sleep(5)
                    continue

                # Handle confirm prompts
                if "[confirm]" in res:
                    logger.info("Confirm prompt detected. Sending enter.")
                    self.sock.send(b"\r")
                    time.sleep(2)
                    continue

                # Login screen counts as "ready enough" when credentials will be used next
                lower = res.lower()
                if accept_login_prompts and any(
                    m.lower() in lower
                    for m in ("username:", "login:", "password:")
                ):
                    logger.info("Login prompt detected during boot wait")
                    return True

                # Check if we got a valid prompt
                if any(p in res for p in prompts if p not in ["[yes/no]:", "[confirm]"]):
                    logger.info("Device prompt detected, boot complete")
                    return True

                time.sleep(1)

            except Exception as e:
                logger.error(f"Error waiting for boot: {e}")
                time.sleep(1)
                continue

        logger.error(f"Timeout waiting for device boot after {timeout}s")
        return False

    def login(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: float = 15.0,
    ) -> bool:
        """Best-effort console login for Username/login/Password prompts.

        Returns True if already at a shell/enable prompt or login appears successful.
        Never logs credentials.
        """
        if not self.sock or not self.connected:
            return False

        shell_markers = [">", "#", "$", "%"]
        user_markers = ["Username:", "username:", "login:", "Login:"]
        pass_markers = ["Password:", "password:"]
        any_markers = user_markers + pass_markers + shell_markers

        def _has_shell(text: str) -> bool:
            stripped = (text or "").strip()
            if not stripped:
                return False
            last = stripped.splitlines()[-1]
            # Login/password prompts end with ':' — not a shell.
            if last.rstrip().endswith(":"):
                return False
            for m in shell_markers:
                if m in last or m in stripped:
                    # Ignore shell chars that appear only inside login banners
                    if any(um in text for um in user_markers + pass_markers):
                        # If last line is still a login prompt, not shell
                        if any(um in last for um in user_markers + pass_markers):
                            return False
                        if last.rstrip().endswith(":"):
                            return False
                    return True
            return False

        def _at_login(text: str) -> bool:
            return any(m in (text or "") for m in user_markers + pass_markers)

        try:
            self.sock.send(b"\r")
            buf = self.read_until(any_markers, timeout=min(timeout, 5.0))

            if _has_shell(buf) and not _at_login(buf):
                logger.info("Console already at shell prompt; login not required")
                return True

            if any(m in buf for m in user_markers):
                if not username:
                    logger.error("Login username required but not provided")
                    return False
                logger.debug("Sending console username")
                self.sock.send(f"{username}\r".encode())
                buf = self.read_until(pass_markers + shell_markers, timeout=5.0)

            if any(m in buf for m in pass_markers):
                if password is None:
                    logger.error("Login password required but not provided")
                    return False
                logger.debug("Sending console password")
                self.sock.send(f"{password}\r".encode())
                buf = self.read_until(shell_markers + user_markers + pass_markers, timeout=5.0)

            # Clear failure: still sitting at login/password
            if _at_login(buf) and not _has_shell(buf):
                logger.error("Console authentication failed")
                return False

            if _has_shell(buf):
                logger.info("Console login completed")
                return True

            # Some devices need a second enter after auth
            self.sock.send(b"\r")
            buf = self.read_until(shell_markers + user_markers + pass_markers, timeout=3.0)

            if _at_login(buf) and not _has_shell(buf):
                logger.error("Console authentication failed")
                return False

            if _has_shell(buf):
                logger.info("Console login completed")
                return True

            # No login markers and no clear shell — treat as soft success
            # (e.g. empty banner devices that only need credentials once).
            if not _at_login(buf):
                logger.info("Console login completed (no login prompt remaining)")
                return True

            logger.error("Console login timed out or failed")
            return False
        except Exception as e:
            logger.error("Console login error: %s", e)
            return False

    def enter_config_mode(self, enable_password: Optional[str] = None) -> bool:
        """Enter privileged and configuration mode (Cisco-style)."""
        if not self.connected:
            return False
        
        try:
            # Try to enter privileged mode
            output = self.send_cmd("enable", wait_for=[">", "#", "Password:"], wait_time=1.0)
            
            if "Password:" in output:
                if not enable_password:
                    logger.error("Enable password required but not provided")
                    return False
                self.send_cmd(enable_password, wait_for=["#"], wait_time=1.0)
            
            # Enter config mode
            output = self.send_cmd("configure terminal", wait_for=["(config)#"], wait_time=1.0)
            
            if "(config)" in output:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to enter config mode: {e}")
            return False

    def exit_config_mode(self) -> bool:
        """Exit configuration mode."""
        if not self.connected:
            return False
        
        try:
            self.send_cmd("end", wait_for=["#"], wait_time=1.0)
            return True
        except Exception as e:
            logger.error(f"Failed to exit config mode: {e}")
            return False

    def save_config(self, confirm: bool = True) -> str:
        """Save running configuration (Cisco-style)."""
        if not self.connected:
            return ""
        
        try:
            output = self.send_cmd("write memory", wait_for=["#", "[OK]", "[confirm]"], wait_time=2.0)
            
            if "[confirm]" in output and confirm:
                output += self.send_cmd("", wait_for=["#", "[OK]"], wait_time=2.0)
            
            return output
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return ""

    def send_config_commands(self, commands: List[str], 
                           enter_config: bool = True,
                           save_config: bool = False,
                           enable_password: Optional[str] = None) -> List[str]:
        """Send multiple configuration commands in sequence."""
        if not self.connected:
            return []
        
        outputs = []
        
        try:
            # Enter config mode if requested
            if enter_config:
                if not self.enter_config_mode(enable_password):
                    logger.error("Failed to enter config mode")
                    return []
            
            # Send each command
            prompts = ["#", "(config)#", "(config-if)#", "(config-router)#", "(config-line)#"]
            
            for cmd in commands:
                output = self.send_cmd(cmd, wait_for=prompts, wait_time=1.0)
                outputs.append(output)
            
            # Exit config mode if we entered it
            if enter_config:
                self.exit_config_mode()
            
            # Save config if requested
            if save_config:
                save_output = self.save_config()
                outputs.append(save_output)
            
            return outputs
            
        except Exception as e:
            logger.error(f"Failed to send config commands: {e}")
            return outputs

    def get_running_config(self) -> str:
        """Get the running configuration."""
        if not self.connected:
            return ""
        
        try:
            output = self.send_cmd("show running-config", wait_for=["#"], wait_time=5.0)
            return output
        except Exception as e:
            logger.error(f"Failed to get running config: {e}")
            return ""
