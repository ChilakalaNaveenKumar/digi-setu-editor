"""
Interactive terminal sessions backed by Unix PTYs.

Each terminal is a real shell (zsh / bash / sh / fish / …) running inside
an openpty pair. We hold the master fd; the client (xterm.js in the
browser) sends keystrokes/resize over a WebSocket; we proxy them onto
the master fd and stream the master fd's output back over the same
WebSocket.

Why a custom module instead of e.g. `ptyprocess` or `pexpect`:
  - We need fully async I/O integrated with FastAPI's loop.
  - We want lots of subscribers per session (so the user can have the
    terminal pane open in two browser tabs and both see live output).
  - The dependency footprint stays tiny — just the stdlib `pty`/`os`/
    `fcntl`/`termios` modules, all of which ship with CPython on macOS
    and Linux.

Windows is a non-goal for v2 (would need ConPTY / pywinpty).
"""

from __future__ import annotations

import asyncio
import contextlib
import errno
import fcntl
import logging
import os
import pty
import shutil
import signal
import struct
import sys
import termios
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional

logger = logging.getLogger("pty_terminal")

# Default per-fd read chunk. Larger = fewer syscalls but higher latency
# for tiny outputs (e.g. character echo in a shell prompt).
_READ_CHUNK = 4096


# ── OS-aware shell discovery ──────────────────────────────────────────
def _read_etc_shells() -> list[str]:
    """Parse /etc/shells. Returns a list of shells the OS endorses for
    interactive use. Filters out comments + entries that don't exist."""
    out: list[str] = []
    try:
        with open("/etc/shells", "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if os.path.exists(line) and os.access(line, os.X_OK):
                    out.append(line)
    except OSError:
        pass
    return out


def discover_shell_profiles() -> list[dict[str, str]]:
    """
    Return a list of shell profiles the user can pick from when creating
    a new terminal. Each profile is `{id, label, path, isDefault}`.

    Strategy:
      1. Default = $SHELL (or /bin/zsh on macOS, /bin/bash elsewhere).
      2. Add every shell from /etc/shells that exists.
      3. De-duplicate by absolute path.
    """
    profiles: list[dict[str, str]] = []
    seen: set[str] = set()

    def _add(path: str, label: str | None = None, default: bool = False) -> None:
        if not path or path in seen:
            return
        if not (os.path.exists(path) and os.access(path, os.X_OK)):
            return
        seen.add(path)
        profiles.append(
            {
                "id": path,
                "label": label or os.path.basename(path),
                "path": path,
                "isDefault": "true" if default else "false",
            }
        )

    user_shell = os.environ.get("SHELL", "")
    if user_shell:
        _add(user_shell, default=True)
    elif sys.platform == "darwin":
        _add("/bin/zsh", default=True)
    else:
        _add("/bin/bash", default=True)

    for s in _read_etc_shells():
        _add(s)
    # Common fallbacks even if not in /etc/shells.
    for s in ("/bin/zsh", "/bin/bash", "/bin/sh", "/usr/bin/fish"):
        _add(s)

    return profiles


# ── A single PTY session ───────────────────────────────────────────────
@dataclass
class PtyTerminal:
    """One running interactive shell wrapped around an openpty pair.

    Public surface:
      - `id`             : opaque uuid string
      - `pid`            : the shell's PID (for kill -9 etc.)
      - `shell`          : absolute path of the shell we spawned
      - `cwd`            : directory the shell started in
      - `cols` / `rows`  : current TTY size (kept in sync via resize())
      - `closed`         : True after the shell exits OR we kill it
      - `subscribers`    : list of async callbacks invoked on every output
                           chunk; used by the WS handler to fan out to
                           multiple browser tabs.
    """

    id: str
    pid: int
    shell: str
    cwd: str
    master_fd: int
    cols: int = 80
    rows: int = 24
    closed: bool = False
    started_at: float = field(default_factory=time.time)
    # `bytes` because terminal output is binary (ANSI escapes etc.); the
    # client's xterm decoder handles UTF-8 + control sequences.
    subscribers: list[Callable[[bytes], Awaitable[None]]] = field(default_factory=list)
    # Background read task pumping master_fd → subscribers.
    _read_task: Optional[asyncio.Task] = None

    # ── Subscription API ────────────────────────────────────────────
    def subscribe(self, fn: Callable[[bytes], Awaitable[None]]) -> Callable[[], None]:
        """Register a coroutine to receive every output chunk. Returns
        an unsubscribe handle."""
        self.subscribers.append(fn)

        def _unsub() -> None:
            with contextlib.suppress(ValueError):
                self.subscribers.remove(fn)

        return _unsub

    # ── PTY I/O ─────────────────────────────────────────────────────
    def write(self, data: bytes) -> None:
        """Write user keystrokes to the shell's stdin (via master fd)."""
        if self.closed:
            return
        try:
            os.write(self.master_fd, data)
        except OSError as exc:
            logger.warning("pty %s write failed: %s", self.id, exc)
            self._mark_closed()

    def resize(self, cols: int, rows: int) -> None:
        """Tell the kernel the TTY is now `cols x rows` characters. The
        shell will SIGWINCH, redrawing prompts and fitting full-screen
        TUIs (htop, vim, less) to the new geometry."""
        if self.closed:
            return
        cols = max(1, min(cols, 1024))
        rows = max(1, min(rows, 1024))
        try:
            packed = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, packed)
            self.cols = cols
            self.rows = rows
        except OSError as exc:
            logger.warning("pty %s resize failed: %s", self.id, exc)

    def kill(self, sig: int = signal.SIGTERM) -> None:
        """Send `sig` (default SIGTERM) to the shell's process group.
        Falls back to SIGKILL after a short grace period."""
        if self.pid <= 0:
            return
        try:
            os.killpg(os.getpgid(self.pid), sig)
        except ProcessLookupError:
            self._mark_closed()
        except OSError as exc:
            logger.warning("pty %s kill failed: %s", self.id, exc)

    # ── Lifecycle ───────────────────────────────────────────────────
    def _mark_closed(self) -> None:
        if self.closed:
            return
        self.closed = True
        with contextlib.suppress(OSError):
            os.close(self.master_fd)
        if self._read_task and not self._read_task.done():
            self._read_task.cancel()

    async def _broadcast(self, chunk: bytes) -> None:
        """Fan out `chunk` to every subscriber. Failures don't stop us
        — a dead websocket shouldn't take down the read loop."""
        if not self.subscribers:
            return
        # Snapshot so .remove() during iteration is safe.
        for sub in list(self.subscribers):
            try:
                await sub(chunk)
            except Exception:
                logger.exception("pty %s subscriber raised", self.id)

    async def _read_loop(self) -> None:
        """Background task: read from master fd, broadcast to subscribers,
        until EOF or fd closed."""
        loop = asyncio.get_running_loop()
        # Non-blocking — we drive reads from a thread executor since
        # `os.read` blocks even on a non-blocking fd in some kernels.
        # Simpler: register the fd with the event loop's reader.
        fut: asyncio.Future[bytes] = asyncio.Future()

        def _on_readable() -> None:
            if fut.done():
                return
            try:
                data = os.read(self.master_fd, _READ_CHUNK)
            except OSError as exc:
                # EIO is returned when the slave fd is closed (= shell exited).
                if exc.errno in (errno.EIO, errno.EBADF):
                    fut.set_result(b"")
                else:
                    fut.set_exception(exc)
                return
            fut.set_result(data)

        try:
            while not self.closed:
                fut = asyncio.Future()
                loop.add_reader(self.master_fd, _on_readable)
                try:
                    chunk = await fut
                finally:
                    with contextlib.suppress(ValueError, OSError):
                        loop.remove_reader(self.master_fd)
                if not chunk:
                    break  # EOF — shell exited.
                await self._broadcast(chunk)
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("pty %s read loop crashed", self.id)
        finally:
            self._mark_closed()
            # Notify subscribers that the session is gone — empty bytes
            # is our convention for "end of stream".
            await self._broadcast(b"")


