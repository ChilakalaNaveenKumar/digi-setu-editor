"""
ShadowGit — per-workspace shadow git repository for AI tool-call snapshots.

This is the SAME pattern used by Cline, Roo Code, and Aider:
    - A real git repo lives OUTSIDE the workspace (PROJECT_ROOT/web/.shadow.git/).
    - It's configured with `core.worktree` pointing at PROJECT_ROOT/workspace,
      so commits track workspace files without polluting any user-level git
      repo the workspace might already have.
    - Every time the AI runs a write/edit tool, we `git add -A && git commit`
      with a message that embeds the tool_call_id.
    - Mapping `tool_call_id -> commit_sha` lives in a tiny SQLite db so we
      can resolve "view diff for this old tool call" instantly.
    - "View diff" then becomes `git diff <sha>~1 <sha> --unified=999999`,
      which gives the WHOLE file with proper context — exactly what the user
      sees in Cursor's diff editor — and works correctly even after many
      subsequent edits to the same file.

Why this is robust:
    - No frontend reverse-apply gymnastics (those break with multi-edit).
    - Survives backend restarts (git + sqlite are persisted on disk).
    - Trivial to extend with "restore" / "undo" later (just `git reset --hard`).
    - Free side-effect: a complete history of every AI change to the workspace.

Layout:
    PROJECT_ROOT/
      workspace/              ← what pi modifies; tracked by shadow repo
      web/
        .shadow-git/          ← bare-ish git dir; never visible to pi
        snapshots.sqlite      ← maps tool_call_id -> commit_sha + path
"""

from __future__ import annotations

import asyncio
import os
import sqlite3
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional

from pi_session import PROJECT_ROOT

WORKSPACE_DIR = PROJECT_ROOT / "workspace"
SHADOW_GIT_DIR = PROJECT_ROOT / "web" / ".shadow-git"
SNAPSHOTS_DB = PROJECT_ROOT / "web" / "snapshots.sqlite"

# Identity used for shadow-repo commits. We hardcode it so user .gitconfig
# isn't required and commits show as agent-authored.
SHADOW_AUTHOR_NAME = "pi-typst-test agent"
SHADOW_AUTHOR_EMAIL = "agent@pi-typst-test.local"


def _git(args: list[str], *, capture: bool = True) -> subprocess.CompletedProcess[str]:
    """Run a `git` command against the shadow repo with the right env."""
    env = os.environ.copy()
    env["GIT_DIR"] = str(SHADOW_GIT_DIR)
    env["GIT_WORK_TREE"] = str(WORKSPACE_DIR)
    env["GIT_AUTHOR_NAME"] = SHADOW_AUTHOR_NAME
    env["GIT_AUTHOR_EMAIL"] = SHADOW_AUTHOR_EMAIL
    env["GIT_COMMITTER_NAME"] = SHADOW_AUTHOR_NAME
    env["GIT_COMMITTER_EMAIL"] = SHADOW_AUTHOR_EMAIL
    return subprocess.run(
        ["git", *args],
        cwd=str(WORKSPACE_DIR),
        env=env,
        capture_output=capture,
        text=True,
        check=False,
    )


