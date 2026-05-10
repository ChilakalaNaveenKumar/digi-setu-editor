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

from fastapi import APIRouter, Depends, HTTPException

from models.workspace import SessionCreate, SessionModelUpdate, SessionRename
from routes._helpers import session_for_user_or_404, workspace_for_user_or_404
from services.auth import require_user
from services.chat_storage import (
    cleanup_categories as _cleanup_categories,
    workspace_storage_summary as _workspace_storage_summary,
)
from services.history import load_history
from services.models_registry import is_allowed
from services.plan_cache import get_plan_id as _get_plan_id
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
        plan_id = _get_plan_id(user_id)
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
    plan_id = _get_plan_id(user_id)
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
    sid: str, user_id: str = Depends(require_user)
) -> dict[str, Any]:
    """Return the rendered chat-message stream for `sid` (used on resume).

    The response is `{messages: ChatMessage[]}` matching the frontend's
    domain model exactly — the chat store hydrates it as-is, no second
    transformation step. See services/history.py for the projection rules.
    """
    session_for_user_or_404(sid, user_id)
    return {"messages": load_history(Registry.instance().session_chat_dir(sid))}


# ── Storage cleanup (per-workspace, manual, multi-category) ────────
# Desktop policy: each workspace exposes 4 cleanup categories — chats
# (newest-100 keep), audits (90-day age trim), uploads (30-day age
# trim), and the destructive "purge shadow git" (kills the AI revert
# history for this workspace).
#
# GET returns the unified summary the Storage panel renders; POST
# accepts ``{categories: ["chats", "audits", ...]}`` and runs each
# in turn. We intentionally split GET vs POST so the UI can show
# "you'd free X MB" without ever risking an accidental delete on
# page load.
#
# See services/chat_storage.py for per-category retention policy and
# the (deliberately tight) list of things we don't auto-touch.
@router.get("/api/workspaces/{wsid}/storage")
async def get_workspace_storage(
    wsid: str, user_id: str = Depends(require_user)
) -> dict[str, Any]:
    workspace_for_user_or_404(wsid, user_id)
    return _workspace_storage_summary(wsid)


@router.post("/api/workspaces/{wsid}/storage/cleanup")
async def cleanup_workspace_storage(
    wsid: str,
    payload: dict[str, Any] | None = None,
    user_id: str = Depends(require_user),
) -> dict[str, Any]:
    """Run cleanup for the categories listed in ``payload.categories``.

    Body shape: ``{"categories": ["chats", "audits", "uploads", "shadows"]}``
    — any subset is fine. Unknown categories are silently ignored
    (forward-compat — see ``services.chat_storage.cleanup_categories``).

    Empty / missing body is treated as "no-op": the SPA always knows
    which categories the user ticked and sends them explicitly.
    """
    workspace_for_user_or_404(wsid, user_id)
    raw = (payload or {}).get("categories")
    categories: list[str] = [str(c) for c in raw] if isinstance(raw, list) else []
    return _cleanup_categories(wsid, categories=categories)