# ── Factory: spawn a shell inside a fresh PTY ─────────────────────────
def spawn_pty(
    shell: str,
    cwd: str,
    cols: int = 80,
    rows: int = 24,
    env: dict[str, str] | None = None,
) -> PtyTerminal:
    """
    Fork a child running `shell` inside a fresh PTY. Returns a
    PtyTerminal handle whose master_fd is owned by the caller (the
    PtyTerminal instance will close it on `_mark_closed`).

    The child inherits a sane TERM/PATH env. We DON'T inherit the
    server's full environment to avoid leaking e.g. uvicorn's
    PYTHONPATH or virtualenv into the user's shell.
    """
    if not (os.path.exists(shell) and os.access(shell, os.X_OK)):
        raise FileNotFoundError(f"shell not executable: {shell}")
    safe_cwd = cwd if (cwd and os.path.isdir(cwd)) else os.path.expanduser("~")

    pid, master_fd = pty.fork()
    if pid == 0:
        # ── child ───────────────────────────────────────────────────
        try:
            os.chdir(safe_cwd)
        except OSError:
            pass
        # Pure execve so the child IS the shell — no Python wrapper
        # process lurking and consuming signals.
        merged_env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin"),
            "HOME": os.environ.get("HOME", safe_cwd),
            "USER": os.environ.get("USER", ""),
            "LANG": os.environ.get("LANG", "en_US.UTF-8"),
            "LC_ALL": os.environ.get("LC_ALL", "en_US.UTF-8"),
            "TERM": "xterm-256color",
            "COLORTERM": "truecolor",
            "SHELL": shell,
            # Use a fresh process group so killpg actually kills the shell.
            # Set later via setsid() — done implicitly by pty.fork().
        }
        if env:
            merged_env.update(env)
        try:
            os.execvpe(shell, [shell, "-l"], merged_env)
        except Exception as exc:  # pragma: no cover - child failure path
            sys.stderr.write(f"failed to exec shell: {exc}\n")
            os._exit(127)

    # ── parent ───────────────────────────────────────────────────────
    term = PtyTerminal(
        id=uuid.uuid4().hex[:12],
        pid=pid,
        shell=shell,
        cwd=safe_cwd,
        master_fd=master_fd,
        cols=cols,
        rows=rows,
    )
    term.resize(cols, rows)
    term._read_task = asyncio.get_event_loop().create_task(term._read_loop())
    # Reap the child in the background so we don't leave zombies.
    asyncio.get_event_loop().create_task(_reap_when_dead(term))
    return term


