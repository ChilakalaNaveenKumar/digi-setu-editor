"""
Chat WebSocket bridge: browser ⇄ pi RPC subprocess.

Per-session pipeline:

    browser  ⇄  /ws/sessions/{session_id}
                   │
                   ├─ Registry.get_session(sid) → workspace_path
                   ├─ PiSession spawned with cwd=workspace_path
                   ├─ WatcherRegistry.acquire(workspace_path) → fs_change events
                   ├─ ShadowGitRegistry.for_workspace(workspace_path) → snapshot per tool call
                   └─ BackgroundProcessRegistry (still global; per-workspace in Phase 3)

The handler runs four pumps concurrently and tears them down when any one
exits (typical case: client disconnects → ws_to_pi exits → all others
cancel). Cleanup releases the watcher refcount, kills the subprocess, and
unsubscribes from the bg event stream.
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from config import (
    BYOK_MODE,
    DEPLOY_MODE,
    PROMPT_TIMEOUT_SECONDS,
    WORKSPACE_DISK_QUOTA_MB,
)
from services.auth import user_for_websocket
from services.bg_processes import BackgroundProcessHub
from services.billing import (
    CreditLedger,
    estimate_prompt_cost,
    extract_sub_llm_usage,
    usage_token_total,
)
from services.disk_usage import invalidate as invalidate_workspace_size
from services.disk_usage import over_quota as workspace_over_quota
from services.file_watcher import WatcherRegistry
from services.models_registry import (
    DEFAULT_MODEL_ID,
    get_model,
    is_allowed,
    pick_default_for_plan,
)
from services.audit import record as audit_record
from services.pi_session import PiSession
from services.policy import check_bash, scrub_secrets
from services.sandbox_layout import stamp_sandbox_dir
from services.rate_limit import RateLimiter
from services.registry import Registry
from services.session_locks import session_locks
from services.shadow_git import ShadowGitRegistry
from services.title_gen import generate_title
from services.user_prefs import user_prefs

# Magic title prefix used by extensions/permission.ts to identify a
# permission-gate select() (vs. some other extension's plain UI request).
# Must stay in sync with the constant of the same name in permission.ts.
_PERMISSION_PREFIX = "[pi-permission]"

router = APIRouter()


_TITLE_MAX_WORDS = 6
_TITLE_MAX_CHARS = 50

# Multi-word polite/filler prefixes stripped from the start of a prompt
# before we extract the title. Order matters — longest first so "could
# you please" doesn't leave a stray "please".
_TITLE_LEADERS = (
    "could you please",
    "would you please",
    "can you please",
    "could you",
    "would you",
    "can you",
    "i need you to",
    "i want you to",
    "please help me",
    "help me",
    "please",
)

# Single-word imperative verbs we drop when they're the FIRST word.
# These add no information ("Run X" → just "X" works as a title).
# We don't strip them mid-sentence because then "Generate report" would
# become an empty string, and we don't strip them when they're the
# only word left ("Run" alone is still a valid title).
_TITLE_IMPERATIVES = {
    "run", "create", "make", "build", "generate", "write", "edit", "update",
    "fix", "add", "show", "list", "find", "give", "do", "implement",
    "execute", "start", "test", "check", "review", "analyze", "summarize",
    "explain", "describe", "tell", "print", "echo", "call",
}

# Stop-words dropped from the head of the title only. Keeps articles in
# the middle of a sentence intact.
_TITLE_LEADING_STOP = {"the", "a", "an", "my", "this", "that", "some"}


def _derive_title(prompt: str) -> str:
    """Build a short, clean session title from the first user prompt.

    Strategy:
      1. Collapse whitespace, strip backticks / triple-backtick fences.
      2. Strip multi-word polite leaders ("could you please", …).
      3. Strip a single-word imperative verb if it's the first word.
      4. Strip a leading article/demonstrative.
      5. Take the first ~6 substantive words, ≤50 chars, capitalised.

    Examples (input → output):
      "Run the bash command `echo hello permission test`"
        → "Echo hello permission test"
      "Create a file hello.txt with the text \"Hello\""
        → "File hello.txt with text \"Hello\""
      "Please can you help me debug this Python script that …"
        → "Debug this Python script"
      "what is the capital of France?"
        → "What is the capital of France?"
    """
    text = (prompt or "").strip()
    if not text:
        return ""
    # Collapse whitespace + drop backtick-fenced code blocks (triple
    # backticks) AND inline backticks. Code is rarely descriptive of a
    # title — it just makes the head longer with low signal.
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = text.replace("`", "")
    text = " ".join(text.split())
    if not text:
        return ""
    # Strip multi-word polite leaders. Loop so chains like
    # "please can you ..." get peeled layer by layer; bound the loop
    # to 4 passes so a pathological input can't spin.
    lower = text.lower()
    for _ in range(4):
        before = text
        for leader in _TITLE_LEADERS:
            if lower.startswith(leader + " "):
                text = text[len(leader) + 1 :].lstrip()
                lower = text.lower()
                break
        if text == before:
            break
    # Strip a single imperative verb if it's the first word.
    words = text.split()
    if words and words[0].lower().rstrip(",.;:") in _TITLE_IMPERATIVES and len(words) > 1:
        words = words[1:]
    # Strip a leading article / demonstrative.
    if words and words[0].lower().rstrip(",.;:") in _TITLE_LEADING_STOP and len(words) > 1:
        words = words[1:]
    head_words = words[: _TITLE_MAX_WORDS]
    head = " ".join(head_words).rstrip(",;:.")
    # Capitalise first character without forcing TitleCase on the rest
    # (preserves identifiers / file paths / acronyms).
    if head:
        head = head[0].upper() + head[1:]
    if len(head) > _TITLE_MAX_CHARS:
        head = head[: _TITLE_MAX_CHARS - 1].rstrip() + "…"
    elif len(words) > _TITLE_MAX_WORDS:
        head = head + "…"
    return head


@router.websocket("/ws/sessions/{session_id}")
async def session_ws(ws: WebSocket, session_id: str) -> None:
    # Verify *before* accept() so unauthenticated upgrades fail at the
    # handshake layer with a proper 401, not a 1008 close. Browsers
    # surface 401 nicely in the network tab; 1008-after-accept is far
    # less debuggable.
    user_id = await user_for_websocket(ws)
    if user_id is None:
        await ws.close(code=4401)
        return

    # Rate-limit WS upgrades per user. 4429 is a custom close code (the
    # WS spec reserves 4xxx for application use); the frontend can
    # surface it as "you're connecting too fast" without misreading it
    # as a generic disconnect.
    rl = RateLimiter.instance()
    if not rl.try_take(user_id, "ws.connect"):
        await ws.close(code=4429)
        return

    await ws.accept()

    reg = Registry.instance()
    sess_rec = reg.get_session(session_id)
    if not sess_rec:
        await ws.send_json({"type": "_bridge_error", "message": f"unknown session id: {session_id}"})
        await ws.close()
        return

    ws_rec = reg.get_workspace(sess_rec["workspace_id"])
    if not ws_rec:
        await ws.send_json(
            {"type": "_bridge_error", "message": f"workspace gone: {sess_rec['workspace_id']}"}
        )
        await ws.close()
        return

    # Owner check: collapsing into the same "unknown session" message
    # so a hostile client can't enumerate session ids.
    if ws_rec.get("owner_user_id") != user_id:
        await ws.send_json({"type": "_bridge_error", "message": f"unknown session id: {session_id}"})
        await ws.close()
        return

    # Multi-tab guard. If this session id is already being served by
    # another WS (same user opened a second tab, or a stale connection
    # didn't tear down cleanly), kick the old one with code 4409 and
    # take ownership ourselves. The frontend listens for 4409 and
    # surfaces "Continued in another tab" instead of a generic
    # disconnect notice.
    locks = session_locks()
    await locks.claim(session_id, ws)

    workspace_path = Path(ws_rec["path"])
    chats_dir = reg.session_chat_dir(session_id)

    # Self-heal a missing workspace directory. This happens when:
    #   - someone wiped web/data/workspaces/ during dev
    #   - the registry was restored from a backup but the on-disk
    #     workspaces weren't (or vice versa)
    #   - a deploy migration left a stale row pointing at a path that
    #     was rotated out
    # Re-creating the dir is the friendly choice: the user keeps their
    # chat history and can immediately start a fresh prompt without
    # being thrown back to the picker. Original files are gone either
    # way — we never had them on this machine.
    if not workspace_path.exists():
        try:
            workspace_path.mkdir(parents=True, exist_ok=True)
            # Stamp the dual-uid sandbox ownership so pi (running as
            # the sandbox uid) can write into this re-created tree.
            # Without this, the AI's first `bash echo > foo.md` would
            # raise EACCES and the session would be effectively read-
            # only until the user manually fixed permissions.
            stamp_sandbox_dir(workspace_path)
            print(
                f"[ws {session_id}] re-created missing workspace dir "
                f"{workspace_path} (registry was stale)",
                file=sys.stderr,
            )
        except OSError as exc:
            await ws.send_json({
                "type": "_bridge_error",
                "message": f"workspace directory could not be created: {exc}",
                "code": "workspace_missing",
            })
            await ws.close()
            return

    # Spawning a pi subprocess is expensive (forks node, loads model
    # client, warms MCP servers). Throttle this separately from the
    # cheap WS upgrade so a hostile client can't burn a thousand
    # subprocesses by reconnecting in a tight loop.
    if not rl.try_take(user_id, "pi.spawn"):
        await ws.send_json(
            {
                "type": "_bridge_error",
                "message": "You're starting chats too quickly. Wait a moment and try again.",
                "code": "rate_limit",
                "bucket": "pi.spawn",
            }
        )
        await ws.close(code=4429)
        return

    # Resolve the model for this spawn:
    #   1. Use the session's pinned model if set AND still allowed on
    #      the user's current plan (they may have downgraded since
    #      pinning Opus).
    #   2. Else fall back to the workspace's last-used model (desktop
    #      remembers per-folder so reopening a workspace defaults to
    #      whatever you used last time there).
    #   3. Otherwise use the cheapest model their plan can afford,
    #      defaulting to Sonnet for paying tiers.
    plan_id = CreditLedger.instance().get_plan_id(user_id)
    pinned_model = (sess_rec.get("model") or "").strip()
    # The session's parent workspace id — defined here so the
    # workspace-default lookup can reuse it. We re-bind the same value
    # below as `workspace_id_for_audit` (kept for the existing audit
    # log call sites) to avoid touching every reference.
    session_workspace_id = (sess_rec.get("workspace_id") or "").strip()
    workspace_default = user_prefs().get_workspace_model(user_id, session_workspace_id) or ""
    if pinned_model and is_allowed(pinned_model, plan_id):
        active_model_id = pinned_model
    elif workspace_default and is_allowed(workspace_default, plan_id):
        active_model_id = workspace_default
    else:
        active_model_id = pick_default_for_plan(plan_id)
    active_model_spec = get_model(active_model_id) or get_model(DEFAULT_MODEL_ID)
    pi_provider = active_model_spec.pi_provider if active_model_spec else None

    # ── BYOK fallback for the default pick ──────────────────────────
    # In BYOK-only desktop launches (no Clerk subscription), the
    # plan-default cycle ends in cloud-routed Haiku, which would
    # then trip the gate below. Substitute the cheapest BYOK-routable
    # model when there's no explicit pin/workspace default — so the
    # user gets a chat instead of an upgrade modal on first launch.
    #
    # We only do this when nothing was pinned: if the user explicitly
    # picked a cloud model we want the gate to fire and explain why.
    if (
        BYOK_MODE
        and not pinned_model
        and not workspace_default
        and active_model_spec is not None
    ):
        from services.byok import (  # noqa: E402
            byok_default_model,
            byok_provider_for,
        )
        from services.models_registry import _MODELS as _ALL_MODELS  # noqa: E402
        if byok_provider_for(active_model_spec) is None:
            fallback = byok_default_model(list(_ALL_MODELS))
            if fallback is not None:
                active_model_id = fallback
                active_model_spec = get_model(fallback) or active_model_spec
                pi_provider = (
                    active_model_spec.pi_provider if active_model_spec else None
                )

    # ── Dispatch: local pi vs cloud relay vs sign-in modal ──────────
    # Three branches in priority order:
    #
    #   1. BYOK_MODE on AND the picked model has a BYOK route
    #      → fall through to the existing local pi spawn below.
    #
    #   2. The picked model has no BYOK route (either because we're
    #      not in BYOK mode at all, or because BYOK is on but the
    #      user has no key compatible with this model's family)
    #      → if the user has a cached Clerk session, hand off to the
    #        cloud relay (`api.digi-setu.com/v1/ws/desktop-relay`)
    #        and return — the relay owns the WS lifetime from there.
    #      → if the user is NOT signed in, close with a clear
    #        sign-in / upgrade message. Frontend ModelPicker gates
    #        this client-side too, but we keep the backend check as
    #        belt-and-braces defence.
    #
    # The relay branch is what turns "no Vertex creds on a stranger's
    # laptop" into "log in, pay subscription, chat works". See
    # docs/desktop-architecture.md §2 for the full architecture.
    if active_model_spec is not None:
        from services.byok import byok_provider_for as _byok_pf  # noqa: E402

        has_byok_route = BYOK_MODE and _byok_pf(active_model_spec) is not None

        if not has_byok_route:
            # Picked model can't be served locally. Route to relay.
            from routes.desktop_auth import get_cached_desktop_session  # noqa: E402

            cached = get_cached_desktop_session()
            if cached is None:
                # Two slightly different toasts so the SPA shows the
                # right CTA: "you have a key, but THIS model needs
                # cloud" vs. "you don't have a key, sign in".
                if BYOK_MODE:
                    await ws.send_json({
                        "type": "_bridge_error",
                        "code": "upgrade_required",
                        "model": active_model_id,
                        "message": (
                            f"Model '{active_model_spec.name}' isn't "
                            "covered by your local key. Sign in for "
                            "cloud access, or pick a model badged BYOK."
                        ),
                    })
                    await ws.close(code=4402)
                else:
                    await ws.send_json({
                        "type": "_bridge_error",
                        "code": "sign_in_required",
                        "message": (
                            "Sign in at digi-setu.com to chat with cloud "
                            "models, or add an AI key to ~/.digi-setu/.env "
                            "to use BYOK mode."
                        ),
                    })
                    await ws.close(code=4401)
                return

            bearer_token, _cached_user = cached
            try:
                from services.relay_bridge import proxy_to_relay  # noqa: E402

                await proxy_to_relay(
                    ws,
                    bearer_token=bearer_token,
                    user_id=user_id,
                )
            except Exception as exc:
                # Last-resort guard: if the bridge itself blew up
                # (uncommon — proxy_to_relay catches its own errors),
                # surface a clean error rather than a 1011 close.
                print(
                    f"[chat_ws] relay bridge failed for {user_id!r}: {exc}",
                    file=sys.stderr,
                )
                try:
                    await ws.send_json({
                        "type": "_bridge_error",
                        "code": "relay_error",
                        "message": f"Relay error: {exc}",
                    })
                    await ws.close(code=1011)
                except Exception:
                    pass
            return

    permission_mode = user_prefs().get_permission_mode(user_id, plan_id=plan_id)
    # Materialise the per-user live file before spawn so the extension's
    # very first tool_call always finds it (no env-fallback path needed).
    permission_mode_file = user_prefs().ensure_live_file(user_id, permission_mode)
    pi = PiSession(
        session_id=session_id,
        workspace_path=workspace_path,
        session_dir=chats_dir,
        model=active_model_id,
        provider=pi_provider,
        permission_mode=permission_mode,
        permission_mode_file=permission_mode_file,
        user_id=user_id,
    )

    # Tell the SPA which model actually got loaded (may differ from
    # what the picker showed if the user downgraded since pinning).
    # The chat header reads this to keep its picker in sync.
    await ws.send_json({
        "type": "_session_info",
        "model": active_model_id,
        "model_name": active_model_spec.name if active_model_spec else active_model_id,
        "plan": plan_id,
        "permission_mode": permission_mode,
        "workspace_id": sess_rec["workspace_id"],
    })

    # Per-user concurrency cap + global capacity gate. No-op when the
    # docker runtime isn't in use (subprocess fallback in laptop dev).
    # See services/container_pool.py for the policy.
    try:
        from services import container_pool as _pool
        await _pool.enforce_quotas(user_id)
    except _pool.GlobalCapacityExceeded as exc:
        await ws.send_json({
            "type": "_bridge_error",
            "code": "vm_capacity",
            "message": (
                "The VM is currently at maximum capacity. "
                "Please try again in a minute."
            ),
            "detail": str(exc),
        })
        await ws.close(code=1013)  # Try Again Later
        return
    except Exception as exc:
        print(f"[ws {session_id}] WARN container_pool quota check failed: {exc}", file=sys.stderr)
        # Don't refuse the chat on a transient docker error; let
        # PiSession.start() decide.

    try:
        await pi.start()
    except Exception as exc:
        print(f"[ws {session_id}] failed to start pi: {exc}", file=sys.stderr)
        await ws.send_json({"type": "_bridge_error", "message": f"Failed to start pi: {exc}"})
        await ws.close()
        return

    reg.touch_session(session_id)

    fs_watcher = await WatcherRegistry.instance().acquire(workspace_path)
    fs_queue = fs_watcher.subscribe()

    bg_registry = BackgroundProcessHub.instance().for_workspace(sess_rec["workspace_id"])
    bg_queue = bg_registry.subscribe()

    shadow = ShadowGitRegistry.instance().for_workspace(workspace_path)
    await shadow.ensure_init()

    pending_tool_calls: dict[str, dict[str, str]] = {}
    current_user_message_id: dict[str, Optional[str]] = {"id": None}

    # Outstanding permission prompts the user hasn't answered yet, keyed by
    # the extension_ui_request id pi assigned. We need this to:
    #   1. audit the user's decision (we have only the id in the response)
    #   2. survive a tab switch — when the user returns, the modal can be
    #      restored from this state (frontend re-asks via /api in v1.1).
    pending_permissions: dict[str, dict[str, Any]] = {}
    workspace_id_for_audit = sess_rec["workspace_id"]

    # Per-prompt watchdog state. `turn_started_at` is set when ws_to_pi
    # forwards a prompt, cleared when pi_to_ws sees the matching
    # message_end. The watchdog task wakes every few seconds and tears
    # down the WS if a turn has been running longer than
    # PROMPT_TIMEOUT_SECONDS — protecting the user from a runaway tool
    # loop that would otherwise drain their token budget for hours.
    turn_started_at: dict[str, Optional[float]] = {"ts": None}
    timed_out: dict[str, bool] = {"flag": False}
    aborted: dict[str, bool] = {"flag": False}

    # Background title-generation state. We only ever fire this once per
    # session (the first time we see a non-empty user prompt). Storing
    # the task handle lets us a) avoid double-firing on subsequent
    # prompts, b) cancel cleanly if the WS tears down before Haiku
    # responds.
    title_task: dict[str, Optional[asyncio.Task[None]]] = {"task": None}

    # Whether the user has actually said anything in this WS session.
    # Used at teardown to decide if a "user opened the chat, never
    # typed, closed the tab" session should be silently garbage-
    # collected so the picker doesn't accumulate empty rows. We only
    # delete on teardown when this is False AND the registry's chat
    # log is also empty (defensive — prevents clobbering a session
    # the user resumed from history but didn't send anything in
    # *this* connection).
    had_user_message: dict[str, bool] = {"flag": False}

    async def _upgrade_title_via_llm(prompt_text: str, heuristic_title: str) -> None:
        """Background helper: ask Haiku for a polished title and CAS-swap
        it in. On any failure we keep the heuristic title (no error path).

        Broadcasts a `_session_titled` envelope on success so the SPA's
        chat-session store can update the picker / brand header without
        waiting for a refresh. The envelope is also harmless if the WS
        is already closed — `send_json` will raise and the surrounding
        `try` swallows it.
        """
        try:
            llm_title = await generate_title(prompt_text)
        except Exception as exc:
            print(
                f"[ws {session_id}] title_gen raised: {exc!r}",
                file=sys.stderr,
            )
            return
        if not llm_title:
            return
        rec = reg.maybe_replace_heuristic_title(
            session_id, heuristic_title, llm_title
        )
        if not rec:
            return
        try:
            await ws.send_json(
                {
                    "type": "_session_titled",
                    "sessionId": session_id,
                    "title": rec["title"],
                    "workspaceId": rec.get("workspace_id"),
                }
            )
        except Exception:
            # WS already closed — ignore. The title is persisted in the
            # registry; the next picker load will pick it up.
            pass

    def _remember_tool_args(evt: dict[str, Any]) -> None:
        """
        Cache (toolName, path) per tool_call_id as it arrives so we can
        attach the path to the post-execution snapshot. The path can come
        either from `args.path` or `args.file_path` depending on the tool.
        """
        sub = evt.get("assistantMessageEvent") or {}
        if sub.get("type") == "toolcall_end":
            tc = sub.get("toolCall") or {}
            tid = tc.get("id")
            if isinstance(tid, str):
                args = tc.get("arguments") or {}
                pending_tool_calls[tid] = {
                    "name": str(tc.get("name") or "tool"),
                    "path": str(args.get("path") or args.get("file_path") or ""),
                }
            return

        if evt.get("type") in ("tool_execution", "tool_execution_start"):
            tid = evt.get("toolCallId")
            if isinstance(tid, str):
                args = evt.get("args") or evt.get("arguments") or {}
                if not isinstance(args, dict):
                    args = {}
                prev = pending_tool_calls.get(tid, {})
                pending_tool_calls[tid] = {
                    "name": str(evt.get("toolName") or prev.get("name") or "tool"),
                    "path": str(
                        args.get("path") or args.get("file_path") or prev.get("path") or ""
                    ),
                }

    async def _maybe_snapshot(evt: dict[str, Any]) -> None:
        """On every successful tool execution, snapshot the workspace."""
        if evt.get("type") not in ("tool_execution_end", "tool_result"):
            return
        if evt.get("isError"):
            return
        tid = evt.get("toolCallId")
        if not isinstance(tid, str):
            return
        meta = pending_tool_calls.pop(tid, {})
        try:
            await shadow.snapshot_after_tool_call(
                tool_call_id=tid,
                tool_name=meta.get("name") or str(evt.get("toolName") or "tool"),
                path=meta.get("path") or "",
                user_message_id=current_user_message_id["id"],
            )
        except Exception as exc:
            print(f"[ws {session_id}] shadow-git snapshot failed for {tid}: {exc}", file=sys.stderr)

    ledger = CreditLedger.instance()

    def _maybe_charge_usage(evt: dict[str, Any]) -> None:
        """On `message_end` from an assistant turn, charge:
          - the daily token bucket (rate-limit fairness signal)
          - the per-user dollar ledger (subscription credit)

        We sum input + output + cache reads + cache writes so the
        budget reflects "what we actually paid the model provider
        for", not just the user-visible bytes. Charge happens
        unconditionally — we never amputate a half-finished answer
        the user already paid for. The cap is enforced on the *next*
        prompt instead (see ws_to_pi).

        Also clears the prompt watchdog: a `message_end` means the
        assistant turn is done, so the wall-clock timer for that
        turn should stop (the user is back in the driver's seat)."""
        if evt.get("type") != "message_end":
            return
        message = evt.get("message") or {}
        if message.get("role") not in (None, "assistant"):
            return
        # Clear the per-prompt watchdog — the assistant returned a
        # complete message, so any tool loop wrapped up cleanly.
        wall_seconds = 0.0
        started = turn_started_at.get("ts")
        if started is not None:
            wall_seconds = max(0.0, asyncio.get_event_loop().time() - started)
            turn_started_at["ts"] = None
        usage = message.get("usage") or {}
        if not isinstance(usage, dict):
            return
        total = (
            int(usage.get("input") or 0)
            + int(usage.get("output") or 0)
            + int(usage.get("cacheRead") or 0)
            + int(usage.get("cacheWrite") or 0)
        )
        if total > 0:
            rl.charge_tokens(user_id, total)
        cost = estimate_prompt_cost(
            usage,
            model_id=active_model_id,
            wall_seconds=wall_seconds,
        )
        # Always log the event — even on $0 turns — so the activity
        # table shows the user something happened. The aggregate
        # spent_usd / prompts counter is gated inside note_cost.
        ledger.note_cost(
            user_id,
            cost.total_usd,
            source="chat",
            model=cost.model_id,
            session_id=session_id,
            workspace_id=workspace_id_for_audit,
            usage=usage,
            breakdown={
                "llm_usd": cost.llm_usd,
                "vm_usd": cost.vm_usd,
                "margin_usd": cost.margin_usd,
                "total_usd": cost.total_usd,
            },
        )

        # ── BYOK ledger (desktop only) ──────────────────────────────
        # When BYOK is active and the picked model has a path through
        # the user's own keys, also record a token-only row in the
        # local SQLite. The Activity page reads this so the user can
        # see usage that never hit our cloud relay (no $ figure
        # because we don't know their provider's price).
        if BYOK_MODE and active_model_spec is not None:
            from services.byok import byok_provider_for as _byok_pf  # noqa: E402
            from services.byok_usage import record as _byok_record  # noqa: E402
            _byok_pick = _byok_pf(active_model_spec)
            if _byok_pick is not None:
                _byok_record(
                    session_id=session_id,
                    workspace_id=workspace_id_for_audit,
                    provider=_byok_pick[1],
                    model_id=active_model_id,
                    input_tokens=int(usage.get("input") or 0),
                    output_tokens=int(usage.get("output") or 0),
                    cache_read=int(usage.get("cacheRead") or 0),
                    cache_write=int(usage.get("cacheWrite") or 0),
                )

    def _maybe_charge_tool_sub_llm(evt: dict[str, Any]) -> None:
        """Bill side-LLM calls that happen *inside* tool execute() bodies.

        The parent assistant turn's `message_end` only carries the parent
        model's tokens; tools that spawn their own provider call (Haiku for
        search_docs, Gemini grounded search for web_search) need a separate
        ledger entry, otherwise we under-bill.

        Pure logic lives in services/billing.py:extract_sub_llm_usage so it
        can be unit-tested without spinning up a websocket. This thin
        wrapper just applies the side effects (rate-limit + ledger)."""
        usage = extract_sub_llm_usage(evt)
        if usage is None:
            return
        total = usage_token_total(usage)
        if total <= 0:
            return
        rl.charge_tokens(user_id, total)
        sub_model = str(usage.get("model") or "")
        cost = estimate_prompt_cost(usage, model_id=sub_model or active_model_id)
        # Tool name is on the tool_execution_end / tool_result envelope,
        # not inside `usage`. Surface it on the event so the table can
        # render "search_docs (haiku-4-5)" rows distinctly from chat
        # turns.
        tool_name = str(evt.get("toolName") or "tool")
        ledger.note_cost(
            user_id,
            cost.total_usd,
            source="tool",
            tool=tool_name,
            model=cost.model_id,
            session_id=session_id,
            workspace_id=workspace_id_for_audit,
            usage=usage,
            breakdown={
                "llm_usd": cost.llm_usd,
                "vm_usd": cost.vm_usd,
                "margin_usd": cost.margin_usd,
                "total_usd": cost.total_usd,
            },
        )

    def _maybe_block_bash(evt: dict[str, Any]) -> Optional[dict[str, Any]]:
        """When pi requests a bash exec, evaluate it against the
        policy. If denied we replace the original event with a
        synthetic tool_execution_end carrying the policy reason.

        The agent then sees its tool call "failed" with a clear
        message ("blocked: privilege escalation (sudo/su/doas)") and
        can adapt the next turn — same affordance as if /bin/sudo
        wasn't on PATH.

        Defence-in-depth caveat: this is an *advisory* block — pi has
        already invoked the bash tool by the time we see the event.
        The OS-level deny-list (firewall + filesystem perms,
        documented in deploy/README) is what actually keeps the
        request from succeeding. This filter makes the agent feel
        the policy in its own context window so it stops trying."""
        if DEPLOY_MODE != "web":
            return None
        if evt.get("type") not in ("tool_execution_start", "tool_execution"):
            return None
        if evt.get("toolName") != "bash":
            return None
        args = evt.get("args") or evt.get("arguments") or {}
        if not isinstance(args, dict):
            return None
        cmd = str(args.get("command") or args.get("cmd") or "")
        verdict = check_bash(cmd)
        if verdict.allowed:
            return None
        # Audit deterministic policy hits separately from user-driven
        # decisions so the trail makes it obvious which guard fired.
        audit_record(
            wsid=workspace_id_for_audit,
            sid=session_id,
            uid=user_id,
            tool="bash",
            event="policy_blocked",
            input={"command": cmd},
            reason=verdict.reason,
        )
        return {
            "type": "tool_execution_end",
            "toolCallId": evt.get("toolCallId"),
            "toolName": "bash",
            "isError": True,
            "result": {
                "text": (
                    f"Command refused by web-mode policy.\n"
                    f"  reason: {verdict.reason}\n"
                    f"  command: {cmd[:240]}\n\n"
                    "If this is legitimate work, ask the user to confirm and "
                    "we can revisit the policy."
                ),
            },
        }

    def _maybe_audit_tool_lifecycle(evt: dict[str, Any]) -> None:
        """Append-only trail of every tool that actually ran (started + finished
        with success/failure). Permission decisions are audited separately;
        this captures the "what got executed" side."""
        kind = evt.get("type")
        if kind == "tool_execution_start":
            tool_name = str(evt.get("toolName") or "tool")
            tid = evt.get("toolCallId")
            args = evt.get("args") or evt.get("arguments") or {}
            audit_record(
                wsid=workspace_id_for_audit,
                sid=session_id,
                uid=user_id,
                tool=tool_name,
                event="started",
                input=args if isinstance(args, dict) else None,
                extra={"tool_call_id": tid} if isinstance(tid, str) else None,
            )
        elif kind in ("tool_execution_end", "tool_result"):
            tool_name = str(evt.get("toolName") or "tool")
            tid = evt.get("toolCallId")
            audit_record(
                wsid=workspace_id_for_audit,
                sid=session_id,
                uid=user_id,
                tool=tool_name,
                event="failed" if evt.get("isError") else "completed",
                extra={"tool_call_id": tid} if isinstance(tid, str) else None,
            )

    def _maybe_track_bg_process(evt: dict[str, Any]) -> None:
        """Mirror the @aliou/pi-processes lifecycle into our local registry."""
        if evt.get("type") not in ("tool_execution_end", "tool_result"):
            return
        if evt.get("isError"):
            return
        if evt.get("toolName") != "process":
            return
        result = evt.get("result")
        if not isinstance(result, dict):
            return
        details = result.get("details")
        if not isinstance(details, dict):
            return
        action = details.get("action")
        if action == "start" and details.get("success"):
            bg_registry.register_from_start_result(details)
        elif action == "kill" and details.get("success"):
            bg_registry.mark_ended_from_result(details)

    def _intercept_permission_request(evt: dict[str, Any]) -> Optional[dict[str, Any]]:
        """If pi emits an extension_ui_request whose title carries our magic
        prefix, replace it with a `permission_request` event the SPA knows
        how to render (modal with diff preview + 4-button choice). All other
        extension_ui_request events fall through — they belong to another
        extension and we don't currently surface them in the web UI."""
        if evt.get("type") != "extension_ui_request":
            return None
        method = evt.get("method")
        # Per pi RPC spec: only select / confirm / input / editor block
        # waiting for a response. notify / setStatus / setWidget / setTitle
        # / set_editor_text are fire-and-forget. We silently swallow the
        # latter (they're for the TUI, not the web UI) and only cancel the
        # former when they're not for us.
        BLOCKING = {"select", "confirm", "input", "editor"}
        title = evt.get("title")
        if not isinstance(title, str) or not title.startswith(_PERMISSION_PREFIX):
            if method in BLOCKING:
                req_id = evt.get("id")
                if isinstance(req_id, str):
                    asyncio.create_task(
                        pi.send({"type": "extension_ui_response", "id": req_id, "cancelled": True})
                    )
                    print(
                        f"[ws {session_id}] auto-cancelling unknown extension_ui_request "
                        f"id={req_id} method={method!r}",
                        file=sys.stderr,
                    )
            return {"type": "_bridge_noop"}  # swallow — don't surface raw extension UI in chat

        try:
            payload_json = title[len(_PERMISSION_PREFIX):]
            payload = json.loads(payload_json)
        except Exception as exc:
            print(
                f"[ws {session_id}] malformed permission payload: {exc}; "
                f"auto-allowing to avoid deadlock",
                file=sys.stderr,
            )
            req_id = evt.get("id")
            if isinstance(req_id, str):
                asyncio.create_task(
                    pi.send({"type": "extension_ui_response", "id": req_id, "value": "allow_once"})
                )
            return {"type": "_bridge_noop"}

        req_id = evt.get("id")
        if not isinstance(req_id, str):
            return {"type": "_bridge_noop"}

        pending_permissions[req_id] = payload
        audit_record(
            wsid=workspace_id_for_audit,
            sid=session_id,
            uid=user_id,
            tool=str(payload.get("tool") or "unknown"),
            event="asked",
            input=payload.get("input") if isinstance(payload.get("input"), dict) else None,
            extra={"mode": payload.get("mode"), "request_id": req_id},
        )
        # The frontend listens for `permission_request` and renders a modal.
        # Everything the modal needs travels in this single payload — no
        # follow-up REST calls.
        return {
            "type": "permission_request",
            "id": req_id,
            "tool": payload.get("tool"),
            "tool_call_id": payload.get("tool_call_id"),
            "input": payload.get("input"),
            "intent": payload.get("intent"),
            "preview": payload.get("preview"),
            "mode": payload.get("mode"),
        }

    async def pi_to_ws() -> None:
        async for evt in pi.events():
            _remember_tool_args(evt)

            permission_override = _intercept_permission_request(evt)
            if permission_override is not None:
                outbound = permission_override
            else:
                override = _maybe_block_bash(evt)
                outbound = override if override is not None else evt
            # Internal noop sentinel — we logged/forwarded out-of-band and
            # nothing should reach the SPA for this event.
            if isinstance(outbound, dict) and outbound.get("type") == "_bridge_noop":
                continue

            try:
                payload = json.dumps(outbound, ensure_ascii=False)
            except Exception as exc:
                print(f"[ws {session_id}] serialize failed: {exc}", file=sys.stderr)
                continue
            if DEPLOY_MODE == "web":
                # Last-line secret scrub on outbound text. Cheap because
                # `scrub_secrets` short-circuits when no marker chars are
                # present, which is the common case.
                payload = scrub_secrets(payload)
            try:
                await ws.send_text(payload)
            except Exception as exc:
                print(f"[ws {session_id}] send failed: {exc}", file=sys.stderr)
                return

            # Use the original event for state-keeping (snapshot,
            # bg tracking, billing) — the override is only for what the
            # client sees, not for our internal accounting.
            await _maybe_snapshot(evt)
            _maybe_track_bg_process(evt)
            _maybe_charge_usage(evt)
            _maybe_charge_tool_sub_llm(evt)
            _maybe_audit_tool_lifecycle(evt)

    async def fs_to_ws() -> None:
        while True:
            try:
                msg = await fs_queue.get()
            except asyncio.CancelledError:
                return
            try:
                await ws.send_text(json.dumps(msg, ensure_ascii=False))
            except Exception as exc:
                print(f"[ws {session_id}] fs send failed: {exc}", file=sys.stderr)
                return

    async def bg_to_ws() -> None:
        while True:
            try:
                msg = await bg_queue.get()
            except asyncio.CancelledError:
                return
            try:
                await ws.send_text(json.dumps(msg, ensure_ascii=False))
            except Exception as exc:
                print(f"[ws {session_id}] bg send failed: {exc}", file=sys.stderr)
                return

    async def prompt_watchdog() -> None:
        """Wall-clock guard. Wakes every 5 seconds; if a turn has been
        running longer than PROMPT_TIMEOUT_SECONDS, sets the timeout
        flag and exits — the parent's `asyncio.wait` will then cancel
        the other pumps and tear down the session.

        Cancellation via close-the-session is the only reliable way
        to interrupt a runaway pi turn: pi's RPC stream doesn't have
        an "abort current turn" frame, so we kill the subprocess and
        let the user reconnect. The session_locks layer makes that
        graceful (the new tab takes over)."""
        if PROMPT_TIMEOUT_SECONDS <= 0:
            return
        loop = asyncio.get_event_loop()
        while True:
            try:
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                return
            started = turn_started_at.get("ts")
            if started is None:
                continue
            elapsed = loop.time() - started
            if elapsed >= PROMPT_TIMEOUT_SECONDS:
                timed_out["flag"] = True
                print(
                    f"[ws {session_id}] prompt timeout: turn ran {elapsed:.0f}s "
                    f"(limit {PROMPT_TIMEOUT_SECONDS}s) — tearing down",
                    file=sys.stderr,
                )
                try:
                    await ws.send_json(
                        {
                            "type": "_bridge_error",
                            "message": (
                                f"Your prompt ran for over "
                                f"{PROMPT_TIMEOUT_SECONDS // 60} minutes "
                                "and was stopped to protect your budget. "
                                "Try a smaller request or break the work "
                                "into steps."
                            ),
                            "code": "prompt_timeout",
                            "elapsed_seconds": int(elapsed),
                        }
                    )
                except Exception:
                    pass
                return

    async def ws_to_pi() -> None:
        while True:
            try:
                raw = await ws.receive_text()
            except WebSocketDisconnect:
                return
            try:
                command = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json(
                    {"type": "_bridge_error", "message": f"Invalid JSON from client: {raw[:120]!r}"}
                )
                continue
            # Client-driven abort. The SPA sends `{type: "abort"}` when
            # the user clicks the stop button (see web/frontend/src/stores/
            # chat.ts:507). pi's RPC stream itself has no "abort current
            # turn" frame — see prompt_watchdog's comment below — so the
            # only reliable way to interrupt a runaway turn is to kill
            # the subprocess. We force-kill rather than the polite 5s
            # grace in `pi.close()` because the user clicked stop *now*;
            # they don't want to wait 5 seconds for the in-flight Vertex
            # request to round-trip on its own.
            #
            # Order matters: send the bridge_error first so the SPA flips
            # `isStreaming` false immediately (its `_dispatch` handler
            # at chat.ts:449 keys off this), then terminate, then return
            # so the parent's `asyncio.wait` tears down the rest of the
            # pumps and closes the WS with our 4410 code. The SPA's
            # bridge handles 4410 by reconnecting automatically (see
            # ws/chat-bridge.ts) so the user can keep chatting without
            # an extra click.
            if command.get("type") == "abort":
                aborted["flag"] = True
                print(
                    f"[ws {session_id}] abort requested by client; force-killing pi",
                    file=sys.stderr,
                )
                try:
                    await ws.send_json(
                        {
                            "type": "_bridge_error",
                            "code": "aborted",
                            "message": "Aborted.",
                        }
                    )
                except Exception:
                    pass
                try:
                    await pi.terminate()
                except Exception as exc:
                    print(
                        f"[ws {session_id}] abort: pi.terminate raised {exc!r}",
                        file=sys.stderr,
                    )
                return
            # Permission gate response. We translate the SPA's high-level
            # decision (allow_once / allow_session / deny_once / deny_session)
            # into the extension_ui_response shape pi expects. The pi-side
            # extension lives in extensions/permission.ts and will resolve
            # its ctx.ui.select() with this value, then either return
            # undefined (allow) or { block: true } (deny).
            if command.get("type") == "permission_response":
                req_id = command.get("id")
                decision = command.get("decision")
                if not isinstance(req_id, str) or not isinstance(decision, str):
                    await ws.send_json(
                        {"type": "_bridge_error", "message": "permission_response missing id/decision"}
                    )
                    continue
                if decision not in ("allow_once", "allow_session", "deny_once", "deny_session"):
                    await ws.send_json(
                        {"type": "_bridge_error", "message": f"unknown decision: {decision!r}"}
                    )
                    continue
                pending = pending_permissions.pop(req_id, None)
                tool_name = (
                    str((pending or {}).get("tool") or "unknown") if pending else "unknown"
                )
                audit_record(
                    wsid=workspace_id_for_audit,
                    sid=session_id,
                    uid=user_id,
                    tool=tool_name,
                    event=decision,  # type-checked above
                    input=(pending or {}).get("input") if isinstance((pending or {}).get("input"), dict) else None,
                    extra={"request_id": req_id},
                )
                try:
                    await pi.send(
                        {"type": "extension_ui_response", "id": req_id, "value": decision}
                    )
                except Exception as exc:
                    await ws.send_json(
                        {"type": "_bridge_error", "message": f"Failed to forward decision to pi: {exc}"}
                    )
                continue
            if command.get("type") == "prompt":
                # Pre-flight rate limit + daily-token check. We block
                # *before* forwarding to pi so we don't pay any model
                # cost for a prompt the user can't legitimately make.
                # Errors are surfaced as `_bridge_error` events so the
                # chat pane can render an inline notice instead of
                # closing the WS (the user can retry after the cooldown).
                if not rl.try_take(user_id, "chat.message"):
                    await ws.send_json(
                        {
                            "type": "_bridge_error",
                            "message": "You're sending prompts too quickly. Slow down for a moment.",
                            "code": "rate_limit",
                            "bucket": "chat.message",
                        }
                    )
                    continue
                if not rl.can_send_message(user_id):
                    remaining = rl.remaining_tokens(user_id)
                    await ws.send_json(
                        {
                            "type": "_bridge_error",
                            "message": (
                                "Daily token budget reached. Resets at UTC midnight. "
                                f"({remaining} tokens left)"
                            ),
                            "code": "token_quota",
                        }
                    )
                    continue
                # Workspace storage cap. We enforce *between* prompts
                # rather than during a tool call — by the time we see
                # tool_execution_end the file is already on disk; we
                # can't unwrite it. Refusing the next prompt makes the
                # agent stop digging the hole and forces the user to
                # clean up (delete files via the UI, or ask the agent
                # to delete them) before continuing.
                # Desktop runs on the user's own disk — no quota
                # applies. The whole "you've hit the sandbox cap"
                # affordance only makes sense for the hosted (web)
                # product where each chat lives in a sandboxed
                # workspaces/<wsid>/ directory under our data root.
                if DEPLOY_MODE == "web" and WORKSPACE_DISK_QUOTA_MB > 0:
                    used_mb = workspace_over_quota(workspace_path, WORKSPACE_DISK_QUOTA_MB)
                    if used_mb is not None:
                        # When a hosted-tier user hits the workspace
                        # cap they're almost always trying to install
                        # heavyweight tooling (rust/go toolchains,
                        # multi-GB datasets, media projects). Rather
                        # than asking them to delete files and stay on
                        # the web — where they'll just hit the same
                        # ceiling on the next install — we steer them
                        # to the desktop app, which uses their local
                        # disk and has no quota. This is also the
                        # signal we use to drive desktop-app adoption
                        # for the ~5% of power users who'd otherwise
                        # churn on a "your sandbox is full" wall.
                        def _fmt(mb: float) -> str:
                            return f"{mb / 1024:.1f} GB" if mb >= 1024 else f"{mb:.0f} MB"

                        await ws.send_json(
                            {
                                "type": "_bridge_error",
                                "message": (
                                    f"You hit the workspace storage limit "
                                    f"({_fmt(used_mb)} of {_fmt(WORKSPACE_DISK_QUOTA_MB)}). "
                                    "Use the local version instead "
                                    "for better storage options that "
                                    "run on your own machine — "
                                    "https://digi-setu.com/download"
                                ),
                                "code": "storage_quota",
                                "used_mb": round(used_mb, 1),
                                "quota_mb": WORKSPACE_DISK_QUOTA_MB,
                                "download_url": "https://digi-setu.com/download",
                            }
                        )
                        continue

                # Subscription credit gate. The token bucket above is
                # the daily-fairness signal; this is the *monthly
                # dollar* signal (free tier $2, pro tier $20, …). When
                # spent_usd ≥ plan.monthly_credit_usd the user has to
                # upgrade or wait for the next billing month.
                if not ledger.can_spend(user_id):
                    snap = ledger.snapshot(user_id)
                    await ws.send_json(
                        {
                            "type": "_bridge_error",
                            "message": (
                                f"You've used your {snap['plan']['label']} "
                                f"plan's ${snap['plan']['monthly_credit_usd']:.2f} "
                                f"of credit for {snap['month']}. "
                                "Upgrade your plan or wait for the next month."
                            ),
                            "code": "credit_exhausted",
                            "snapshot": snap,
                        }
                    )
                    continue
                rl.note_message(user_id)

                cid = command.get("id")
                if isinstance(cid, str) and cid:
                    current_user_message_id["id"] = cid
                # Auto-title on the first prompt so the picker shows
                # something meaningful instead of "Untitled chat".
                #
                # Two-phase strategy:
                #   1. Synchronous heuristic — first ~6 substantive
                #      words, capitalised. Keeps the picker readable
                #      *now* without blocking the prompt round-trip on
                #      a network call.
                #   2. Async LLM upgrade — kicked off in the background
                #      via `_upgrade_title_via_llm`. Replaces the
                #      heuristic with a polished Haiku-generated title
                #      and broadcasts `_session_titled` so the SPA
                #      refreshes the picker / brand header live.
                #
                # We only fire the upgrade once per session (guarded by
                # `title_task`), and only if we successfully placed the
                # heuristic — if the user already named the chat, both
                # the heuristic CAS and the LLM CAS will refuse to
                # overwrite their version.
                msg = command.get("message")
                if isinstance(msg, str) and msg.strip():
                    had_user_message["flag"] = True
                    heuristic = _derive_title(msg)
                    placed = reg.maybe_set_initial_title(session_id, heuristic)
                    if placed and title_task["task"] is None:
                        title_task["task"] = asyncio.create_task(
                            _upgrade_title_via_llm(msg, heuristic),
                            name=f"title_gen[{session_id}]",
                        )
                reg.touch_session(session_id)
                # Arm the per-prompt wall-clock watchdog. Cleared in
                # _maybe_charge_usage when message_end fires.
                turn_started_at["ts"] = asyncio.get_event_loop().time()
                # Drop the cached workspace size so the next prompt's
                # quota check sees the post-tool-call reality, not a
                # stale measurement from before this turn's writes.
                invalidate_workspace_size(workspace_path)
            try:
                await pi.send(command)
            except Exception as exc:
                await ws.send_json(
                    {"type": "_bridge_error", "message": f"Failed to forward command to pi: {exc}"}
                )
                return

    pump_out = asyncio.create_task(pi_to_ws(), name=f"pi_to_ws[{session_id}]")
    pump_fs = asyncio.create_task(fs_to_ws(), name=f"fs_to_ws[{session_id}]")
    pump_bg = asyncio.create_task(bg_to_ws(), name=f"bg_to_ws[{session_id}]")
    pump_in = asyncio.create_task(ws_to_pi(), name=f"ws_to_pi[{session_id}]")
    pump_wd = asyncio.create_task(prompt_watchdog(), name=f"prompt_wd[{session_id}]")

    done, pending = await asyncio.wait(
        {pump_out, pump_fs, pump_bg, pump_in, pump_wd},
        return_when=asyncio.FIRST_COMPLETED,
    )
    for task in pending:
        task.cancel()

    fs_watcher.unsubscribe(fs_queue)
    bg_registry.unsubscribe(bg_queue)
    await WatcherRegistry.instance().release(workspace_path)
    await pi.close()
    # Release the multi-tab guard. Idempotent — if a newer tab took
    # ownership while we were winding down, this is a no-op.
    await locks.release(session_id, ws)

    # NOTE: we deliberately DO NOT delete an empty session on WS close
    # anymore. A WS close is not always "the user gave up" — it could be:
    #   * the browser backgrounding the tab (some browsers close idle WS
    #     after ~2 minutes)
    #   * a transient network blip / Wi-Fi roam
    #   * Vite HMR closing the bridge during a frontend hot-reload
    #   * a model swap (we explicitly tear down + reopen on picker change)
    # Deleting on any of those would 404 the session as soon as the SPA
    # reconnects, which surfaces as the "session not found" toast users
    # hate. Empty/abandoned sessions are still cleaned up — but on the
    # picker's terms, not the WS's:
    #   * `Registry.prune_empty_sessions(older_than_seconds=300)` runs
    #     every time the user lists sessions in a workspace
    #     (routes/sessions.py:list_sessions_in_workspace)
    #   * That sweep is age-gated, so a session created two seconds ago
    #     survives a brief disconnect; one created six minutes ago with
    #     zero user messages is gone the next time the picker loads.
    # If you reintroduce eager deletion here, please rate-limit by
    # session age (e.g. only delete if `created_at` was within the last
    # ~30s) so a real user reconnecting doesn't lose their workspace.
    try:
        # Touch the unused locals so future contributors don't think the
        # variable was renamed and miss the comment above.
        _ = had_user_message["flag"]
    except Exception as exc:
        # Cleanup is best-effort — never let it bring down the WS
        # close path.
        print(
            f"[ws {session_id}] empty-session GC raised: {exc!r}",
            file=sys.stderr,
        )
    try:
        # If we were torn down by the watchdog, send a deterministic
        # close code so the SPA can render "your prompt timed out"
        # instead of a generic disconnect.
        if timed_out["flag"]:
            await ws.close(code=4408)
        elif aborted["flag"]:
            await ws.close(code=4410)
        else:
            await ws.close()
    except Exception:
        pass

    print(f"[ws {session_id}] closed", file=sys.stderr)
