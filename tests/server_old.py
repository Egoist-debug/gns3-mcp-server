#!/usr/bin/env python3
"""
GNS3 MCP Server - FastMCP implementation for GNS3 network simulation integration.

This MCP server provides tools for managing GNS3 network topologies,
project management, and simulation control through direct HTTP API calls.
"""

import asyncio
import json
import logging
import socket
import time
import re
from typing import Any, Dict, List, Optional

import httpx
from fastmcp import FastMCP
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastMCP server instance
mcp = FastMCP("GNS3 Network Simulator")

# Configuration models
class GNS3Config(BaseModel):
    """Configuration for GNS3 server connection."""
    server_url: str = Field(default="http://localhost:3080", description="GNS3 server URL")
    username: Optional[str] = Field(default=None, description="Username for authentication")
    password: Optional[str] = Field(default=None, description="Password for authentication")
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")

class TelnetClient:
    """Simple Telnet client for GNS3 console interaction."""
    
    def __init__(self, host: str, port: int, timeout: float = 10.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock = None

    def connect(self):
        """Connect to the Telnet server."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(self.timeout)
            self.sock.connect((self.host, self.port))
            return True
        except Exception as e:
            logger.error(f"Telnet connection failed to {self.host}:{self.port}: {e}")
            return False

    def close(self):
        """Close the connection."""
        if self.sock:
            self.sock.close()
            self.sock = None

    def read_until(self, valid_end_chars: List[str], timeout: float = None) -> str:
        """Read from socket until one of valid_end_chars is seen."""
        if not self.sock:
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

    def send_cmd(self, cmd: str, wait_for: List[str] = None, wait_time: float = 0.5) -> str:
        """Send a command and wait for response."""
        if not self.sock:
            return ""
        
        try:
            full_cmd = f"{cmd}\r"
            self.sock.send(full_cmd.encode())
            
            if wait_for:
                return self.read_until(wait_for)
            
            time.sleep(wait_time)
            # Read whatever is available
            try:
                return self.sock.recv(4096).decode('utf-8', errors='ignore')
            except socket.timeout:
                return ""
        except Exception as e:
            logger.error(f"Send error: {e}")
            return ""

    def wait_for_boot(self, timeout: int = 60) -> bool:
        """Wait for device to boot and show a prompt."""
        if not self.sock:
            return False
            
        start_time = time.time()
        prompts = [">", "#", "PC1>", "PC2>", "Laptop1>", "Laptop2>", "[yes/no]:"]
        
        while time.time() - start_time < timeout:
            self.sock.send(b"\r")
            res = self.read_until(prompts, timeout=2)
            
            if "[yes/no]:" in res:
                logger.info("Initial Config Dialog detected. Sending 'no'.")
                self.sock.send(b"no\r")
                time.sleep(5)
                continue
            
            if any(p in res for p in prompts if p != "[yes/no]:"):
                return True
            
            time.sleep(1)
            
        return False

class GNS3APIClient:
    """HTTP client for GNS3 REST API."""
    
    def __init__(self, config: GNS3Config):
        self.config = config
        self.base_url = config.server_url.rstrip('/')
        self.auth = None
        if config.username and config.password:
            self.auth = (config.username, config.password)
    
    async def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request to GNS3 API."""
        url = f"{self.base_url}/v2{endpoint}"
        headers = {"Content-Type": "application/json"}
        
        try:
            async with httpx.AsyncClient(verify=self.config.verify_ssl, timeout=30.0) as client:
                if method.upper() == "GET":
                    response = await client.get(url, headers=headers, auth=self.auth)
                elif method.upper() == "POST":
                    response = await client.post(url, json=data, headers=headers, auth=self.auth)
                elif method.upper() == "PUT":
                    response = await client.put(url, json=data, headers=headers, auth=self.auth)
                elif method.upper() == "DELETE":
                    response = await client.delete(url, headers=headers, auth=self.auth)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                response.raise_for_status()
                return response.json()
                
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise Exception(f"Failed to connect to GNS3 server: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e}")
            raise Exception(f"GNS3 API error: {e.response.status_code} - {e.response.text}")
    
    async def get_server_info(self) -> Dict[str, Any]:
        return await self._request("GET", "/version")
    
    async def get_projects(self) -> List[Dict[str, Any]]:
        return await self._request("GET", "/projects")
    
    async def create_project(self, name: str, auto_close: bool = False) -> Dict[str, Any]:
        data = {"name": name, "auto_close": auto_close}
        return await self._request("POST", "/projects", data)
    
    async def get_project(self, project_id: str) -> Dict[str, Any]:
        return await self._request("GET", f"/projects/{project_id}")
    
    async def open_project(self, project_id: str) -> Dict[str, Any]:
        return await self._request("PUT", f"/projects/{project_id}/open")
    
    async def get_project_nodes(self, project_id: str) -> List[Dict[str, Any]]:
        return await self._request("GET", f"/projects/{project_id}/nodes")
    
    async def get_project_links(self, project_id: str) -> List[Dict[str, Any]]:
        return await self._request("GET", f"/projects/{project_id}/links")
    
    async def create_node(self, project_id: str, node_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request("POST", f"/projects/{project_id}/nodes", node_data)
    
    async def create_node_from_template(self, project_id: str, template_id: str, x: int = 0, y: int = 0, compute_id: Optional[str] = None, name: Optional[str] = None) -> Dict[str, Any]:
        data = {"x": x, "y": y}
        if compute_id:
            data["compute_id"] = compute_id
        if name:
            data["name"] = name
        return await self._request("POST", f"/projects/{project_id}/templates/{template_id}", data)
    
    async def get_node(self, project_id: str, node_id: str) -> Dict[str, Any]:
        return await self._request("GET", f"/projects/{project_id}/nodes/{node_id}")
    
    async def update_node(self, project_id: str, node_id: str, node_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request("PUT", f"/projects/{project_id}/nodes/{node_id}", node_data)
    
    async def start_node(self, project_id: str, node_id: str) -> Dict[str, Any]:
        return await self._request("POST", f"/projects/{project_id}/nodes/{node_id}/start")
    
    async def stop_node(self, project_id: str, node_id: str) -> Dict[str, Any]:
        return await self._request("POST", f"/projects/{project_id}/nodes/{node_id}/stop")
    
    async def create_link(self, project_id: str, link_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request("POST", f"/projects/{project_id}/links", link_data)
    
    async def start_capture(self, project_id: str, link_id: str, capture_file_name: str) -> Dict[str, Any]:
        data = {"capture_file_name": capture_file_name}
        return await self._request("POST", f"/projects/{project_id}/links/{link_id}/start_capture", data)
    
    async def create_snapshot(self, project_id: str, name: str) -> Dict[str, Any]:
        data = {"name": name}
        return await self._request("POST", f"/projects/{project_id}/snapshots", data)
    
    async def get_node_console_info(self, project_id: str, node_id: str) -> Dict[str, Any]:
        """Get console host and port for a node."""
        node = await self.get_node(project_id, node_id)
        return {
            "host": node.get("console_host"),
            "port": node.get("console"),
            "type": node.get("console_type"),
            "name": node.get("name")
        }

# Tool: List all GNS3 projects
@mcp.tool
async def gns3_list_projects(
    server_url: str = "http://localhost:3080",
    username: Optional[str] = None,
    password: Optional[str] = None
) -> Dict[str, Any]:
    """List all projects on the GNS3 server."""
    try:
        config = GNS3Config(server_url=server_url, username=username, password=password)
        client = GNS3APIClient(config)
        server_info = await client.get_server_info()
        projects = await client.get_projects()
        
        projects_summary = []
        for project in projects:
            projects_summary.append({
                "Project Name": project.get("name", "Unnamed"),
                "Project ID": project.get("project_id", ""),
                "Total Nodes": project.get("stats", {}).get("nodes", 0),
                "Total Links": project.get("stats", {}).get("links", 0),
                "Status": project.get("status", "unknown")
            })
        
        return {
            "status": "success",
            "server_info": {"version": server_info.get("version"), "user": server_info.get("user")},
            "projects": projects_summary,
            "total_projects": len(projects_summary)
        }
    except Exception as e:
        logger.error(f"Failed to list projects: {e}")
        return {"status": "error", "error": str(e)}

# Tool: Create a new GNS3 project
@mcp.tool
async def gns3_create_project(
    name: str,
    server_url: str = "http://localhost:3080",
    username: Optional[str] = None,
    password: Optional[str] = None,
    auto_close: bool = False
) -> Dict[str, Any]:
    """Create a new GNS3 project."""
    try:
        config = GNS3Config(server_url=server_url, username=username, password=password)
        client = GNS3APIClient(config)
        project = await client.create_project(name, auto_close)
        return {"status": "success", "project": project}
    except Exception as e:
        logger.error(f"Failed to create project: {e}")
        return {"status": "error", "error": str(e)}

# Tool: Open an existing project
@mcp.tool
async def gns3_open_project(
    project_id: str,
    server_url: str = "http://localhost:3080",
    username: Optional[str] = None,
    password: Optional[str] = None
) -> Dict[str, Any]:
    """Open an existing GNS3 project."""
    try:
        config = GNS3Config(server_url=server_url, username=username, password=password)
        client = GNS3APIClient(config)
        await client.get_project(project_id) # Verify exists
        opened_project = await client.open_project(project_id)
        return {"status": "success", "project": opened_project}
    except Exception as e:
        logger.error(f"Failed to open project: {e}")
        return {"status": "error", "error": str(e)}

# Tool: Add a network node/device
@mcp.tool
async def gns3_add_node(
    project_id: str,
    node_name: str,
    node_type: str = "ethernet_switch",
    template_id: Optional[str] = None,
    compute_id: Optional[str] = "local",
    server_url: str = "http://localhost:3080",
    username: Optional[str] = None,
    password: Optional[str] = None,
    x: Optional[int] = None,
    y: Optional[int] = None,
    console_type: Optional[str] = None,
    console_auto_start: bool = False
) -> Dict[str, Any]:
    """Add a network device/node to a GNS3 project."""
    try:
        config = GNS3Config(server_url=server_url, username=username, password=password)
        client = GNS3APIClient(config)
        
        if template_id:
             node = await client.create_node_from_template(
                 project_id=project_id,
                 template_id=template_id,
                 x=x if x is not None else 0,
                 y=y if y is not None else 0,
                 compute_id=compute_id,
                 name=node_name
             )
        else:
            node_data = {
                "name": node_name,
                "node_type": node_type,
                "compute_id": compute_id
            }
            if x is not None: node_data["x"] = x
            if y is not None: node_data["y"] = y
            if console_type is not None: node_data["console_type"] = console_type
            if console_auto_start: node_data["console_auto_start"] = console_auto_start
            
            node = await client.create_node(project_id, node_data)
        
        return {"status": "success", "node": node}
    except Exception as e:
        logger.error(f"Failed to add node: {e}")
        return {"status": "error", "error": str(e)}

# Tool: Add a link between two nodes
@mcp.tool
async def gns3_add_link(
    project_id: str,
    node_a_id: str,
    node_b_id: str,
    node_a_port: Optional[str] = None,
    node_b_port: Optional[str] = None,
    server_url: str = "http://localhost:3080",
    username: Optional[str] = None,
    password: Optional[str] = None
) -> Dict[str, Any]:
    """Add a link between two nodes in a GNS3 project."""
    try:
        config = GNS3Config(server_url=server_url, username=username, password=password)
        client = GNS3APIClient(config)
        
        link_data = {
            "nodes": [
                {"node_id": node_a_id, "port_name": node_a_port},
                {"node_id": node_b_id, "port_name": node_b_port}
            ]
        }
        link = await client.create_link(project_id, link_data)
        return {"status": "success", "link": link}
    except Exception as e:
        logger.error(f"Failed to add link: {e}")
        return {"status": "error", "error": str(e)}

# Tool: Configure device settings
@mcp.tool
async def gns3_configure_device(
    project_id: str,
    node_id: str,
    server_url: str = "http://localhost:3080",
    username: Optional[str] = None,
    password: Optional[str] = None,
    console_type: Optional[str] = None,
    console_auto_start: bool = False,
    properties: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Configure settings for a network device."""
    try:
        config = GNS3Config(server_url=server_url, username=username, password=password)
        client = GNS3APIClient(config)
        
        config_params = {}
        if console_type is not None: config_params["console_type"] = console_type
        if console_auto_start: config_params["console_auto_start"] = console_auto_start
        if properties is not None: config_params.update(properties)
        
        updated_node = await client.update_node(project_id, node_id, config_params)
        return {"status": "success", "node": updated_node}
    except Exception as e:
        logger.error(f"Failed to configure device: {e}")
        return {"status": "error", "error": str(e)}

# Tool: Start network simulation
@mcp.tool
async def gns3_start_simulation(
    project_id: str,
    server_url: str = "http://localhost:3080",
    username: Optional[str] = None,
    password: Optional[str] = None
) -> Dict[str, Any]:
    """Start all nodes in a network simulation."""
    try:
        config = GNS3Config(server_url=server_url, username=username, password=password)
        client = GNS3APIClient(config)
        nodes = await client.get_project_nodes(project_id)
        
        started_nodes = []
        failed_nodes = []
        
        for node in nodes:
            try:
                await client.start_node(project_id, node["node_id"])
                started_nodes.append({"node_id": node["node_id"], "name": node["name"], "status": "started"})
            except Exception as e:
                failed_nodes.append({"node_id": node["node_id"], "name": node["name"], "error": str(e)})
        
        return {
            "status": "success", "project_id": project_id,
            "started_nodes": started_nodes, "failed_nodes": failed_nodes,
            "total_nodes": len(nodes), "successful_starts": len(started_nodes)
        }
    except Exception as e:
        logger.error(f"Failed to start simulation: {e}")
        return {"status": "error", "error": str(e), "project_id": project_id}

# Tool: Stop network simulation
@mcp.tool
async def gns3_stop_simulation(
    project_id: str,
    server_url: str = "http://localhost:3080",
    username: Optional[str] = None,
    password: Optional[str] = None
) -> Dict[str, Any]:
    """Stop all nodes in a network simulation."""
    try:
        config = GNS3Config(server_url=server_url, username=username, password=password)
        client = GNS3APIClient(config)
        nodes = await client.get_project_nodes(project_id)
        
        stopped_nodes = []
        failed_nodes = []
        
        for node in nodes:
            try:
                await client.stop_node(project_id, node["node_id"])
                stopped_nodes.append({"node_id": node["node_id"], "name": node["name"], "status": "stopped"})
            except Exception as e:
                failed_nodes.append({"node_id": node["node_id"], "name": node["name"], "error": str(e)})
        
        return {
            "status": "success", "project_id": project_id,
            "stopped_nodes": stopped_nodes, "failed_nodes": failed_nodes,
            "total_nodes": len(nodes), "successful_stops": len(stopped_nodes)
        }
    except Exception as e:
        logger.error(f"Failed to stop simulation: {e}")
        return {"status": "error", "error": str(e), "project_id": project_id}

# Tool: Capture network traffic on links
@mcp.tool
async def gns3_capture_traffic(
    project_id: str,
    link_id: str,
    capture_file: str,
    server_url: str = "http://localhost:3080",
    username: Optional[str] = None,
    password: Optional[str] = None
) -> Dict[str, Any]:
    """Start capturing network traffic on a link."""
    try:
        config = GNS3Config(server_url=server_url, username=username, password=password)
        client = GNS3APIClient(config)
        result = await client.start_capture(project_id, link_id, capture_file)
        return {"status": "success", "link_id": link_id, "capture_started": True, "result": result}
    except Exception as e:
        logger.error(f"Failed to start traffic capture: {e}")
        return {"status": "error", "error": str(e)}

# Tool: Get current network topology
@mcp.tool
async def gns3_get_topology(
    project_id: str,
    server_url: str = "http://localhost:3080",
    username: Optional[str] = None,
    password: Optional[str] = None
) -> Dict[str, Any]:
    """Get the current network topology for a project."""
    try:
        config = GNS3Config(server_url=server_url, username=username, password=password)
        client = GNS3APIClient(config)
        
        project = await client.get_project(project_id)
        nodes = await client.get_project_nodes(project_id)
        links = await client.get_project_links(project_id)
        
        nodes_summary = []
        for node in nodes:
            nodes_summary.append({
                "Node": node.get("name"), "Status": node.get("status"),
                "Console Port": node.get("console"), "ID": node.get("node_id"),
                "Node Type": node.get("node_type")
            })
        
        links_summary = []
        for link in links:
            n1 = next((n for n in nodes if n["node_id"] == link["nodes"][0]["node_id"]), {})
            n2 = next((n for n in nodes if n["node_id"] == link["nodes"][1]["node_id"]), {})
            links_summary.append({
                "Node A": n1.get("name"), "Port A": link["nodes"][0].get("port_name"),
                "Node B": n2.get("name"), "Port B": link["nodes"][1].get("port_name")
            })
        
        return {
            "status": "success", "project": project,
            "nodes": nodes_summary, "links": links_summary,
            "summary": {"total_nodes": len(nodes), "total_links": len(links)}
        }
    except Exception as e:
        logger.error(f"Failed to get topology: {e}")
        return {"status": "error", "error": str(e)}

# Tool: Save project
@mcp.tool
async def gns3_save_project(
    project_id: str,
    server_url: str = "http://localhost:3080",
    username: Optional[str] = None,
    password: Optional[str] = None,
    snapshot_name: Optional[str] = None
) -> Dict[str, Any]:
    """Save a GNS3 project."""
    try:
        config = GNS3Config(server_url=server_url, username=username, password=password)
        client = GNS3APIClient(config)
        
        if snapshot_name:
            await client.create_snapshot(project_id, snapshot_name)
        
        return {"status": "success", "project_id": project_id, "saved": True}
    except Exception as e:
        logger.error(f"Failed to save project: {e}")
        return {"status": "error", "error": str(e)}

# Tool: Export project
@mcp.tool
async def gns3_export_project(
    project_id: str,
    export_path: str,
    server_url: str = "http://localhost:3080",
    username: Optional[str] = None,
    password: Optional[str] = None,
    include_ios_images: bool = False,
    include_node_images: bool = False
) -> Dict[str, Any]:
    """Export a GNS3 project (params only, action via GUI usually)."""
    return {
        "status": "success", "project_id": project_id,
        "note": "Export parameters valid. Use GNS3 GUI for actual export."
    }

# Tool: Send console commands
@mcp.tool
async def gns3_send_console_commands(
    project_id: str,
    node_id: str,
    commands: List[str],
    server_url: str = "http://localhost:3080",
    username: Optional[str] = None,
    password: Optional[str] = None,
    wait_for_prompts: bool = True,
    timeout: int = 30
) -> Dict[str, Any]:
    """Send commands to a node's console (Telnet).    
    Args:
        project_id: ID of the project
        node_id: ID of the node
        commands: List of commands to execute
        server_url: GNS3 server URL
        wait_for_prompts: Whether to wait for prompts (>, #) after each command
        timeout: Timeout for connection and command execution
    
    Returns:
        Dictionary containing execution results and output
    """
    try:
        config = GNS3Config(server_url=server_url, username=username, password=password)
        client = GNS3APIClient(config)
        
        # Get console info
        console_info = await client.get_node_console_info(project_id, node_id)
        host = console_info.get("host")
        port = console_info.get("port")
        
        if not host or not port:
             return {"status": "error", "error": "Node has no console or is not running"}
            
        # Connect to console
        telnet = TelnetClient(host, port, timeout=float(timeout))
        if not telnet.connect():
             return {"status": "error", "error": f"Failed to connect to console {host}:{port}"}
        
        try:
            # Wait for boot/prompt
            if wait_for_prompts:
                if not telnet.wait_for_boot(timeout=60):
                     return {"status": "error", "error": "Timeout waiting for boot prompt"}
            
            output = []
            prompts = [">", "#", "PC1>", "PC2>", "Laptop1>", "Laptop2>"]
            
            for cmd in commands:
                wait_for = prompts if wait_for_prompts else None
                res = telnet.send_cmd(cmd, wait_for=wait_for, wait_time=1.0)
                output.append({"command": cmd, "response": res})
            
            return {
                "status": "success",
                "node_id": node_id,
                "node_name": console_info.get("name"),
                "results": output
            }
        finally:
            telnet.close()
            
    except Exception as e:
        logger.error(f"Failed to send console commands: {e}")
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
