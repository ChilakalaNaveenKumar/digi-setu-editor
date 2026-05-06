"""
PiSession — owns one `pi --mode rpc` subprocess and its JSONL plumbing.

Single responsibility: spawn pi for a given session id, expose two queues
(events out, commands in), and clean up on close. Knows nothing about Vue
or WebSockets — that's app.py's job.

The `--session-dir` flag points pi at a per-session folder so its built-in
SessionManager handles persistence/resume for free. Drop --no-session
deliberately; that was the whole "no session management" complaint earlier.
"""

from __future__ import annotations

import asyncio
import json
import os
import shlex
import sys
from pathlib import Path
from typing import Any, AsyncIterator, Optional

# pi-typst-test/web/backend/pi_session.py
#   .parents[0] = backend/
#   .parents[1] = web/
#   .parents[2] = pi-typst-test/   <-- PROJECT_ROOT (cwd for pi, has extensions/)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SESSIONS_ROOT = PROJECT_ROOT / "web" / "sessions"


def _load_env_sh() -> dict[str, str]:
    """
    Source pi-typst-test/scripts/env.sh in a child shell and capture the
    resulting environment, so the backend inherits the same provider/model
    defaults the user has been running interactively. Falls back to the
    current process env if env.sh is missing or fails.

    NOTE: env.sh is "first one wins" (it never overwrites a pre-set value).
    We pre-set PI_PROVIDER=anthropic-vertex and PI_MODEL=claude-sonnet-4-6 so
    the web backend pins to your patched provider regardless of env.sh's
    google-vertex defaults. Override per-session via PiSession(...) args.
    """
    env_sh = PROJECT_ROOT / "scripts" / "env.sh"
    if not env_sh.exists():
        return dict(os.environ)

    try:
        import subprocess

        # Pre-pin the patched provider so env.sh respects it.
        bash_prefix = (
            'export PI_PROVIDER="${PI_PROVIDER:-anthropic-vertex}"; '
            'export PI_MODEL="${PI_MODEL:-claude-sonnet-4-6}"; '
        )
        result = subprocess.run(
            ["bash", "-c", f"{bash_prefix} source {shlex.quote(str(env_sh))} && env -0"],
            capture_output=True,
            check=True,
            cwd=str(PROJECT_ROOT),
        )
        env: dict[str, str] = {}
        for entry in result.stdout.split(b"\x00"):
            if not entry:
                continue
            key, _, value = entry.decode("utf-8", "replace").partition("=")
            if key:
                env[key] = value
        return env
    except Exception as exc:  # pragma: no cover — defensive
        print(f"[pi_session] WARN: failed to source env.sh ({exc}); using os.environ", file=sys.stderr)
        return dict(os.environ)


class PiSession:
    """
    One pi RPC subprocess. Lifecycle:

        s = PiSession(session_id="abc")
        await s.start()
        async for evt in s.events():        # incoming JSONL from pi
            ...
        await s.send({"type": "prompt", "id": "r1", "message": "hello"})
        await s.close()

    `events()` yields parsed JSON dicts forever until the process exits or
    `close()` is called. Stderr is forwarded to backend stderr so you see
    pi's diagnostics in the uvicorn log, but does NOT mix with the event
    stream (per RPC protocol rules).
    """

    def __init__(self, session_id: str, *, provider: Optional[str] = None, model: Optional[str] = None):
        self.session_id = session_id
        self.session_dir = SESSIONS_ROOT / session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)

        env = _load_env_sh()
        # Per-session overrides win over env.sh defaults.
        self._provider = provider or env.get("PI_PROVIDER", "anthropic-vertex")
        self._model = model or env.get("PI_MODEL", "claude-opus-4-7")
        # anthropic-vertex needs location pinned to "global" for opus-4-7 (per patches/PATCH.md).
        if self._provider == "anthropic-vertex":
            env.setdefault("PI_VERTEX_ANTHROPIC_LOCATION", "global")

        self._env = env
        self._proc: Optional[asyncio.subprocess.Process] = None
        self._closed = False
        self._stderr_task: Optional[asyncio.Task] = None

    # ── lifecycle ───────────────────────────────────────────────────────────
    async def start(self) -> None:
        if self._proc is not None:
            return

        cmd = [
            "pi",
            "--mode", "rpc",
            "--provider", self._provider,
            "--model", self._model,
            "--session-dir", str(self.session_dir),
            "--extension", "./extensions/typst-tools.ts",
        ]

        # asyncio.StreamReader defaults to a 64 KB line limit. pi RPC events
        # routinely exceed that (e.g. tool_execution_end for a `write` of a
        # multi-KB file ships the full content as one JSON line). Bump to 16 MB
        # to comfortably hold any reasonable single tool result.
        self._proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(PROJECT_ROOT),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self._env,
            limit=16 * 1024 * 1024,
        )
        self._stderr_task = asyncio.create_task(self._drain_stderr())

        print(
            f"[pi_session {self.session_id}] spawned pid={self._proc.pid} "
            f"provider={self._provider} model={self._model} dir={self.session_dir}",
            file=sys.stderr,
        )

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True

        if self._proc is None:
            return

        # Polite: close stdin so pi exits cleanly; force kill after grace period.
        try:
            if self._proc.stdin and not self._proc.stdin.is_closing():
                self._proc.stdin.close()
        except Exception:
            pass

        try:
            await asyncio.wait_for(self._proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            print(f"[pi_session {self.session_id}] grace period elapsed, killing", file=sys.stderr)
            self._proc.kill()
            await self._proc.wait()

        if self._stderr_task and not self._stderr_task.done():
            self._stderr_task.cancel()

    # ── i/o ─────────────────────────────────────────────────────────────────
    async def send(self, command: dict[str, Any]) -> None:
        """Write one JSON command + LF to pi's stdin."""
        if self._proc is None or self._proc.stdin is None:
            raise RuntimeError("PiSession not started")
        line = (json.dumps(command, ensure_ascii=False) + "\n").encode("utf-8")
        self._proc.stdin.write(line)
        await self._proc.stdin.drain()

    async def events(self) -> AsyncIterator[dict[str, Any]]:
        """Yield parsed JSON events from pi's stdout until process exits."""
        if self._proc is None or self._proc.stdout is None:
            raise RuntimeError("PiSession not started")

        stdout = self._proc.stdout
        # RPC protocol: split on LF only. Strip optional CR. Never use generic
        # line readers that split on U+2028/U+2029 — those are valid inside JSON.
        while True:
            line = await stdout.readline()
            if not line:  # EOF
                break
            text = line.rstrip(b"\r\n")
            if not text:
                continue
            try:
                yield json.loads(text.decode("utf-8"))
            except json.JSONDecodeError as exc:
                print(
                    f"[pi_session {self.session_id}] non-json line: {text!r} ({exc})",
                    file=sys.stderr,
                )

    # ── internals ───────────────────────────────────────────────────────────
    async def _drain_stderr(self) -> None:
        if self._proc is None or self._proc.stderr is None:
            return
        while True:
            line = await self._proc.stderr.readline()
            if not line:
                break
            sys.stderr.write(f"[pi {self.session_id}] {line.decode('utf-8', 'replace')}")
            sys.stderr.flush()
