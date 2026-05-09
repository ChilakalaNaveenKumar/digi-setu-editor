"""
ShadowGit — per-workspace shadow git repository for AI tool-call snapshots.

This is the SAME pattern used by Cline, Roo Code, and Aider:
    - A real git repo lives OUTSIDE the user-visible workspace, with
      `core.worktree` pointing at the workspace's user-files dir, so
      commits track files without polluting any user-level git repo the
      workspace might already have.
    - Every time the AI runs a write/edit tool, we `git add -A && git commit`
      with a message embedding the tool_call_id.
    - Mapping `tool_call_id -> commit_sha` lives in a per-workspace SQLite
      DB so "view diff" is O(1).
    - "View diff" then becomes `git diff <sha>~1 <sha> --unified=999999` —
      whole file with proper context, correct even after many subsequent
      edits to the same file.

**Important: shadow repos live OUTSIDE the sandbox.**

The agent's `pi` subprocess has cwd=<sandbox> and a `bash` tool; if
`.shadow-git/` lived inside the sandbox the agent could see it via
`ls -la ..` and a malicious prompt could trick pi into `rm -rf .shadow-git/`
or `git commit --amend` to forge history. Putting it under a sibling root
the agent literally cannot reach via its cwd is the simplest, hardest
boundary.

Layout (one per active workspace):
    web/data/
      workspaces/<wsid>/             ← agent's cwd. Sees workspace/ + symlinks.
        workspace/
        extensions → symlink, …

      shadows/<wsid>/                ← INVISIBLE to the agent. Never symlinked.
        .git/                        ← bare-ish git dir
        snapshots.sqlite             ← tool_call_id -> commit_sha + path

Use:
    sg = ShadowGitRegistry.instance().for_workspace(workspace_path)
    await sg.ensure_init()
    await sg.snapshot_after_tool_call(...)
    sg.diff_for_tool_call(...)

Cleanup: when a workspace is deleted (Registry.delete_workspace), call
ShadowGitRegistry.instance().purge_workspace(workspace_path) to remove the
shadow repo too. Storage stays bounded because deletes cascade.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional

from config import DATA_ROOT
from services.paths import ws_root

# Identity used for shadow-repo commits. Hardcoded so user .gitconfig
# isn't required and commits show as agent-authored.
SHADOW_AUTHOR_NAME = "Digi Setu agent"
SHADOW_AUTHOR_EMAIL = "agent@digi-setu.local"

SHADOWS_ROOT_NAME = "shadows"
GIT_DIR_NAME = ".git"
SNAPSHOTS_DB_NAME = "snapshots.sqlite"


def _shadow_key_for(workspace_path: Path) -> str:
    """
    Stable, filesystem-safe key derived from a workspace's canonical path.

    Desktop workspaces are arbitrary user folders (e.g.
    `/Users/me/Test`) — there's no embedded wsid in the path we can reuse,
    and two folders named `Test` under different parents would collide
    if we used the basename alone. We use:

        <basename>-<8-hex-of-sha1(canonical_path)>

    so the directory name is human-recognisable on disk AND unique per
    canonical path. SHA1 is fine here — this is not a security boundary,
    just a uniqueness label.
    """
    canon = str(Path(workspace_path).expanduser().resolve())
    digest = hashlib.sha1(canon.encode("utf-8")).hexdigest()[:8]
    name = Path(canon).name or "root"
    # Strip anything filesystem-unfriendly from the basename so we never
    # produce a path that mkdir would reject. POSIX is permissive but
    # FAT/NTFS aren't, and this code runs on Windows too.
    safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in name)[:48]
    return f"{safe_name}-{digest}"


def _shadow_root_for(workspace_path: Path) -> Path:
    """
    Per-workspace shadow repo root, anchored under DATA_ROOT.

    In the desktop fork DATA_ROOT is `~/.digi-setu/`, so shadows live at
    `~/.digi-setu/shadows/<key>/`. We never walk up from `workspace_path`
    anymore: that strategy worked when workspaces were sandboxes the
    backend itself created (`web/data/workspaces/<wsid>/`), but in
    desktop the workspace is the user's real folder and walking up from
    `/Users/me/Test` lands in `/Users/` which we can't write to.

    The agent never sees this folder — it's outside its cwd and outside
    DATA_ROOT/.. — so the existing isolation guarantees still hold.
    """
    return DATA_ROOT / SHADOWS_ROOT_NAME / _shadow_key_for(workspace_path)


def _git_dir(workspace_path: Path) -> Path:
    return _shadow_root_for(workspace_path) / GIT_DIR_NAME


def _snapshots_db(workspace_path: Path) -> Path:
    return _shadow_root_for(workspace_path) / SNAPSHOTS_DB_NAME


class ShadowGit:
    """
    One shadow repo per workspace. Construct via ShadowGitRegistry; don't
    instantiate directly.
    """

    def __init__(self, workspace_path: Path) -> None:
        self.workspace_path = Path(workspace_path)
        self.work_tree = ws_root(self.workspace_path)
        # Shadow repo lives in a sibling shadows/<wsid>/ folder, NOT inside
        # the sandbox, so the agent can't see it via its bash tool.
        self.shadow_root = _shadow_root_for(self.workspace_path)
        self.git_dir = _git_dir(self.workspace_path)
        self.db_path = _snapshots_db(self.workspace_path)
        # Per-workspace lock so concurrent tool_execution_end events from
        # the same workspace don't race on `git add` + `git commit`.
        self._commit_lock = asyncio.Lock()
        self._initialized = False

    # ── git command helper ───────────────────────────────────────────────
    def _git(self, args: list[str], *, capture: bool = True) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["GIT_DIR"] = str(self.git_dir)
        env["GIT_WORK_TREE"] = str(self.work_tree)
        env["GIT_AUTHOR_NAME"] = SHADOW_AUTHOR_NAME
        env["GIT_AUTHOR_EMAIL"] = SHADOW_AUTHOR_EMAIL
        env["GIT_COMMITTER_NAME"] = SHADOW_AUTHOR_NAME
        env["GIT_COMMITTER_EMAIL"] = SHADOW_AUTHOR_EMAIL
        return subprocess.run(
            ["git", *args],
            cwd=str(self.work_tree),
            env=env,
            capture_output=capture,
            text=True,
            check=False,
        )

    # ── SQLite ────────────────────────────────────────────────────────────
    @contextmanager
    def _db(self) -> Iterator[sqlite3.Connection]:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS snapshots (
                    tool_call_id    TEXT PRIMARY KEY,
                    commit_sha      TEXT NOT NULL,
                    tool_name       TEXT NOT NULL,
                    path            TEXT NOT NULL,
                    user_message_id TEXT,
                    created_ts      REAL NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_path ON snapshots(path)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_snapshots_user_msg ON snapshots(user_message_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_snapshots_created ON snapshots(created_ts)"
            )
            yield conn
            conn.commit()
        finally:
            conn.close()

    # ── lifecycle ─────────────────────────────────────────────────────────
    async def ensure_init(self) -> None:
        """Create shadow repo + initial baseline commit (idempotent)."""
        if self._initialized:
            return

        if not self.work_tree.exists():
            self.work_tree.mkdir(parents=True, exist_ok=True)
        # Make sure the OUT-OF-SANDBOX shadow root exists too.
        self.shadow_root.mkdir(parents=True, exist_ok=True)

        if not self.git_dir.exists():
            self.git_dir.mkdir(parents=True, exist_ok=True)
            r = self._git(["init", "--initial-branch=main"])
            if r.returncode != 0:
                raise RuntimeError(f"shadow git init failed: {r.stderr}")
            self._git(["symbolic-ref", "HEAD", "refs/heads/main"])
            print(f"[shadow-git] initialized at {self.git_dir}", file=sys.stderr)

        log = self._git(["log", "-1", "--format=%H"])
        if log.returncode != 0 or not log.stdout.strip():
            r = self._git(["add", "-A"])
            if r.returncode != 0:
                print(f"[shadow-git] baseline add: {r.stderr}", file=sys.stderr)
            r = self._git([
                "commit",
                "--allow-empty",
                "-m", "shadow-git: baseline (session bootstrap)",
            ])
            if r.returncode != 0:
                print(f"[shadow-git] baseline commit: {r.stderr}", file=sys.stderr)
            else:
                print(f"[shadow-git] baseline commit created in {self.git_dir.name}", file=sys.stderr)

        self._initialized = True

    # ── snapshot ─────────────────────────────────────────────────────────
    async def snapshot_after_tool_call(
        self,
        *,
        tool_call_id: str,
        tool_name: str,
        path: str,
        user_message_id: Optional[str] = None,
    ) -> Optional[str]:
        """Commit any workspace changes, record `tool_call_id -> commit_sha`."""
        async with self._commit_lock:
            r_add = await self._run_async(self._git, ["add", "-A"])
            if r_add.returncode != 0:
                print(f"[shadow-git] add failed: {r_add.stderr}", file=sys.stderr)
                return None

            msg = (
                f"tool:{tool_name} call:{tool_call_id} "
                f"user_msg:{user_message_id or '-'} path:{path or '<unknown>'}"
            )
            r_commit = await self._run_async(self._git, ["commit", "-m", msg])

            if r_commit.returncode == 0:
                r_sha = await self._run_async(self._git, ["rev-parse", "HEAD"])
                sha = r_sha.stdout.strip() if r_sha.returncode == 0 else ""
            else:
                if "nothing to commit" not in (r_commit.stdout + r_commit.stderr).lower():
                    print(
                        f"[shadow-git] commit non-fatal: {r_commit.stdout}{r_commit.stderr}",
                        file=sys.stderr,
                    )
                r_sha = await self._run_async(self._git, ["rev-parse", "HEAD"])
                sha = r_sha.stdout.strip() if r_sha.returncode == 0 else ""

            if not sha:
                return None

            with self._db() as db:
                db.execute(
                    "INSERT OR REPLACE INTO snapshots"
                    "(tool_call_id, commit_sha, tool_name, path, user_message_id, created_ts) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (tool_call_id, sha, tool_name, path, user_message_id, time.time()),
                )
            return sha

    # ── readback ─────────────────────────────────────────────────────────
    def lookup(self, tool_call_id: str) -> Optional[dict[str, Any]]:
        with self._db() as db:
            row = db.execute(
                "SELECT commit_sha, tool_name, path, created_ts FROM snapshots WHERE tool_call_id=?",
                (tool_call_id,),
            ).fetchone()
        if not row:
            return None
        return {
            "tool_call_id": tool_call_id,
            "commit_sha": row[0],
            "tool_name": row[1],
            "path": row[2],
            "created_ts": row[3],
        }

    def diff_for_tool_call(self, tool_call_id: str) -> Optional[dict[str, Any]]:
        snap = self.lookup(tool_call_id)
        if not snap:
            return None
        sha = snap["commit_sha"]
        path = snap["path"]
        cmd = ["diff", "--no-color", "--unified=1000000", f"{sha}~1", sha, "--", path]
        r = self._git(cmd)
        if r.returncode != 0:
            r = self._git([
                "diff", "--no-color", "--unified=1000000",
                "4b825dc642cb6eb9a060e54bf8d69288fbee4904",  # empty tree sha
                sha, "--", path,
            ])
            if r.returncode != 0:
                print(f"[shadow-git] diff failed: {r.stderr}", file=sys.stderr)
                return None
        return {
            "path": path,
            "tool_name": snap["tool_name"],
            "commit_sha": sha,
            "unified_diff": r.stdout,
        }

    # ── restore (rewind-from-here, opencode pattern) ─────────────────────
    def _files_changed_in(self, sha: str) -> list[str]:
        r = self._git(["diff", "--no-color", "--name-only", f"{sha}~1", sha])
        if r.returncode != 0:
            r = self._git([
                "diff", "--no-color", "--name-only",
                "4b825dc642cb6eb9a060e54bf8d69288fbee4904", sha,
            ])
            if r.returncode != 0:
                return []
        return [line for line in r.stdout.splitlines() if line.strip()]

    def _parent_sha(self, sha: str) -> Optional[str]:
        r = self._git(["rev-parse", f"{sha}~1"])
        if r.returncode != 0:
            return None
        return r.stdout.strip() or None

    async def restore_to_before_tool_call(self, tool_call_id: str) -> Optional[dict[str, Any]]:
        snap = self.lookup(tool_call_id)
        if not snap:
            return None
        target_sha = snap["commit_sha"]
        target_ts = snap["created_ts"]
        baseline_sha = self._parent_sha(target_sha)
        if not baseline_sha:
            baseline_sha = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

        with self._db() as db:
            rows = db.execute(
                "SELECT commit_sha FROM snapshots WHERE created_ts >= ? ORDER BY created_ts ASC",
                (target_ts,),
            ).fetchall()

        affected: list[str] = []
        seen: set[str] = set()
        for (sha,) in rows:
            for fpath in self._files_changed_in(sha):
                if fpath in seen:
                    continue
                seen.add(fpath)
                affected.append(fpath)

        if not affected:
            return {"restored_files": [], "baseline_sha": baseline_sha}

        async with self._commit_lock:
            for fpath in affected:
                r = self._git(["checkout", baseline_sha, "--", fpath])
                if r.returncode != 0:
                    full = self.work_tree / fpath
                    try:
                        if full.exists():
                            full.unlink()
                    except OSError as exc:
                        print(
                            f"[shadow-git] restore: could not unlink {fpath}: {exc}",
                            file=sys.stderr,
                        )

            await self._run_async(self._git, ["add", "-A"])
            await self._run_async(
                self._git,
                ["commit", "--allow-empty", "-m", f"shadow-git: restore to before {tool_call_id}"],
            )

        return {
            "restored_files": affected,
            "baseline_sha": baseline_sha,
            "tool_call_id": tool_call_id,
        }

    async def revert_user_turn(self, user_message_id: str) -> Optional[dict[str, Any]]:
        with self._db() as db:
            row = db.execute(
                "SELECT tool_call_id FROM snapshots WHERE user_message_id=? "
                "ORDER BY created_ts ASC LIMIT 1",
                (user_message_id,),
            ).fetchone()
        if not row:
            return None
        result = await self.restore_to_before_tool_call(row[0])
        if result is None:
            return None
        result["user_message_id"] = user_message_id
        return result

    @staticmethod
    async def _run_async(fn, *args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))


# ── registry: one ShadowGit per workspace, on demand ──────────────────────
class ShadowGitRegistry:
    """Process-wide cache: one ShadowGit instance per workspace_path."""

    _singleton: "ShadowGitRegistry | None" = None
    _singleton_lock = threading.Lock()

    @classmethod
    def instance(cls) -> "ShadowGitRegistry":
        with cls._singleton_lock:
            if cls._singleton is None:
                cls._singleton = cls()
            return cls._singleton

    def __init__(self) -> None:
        self._cache: dict[str, ShadowGit] = {}
        self._lock = threading.Lock()

    def for_workspace(self, workspace_path: Path) -> ShadowGit:
        key = str(Path(workspace_path).resolve())
        with self._lock:
            sg = self._cache.get(key)
            if sg is None:
                sg = ShadowGit(workspace_path)
                self._cache[key] = sg
            return sg

    def purge_workspace(self, workspace_path: Path) -> None:
        """
        Drop the cached ShadowGit AND `rm -rf` the on-disk shadow root
        for this workspace. Safe to call even if nothing was ever
        initialized; called from Registry.delete_workspace().
        """
        key = str(Path(workspace_path).resolve())
        with self._lock:
            self._cache.pop(key, None)
        shadow_root = _shadow_root_for(workspace_path)
        if shadow_root.exists():
            shutil.rmtree(shadow_root, ignore_errors=True)
