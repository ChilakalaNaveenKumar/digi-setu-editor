"""
Registry — single-file JSON catalogue of workspaces and chat sessions.

Conceptual model:

    Workspace = "a place where pi runs (cwd) and where files live"
    Session   = "a chat thread inside a workspace, with a title and history"

In **web mode**, every new session auto-creates its own sandboxed workspace
under web/data/workspaces/<wsid>/. The mapping is 1:1.

In **desktop mode** (later), the user picks a real folder via the OS dialog,
and that one workspace can host many chat sessions.

Why JSON not SQLite: at the volumes we expect for v1 (hundreds of workspaces,
thousands of sessions) JSON is simpler, easier to inspect, easier to back up.
We can swap to SQLite/Postgres later without changing call sites because the
public API of this module returns plain dicts.

Concurrency: a single asyncio.Lock guards write operations. Readers don't
need it because dict operations are atomic at the GIL level and we only
return shallow copies.
"""

from __future__ import annotations

import asyncio
import json
import os
import secrets
import shutil
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Single source of truth for layout — services/ never hardcodes paths now.
# In Cloud Run, PI_DATA_ROOT points DATA_ROOT at a writable tmpfs (/tmp/pi-data).
from config import DATA_ROOT, DEV_USER_ID, PROJECT_ROOT  # noqa: E402
from services.sandbox_layout import stamp_sandbox_dir  # noqa: E402

REGISTRY_PATH = DATA_ROOT / "registry.json"
WORKSPACES_ROOT = DATA_ROOT / "workspaces"

