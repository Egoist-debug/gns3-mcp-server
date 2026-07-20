"""gns3_diagnose_connectivity goal implementation."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from gns3_mcp.gns3_client import GNS3APIClient, GNS3Config
from gns3_mcp.server_lifecycle import ensure_gns3_server, normalize_server_url
from gns3_mcp.workflow.console_ops import send_console_commands
from gns3_mcp.workflow.envelopes import (
    STATUS_SUCCESS,
    STEP_FAILED,
    STEP_SKIPPED,
    STEP_SUCCESS,
    error_envelope,
    goal_envelope,
    step_entry,
)
from gns3_mcp.workflow.resolve import ResolveAmbiguous, ResolveMissing, resolve_node, resolve_project
from gns3_mcp.workflow.runner import Step, run_steps


async def diagnose_connectivity_goal(
    *,
    project_name: Optional[str] = None,
    project_id: Optional[str] = None,
    suspect_nodes: Optional[List[Dict[str, Any]]] = None,
    probe_commands: Optional[List[str]] = None,
    server_url: str = "http://localhost:3080",
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> Dict[str, Any]:
    goal = "diagnose_connectivity"
    url = normalize_server_url(server_url)
    suspect_nodes = suspect_nodes or []
    probe_commands = probe_commands or ["show ip interface brief", "show ip route"]
    if not project_id and not (project_name and str(project_name).strip()):
        return error_envelope(goal, "project_id or project_name is required")

    ctx: Dict[str, Any] = {
        "client": None,
        "project": None,
        "validation": None,
        "topology": None,
        "probes": [],
        "findings": [],
    }

    async def ensure_step() -> Dict[str, Any]:
        config = GNS3Config.from_env(server_url=url, username=username, password=password)
        result = await ensure_gns3_server(
            config.server_url, username=config.username, password=config.password
        )
        if result.get("status") != "success":
            return step_entry(
                "ensure_server",
                STEP_FAILED,
                error=result.get("error") or "GNS3 server not available",
            )
        ctx["client"] = GNS3APIClient(config)
        return step_entry("ensure_server", STEP_SUCCESS)

    async def resolve_project_step() -> Dict[str, Any]:
        try:
            project = await resolve_project(
                ctx["client"], project_id=project_id, project_name=project_name
            )
        except (ResolveMissing, ResolveAmbiguous, ValueError) as exc:
            return step_entry("resolve_project", STEP_FAILED, error=str(exc))
        ctx["project"] = project
        return step_entry(
            "resolve_project",
            STEP_SUCCESS,
            detail={"project_id": project.get("project_id")},
        )

    async def validate_step() -> Dict[str, Any]:
        client: GNS3APIClient = ctx["client"]
        pid = ctx["project"]["project_id"]
        nodes = await client.get_project_nodes(pid)
        links = await client.get_project_links(pid)
        connected = set()
        for link in links:
            ends = link.get("nodes") or []
            if len(ends) >= 2:
                connected.add(ends[0].get("node_id"))
                connected.add(ends[1].get("node_id"))
        warnings = []
        for n in nodes:
            if n.get("node_id") not in connected:
                msg = f"Node '{n.get('name')}' has no connections"
                warnings.append(msg)
                ctx["findings"].append(
                    {
                        "severity": "warning",
                        "code": "disconnected_node",
                        "message": msg,
                        "source_step": "validate_topology",
                        "node": n.get("name"),
                    }
                )
            if n.get("node_type") in ("dynamips", "iou", "qemu") and n.get("status") != "started":
                msg = f"Critical node '{n.get('name')}' is not running"
                warnings.append(msg)
                ctx["findings"].append(
                    {
                        "severity": "warning",
                        "code": "node_not_started",
                        "message": msg,
                        "source_step": "validate_topology",
                        "node": n.get("name"),
                    }
                )
        ctx["validation"] = {
            "total_nodes": len(nodes),
            "total_links": len(links),
            "warnings": warnings,
            "is_valid": True,
        }
        ctx["topology"] = {
            "nodes": [
                {
                    "name": n.get("name"),
                    "node_id": n.get("node_id"),
                    "status": n.get("status"),
                    "node_type": n.get("node_type"),
                }
                for n in nodes
            ],
            "link_count": len(links),
        }
        return step_entry("validate_topology", STEP_SUCCESS, detail=ctx["validation"])

    async def probe_step() -> Dict[str, Any]:
        if not suspect_nodes:
            return step_entry(
                "console_probes",
                STEP_SKIPPED,
                detail={"reason": "no suspect_nodes"},
            )
        client: GNS3APIClient = ctx["client"]
        pid = ctx["project"]["project_id"]
        for spec in suspect_nodes:
            try:
                node = await resolve_node(
                    client,
                    pid,
                    node_id=spec.get("node_id"),
                    node_name=spec.get("node_name") or spec.get("name"),
                )
            except (ResolveMissing, ResolveAmbiguous, ValueError) as exc:
                return step_entry(
                    "console_probes",
                    STEP_FAILED,
                    error=str(exc),
                )
            cmds = list(spec.get("commands") or probe_commands)
            if node.get("status") != "started":
                try:
                    await client.start_node(pid, node["node_id"])
                except Exception as exc:
                    return step_entry(
                        "console_probes",
                        STEP_FAILED,
                        error=f"cannot start {node.get('name')}: {exc}",
                    )
            out = await send_console_commands(
                project_id=pid,
                node_id=node["node_id"],
                commands=cmds,
                server_url=url,
                username=username,
                password=password,
                enter_config_mode=False,
                save_config=False,
                login_username=spec.get("login_username"),
                login_password=spec.get("login_password"),
            )
            if out.get("status") != "success":
                return step_entry(
                    "console_probes",
                    STEP_FAILED,
                    error=out.get("error") or "probe failed",
                    detail={"node": node.get("name")},
                )
            ctx["probes"].append(
                {
                    "node_name": node.get("name"),
                    "node_id": node.get("node_id"),
                    "results": out.get("results"),
                }
            )
            for item in out.get("results") or []:
                body = (item.get("response") or "").strip()
                if not body:
                    continue
                # evidence-only finding — no ML root cause
                ctx["findings"].append(
                    {
                        "severity": "info",
                        "code": "console_probe_output",
                        "message": f"Probe on {node.get('name')}: {item.get('command')}",
                        "source_step": "console_probes",
                        "node": node.get("name"),
                        "command": item.get("command"),
                        "response_excerpt": body[:500],
                    }
                )
        return step_entry(
            "console_probes",
            STEP_SUCCESS,
            detail={"probed": [p["node_name"] for p in ctx["probes"]]},
        )

    result = await run_steps(
        [
            Step("ensure_server", ensure_step),
            Step("resolve_project", resolve_project_step),
            Step("validate_topology", validate_step),
            Step("console_probes", probe_step),
        ]
    )
    return goal_envelope(
        goal,
        result.status,
        result.steps,
        result={
            "project_id": (ctx.get("project") or {}).get("project_id"),
            "validation": ctx["validation"],
            "topology": ctx["topology"],
            "probes": ctx["probes"],
            "findings": ctx["findings"],
        },
        error=result.error,
        next_hint=None
        if result.status == STATUS_SUCCESS
        else "Review findings; no automatic remediation was applied",
    )
