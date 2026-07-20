"""gns3_finish_lab goal implementation."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from gns3_mcp.gns3_client import GNS3APIClient, GNS3Config
from gns3_mcp.server_lifecycle import (
    ensure_gns3_server,
    is_local_server_url,
    normalize_server_url,
    stop_gns3_server,
)
from gns3_mcp.workflow.confirm import consume_token, issue_token
from gns3_mcp.workflow.envelopes import (
    STATUS_PARTIAL,
    STATUS_SUCCESS,
    STEP_CHANGED,
    STEP_FAILED,
    STEP_SKIPPED,
    STEP_SUCCESS,
    confirmation_required_envelope,
    error_envelope,
    goal_envelope,
    step_entry,
)
from gns3_mcp.workflow.resolve import ResolveAmbiguous, ResolveMissing, resolve_project
from gns3_mcp.workflow.runner import Step, run_steps


async def finish_lab_goal(
    *,
    project_name: Optional[str] = None,
    project_id: Optional[str] = None,
    stop_nodes: bool = False,
    close_project: bool = False,
    stop_server: bool = False,
    confirmation_token: Optional[str] = None,
    server_url: str = "http://localhost:3080",
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> Dict[str, Any]:
    goal = "finish_lab"
    url = normalize_server_url(server_url)
    destructive = bool(stop_nodes or close_project or stop_server)

    if not destructive:
        return goal_envelope(
            goal,
            STATUS_SUCCESS,
            [
                step_entry(
                    "intent",
                    STEP_SKIPPED,
                    detail={
                        "reason": "all cleanup flags false",
                        "hint": "Ask the user which of stop_nodes/close_project/stop_server to enable",
                    },
                )
            ],
            result={
                "stop_nodes": False,
                "close_project": False,
                "stop_server": False,
                "message": "nothing requested; ask user before enabling destructive flags",
            },
            next_hint="Confirm with user, then re-call with explicit flags (and token if needed)",
        )

    target = {
        "action": "finish_lab",
        "project_id": project_id,
        "project_name": project_name,
        "stop_nodes": bool(stop_nodes),
        "close_project": bool(close_project),
        "stop_server": bool(stop_server),
        "server_url": url,
    }
    impact = {
        "stop_nodes": bool(stop_nodes),
        "close_project": bool(close_project),
        "stop_server": bool(stop_server),
        "server_url": url,
        "local_server": is_local_server_url(url),
        "order": ["stop_nodes", "close_project", "stop_server"],
    }

    if not confirmation_token:
        token, expires = issue_token("finish_lab", target)
        return confirmation_required_envelope(
            goal,
            [
                step_entry(
                    "authorization",
                    STEP_SUCCESS,
                    detail={"phase": "preview", "impact": impact},
                )
            ],
            action="finish_lab",
            target=target,
            impact=impact,
            confirmation_token=token,
            expires_at=expires,
        )

    consumed = consume_token(confirmation_token, "finish_lab", target)
    steps: List[Dict[str, Any]] = []
    if not consumed.get("ok"):
        steps.append(
            step_entry(
                "authorization",
                STEP_FAILED,
                error=consumed.get("error") or "token rejected",
            )
        )
        return goal_envelope(
            goal, "error", steps, error=consumed.get("error") or "token rejected"
        )
    steps.append(
        step_entry("authorization", STEP_SUCCESS, detail={"phase": "consumed"})
    )

    ctx: Dict[str, Any] = {"client": None, "project": None}

    # Resolve project if needed
    needs_project = stop_nodes or close_project
    if needs_project:
        config = GNS3Config.from_env(server_url=url, username=username, password=password)
        ensure = await ensure_gns3_server(
            config.server_url, username=config.username, password=config.password
        )
        if ensure.get("status") != "success":
            steps.append(
                step_entry(
                    "ensure_server",
                    STEP_FAILED,
                    error=ensure.get("error") or "server unavailable",
                )
            )
            return goal_envelope(goal, "error", steps, error=ensure.get("error"))
        steps.append(step_entry("ensure_server", STEP_SUCCESS))
        client = GNS3APIClient(config)
        ctx["client"] = client
        try:
            project = await resolve_project(
                client, project_id=project_id, project_name=project_name
            )
        except (ResolveMissing, ResolveAmbiguous, ValueError) as exc:
            steps.append(step_entry("resolve_project", STEP_FAILED, error=str(exc)))
            return goal_envelope(goal, "error", steps, error=str(exc))
        ctx["project"] = project
        steps.append(
            step_entry(
                "resolve_project",
                STEP_SUCCESS,
                detail={"project_id": project.get("project_id")},
            )
        )
        pid = project["project_id"]
    else:
        pid = project_id

    # stop_nodes
    if not stop_nodes:
        steps.append(
            step_entry("stop_nodes", STEP_SKIPPED, detail={"reason": "stop_nodes=false"})
        )
    else:
        client = ctx["client"]
        try:
            nodes = await client.get_project_nodes(pid)
            stopped, failed = [], []
            for n in nodes:
                try:
                    await client.stop_node(pid, n["node_id"])
                    stopped.append(n.get("name"))
                except Exception as exc:
                    failed.append({"name": n.get("name"), "error": str(exc)})
            if failed and not stopped:
                steps.append(
                    step_entry(
                        "stop_nodes",
                        STEP_FAILED,
                        error="all node stop attempts failed",
                        detail={"failed": failed},
                    )
                )
            elif failed:
                steps.append(
                    step_entry(
                        "stop_nodes",
                        STEP_FAILED,
                        error="some nodes failed to stop",
                        detail={"stopped": stopped, "failed": failed},
                    )
                )
            else:
                steps.append(
                    step_entry(
                        "stop_nodes",
                        STEP_CHANGED if stopped else STEP_SUCCESS,
                        detail={"stopped": stopped},
                    )
                )
        except Exception as exc:
            steps.append(step_entry("stop_nodes", STEP_FAILED, error=str(exc)))

    # close_project
    if not close_project:
        steps.append(
            step_entry(
                "close_project", STEP_SKIPPED, detail={"reason": "close_project=false"}
            )
        )
    else:
        try:
            await ctx["client"].close_project(pid)
            steps.append(
                step_entry(
                    "close_project",
                    STEP_CHANGED,
                    detail={"project_id": pid},
                )
            )
        except Exception as exc:
            steps.append(step_entry("close_project", STEP_FAILED, error=str(exc)))

    # stop_server
    if not stop_server:
        steps.append(
            step_entry(
                "stop_server", STEP_SKIPPED, detail={"reason": "stop_server=false"}
            )
        )
    else:
        if not is_local_server_url(url):
            steps.append(
                step_entry(
                    "stop_server",
                    STEP_FAILED,
                    error="refusing to stop remote GNS3 server",
                    detail={"server_url": url},
                )
            )
        else:
            try:
                stop_result = await stop_gns3_server(url)
                if stop_result.get("status") == "success":
                    steps.append(
                        step_entry(
                            "stop_server",
                            STEP_CHANGED if stop_result.get("stopped") else STEP_SUCCESS,
                            detail=stop_result,
                        )
                    )
                else:
                    steps.append(
                        step_entry(
                            "stop_server",
                            STEP_FAILED,
                            error=stop_result.get("error") or "stop failed",
                            detail=stop_result,
                        )
                    )
            except Exception as exc:
                steps.append(step_entry("stop_server", STEP_FAILED, error=str(exc)))

    any_failed = any(s.get("status") == STEP_FAILED for s in steps)
    any_done = any(s.get("status") in (STEP_SUCCESS, STEP_CHANGED) for s in steps)
    if any_failed and any_done:
        status = STATUS_PARTIAL
    elif any_failed:
        status = "error"
    else:
        status = STATUS_SUCCESS

    return goal_envelope(
        goal,
        status,
        steps,
        result={
            "project_id": pid,
            "stop_nodes": stop_nodes,
            "close_project": close_project,
            "stop_server": stop_server,
            "server_url": url,
        },
        error=None if status == STATUS_SUCCESS else "one or more cleanup steps failed",
    )
