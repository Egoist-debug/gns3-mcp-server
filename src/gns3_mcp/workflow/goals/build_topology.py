"""gns3_build_topology goal implementation."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from gns3_mcp.gns3_client import GNS3APIClient, GNS3Config
from gns3_mcp.server_lifecycle import ensure_gns3_server, normalize_server_url
from gns3_mcp.workflow.envelopes import (
    STATUS_CONFLICT,
    STATUS_SUCCESS,
    STEP_CHANGED,
    STEP_FAILED,
    STEP_SKIPPED,
    STEP_SUCCESS,
    conflict_envelope,
    error_envelope,
    goal_envelope,
    step_entry,
)
from gns3_mcp.workflow.resolve import (
    ResolveAmbiguous,
    ResolveConflict,
    ResolveMissing,
    check_node_template_conflict,
    find_link_by_endpoints,
    link_endpoint_key,
    node_template_id,
    resolve_project,
    resolve_template,
    unordered_link_key,
)
from gns3_mcp.workflow.runner import Step, run_steps


def _endpoint_spec(end: Dict[str, Any]) -> Tuple[str, Optional[int], Optional[int]]:
    name = (end.get("node_name") or end.get("name") or "").strip()
    adapter = end.get("adapter")
    port = end.get("port")
    a = int(adapter) if adapter is not None else None
    p = int(port) if port is not None else None
    return name, a, p


async def build_topology_goal(
    *,
    project_name: Optional[str] = None,
    project_id: Optional[str] = None,
    nodes: Optional[List[Dict[str, Any]]] = None,
    links: Optional[List[Dict[str, Any]]] = None,
    start: bool = False,
    validate: bool = True,
    server_url: str = "http://localhost:3080",
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> Dict[str, Any]:
    goal = "build_topology"
    url = normalize_server_url(server_url)
    nodes = nodes or []
    links = links or []
    ctx: Dict[str, Any] = {
        "client": None,
        "project": None,
        "node_by_name": {},
        "created_nodes": [],
        "skipped_nodes": [],
        "created_links": [],
        "skipped_links": [],
        "validation": None,
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
                detail=result,
                error=result.get("error") or "GNS3 server not available",
            )
        ctx["client"] = GNS3APIClient(config)
        return step_entry("ensure_server", STEP_SUCCESS, detail={"server_url": url})

    async def resolve_project_step() -> Dict[str, Any]:
        client: GNS3APIClient = ctx["client"]
        try:
            project = await resolve_project(
                client, project_id=project_id, project_name=project_name
            )
        except ResolveMissing as exc:
            return step_entry("resolve_project", STEP_FAILED, error=str(exc))
        except ResolveAmbiguous as exc:
            return step_entry(
                "resolve_project",
                STEP_FAILED,
                error=str(exc),
                detail={"candidates": exc.candidates},
            )
        ctx["project"] = project
        if project.get("status") != "opened":
            await client.open_project(project["project_id"])
        return step_entry(
            "resolve_project",
            STEP_SUCCESS,
            detail={"project_id": project.get("project_id"), "name": project.get("name")},
        )

    async def converge_nodes_step() -> Dict[str, Any]:
        client: GNS3APIClient = ctx["client"]
        pid = ctx["project"]["project_id"]
        existing = await client.get_project_nodes(pid)
        by_name = {
            n.get("name"): n
            for n in existing
            if isinstance(n, dict) and n.get("name")
        }
        for spec in nodes:
            name = (spec.get("name") or "").strip()
            if not name:
                return step_entry(
                    "converge_nodes",
                    STEP_FAILED,
                    error="node entry missing name",
                    detail={"spec": spec},
                )
            tpl_id = spec.get("template_id")
            tpl_name = spec.get("template_name")
            if name in by_name:
                node = by_name[name]
                try:
                    if tpl_id or tpl_name:
                        if not tpl_id and tpl_name:
                            tpl = await resolve_template(client, template_name=tpl_name)
                            tpl_id = tpl.get("template_id")
                        check_node_template_conflict(
                            node,
                            expected_template_id=tpl_id,
                            expected_template_name=tpl_name,
                        )
                except ResolveConflict as exc:
                    return step_entry(
                        "converge_nodes",
                        STEP_FAILED,
                        error=str(exc),
                        detail={"existing": exc.existing, "expected": exc.expected},
                    )
                ctx["skipped_nodes"].append({"name": name, "node_id": node.get("node_id")})
                ctx["node_by_name"][name] = node
                continue

            try:
                if not tpl_id:
                    tpl = await resolve_template(
                        client, template_id=tpl_id, template_name=tpl_name
                    )
                    tpl_id = tpl.get("template_id")
                else:
                    await resolve_template(client, template_id=tpl_id)
            except (ResolveMissing, ResolveAmbiguous, ValueError) as exc:
                return step_entry(
                    "converge_nodes",
                    STEP_FAILED,
                    error=f"template resolve failed for node {name}: {exc}",
                )

            created = await client.create_node_from_template(
                pid,
                tpl_id,
                x=int(spec.get("x") or 0),
                y=int(spec.get("y") or 0),
                name=name,
                compute_id=spec.get("compute_id"),
            )
            by_name[name] = created
            ctx["node_by_name"][name] = created
            ctx["created_nodes"].append(
                {"name": name, "node_id": created.get("node_id"), "template_id": tpl_id}
            )

        # refresh map with all existing for link phase
        for n in by_name.values():
            if n.get("name"):
                ctx["node_by_name"][n["name"]] = n

        status = STEP_CHANGED if ctx["created_nodes"] else STEP_SUCCESS
        if not nodes:
            status = STEP_SKIPPED
        return step_entry(
            "converge_nodes",
            status,
            detail={
                "created": ctx["created_nodes"],
                "skipped": ctx["skipped_nodes"],
            },
        )

    async def converge_links_step() -> Dict[str, Any]:
        if not links:
            return step_entry("converge_links", STEP_SKIPPED, detail={"reason": "no links"})
        client: GNS3APIClient = ctx["client"]
        pid = ctx["project"]["project_id"]
        # load nodes for port inventory
        all_nodes = await client.get_project_nodes(pid)
        name_to_node = {
            n.get("name"): n for n in all_nodes if isinstance(n, dict) and n.get("name")
        }
        ctx["node_by_name"].update(name_to_node)

        used_ports: Dict[str, set] = {}
        for n in all_nodes:
            used_ports[n.get("node_id")] = set()
        existing_links = await client.get_project_links(pid)
        for link in existing_links:
            for end in link.get("nodes") or []:
                nid = end.get("node_id")
                if nid in used_ports:
                    used_ports[nid].add(
                        (int(end.get("adapter_number", 0)), int(end.get("port_number", 0)))
                    )

        def pick_port(node: Dict[str, Any], adapter: Optional[int], port: Optional[int]) -> Tuple[int, int]:
            nid = node.get("node_id")
            used = used_ports.setdefault(nid, set())
            if adapter is not None and port is not None:
                key = (int(adapter), int(port))
                if key in used:
                    # allow if already for matching link; still mark used
                    return key
                used.add(key)
                return key
            # Prefer adapter 0 ports 0..15 first free
            for a in range(0, 8):
                for p in range(0, 16):
                    key = (a, p)
                    if key not in used:
                        used.add(key)
                        return key
            raise RuntimeError(f"no free ports on node {node.get('name')}")

        for spec in links:
            a_spec = spec.get("a") or spec.get("node_a") or {}
            b_spec = spec.get("b") or spec.get("node_b") or {}
            if not isinstance(a_spec, dict):
                a_spec = {"node_name": a_spec}
            if not isinstance(b_spec, dict):
                b_spec = {"node_name": b_spec}
            a_name, a_ad, a_po = _endpoint_spec(a_spec)
            b_name, b_ad, b_po = _endpoint_spec(b_spec)
            if not a_name or not b_name:
                return step_entry(
                    "converge_links",
                    STEP_FAILED,
                    error="link endpoints require node_name",
                    detail={"spec": spec},
                )
            a_node = name_to_node.get(a_name) or ctx["node_by_name"].get(a_name)
            b_node = name_to_node.get(b_name) or ctx["node_by_name"].get(b_name)
            if not a_node or not b_node:
                return step_entry(
                    "converge_links",
                    STEP_FAILED,
                    error=f"link endpoint node missing: {a_name!r} or {b_name!r}",
                )
            try:
                a_ap = pick_port(a_node, a_ad, a_po)
                b_ap = pick_port(b_node, b_ad, b_po)
            except RuntimeError as exc:
                return step_entry("converge_links", STEP_FAILED, error=str(exc))

            a_key = link_endpoint_key(a_name, a_ap[0], a_ap[1])
            b_key = link_endpoint_key(b_name, b_ap[0], b_ap[1])
            existing = await find_link_by_endpoints(client, pid, a_key, b_key)
            if existing:
                ctx["skipped_links"].append(
                    {
                        "link_id": existing.get("link_id"),
                        "a": a_key,
                        "b": b_key,
                    }
                )
                continue

            link_data = {
                "nodes": [
                    {
                        "node_id": a_node["node_id"],
                        "adapter_number": a_ap[0],
                        "port_number": a_ap[1],
                    },
                    {
                        "node_id": b_node["node_id"],
                        "adapter_number": b_ap[0],
                        "port_number": b_ap[1],
                    },
                ]
            }
            created = await client.create_link(pid, link_data)
            ctx["created_links"].append(
                {
                    "link_id": created.get("link_id") if isinstance(created, dict) else None,
                    "a": a_key,
                    "b": b_key,
                }
            )

        status = STEP_CHANGED if ctx["created_links"] else STEP_SUCCESS
        return step_entry(
            "converge_links",
            status,
            detail={"created": ctx["created_links"], "skipped": ctx["skipped_links"]},
        )

    async def start_step() -> Dict[str, Any]:
        if not start:
            return step_entry("start_nodes", STEP_SKIPPED, detail={"reason": "start=false"})
        client: GNS3APIClient = ctx["client"]
        pid = ctx["project"]["project_id"]
        all_nodes = await client.get_project_nodes(pid)
        started, failed = [], []
        for n in all_nodes:
            if n.get("status") == "started":
                continue
            try:
                await client.start_node(pid, n["node_id"])
                started.append(n.get("name"))
            except Exception as exc:
                failed.append({"name": n.get("name"), "error": str(exc)})
        if failed and not started:
            return step_entry(
                "start_nodes",
                STEP_FAILED,
                error="all start attempts failed",
                detail={"failed": failed},
            )
        if failed:
            return step_entry(
                "start_nodes",
                STEP_FAILED,
                error="some nodes failed to start",
                detail={"started": started, "failed": failed},
            )
        return step_entry(
            "start_nodes",
            STEP_CHANGED if started else STEP_SUCCESS,
            detail={"started": started},
        )

    async def validate_step() -> Dict[str, Any]:
        if not validate:
            return step_entry("validate", STEP_SKIPPED, detail={"reason": "validate=false"})
        client: GNS3APIClient = ctx["client"]
        pid = ctx["project"]["project_id"]
        all_nodes = await client.get_project_nodes(pid)
        all_links = await client.get_project_links(pid)
        connected = set()
        for link in all_links:
            ends = link.get("nodes") or []
            if len(ends) >= 2:
                connected.add(ends[0].get("node_id"))
                connected.add(ends[1].get("node_id"))
        warnings = []
        for n in all_nodes:
            if n.get("node_id") not in connected:
                warnings.append(f"Node '{n.get('name')}' has no connections")
        ctx["validation"] = {
            "total_nodes": len(all_nodes),
            "total_links": len(all_links),
            "warnings": warnings,
            "is_valid": True,
        }
        return step_entry("validate", STEP_SUCCESS, detail=ctx["validation"])

    if not project_id and not (project_name and str(project_name).strip()):
        return error_envelope(goal, "project_id or project_name is required")

    try:
        result = await run_steps(
            [
                Step("ensure_server", ensure_step),
                Step("resolve_project", resolve_project_step),
                Step("converge_nodes", converge_nodes_step),
                Step("converge_links", converge_links_step),
                Step("start_nodes", start_step),
                Step("validate", validate_step),
            ]
        )
    except ResolveConflict as exc:
        return conflict_envelope(
            goal,
            [],
            existing=exc.existing,
            expected=exc.expected,
            message=str(exc),
        )

    # surface conflict-style node failure as conflict status when detail present
    for s in result.steps:
        if s.get("status") == STEP_FAILED and s.get("detail", {}).get("existing"):
            return conflict_envelope(
                goal,
                result.steps,
                existing=s["detail"]["existing"],
                expected=s["detail"]["expected"],
                message=s.get("error") or "resource conflict",
            )

    project = ctx.get("project") or {}
    payload = {
        "project_id": project.get("project_id"),
        "created_nodes": ctx["created_nodes"],
        "skipped_nodes": ctx["skipped_nodes"],
        "created_links": ctx["created_links"],
        "skipped_links": ctx["skipped_links"],
        "validation": ctx["validation"],
    }
    return goal_envelope(
        goal,
        result.status if result.status != STATUS_SUCCESS else STATUS_SUCCESS,
        result.steps,
        result=payload,
        error=result.error,
        next_hint=None if result.status == STATUS_SUCCESS else "Inspect steps and retry safely",
    )
