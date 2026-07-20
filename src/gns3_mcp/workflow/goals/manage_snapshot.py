"""gns3_manage_snapshot goal implementation."""

from __future__ import annotations

from typing import Any, Dict, Optional

from gns3_mcp.gns3_client import GNS3APIClient, GNS3Config
from gns3_mcp.server_lifecycle import ensure_gns3_server, normalize_server_url
from gns3_mcp.workflow.confirm import consume_token, issue_token
from gns3_mcp.workflow.envelopes import (
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
from gns3_mcp.workflow.resolve import (
    ResolveAmbiguous,
    ResolveMissing,
    resolve_or_missing_project,
    resolve_project,
    resolve_snapshot,
)
from gns3_mcp.workflow.runner import Step, run_steps

_DESTRUCTIVE = {"restore", "delete_snapshot", "delete_project"}


async def manage_snapshot_goal(
    *,
    operation: str,
    project_name: Optional[str] = None,
    project_id: Optional[str] = None,
    snapshot_name: Optional[str] = None,
    snapshot_id: Optional[str] = None,
    confirmation_token: Optional[str] = None,
    safety_snapshot_name: Optional[str] = None,
    server_url: str = "http://localhost:3080",
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> Dict[str, Any]:
    goal = "manage_snapshot"
    op = (operation or "").strip().lower()
    if op not in {"create", "list", "restore", "delete_snapshot", "delete_project"}:
        return error_envelope(
            goal,
            "operation must be create|list|restore|delete_snapshot|delete_project",
        )
    url = normalize_server_url(server_url)
    ctx: Dict[str, Any] = {"client": None, "project": None, "result": None}

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
            detail={"project_id": project.get("project_id"), "name": project.get("name")},
        )

    # --- ensure + resolve first for all ops ---
    pre = await run_steps(
        [
            Step("ensure_server", ensure_step),
            Step("resolve_project", resolve_project_step),
        ]
    )
    if pre.status != STATUS_SUCCESS:
        return goal_envelope(goal, pre.status, pre.steps, error=pre.error)

    client: GNS3APIClient = ctx["client"]
    project = ctx["project"]
    pid = project["project_id"]
    steps = list(pre.steps)

    target = {
        "operation": op,
        "project_id": pid,
        "project_name": project.get("name"),
        "snapshot_id": snapshot_id,
        "snapshot_name": snapshot_name,
    }

    if op in _DESTRUCTIVE and not confirmation_token:
        token, expires = issue_token(op, target)
        impact = {
            "operation": op,
            "project_id": pid,
            "project_name": project.get("name"),
            "snapshot_id": snapshot_id,
            "snapshot_name": snapshot_name,
        }
        if op == "restore":
            impact["note"] = "restore will be preceded by an automatic safety snapshot when possible"
        steps.append(
            step_entry(
                "authorization",
                STEP_SUCCESS,
                detail={"phase": "preview", "action": op},
            )
        )
        return confirmation_required_envelope(
            goal,
            steps,
            action=op,
            target=target,
            impact=impact,
            confirmation_token=token,
            expires_at=expires,
        )

    if op in _DESTRUCTIVE:
        consumed = consume_token(confirmation_token, op, target)
        if not consumed.get("ok"):
            steps.append(
                step_entry(
                    "authorization",
                    STEP_FAILED,
                    error=consumed.get("error") or "token rejected",
                )
            )
            return goal_envelope(
                goal,
                "error",
                steps,
                error=consumed.get("error") or "token rejected",
            )
        steps.append(
            step_entry(
                "authorization",
                STEP_SUCCESS,
                detail={"phase": "consumed", "action": op},
            )
        )

    try:
        if op == "list":
            snaps = await client.get_snapshots(pid)
            steps.append(
                step_entry("list_snapshots", STEP_SUCCESS, detail={"count": len(snaps)})
            )
            ctx["result"] = {"snapshots": snaps, "total": len(snaps)}
        elif op == "create":
            name = (snapshot_name or "").strip()
            if not name:
                steps.append(
                    step_entry("create_snapshot", STEP_FAILED, error="snapshot_name required")
                )
                return goal_envelope(goal, "error", steps, error="snapshot_name required")
            try:
                existing = await resolve_snapshot(
                    client, pid, snapshot_name=name
                )
                steps.append(
                    step_entry(
                        "create_snapshot",
                        STEP_SKIPPED,
                        detail={
                            "action": "reuse",
                            "snapshot_id": existing.get("snapshot_id"),
                            "name": existing.get("name"),
                        },
                    )
                )
                ctx["result"] = {"snapshot": existing, "action": "reuse"}
            except ResolveMissing:
                created = await client.create_snapshot(pid, name)
                steps.append(
                    step_entry(
                        "create_snapshot",
                        STEP_CHANGED,
                        detail={
                            "snapshot_id": created.get("snapshot_id")
                            if isinstance(created, dict)
                            else None,
                            "name": name,
                        },
                    )
                )
                ctx["result"] = {"snapshot": created, "action": "create"}
        elif op == "restore":
            snap = await resolve_snapshot(
                client, pid, snapshot_id=snapshot_id, snapshot_name=snapshot_name
            )
            safety_name = safety_snapshot_name or f"safety-before-restore-{snap.get('name') or snap.get('snapshot_id')}"
            try:
                safety = await client.create_snapshot(pid, safety_name)
                steps.append(
                    step_entry(
                        "safety_snapshot",
                        STEP_CHANGED,
                        detail={
                            "name": safety_name,
                            "snapshot_id": safety.get("snapshot_id")
                            if isinstance(safety, dict)
                            else None,
                        },
                    )
                )
            except Exception as exc:
                steps.append(
                    step_entry(
                        "safety_snapshot",
                        STEP_FAILED,
                        error=f"safety snapshot failed: {exc}",
                    )
                )
                return goal_envelope(
                    goal, "error", steps, error=f"safety snapshot failed: {exc}"
                )
            restored = await client.restore_snapshot(pid, snap["snapshot_id"])
            steps.append(
                step_entry(
                    "restore_snapshot",
                    STEP_CHANGED,
                    detail={"snapshot_id": snap.get("snapshot_id"), "name": snap.get("name")},
                )
            )
            ctx["result"] = {"restored": restored, "from_snapshot": snap}
        elif op == "delete_snapshot":
            snap = await resolve_snapshot(
                client, pid, snapshot_id=snapshot_id, snapshot_name=snapshot_name
            )
            await client.delete_snapshot(pid, snap["snapshot_id"])
            steps.append(
                step_entry(
                    "delete_snapshot",
                    STEP_CHANGED,
                    detail={"snapshot_id": snap.get("snapshot_id"), "name": snap.get("name")},
                )
            )
            ctx["result"] = {"deleted_snapshot_id": snap.get("snapshot_id")}
        elif op == "delete_project":
            await client.delete_project(pid)
            steps.append(
                step_entry(
                    "delete_project",
                    STEP_CHANGED,
                    detail={"project_id": pid, "name": project.get("name")},
                )
            )
            ctx["result"] = {"deleted_project_id": pid}
    except (ResolveMissing, ResolveAmbiguous, ValueError) as exc:
        steps.append(step_entry(op, STEP_FAILED, error=str(exc)))
        return goal_envelope(goal, "error", steps, error=str(exc))
    except Exception as exc:
        steps.append(step_entry(op, STEP_FAILED, error=str(exc)))
        return goal_envelope(goal, "error", steps, error=str(exc))

    return goal_envelope(
        goal,
        STATUS_SUCCESS,
        steps,
        result={
            "operation": op,
            "project_id": pid,
            "project_name": project.get("name"),
            **(ctx.get("result") or {}),
        },
    )
