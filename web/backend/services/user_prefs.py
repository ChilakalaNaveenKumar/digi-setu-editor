"""
Per-user UI preferences.

Tiny key/value store for things that aren't billing or auth — currently
the permission_mode (auto / approve_all / manual) and a few desktop-
specific prefs (per-workspace last-used model, BYOK vs Cloud routing
default). Designed so we can drop in more (theme, default model,
default thinking level, etc.) without churning the API surface.

Persistence is plain JSON at web/data/user_prefs.json. We chose flat
JSON over SQLite because:
  - the dataset is tiny (one row per user, ~64 bytes)
  - it survives restarts without a migration story
  - it's trivial to inspect and bulk-edit during development

If/when this hits ~10k users we'll move it into the same SQLite store
the CreditLedger eventually wants.

Permission-mode IDs (canonical → user-facing label):
    auto         → "Auto"          Prompt for risky tools (bash, write,
                                    edit, process) so the user sees what's
                                    about to run; auto-approve after 15s
                                    if no click. Reads / greps / lists are
                                    silent. THIS IS THE DEFAULT — fastest
                                    UX with the modal still acting as a
                                    visible audit trail.

    approve_all  → "Approve all"   No prompt at all, every tool runs
                                    instantly. For users who trust the
                                    agent fully and want a pure Cursor-
                                    style experience.

    manual       → "Ask each time" Prompt for risky tools AND wait
                                    forever for an explicit click — the
                                    agent will sit idle rather than
                                    auto-approve. For users who want to
                                    vet every risky call individually.

Migration on read (mapping older / legacy IDs to the current canonical
set, applied silently and rewritten on first save):

    old "auto" (silent)         → "auto" kept as-is; the user gets a
                                  modal+15s where before there was
                                  silence. This is a safer default
                                  (more visibility, never blocks).
    old "ask"                   → "auto"   (same prompt+15s behaviour)
    old "cautious"              → "manual" (strictest → strictest)
    legacy "approve_risky"      → "auto"
    legacy "approve_all" (old)  → "manual" (was prompt-all; now becomes
                                  the strict mode, never auto-approve)

Default for both web and desktop is `auto` — the spec the operator
locked in 2026-05 after Nicholas Bian's blocked-modal incident.
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
from pathlib import Path
from typing import Any, Optional

from config import DATA_ROOT

PREFS_PATH = DATA_ROOT / "user_prefs.json"

# Per-user "live" permission-mode file. Each spawned pi receives this path
# in PI_PERMISSION_MODE_FILE and re-reads it on every tool_call, so a mode
# change applies to the running pi process — no respawn needed. We keep
# this OUTSIDE the JSON pref blob so it can be read with a single open()
# from the extension without parsing JSON.
_USERS_DIR = DATA_ROOT / "users"

# Canonical permission-mode IDs the rest of the codebase should use.
# Keep the tuple ordered least-restrictive → most-restrictive — the
# picker reads it in this order so the row layout matches Cursor /
# Cline / Continue conventions (relaxed at the top).
VALID_PERMISSION_MODES = ("approve_all", "auto", "manual")

# Migration table for older / legacy IDs. The mapping must always go
# from a previous canonical name (or an even older legacy alias) to a
# current canonical name. We deliberately map at the "same security
# level or stricter" — never relax — so a stale prefs file can't
# silently weaken a user's previous choice.
_LEGACY_PERMISSION_ALIASES = {
    # Previous canonical names (3-mode auto/ask/cautious era):
    "ask": "auto",         # old ask was prompt-risky+15s → new auto is the same
    "cautious": "manual",  # old cautious prompted for everything → new manual is the strictest mode
    # Even older aliases used by 2-mode era extensions:
    "approve_risky": "auto",
    # NOTE: there is intentionally no mapping for the legacy
    # "approve_all" value here — in the OLD scheme `approve_all` was an
    # alias for `cautious` (prompt for all) but in the NEW scheme
    # `approve_all` is the silent-run-everything mode. If a stale
    # prefs file literally contains "approve_all" we want it to mean
    # the new (correct) thing, not the old one, because:
    #   1. the picker has always presented it under a "less prompting"
    #      label, so user intent is preserved
    #   2. defaulting to the new meaning matches the renamed extension
    # If you genuinely need to preserve the old "prompt-for-everything"
    # semantics for a specific user, write `manual` to their prefs.
}


def normalize_permission_mode(raw: str) -> Optional[str]:
    """Return the canonical mode for `raw`, or None if it's invalid.

    Accepts the canonical IDs unchanged and the legacy aliases mapped to
    their modern equivalents. Whitespace and case are normalised.
    """
    cleaned = (raw or "").strip().lower()
    if cleaned in VALID_PERMISSION_MODES:
        return cleaned
    return _LEGACY_PERMISSION_ALIASES.get(cleaned)


# Default first-launch posture: `auto`. The agent prompts for risky
# tools (bash / write / edit / process) and auto-approves after 15s if
# the user doesn't click — the modal serves as a visible audit trail
# without becoming the "blocked modal" failure mode Nicholas Bian hit
# in 2026-05 (a 58-message loop where every bash call stalled behind
# an off-screen prompt). Users who want full silence flip to
# `approve_all`; users who want to vet every call flip to `manual`.
# Override with PI_PERMISSION_MODE_DEFAULT to restore a non-auto
# default without a code change.
_DEFAULT_FROM_ENV = os.environ.get("PI_PERMISSION_MODE_DEFAULT", "").strip().lower()
_DEFAULT_NORMALISED = normalize_permission_mode(_DEFAULT_FROM_ENV)
DEFAULT_PERMISSION_MODE = _DEFAULT_NORMALISED if _DEFAULT_NORMALISED else "auto"

# user_id from Clerk looks like "user_2abcXYZ..."; in dev we sometimes
# pass "anon" or an email. Restrict to filesystem-safe chars to avoid
# directory traversal or weird chars on Windows-style filesystems.
_SAFE_USER_ID = re.compile(r"[^A-Za-z0-9._-]")


def _sanitize_user_id(user_id: str) -> str:
    return _SAFE_USER_ID.sub("_", user_id)[:128]

# Plan-based default override.
#
# Historically we used this to bump paid plans onto a stricter or
# looser default than free users. With the current 3-mode set the
# `auto` default already gives every plan the right UX (visible
# prompts with a 15s safety net), so this hook is a no-op for now.
# Kept as a vector for future tiering — if e.g. enterprise wants
# `manual` by default for compliance reasons, add the plan id to
# `_PLAN_DEFAULTS` below.
_PLAN_DEFAULTS: dict[str, str] = {}


def _default_for_plan(plan_id: Optional[str]) -> str:
    if plan_id:
        override = _PLAN_DEFAULTS.get(plan_id.lower())
        if override:
            return override
    return DEFAULT_PERMISSION_MODE


class UserPrefs:
    """Process-local cache backed by a JSON file. Singleton."""

    _instance: Optional["UserPrefs"] = None
    _instance_lock = threading.Lock()

    @classmethod
    def instance(cls) -> "UserPrefs":
        # Double-checked locking so we don't pay the lock cost on every call.
        if cls._instance is not None:
            return cls._instance
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: dict[str, dict[str, Any]] = {}
        self._load()

    # ── persistence ─────────────────────────────────────────────────────────

    def _load(self) -> None:
        if not PREFS_PATH.exists():
            return
        try:
            with PREFS_PATH.open("r", encoding="utf-8") as f:
                blob = json.load(f)
            if isinstance(blob, dict):
                self._data = {
                    str(k): dict(v) for k, v in blob.items() if isinstance(v, dict)
                }
        except Exception as exc:
            print(f"[user_prefs] WARN: prefs file unreadable ({exc}); starting empty", file=sys.stderr)
            self._data = {}

    def _flush_locked(self) -> None:
        try:
            PREFS_PATH.parent.mkdir(parents=True, exist_ok=True)
            tmp = PREFS_PATH.with_suffix(".json.tmp")
            with tmp.open("w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, PREFS_PATH)
        except Exception as exc:
            print(f"[user_prefs] WARN: flush failed: {exc}", file=sys.stderr)

    # ── permission_mode API ─────────────────────────────────────────────────

    def get_permission_mode(self, user_id: str, *, plan_id: Optional[str] = None) -> str:
        """
        Return the user's chosen mode, falling back to the plan-aware
        default when no explicit choice has been made.

        Legacy IDs in the on-disk JSON (`approve_risky`, `approve_all`)
        are silently mapped to the canonical equivalents and rewritten
        on the next save — users keep their setting through the rename.
        """
        if not user_id:
            return _default_for_plan(plan_id)
        with self._lock:
            row = self._data.get(user_id) or {}
            chosen = row.get("permission_mode")
        if isinstance(chosen, str):
            normalised = normalize_permission_mode(chosen)
            if normalised:
                # Lazy migration: if the on-disk value was a legacy
                # alias, rewrite it now so future reads skip the
                # alias-lookup path. Best-effort — we don't fail the
                # call if the flush fails.
                if normalised != chosen:
                    try:
                        with self._lock:
                            self._data.setdefault(user_id, {})["permission_mode"] = normalised
                            self._flush_locked()
                    except Exception:  # noqa: BLE001 — defensive
                        pass
                return normalised
        return _default_for_plan(plan_id)

    def set_permission_mode(self, user_id: str, mode: str) -> str:
        """
        Persist the user's mode choice. Returns the mode that was
        actually stored (may differ from input if a legacy alias was
        normalised, or if input was invalid and got clamped to the
        plan-aware default).

        Also writes the mode to the per-user "live" file at
        web/data/users/<sanitized-user>/permission_mode so any pi
        process currently running for this user can pick up the new
        value on its next tool_call (the extension re-reads
        PI_PERMISSION_MODE_FILE on every tool call). This is what makes
        mode swaps apply immediately to the running chat instead of
        only the next spawn.
        """
        if not user_id:
            return DEFAULT_PERMISSION_MODE
        cleaned = normalize_permission_mode(mode) or DEFAULT_PERMISSION_MODE
        with self._lock:
            row = self._data.setdefault(user_id, {})
            row["permission_mode"] = cleaned
            self._flush_locked()
        self._write_live_file(user_id, cleaned)
        return cleaned

    # ── live-file API ───────────────────────────────────────────────────────
    #
    # The pi extension permission.ts reads this file on every tool_call so
    # changes propagate to running processes. We keep the file format dead
    # simple — one mode token per file, no JSON, no quoting — so the
    # extension can do a single readFileSync without parsing.

    def permission_mode_file(self, user_id: str) -> Path:
        """Return (and ensure parent exists for) the per-user live file."""
        safe = _sanitize_user_id(user_id) or "anon"
        directory = _USERS_DIR / safe
        directory.mkdir(parents=True, exist_ok=True)
        return directory / "permission_mode"

    def _write_live_file(self, user_id: str, mode: str) -> None:
        try:
            path = self.permission_mode_file(user_id)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(mode + "\n", encoding="utf-8")
            os.replace(tmp, path)
        except Exception as exc:
            # The JSON pref store is the source of truth; if the live file
            # write fails the new mode still applies on next pi spawn, so
            # this is non-fatal.
            print(f"[user_prefs] WARN: live-file write failed: {exc}", file=sys.stderr)

    def ensure_live_file(self, user_id: str, mode: str) -> Path:
        """
        Idempotently materialise the live file at the current mode and
        return its path. Called at pi spawn so the file always exists for
        the extension to read (avoiding a "file not found, fall back to
        env" code path).
        """
        path = self.permission_mode_file(user_id)
        if not path.exists():
            self._write_live_file(user_id, mode)
        return path

    # ── per-workspace last-used model ───────────────────────────────────────
    #
    # Desktop UX: each folder remembers its last-used model so opening the
    # folder again (or starting a fresh chat in it) defaults to whatever the
    # user picked last time. We store these inline on the user pref blob
    # under "workspace_models": { wsid: model_id } — flat dict, tiny, no
    # migration concerns. Web mode uses this too (it doesn't hurt) but the
    # picker behaves the same as before because users typically only have
    # one or two workspaces in a session.

    def get_workspace_model(self, user_id: str, wsid: str) -> Optional[str]:
        """Return the last model id picked in this workspace, or None.
        The caller (chat_ws) treats None as "no preference; use plan
        default" — same path it took before this feature existed."""
        if not user_id or not wsid:
            return None
        with self._lock:
            row = self._data.get(user_id) or {}
            blob = row.get("workspace_models")
            if isinstance(blob, dict):
                value = blob.get(wsid)
                if isinstance(value, str) and value:
                    return value
        return None

    def set_workspace_model(self, user_id: str, wsid: str, model_id: str) -> None:
        """Record `model_id` as the last-used choice for `wsid`. Idempotent
        — repeated writes of the same model are cheap (we still flush, but
        no diff). Empty / falsy inputs are no-ops."""
        if not user_id or not wsid or not model_id:
            return
        with self._lock:
            row = self._data.setdefault(user_id, {})
            blob = row.get("workspace_models")
            if not isinstance(blob, dict):
                blob = {}
                row["workspace_models"] = blob
            if blob.get(wsid) == model_id:
                return
            blob[wsid] = model_id
            self._flush_locked()

    # ── desktop routing default (BYOK vs Cloud) ─────────────────────────────
    #
    # When the user has BYOK keys configured the model picker badges each
    # row as BYOK or CLOUD; this preference is the *default* posture used
    # when opening a brand-new chat with no model pinned yet. Per-chat
    # picks always override this.

    VALID_ROUTING_DEFAULTS = ("byok", "cloud")

    def get_routing_default(self, user_id: str, *, fallback: str = "byok") -> str:
        """Return the user's preferred default route. `fallback` is what
        we return when nothing's stored yet — caller passes "byok" when
        BYOK keys are present, "cloud" otherwise."""
        if not user_id:
            return fallback
        with self._lock:
            row = self._data.get(user_id) or {}
            chosen = row.get("routing_default")
        if isinstance(chosen, str) and chosen in self.VALID_ROUTING_DEFAULTS:
            return chosen
        return fallback

    def set_routing_default(self, user_id: str, value: str) -> str:
        """Persist the user's BYOK/Cloud routing default. Returns the
        value actually stored (may differ if input was invalid)."""
        if not user_id:
            return "byok"
        cleaned = (value or "").strip().lower()
        if cleaned not in self.VALID_ROUTING_DEFAULTS:
            cleaned = "byok"
        with self._lock:
            row = self._data.setdefault(user_id, {})
            if row.get("routing_default") == cleaned:
                return cleaned
            row["routing_default"] = cleaned
            self._flush_locked()
        return cleaned

    def snapshot(self, user_id: str) -> dict[str, Any]:
        """Return a copy of all known prefs for the user (useful for /me APIs)."""
        if not user_id:
            return {}
        with self._lock:
            return dict(self._data.get(user_id) or {})


def user_prefs() -> UserPrefs:
    """Module-level convenience wrapper for the singleton."""
    return UserPrefs.instance()
