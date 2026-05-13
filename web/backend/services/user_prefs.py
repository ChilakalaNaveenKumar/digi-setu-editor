"""
Per-user UI preferences.

Tiny key/value store for things that aren't billing or auth — currently
the permission_mode (auto / ask / cautious) and a few desktop-specific
prefs (per-workspace last-used model, BYOK vs Cloud routing default).
Designed so we can drop in more (theme, default model, default thinking
level, etc.) without churning the API surface.

Persistence is plain JSON at web/data/user_prefs.json. We chose flat
JSON over SQLite because:
  - the dataset is tiny (one row per user, ~64 bytes)
  - it survives restarts without a migration story
  - it's trivial to inspect and bulk-edit during development

If/when this hits ~10k users we'll move it into the same SQLite store
the CreditLedger eventually wants.

Permission-mode IDs (canonical → user-facing label):
    auto       → "Auto"      Run every tool without asking; audit log
                              records every action.
    ask        → "Ask"       Ask before bash / write / edit / process.
                              Reads pass silently. (Default.)
    cautious   → "Cautious"  Ask before every tool call, including
                              reads.

Legacy IDs ("approve_risky" ≡ "ask", "approve_all" ≡ "cautious") are
accepted on read and silently rewritten to the canonical form on the
first save — so a stale prefs.json keeps working through the upgrade
without manual intervention.

Default for the hosted web app is `ask` for every plan, paired with
the auto-allow safety net (30s visible countdown in the modal +
60s hard timeout server-side, both resolving to ALLOW). The brief
stint at `auto` removed the silent-stall failure mode but also
removed the speed bump for first-time users — they had no idea
what tool calls the agent was running until the side-effects landed.
`ask` puts a face on every bash / write / edit / process call
without sacrificing the safety net: the modal auto-resolves to
ALLOW after thirty seconds whether the user sees it or not, so the
previous "prompt invisible AND wait forever" failure mode is
impossible. Users who do want full silence can flip to `auto` from
the chat settings menu; users who want to gate every read can flip
to `cautious`. Desktop matches this default for the same reasons
(its copy of this file).
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
VALID_PERMISSION_MODES = ("auto", "ask", "cautious")

# Legacy aliases. These appeared in earlier builds; we map them to the
# canonical IDs on read (and rewrite on next save). Update this dict if
# we ever need another rename — never expand the canonical tuple.
_LEGACY_PERMISSION_ALIASES = {
    "approve_risky": "ask",
    "approve_all": "cautious",
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


# Default first-launch posture for the hosted web app. We pick `auto`
# so the agent's bash / write / edit calls don't stall behind an
# approval modal the user might never see (the modal piggybacks on the
# same SSE stream the assistant uses, so any drop also drops the
# prompt). Users who want the speed bump can flip to `ask` or
# `cautious` from the chat settings menu and the choice persists.
# Override with PI_PERMISSION_MODE_DEFAULT (e.g. `ask`) if a particular
# deploy wants to restore the old posture without a code change.
_DEFAULT_FROM_ENV = os.environ.get("PI_PERMISSION_MODE_DEFAULT", "").strip().lower()
_DEFAULT_NORMALISED = normalize_permission_mode(_DEFAULT_FROM_ENV)
DEFAULT_PERMISSION_MODE = _DEFAULT_NORMALISED if _DEFAULT_NORMALISED else "ask"

# user_id from Clerk looks like "user_2abcXYZ..."; in dev we sometimes
# pass "anon" or an email. Restrict to filesystem-safe chars to avoid
# directory traversal or weird chars on Windows-style filesystems.
_SAFE_USER_ID = re.compile(r"[^A-Za-z0-9._-]")


def _sanitize_user_id(user_id: str) -> str:
    return _SAFE_USER_ID.sub("_", user_id)[:128]

# Plan tiers that get the lighter-touch default. Anything not listed falls
# back to DEFAULT_PERMISSION_MODE.
_AUTO_MODE_PLANS = frozenset({"pro", "enterprise"})


def _default_for_plan(plan_id: Optional[str]) -> str:
    if plan_id and plan_id.lower() in _AUTO_MODE_PLANS:
        return "auto"
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
