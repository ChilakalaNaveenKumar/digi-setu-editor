"""
Sessions = chat threads inside a workspace.

Listing + creating live under `/api/workspaces/{wsid}/sessions` so the URL
expresses the parent relationship; rename/delete live under `/api/sessions`
because the workspace id is implicit in the session record.

Authorisation: every endpoint requires a signed-in user (via Clerk in
prod, the synthetic "dev" user in dev mode) and goes through the
ownership-aware helpers so cross-tenant access returns 404.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response

from models.workspace import SessionCreate, SessionModelUpdate, SessionRename
from routes._helpers import session_for_user_or_404, workspace_for_user_or_404
from services.auth import require_user
from services.billing import CreditLedger
from services.chat_storage import (
    cleanup_for_user as _cleanup_for_user,
    cycle_status_for_user as _cycle_status_for_user,
    default_keep as _default_keep,
    run_cycle_for_user as _run_cycle_for_user,
    stats_for_user as _stats_for_user,
)
from services.history import load_history
from services.models_registry import is_allowed
from services.registry import Registry
from services.user_prefs import user_prefs

router = APIRouter(tags=["sessions"])


@router.get("/api/workspaces/{wsid}/sessions")
async def list_sessions_in_workspace(
    wsid: str, user_id: str = Depends(require_user)
) -> dict[str, Any]:
    workspace_for_user_or_404(wsid, user_id)
    reg = Registry.instance()
    # Opportunistic GC: drop "ghost" sessions (created via POST but
    # never followed by a user message — usually a "+ New chat" tab
    # that got closed before connecting). 5 min threshold is well
    # above the worst-case page-load → first-prompt latency.
    reg.prune_empty_sessions(workspace_id=wsid)
    return {"sessions": reg.list_sessions(wsid)}


@router.post("/api/workspaces/{wsid}/sessions")
async def create_session(
    wsid: str,
    payload: SessionCreate | None = None,
    user_id: str = Depends(require_user),
) -> dict[str, Any]:
    workspace_for_user_or_404(wsid, user_id)
    title = ((payload.title if payload else "") or "").strip()
    requested_model = (payload.model if payload else None)

    # If the client passed an explicit model, validate it against the
    # user's plan so we never persist a model the user can't use. Same
    # check the model PATCH route uses below — duplicate intentional;
    # cheaper than adding a route helper just for this one call.
    if requested_model:
        plan_id = CreditLedger.instance().get_plan_id(user_id)
        if not is_allowed(requested_model, plan_id):
            raise HTTPException(
                status_code=403,
                detail=f"model '{requested_model}' is not available on the {plan_id} plan",
            )

    try:
        return Registry.instance().create_session(
            wsid, title=title, model=requested_model
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown workspace: {wsid}")


@router.patch("/api/sessions/{sid}/model")
async def set_session_model(
    sid: str,
    payload: SessionModelUpdate,
    user_id: str = Depends(require_user),
) -> dict[str, Any]:
    """Switch the model for an existing session.

    The change applies to the *next* prompt — the currently running pi
    subprocess (if any) keeps the model it was spawned with. Frontend
    surfaces this by labelling the picker's selection "from next prompt"
    when the chat WS is open.
    """
    sess_rec = session_for_user_or_404(sid, user_id)
    plan_id = CreditLedger.instance().get_plan_id(user_id)
    if not is_allowed(payload.model, plan_id):
        raise HTTPException(
            status_code=403,
            detail=f"model '{payload.model}' is not available on the {plan_id} plan",
        )
    try:
        result = Registry.instance().set_session_model(sid, payload.model)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown session: {sid}")

    # Remember this pick as the workspace's default for the next new
    # chat. Per-workspace memory means each folder stays "sticky" on
    # whatever model the user used there last — they don't have to
    # re-pick every time they hop between projects with different
    # cost/quality trade-offs.
    wsid = (sess_rec.get("workspace_id") or "").strip()
    if wsid:
        user_prefs().set_workspace_model(user_id, wsid, payload.model)

    return result


@router.patch("/api/sessions/{sid}")
async def rename_session(
    sid: str, payload: SessionRename, user_id: str = Depends(require_user)
) -> dict[str, Any]:
    session_for_user_or_404(sid, user_id)
    try:
        return Registry.instance().rename_session(sid, payload.title.strip())
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown session: {sid}")


@router.delete("/api/sessions/{sid}")
async def delete_session(
    sid: str, user_id: str = Depends(require_user)
) -> dict[str, Any]:
    session_for_user_or_404(sid, user_id)
    try:
        rec = Registry.instance().delete_session(sid)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown session: {sid}")
    return {"ok": True, "session": rec}


@router.get("/api/sessions/{sid}/history")
async def get_session_history(
    sid: str,
    response: Response,
    user_id: str = Depends(require_user),
) -> dict[str, Any]:
    """Return the rendered chat-message stream for `sid` (used on resume).

    The response is `{messages: ChatMessage[]}` matching the frontend's
    domain model exactly — the chat store hydrates it as-is, no second
    transformation step. See services/history.py for the projection rules.
    """
    session_for_user_or_404(sid, user_id)
    # Partial-turn snapshots land milliseconds before this GET (after Stop
    # / disconnect). Never serve a stale cached body from a CDN or browser.
    response.headers["Cache-Control"] = "no-store"
    return {"messages": load_history(Registry.instance().session_chat_dir(sid))}


# ── Storage cleanup (account-wide) ─────────────────────────────────
# Web policy: a rolling 90-day cycle automatically sweeps every
# user-removable artifact (chats, audits, uploads) older than the
# cycle window. The SPA shows a banner 5 days before each sweep.
#
# Routes:
#   GET  /api/storage/cycle      → cycle status (banner data + pending counts)
#   POST /api/storage/cycle/run  → force-run the cycle now (the
#                                  "Clean now" button)
#
# The legacy keep-newest-100 endpoints below are retained so older
# SPA versions in the wild keep working during rollout. Once the new
# UI is everywhere we can drop them.
@router.get("/api/storage/cycle")
async def get_storage_cycle(
    background: BackgroundTasks,
    user_id: str = Depends(require_user),
) -> dict[str, Any]:
    """Cycle state for the SPA banner.

    Side effect: if the cycle is past due and the SPA-rendered
    banner has already been visible for ``banner_lead_days``, we
    schedule the actual sweep as a background task so it runs
    AFTER the response is sent. This is how "auto-cleanup at 90
    days" is implemented without a cron / scheduler — every page
    load nudges the cycle forward when due.

    The user already had at least ``banner_lead_days`` of warning
    (status returned ``show_banner: True`` for that whole window),
    so the actual sweep at day 90 is the documented behavior, not
    a surprise.
    """
    status = _cycle_status_for_user(user_id)
    if status["days_until_cycle"] == 0 and status["last_cycle_at"] is not None:
        # Past-due and not a fresh account → auto-sweep in the
        # background. Brand-new accounts (last_cycle_at is None)
        # never auto-sweep — they get a full window first.
        background.add_task(_run_cycle_for_user, user_id, force=False)
    return status


@router.post("/api/storage/cycle/run")
async def run_storage_cycle(
    payload: dict[str, Any] | None = None,
    user_id: str = Depends(require_user),
) -> dict[str, Any]:
    """Run the 90-day sweep now.

    Body shape:
      ``{"force": true}``  → manual "Clean now" — runs immediately
                             even if the cycle isn't due.
      ``{"force": false}`` → only run if the cycle is actually due
                             (e.g. used by a periodic background
                             task running on each request).
    """
    force = bool((payload or {}).get("force", False))
    return _run_cycle_for_user(user_id, force=force)


# Legacy: keep-newest-100 endpoints. Used by older SPA bundles still
# in user caches; the new banner-driven flow uses /api/storage/cycle.
@router.get("/api/workspaces/{wsid}/storage")
async def get_workspace_storage(
    wsid: str, user_id: str = Depends(require_user)
) -> dict[str, Any]:
    workspace_for_user_or_404(wsid, user_id)
    return _stats_for_user(user_id, keep=_default_keep())


@router.post("/api/workspaces/{wsid}/storage/cleanup")
async def cleanup_workspace_storage(
    wsid: str, user_id: str = Depends(require_user)
) -> dict[str, Any]:
    workspace_for_user_or_404(wsid, user_id)
    return _cleanup_for_user(user_id, keep=_default_keep())