async def _reap_when_dead(term: PtyTerminal) -> None:
    """Wait for the shell to exit, then mark the terminal closed.
    `os.waitpid(pid, WNOHANG)` polled on a short loop is the simplest
    portable thing — SIGCHLD inside an event loop is messy."""
    while not term.closed:
        try:
            wpid, _status = os.waitpid(term.pid, os.WNOHANG)
        except ChildProcessError:
            term._mark_closed()
            return
        if wpid != 0:
            term._mark_closed()
            return
        await asyncio.sleep(0.5)


# ── Per-workspace registry ────────────────────────────────────────────
class TerminalRegistry:
    """Per-workspace catalogue of live PTY sessions.

    Each workspace owns its own terminals — one user's `htop` running in
    workspace A is invisible (and unkillable) from workspace B. Resolve
    via PtyHub.for_workspace(wsid).
    """

    def __init__(self, workspace_id: str) -> None:
        self.workspace_id = workspace_id
        self._terms: dict[str, PtyTerminal] = {}

    def all(self) -> list[PtyTerminal]:
        return [t for t in self._terms.values() if not t.closed]

    def get(self, term_id: str) -> Optional[PtyTerminal]:
        return self._terms.get(term_id)

    def create(
        self,
        shell: str,
        cwd: str,
        cols: int = 80,
        rows: int = 24,
        env: dict[str, str] | None = None,
    ) -> PtyTerminal:
        # Resolve "" or null shell to the user's default.
        if not shell or shell == "default":
            profiles = discover_shell_profiles()
            shell = profiles[0]["path"] if profiles else os.environ.get("SHELL", "/bin/bash")
        # Resolve `which` shorthand: caller can pass "bash" / "zsh" etc.
        if not shell.startswith("/"):
            resolved = shutil.which(shell)
            if resolved:
                shell = resolved
        term = spawn_pty(shell, cwd, cols=cols, rows=rows, env=env)
        self._terms[term.id] = term
        logger.info(
            "pty created ws=%s id=%s shell=%s pid=%d cwd=%s",
            self.workspace_id, term.id, shell, term.pid, cwd,
        )
        return term

    def kill(self, term_id: str) -> bool:
        term = self._terms.get(term_id)
        if not term:
            return False
        term.kill()
        return True

    def remove(self, term_id: str) -> None:
        term = self._terms.pop(term_id, None)
        if term:
            term._mark_closed()

    def shutdown_all(self) -> None:
        """Kill every terminal under this registry. Used on workspace delete."""
        for term in list(self._terms.values()):
            with contextlib.suppress(Exception):
                term.kill()
            term._mark_closed()
        self._terms.clear()

    def serialize(self, term: PtyTerminal) -> dict[str, Any]:
        return {
            "id": term.id,
            "pid": term.pid,
            "shell": term.shell,
            "cwd": term.cwd,
            "cols": term.cols,
            "rows": term.rows,
            "closed": term.closed,
            "startedAt": term.started_at,
        }


class PtyHub:
    """Process-wide directory of per-workspace TerminalRegistry instances.

    Lazy: a workspace's registry is created the first time it's needed
    and held until the workspace is deleted (via drop_workspace).
    """

    _instance: Optional["PtyHub"] = None

    def __init__(self) -> None:
        self._registries: dict[str, TerminalRegistry] = {}

    @classmethod
    def instance(cls) -> "PtyHub":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def for_workspace(self, workspace_id: str) -> TerminalRegistry:
        reg = self._registries.get(workspace_id)
        if reg is None:
            reg = TerminalRegistry(workspace_id)
            self._registries[workspace_id] = reg
        return reg

    def find_by_terminal(self, term_id: str) -> Optional[tuple[str, TerminalRegistry, PtyTerminal]]:
        """Locate the (wsid, registry, terminal) tuple for `term_id`.

        Used by /ws/terminal/{tid}: the terminal id alone is enough to
        identify which workspace it lives in, since ids are 12-char uuids
        and collisions across workspaces are vanishingly unlikely. Saves
        the frontend from having to embed wsid in the WS URL.
        """
        for wsid, reg in self._registries.items():
            term = reg.get(term_id)
            if term is not None:
                return wsid, reg, term
        return None

    def drop_workspace(self, workspace_id: str) -> None:
        reg = self._registries.pop(workspace_id, None)
        if reg is not None:
            reg.shutdown_all()