# Files the agent expects to see in its cwd (pi auto-loads extensions from
# package.json, the agent reads AGENTS.md and .pi/APPEND_SYSTEM.md, etc.).
# These get symlinked into every new sandbox at create time.
#
# `node_modules` is symlinked too because pi's extension loader (tsx)
# does NOT realpath symlinks before module resolution — when it loads
# `extensions/typst-tools.ts` from the workspace cwd it walks UP from
# the workspace dir looking for node_modules, NOT from /app/. Without
# this symlink the very first `require('@google/genai')` inside the
# extension throws MODULE_NOT_FOUND and pi crashes at boot, taking the
# whole chat WS down with "bridge is down or pi crashed".
#
# Safety: the symlink only grants ACCESS to /app/node_modules contents.
# Nothing in node_modules is a secret (it's all public npm packages),
# and pi already needs read access there anyway to function. The AI's
# bash CAN now `ls workspace/../node_modules/...` but that just lists
# the same JS files pi loaded itself. Real secrets stay in
# /opt/pi/stack.env (not in image) and are scrubbed from the env
# passed to pi by services/pi_session.py:_scrub_env_for_pi.
SANDBOX_SYMLINKS = (
    "package.json",
    "extensions",
    "guides",
    "AGENTS.md",
    ".pi",
    "node_modules",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_id(prefix: str = "") -> str:
    """URL-safe random id; only [A-Za-z0-9_-]. Filesystem-safe everywhere."""
    return f"{prefix}{secrets.token_urlsafe(8)}"


class Registry:
    """JSON-backed workspace/session catalogue. Singleton via Registry.instance()."""

    _singleton: Optional["Registry"] = None
    _singleton_lock = threading.Lock()

    @classmethod
    def instance(cls) -> "Registry":
        if cls._singleton is None:
            with cls._singleton_lock:
                if cls._singleton is None:
                    cls._singleton = cls()
        return cls._singleton

    def __init__(self) -> None:
        DATA_ROOT.mkdir(parents=True, exist_ok=True)
        WORKSPACES_ROOT.mkdir(parents=True, exist_ok=True)
        self._async_lock = asyncio.Lock()
        self._sync_lock = threading.Lock()
        self._data: dict[str, Any] = self._load()

    # ── persistence ────────────────────────────────────────────────────────
    def _load(self) -> dict[str, Any]:
        if not REGISTRY_PATH.exists():
            return {"workspaces": {}, "sessions": {}}
        try:
            with REGISTRY_PATH.open("r", encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            print(
                f"[registry] WARN: registry.json unreadable ({exc}); starting empty",
                file=sys.stderr,
            )
            return {"workspaces": {}, "sessions": {}}
        raw.setdefault("workspaces", {})
        raw.setdefault("sessions", {})
        # Backfill owner_user_id on any pre-auth workspace records. Without
        # this every existing dev workspace would 404 after the auth wiring
        # lands. Stamping with DEV_USER_ID keeps the dev loop seamless and
        # is harmless in prod (a fresh prod registry has no rows to migrate).
        for rec in raw["workspaces"].values():
            if not rec.get("owner_user_id"):
                rec["owner_user_id"] = DEV_USER_ID
        return raw

    def _flush(self) -> None:
        """Atomic write: temp file + rename. Caller must hold _sync_lock."""
        tmp = REGISTRY_PATH.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, REGISTRY_PATH)

    # ── workspace CRUD ─────────────────────────────────────────────────────
    # All workspace records carry an `owner_user_id`. In dev mode every row
    # gets owner_user_id="dev" so the dev loop never has to log in; in prod
    # mode we stamp the verified Clerk `sub`. The owner filter is enforced
    # by the route layer (via `routes/_helpers.workspace_for_user_or_404`),
    # not here, so unit tests + admin tooling can still see all rows.
    def create_web_workspace(self, name: str = "", *, owner_user_id: str) -> dict[str, Any]:
        """
        Allocate a new web-mode sandbox folder. Returns the workspace record.
        Idempotent in the sense that every call creates a fresh id; callers
        wanting "find or create" should query first.
        """
        wsid = _safe_id("ws_")
        path = WORKSPACES_ROOT / wsid
        path.mkdir(parents=True, exist_ok=False)
        # Stamp ownership BEFORE creating subdirs so SGID + the new gid
        # propagate to every child. Without this, `pi --mode rpc`
        # (running as the sandbox uid) would hit EACCES the moment it
        # tried to write a file into the workspace.
        stamp_sandbox_dir(path)
        # Inside the sandbox, the agent writes into a "workspace/" subdir
        # (the existing AGENTS.md tells it to). Pre-create it so the first
        # `bash ls` doesn't surprise the agent.
        ws_subdir = path / "workspace"
        ws_subdir.mkdir(exist_ok=True)
        stamp_sandbox_dir(ws_subdir)
        # Pre-create workspace/uploads/ so the user-attachment flow has a
        # canonical drop target. The system prompt instructs the agent to
        # look there for files the user shared in the chat (paste, drop,
        # paperclip). Keeping it under workspace/ means the agent's
        # default "list workspace" walk catches uploads automatically.
        uploads = ws_subdir / "uploads"
        uploads.mkdir(exist_ok=True)
        stamp_sandbox_dir(uploads)
        self._wire_sandbox_symlinks(path)

        record = {
            "id": wsid,
            "mode": "web",
            "path": str(path),
            "name": name or "Untitled workspace",
            "owner_user_id": owner_user_id,
            "created_at": _now_iso(),
            "last_used": _now_iso(),
        }
        with self._sync_lock:
            self._data["workspaces"][wsid] = record
            self._flush()
        return dict(record)

    def get_workspace(self, wsid: str) -> Optional[dict[str, Any]]:
        rec = self._data["workspaces"].get(wsid)
        return dict(rec) if rec else None

    def list_workspaces(self, owner_user_id: Optional[str] = None) -> list[dict[str, Any]]:
        items = [dict(r) for r in self._data["workspaces"].values()]
        if owner_user_id is not None:
            items = [r for r in items if r.get("owner_user_id") == owner_user_id]
        items.sort(key=lambda r: r.get("last_used", ""), reverse=True)
        return items

    def workspaces_owned_by(self, owner_user_id: str) -> list[str]:
        """Return wsids owned by a user (used by the cascade-delete webhook)."""
        return [
            wsid for wsid, rec in self._data["workspaces"].items()
            if rec.get("owner_user_id") == owner_user_id
        ]

    def rename_workspace(self, wsid: str, name: str) -> dict[str, Any]:
        with self._sync_lock:
            rec = self._data["workspaces"].get(wsid)
            if not rec:
                raise KeyError(wsid)
            rec["name"] = name.strip() or rec["name"]
            rec["last_used"] = _now_iso()
            self._flush()
            return dict(rec)

    def delete_workspace(self, wsid: str) -> dict[str, Any]:
        """
        Remove a workspace and all its sessions. Web mode: also rm -rf the
        sandbox folder AND the sibling shadows/<wsid>/ shadow-git repo
        AND every per-session chat dir under data/chats/. Desktop mode:
        leave the user's folder alone, but still purge shadow + chats.
        """
        with self._sync_lock:
            rec = self._data["workspaces"].pop(wsid, None)
            if not rec:
                raise KeyError(wsid)
            # Capture the session ids so we can purge their chat JSONLs.
            owned_sids = [
                sid for sid, s in self._data["sessions"].items()
                if s.get("workspace_id") == wsid
            ]
            for sid in owned_sids:
                self._data["sessions"].pop(sid, None)
            self._flush()

        # Local imports to avoid a cycle at module load time.
        try:
            from services.shadow_git import ShadowGitRegistry  # type: ignore
            ShadowGitRegistry.instance().purge_workspace(Path(rec["path"]))
        except Exception as exc:
            print(
                f"[registry] WARN: shadow-git purge failed for {wsid}: {exc}",
                file=sys.stderr,
            )
        try:
            from services.bg_processes import BackgroundProcessHub  # type: ignore
            BackgroundProcessHub.instance().drop_workspace(wsid)
        except Exception as exc:
            print(
                f"[registry] WARN: bg-process drop failed for {wsid}: {exc}",
                file=sys.stderr,
            )
        try:
            from services.pty_terminal import PtyHub  # type: ignore
            PtyHub.instance().drop_workspace(wsid)
        except Exception as exc:
            print(
                f"[registry] WARN: pty drop failed for {wsid}: {exc}",
                file=sys.stderr,
            )

        if rec.get("mode") == "web":
            shutil.rmtree(rec["path"], ignore_errors=True)

        chats_root = DATA_ROOT / "chats"
        for sid in owned_sids:
            shutil.rmtree(chats_root / sid, ignore_errors=True)
        return dict(rec)

    def touch_workspace(self, wsid: str) -> None:
        with self._sync_lock:
            rec = self._data["workspaces"].get(wsid)
            if rec:
                rec["last_used"] = _now_iso()
                self._flush()

    # ── session CRUD ───────────────────────────────────────────────────────
    def create_session(
        self,
        workspace_id: str,
        title: str = "",
        model: Optional[str] = None,
    ) -> dict[str, Any]:
        if workspace_id not in self._data["workspaces"]:
            raise KeyError(f"unknown workspace_id: {workspace_id}")
        sid = _safe_id("s_")
        record: dict[str, Any] = {
            "id": sid,
            "workspace_id": workspace_id,
            "title": title or "",
            # Optional. None means "use whatever the user's plan defaults
            # to at spawn time" — chat_ws picks the default via
            # billing.CreditLedger.get_plan_id + models_registry.
            "model": (model.strip() if isinstance(model, str) and model.strip() else None),
            "created_at": _now_iso(),
            "last_used": _now_iso(),
        }
        with self._sync_lock:
            self._data["sessions"][sid] = record
            ws = self._data["workspaces"].get(workspace_id)
            if ws:
                ws["last_used"] = _now_iso()
            self._flush()
        return dict(record)

    def set_session_model(self, sid: str, model: str) -> dict[str, Any]:
        """PATCH the session's pinned model. Caller must validate the
        model id is in the registry AND the user's plan permits it."""
        with self._sync_lock:
            rec = self._data["sessions"].get(sid)
            if not rec:
                raise KeyError(sid)
            rec["model"] = model.strip()
            rec["last_used"] = _now_iso()
            self._flush()
            return dict(rec)

    def get_session(self, sid: str) -> Optional[dict[str, Any]]:
        rec = self._data["sessions"].get(sid)
        return dict(rec) if rec else None

    def list_sessions(self, workspace_id: Optional[str] = None) -> list[dict[str, Any]]:
        items = [dict(r) for r in self._data["sessions"].values()]
        if workspace_id is not None:
            items = [r for r in items if r.get("workspace_id") == workspace_id]
        items.sort(key=lambda r: r.get("last_used", ""), reverse=True)
        return items

    def rename_session(self, sid: str, title: str) -> dict[str, Any]:
        with self._sync_lock:
            rec = self._data["sessions"].get(sid)
            if not rec:
                raise KeyError(sid)
            rec["title"] = title.strip()
            rec["last_used"] = _now_iso()
            self._flush()
            return dict(rec)

    def maybe_set_initial_title(self, sid: str, title: str) -> Optional[dict[str, Any]]:
        """Atomically set a session's title only if it's currently empty.

        Used by the chat WS for auto-titling on the first user prompt:
        we want to avoid clobbering a title the user explicitly set in
        the picker, and we don't want a race between two near-simultaneous
        prompts to overwrite each other. Returns the updated record on
        success, None if the title was already set (or session missing).
        """
        clean = (title or "").strip()
        if not clean:
            return None
        with self._sync_lock:
            rec = self._data["sessions"].get(sid)
            if not rec:
                return None
            if (rec.get("title") or "").strip():
                return None
            rec["title"] = clean
            rec["last_used"] = _now_iso()
            self._flush()
            return dict(rec)

    def maybe_replace_heuristic_title(
        self,
        sid: str,
        expected_old: str,
        new: str,
    ) -> Optional[dict[str, Any]]:
        """CAS update: replace `expected_old` with `new` only if no one
        else has touched the title in the meantime.

        Used by the background LLM title generator: we set a cheap
        heuristic title up front, then call out to Haiku for a polished
        rewrite. By the time the LLM responds the user might have
        manually renamed the session in the picker — in that case we
        leave their title alone. Compare-and-swap on the title text is
        the simplest way to express "I'm only allowed to upgrade my
        own previous best guess".

        Returns the updated record on success, None if the swap was
        rejected (record missing, title was already changed, or the
        new title is empty/identical to the old one).
        """
        old_clean = (expected_old or "").strip()
        new_clean = (new or "").strip()
        if not new_clean or new_clean == old_clean:
            return None
        with self._sync_lock:
            rec = self._data["sessions"].get(sid)
            if not rec:
                return None
            current = (rec.get("title") or "").strip()
            if current != old_clean:
                # User renamed (or another titling attempt landed first);
                # respect their version.
                return None
            rec["title"] = new_clean
            rec["last_used"] = _now_iso()
            self._flush()
            return dict(rec)

    def delete_session(self, sid: str) -> dict[str, Any]:
        with self._sync_lock:
            rec = self._data["sessions"].pop(sid, None)
            if not rec:
                raise KeyError(sid)
            self._flush()
        # Drop the chat JSONL dir too. Workspace files are kept (might host
        # other sessions, in desktop mode).
        shutil.rmtree(DATA_ROOT / "chats" / sid, ignore_errors=True)
        return dict(rec)

    def prune_empty_sessions(
        self,
        *,
        older_than_seconds: int = 300,
        workspace_id: Optional[str] = None,
    ) -> list[str]:
        """Sweep "ghost" sessions: created or touched more than
        `older_than_seconds` ago, with no user message ever sent.

        Two paths land us with a ghost session:
          1. User clicks "+ New chat", the SPA POSTs to create the
             session, then closes the tab before the WS connects.
             The chat_ws teardown cleanup never runs.
          2. WS connects but the very first network frame fails so
             we tear down before recording anything. Rare but real.

        We *only* prune sessions whose `last_used` is older than the
        threshold so a freshly-created session that's still being
        opened in the same tab isn't snatched out from under the
        navigator. Five minutes is far longer than any realistic
        page-load → first-prompt latency.

        Returns the list of deleted session ids so callers can log
        what they GC'd.
        """
        if older_than_seconds <= 0:
            return []
        now = datetime.now(timezone.utc)
        with self._sync_lock:
            candidates = [
                (sid, dict(rec))
                for sid, rec in self._data["sessions"].items()
                if workspace_id is None or rec.get("workspace_id") == workspace_id
            ]
        pruned: list[str] = []
        # Track which workspaces lost a session so we can chase down
        # orphan web-mode workspaces in a second pass.
        touched_workspaces: set[str] = set()
        for sid, rec in candidates:
            last_used = rec.get("last_used") or rec.get("created_at") or ""
            if not last_used:
                continue
            try:
                # `fromisoformat` accepts "+00:00" but not the "Z" suffix
                # pi/uvicorn write — normalise so we can parse both.
                ts = datetime.fromisoformat(last_used.replace("Z", "+00:00"))
            except ValueError:
                continue
            if (now - ts).total_seconds() < older_than_seconds:
                continue
            if not self.is_session_empty(sid):
                continue
            try:
                self.delete_session(sid)
                pruned.append(sid)
                wsid = rec.get("workspace_id")
                if isinstance(wsid, str):
                    touched_workspaces.add(wsid)
            except KeyError:
                pass

        # Web mode: a workspace exists 1:1 per session, so once the
        # ghost session is gone the workspace is dead weight too.
        # Desktop mode workspaces represent a real folder the user
        # picked — never delete those automatically even if they're
        # empty (the user might be about to create a new chat in
        # them).
        for wsid in touched_workspaces:
            ws_rec = self._data["workspaces"].get(wsid)
            if not ws_rec or ws_rec.get("mode") != "web":
                continue
            if any(
                s.get("workspace_id") == wsid
                for s in self._data["sessions"].values()
            ):
                continue
            try:
                self.delete_workspace(wsid)
            except KeyError:
                pass

        return pruned

    def is_session_empty(self, sid: str) -> bool:
        """True when the session has never received a user message.

        Implementation note: pi writes a fresh JSONL file per RPC
        invocation under `data/chats/<sid>/` and emits ~3 metadata
        events (`session`, `model_change`, `thinking_level_change`)
        before the user types anything. So "no JSONL files" doesn't
        cleanly mean "empty" — we have to scan for the actual user
        message marker.

        We short-circuit on the first hit. Even on a large multi-day
        session this is cheap because we only call it on WS teardown
        (rare event) and the file format is line-oriented.

        Used by the chat_ws cleanup path: if the user opened a chat,
        typed nothing, and navigated away, we'd otherwise leave a dead
        "Untitled" entry in the picker forever. With this signal the
        teardown can call `delete_session` cleanly.
        """
        chat_dir = DATA_ROOT / "chats" / sid
        if not chat_dir.is_dir():
            return True
        marker = b'"role":"user"'
        for jsonl in chat_dir.glob("*.jsonl"):
            try:
                with jsonl.open("rb") as fp:
                    for line in fp:
                        if marker in line:
                            return False
            except OSError:
                # Unreadable file — safer to treat as "has content"
                # so we don't clobber something we couldn't inspect.
                return False
        return True

    def touch_session(self, sid: str) -> None:
        with self._sync_lock:
            rec = self._data["sessions"].get(sid)
            if rec:
                rec["last_used"] = _now_iso()
                ws = self._data["workspaces"].get(rec.get("workspace_id", ""))
                if ws:
                    ws["last_used"] = _now_iso()
                self._flush()

    # ── path helpers ──────────────────────────────────────────────────────
    def session_chat_dir(self, sid: str) -> Path:
        """Where pi's --session-dir points. Per-session, never shared.

        pi runs as the sandbox uid in production, so the directory it
        writes its JSONL into has to be sandbox-writable. We stamp it
        2770 1000:1000 — same model as workspaces.
        """
        path = DATA_ROOT / "chats" / sid
        path.mkdir(parents=True, exist_ok=True)
        stamp_sandbox_dir(path)
        return path

    def workspace_path(self, wsid: str) -> Path:
        rec = self._data["workspaces"].get(wsid)
        if not rec:
            raise KeyError(wsid)
        path = Path(rec["path"])
        # Cold-archive thaw: if a nightly reaper archived this
        # workspace to GCS, the on-disk tree is just a marker file.
        # Block here while we pull it back, then continue. First
        # caller pays the latency (~5–15 s for typical workspaces);
        # concurrent callers serialise on a per-wsid lock inside
        # services.cold_archive. Idempotent — a no-op if not cold.
        # We import lazily so laptop dev (no GCS bucket configured)
        # doesn't have to install gsutil.
        try:
            from services.cold_archive import is_cold, thaw_workspace
            if is_cold(wsid):
                thaw_workspace(wsid)
        except ImportError:
            pass
        return path

    def ensure_uploads_dir(self, wsid: str) -> Path:
        """Return (and create if missing) workspace/uploads/.

        Self-heals for older workspaces created before the uploads/ dir
        was part of the bootstrap.
        """
        rec = self._data["workspaces"].get(wsid)
        if not rec:
            raise KeyError(wsid)
        base = Path(rec["path"])
        uploads = base / "workspace" / "uploads"
        uploads.mkdir(parents=True, exist_ok=True)
        # Re-stamp on every call so legacy uploads/ dirs created before
        # the dual-uid migration get pulled into compliance the first
        # time they're touched after upgrade.
        stamp_sandbox_dir(uploads)
        return uploads

    # ── sandbox bootstrap ─────────────────────────────────────────────────
    def _wire_sandbox_symlinks(self, sandbox: Path) -> None:
        """
        Symlink the agent's required files (extensions/, guides/, .pi/, …)
        from PROJECT_ROOT into the sandbox so pi auto-loads them when run
        with cwd=sandbox. Read-only by convention; in v1 we don't enforce
        that (Day 5+ adds container-level enforcement).
        """
        for name in SANDBOX_SYMLINKS:
            src = PROJECT_ROOT / name
            if not src.exists():
                continue
            dst = sandbox / name
            if dst.exists() or dst.is_symlink():
                continue
            try:
                os.symlink(src, dst)
            except OSError as exc:
                print(
                    f"[registry] WARN: could not symlink {src} -> {dst}: {exc}",
                    file=sys.stderr,
                )