# ── SQLite mapping ───────────────────────────────────────────────────────────
@contextmanager
def _db() -> Iterator[sqlite3.Connection]:
    SNAPSHOTS_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(SNAPSHOTS_DB))
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
        # Best-effort migration for older DBs that predate user_message_id.
        # (SQLite ADD COLUMN is idempotent-safe via try/except.)
        try:
            conn.execute("ALTER TABLE snapshots ADD COLUMN user_message_id TEXT")
        except sqlite3.OperationalError:
            pass  # already exists
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_snapshots_path ON snapshots(path)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_snapshots_user_msg
                ON snapshots(user_message_id)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_snapshots_created
                ON snapshots(created_ts)
            """
        )
        yield conn
        conn.commit()
    finally:
        conn.close()


# ── Public API ───────────────────────────────────────────────────────────────
class ShadowGit:
    """
    Process-level singleton wrapper. Use `ShadowGit.instance()`.
    """

    _instance: Optional["ShadowGit"] = None
    _init_lock = asyncio.Lock()

    @classmethod
    def instance(cls) -> "ShadowGit":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        # Per-WS lock so concurrent tool_execution_end events from multiple
        # sessions don't race on `git add` + `git commit`.
        self._commit_lock = asyncio.Lock()

    # ── lifecycle ─────────────────────────────────────────────────────────
    async def ensure_init(self) -> None:
        """Create shadow repo + initial baseline commit (idempotent)."""
        if not WORKSPACE_DIR.exists():
            WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

        if not SHADOW_GIT_DIR.exists():
            SHADOW_GIT_DIR.mkdir(parents=True, exist_ok=True)
            r = _git(["init", "--initial-branch=main"])
            if r.returncode != 0:
                raise RuntimeError(f"shadow git init failed: {r.stderr}")
            # Some git versions ignore --initial-branch; force.
            _git(["symbolic-ref", "HEAD", "refs/heads/main"])
            print(f"[shadow-git] initialized at {SHADOW_GIT_DIR}", file=sys.stderr)

        # Commit current state as baseline if no commits yet.
        log = _git(["log", "-1", "--format=%H"])
        if log.returncode != 0 or not log.stdout.strip():
            r = _git(["add", "-A"])
            if r.returncode != 0:
                print(f"[shadow-git] baseline add: {r.stderr}", file=sys.stderr)
            r = _git([
                "commit",
                "--allow-empty",
                "-m", "shadow-git: baseline (session bootstrap)",
            ])
            if r.returncode != 0:
                print(f"[shadow-git] baseline commit: {r.stderr}", file=sys.stderr)
            else:
                print("[shadow-git] baseline commit created", file=sys.stderr)

    # ── snapshot ─────────────────────────────────────────────────────────
    async def snapshot_after_tool_call(
        self,
        *,
        tool_call_id: str,
        tool_name: str,
        path: str,
        user_message_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Commit any workspace changes and record `tool_call_id -> commit_sha`.

        Returns the commit sha if a real commit happened (changes existed),
        OR the existing HEAD sha if nothing changed (so future "view diff"
        for this id still resolves — diff will show empty). Returns None
        on hard failure.

        `user_message_id` (when provided) lets us group every tool call that
        happened in response to one user prompt — required for "revert turn".

        Safe to call from the WS event loop. Internally serialized so
        concurrent tool calls don't race on git index.
        """
        async with self._commit_lock:
            r_add = await _run_async(_git, ["add", "-A"])
            if r_add.returncode != 0:
                print(f"[shadow-git] add failed: {r_add.stderr}", file=sys.stderr)
                return None

            msg = (
                f"tool:{tool_name} call:{tool_call_id} "
                f"user_msg:{user_message_id or '-'} path:{path or '<unknown>'}"
            )
            r_commit = await _run_async(_git, ["commit", "-m", msg])

            if r_commit.returncode == 0:
                r_sha = await _run_async(_git, ["rev-parse", "HEAD"])
                sha = r_sha.stdout.strip() if r_sha.returncode == 0 else ""
            else:
                if "nothing to commit" not in (r_commit.stdout + r_commit.stderr).lower():
                    print(
                        f"[shadow-git] commit non-fatal: {r_commit.stdout}{r_commit.stderr}",
                        file=sys.stderr,
                    )
                r_sha = await _run_async(_git, ["rev-parse", "HEAD"])
                sha = r_sha.stdout.strip() if r_sha.returncode == 0 else ""

            if not sha:
                return None

            with _db() as db:
                db.execute(
                    "INSERT OR REPLACE INTO snapshots"
                    "(tool_call_id, commit_sha, tool_name, path, user_message_id, created_ts) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (tool_call_id, sha, tool_name, path, user_message_id, time.time()),
                )
            return sha

    # ── readback ─────────────────────────────────────────────────────────
    def lookup(self, tool_call_id: str) -> Optional[dict[str, Any]]:
        with _db() as db:
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
        """
        Return `{ path, tool_name, unified_diff }` for one tool call, where
        `unified_diff` is a full-context unified diff (every line of the file
        as context, changed lines marked +/-) ready to feed to diff2html.

        Resolution: diff between this commit and its parent. For the very
        first commit (no parent) we synthesize a /dev/null parent so the
        whole file shows as additions.
        """
        snap = self.lookup(tool_call_id)
        if not snap:
            return None
        sha = snap["commit_sha"]
        path = snap["path"]

        # Use a very large -U so EVERY line of the file is shown as context.
        # 1_000_000 is well beyond any realistic source file.
        # `--no-color` keeps the output ANSI-clean for text consumers.
        # Limit to the specific path to avoid noise from unrelated files.
        # Try with a parent first; if there's no parent (first commit), git
        # exits with code 128 — fall back to /dev/null comparison.
        cmd = [
            "diff",
            "--no-color",
            "--unified=1000000",
            f"{sha}~1",
            sha,
            "--",
            path,
        ]
        r = _git(cmd)
        if r.returncode != 0:
            # Probably first commit. Compare against /dev/null (i.e. show
            # this file as fully added).
            r = _git([
                "diff",
                "--no-color",
                "--unified=1000000",
                "4b825dc642cb6eb9a060e54bf8d69288fbee4904",  # empty tree sha
                sha,
                "--",
                path,
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
        """List of paths that this commit modified (vs its parent)."""
        r = _git(["diff", "--no-color", "--name-only", f"{sha}~1", sha])
        if r.returncode != 0:
            # First commit (no parent) — diff against empty tree.
            r = _git([
                "diff",
                "--no-color",
                "--name-only",
                "4b825dc642cb6eb9a060e54bf8d69288fbee4904",
                sha,
            ])
            if r.returncode != 0:
                return []
        return [line for line in r.stdout.splitlines() if line.strip()]

    def _parent_sha(self, sha: str) -> Optional[str]:
        """Return the parent commit sha, or None if `sha` is the root."""
        r = _git(["rev-parse", f"{sha}~1"])
        if r.returncode != 0:
            return None
        return r.stdout.strip() or None

    async def restore_to_before_tool_call(
        self,
        tool_call_id: str,
    ) -> Optional[dict[str, Any]]:
        """
        Rewind the workspace to the state RIGHT BEFORE this tool call ran.

        Strategy (opencode-style "revert from here"):
          1. Find the snapshot for `tool_call_id`.
          2. Collect every snapshot whose created_ts >= target.created_ts
             (this snapshot AND every snapshot that came after it).
          3. For each unique file mentioned by ANY of those snapshots:
                git checkout <target.parent_sha> -- <file>
             which restores it to whatever it was before THIS tool call
             touched it. Files that didn't exist back then are deleted.
          4. Make a fresh commit recording the restore (so a later "View
             diff" on a NEW tool call has a sane parent).

        Returns `{ restored_files: [...], baseline_sha: ... }` on success,
        None if the tool_call_id is unknown.
        """
        snap = self.lookup(tool_call_id)
        if not snap:
            return None
        target_sha = snap["commit_sha"]
        target_ts = snap["created_ts"]
        baseline_sha = self._parent_sha(target_sha)

        # Empty tree fallback for the very first commit.
        if not baseline_sha:
            baseline_sha = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

        # Files we need to restore = union of files touched by THIS commit
        # AND any commit recorded later. Use the DB (not git log) so we only
        # touch files our agent owns — never a hand-edit the user made.
        with _db() as db:
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
            # Restore each file. `git checkout <sha> -- <file>` works for
            # both modify and delete (file absent in baseline = removed).
            for fpath in affected:
                r = _git(["checkout", baseline_sha, "--", fpath])
                if r.returncode != 0:
                    # File didn't exist in baseline — delete it from worktree.
                    full = WORKSPACE_DIR / fpath
                    try:
                        if full.exists():
                            full.unlink()
                    except OSError as exc:
                        print(
                            f"[shadow-git] restore: could not unlink {fpath}: {exc}",
                            file=sys.stderr,
                        )

            # Snapshot the restore itself so the next AI tool call has a
            # clean parent. Without this, "View diff" on a future call
            # would diff against the not-yet-restored state.
            await _run_async(_git, ["add", "-A"])
            await _run_async(
                _git,
                [
                    "commit",
                    "--allow-empty",
                    "-m",
                    f"shadow-git: restore to before {tool_call_id}",
                ],
            )

        return {
            "restored_files": affected,
            "baseline_sha": baseline_sha,
            "tool_call_id": tool_call_id,
        }

    async def revert_user_turn(self, user_message_id: str) -> Optional[dict[str, Any]]:
        """
        Revert every file change that happened in response to one user
        prompt. Resolves the EARLIEST tool call recorded for this
        user_message_id and delegates to `restore_to_before_tool_call`.

        Returns `{ restored_files, baseline_sha, user_message_id }`, or
        None if no snapshots are tied to this user message.
        """
        with _db() as db:
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


# ── helpers ──────────────────────────────────────────────────────────────────
async def _run_async(fn, *args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
    """Run a blocking subprocess call off the event loop."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))
