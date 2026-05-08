"""
PiSession — owns one `pi --mode rpc` subprocess and its JSONL plumbing.

Single responsibility: spawn pi for a given (session_id, workspace_path)
pair, expose two queues (events out, commands in), and clean up on close.
Knows nothing about Vue or WebSockets — that's app.py's job.

The `--session-dir` flag points pi at a per-session folder so its built-in
SessionManager handles persistence/resume for free.

The `cwd` of the spawned subprocess is the **workspace_path** the caller
supplies. In web mode that's a fresh per-session sandbox under
web/data/workspaces/<wsid>/. In desktop mode it's whatever folder the user
opened. Either way, pi's filesystem-touching tools (write/edit/read/bash)
live entirely inside that path.
"""

from __future__ import annotations

import asyncio
import json
import os
import shlex
import sys
from pathlib import Path
from typing import Any, AsyncIterator, Optional

from config import DATA_ROOT, PROJECT_ROOT  # noqa: E402
from services.sandbox_layout import (  # noqa: E402
    SANDBOX_UID, SANDBOX_GID, stamp_sandbox_dir, is_active as sandbox_active,
)

SESSIONS_ROOT = DATA_ROOT / "chats"

# Path to the setpriv binary (util-linux). Installed by Dockerfile.backend.
# Pinned absolute so a hostile $PATH manipulation can't redirect it.
_SETPRIV = "/usr/bin/setpriv"


# ── Env allow-list ───────────────────────────────────────────────────────
# pi spawns bash, npm, git, typst, etc. as direct subprocesses; every one
# of them inherits pi's environment, which is whatever WE pass via
# `env=self._env` to asyncio.create_subprocess_exec. So the env we pass
# pi is the env the AI's bash sees when it runs `env` or `printenv`.
#
# The container (docker-compose.yml) loads /opt/pi/stack.env via env_file
# AND sets explicit `environment:` keys, so the backend process starts
# with the FULL set of operator secrets in os.environ:
#
#   CLERK_SECRET_KEY, CLERK_WEBHOOK_SECRET, CLERK_PUBLISHABLE_KEY
#   STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, STRIPE_PRICE_*
#   CLOUDFLARE_API_TOKEN, ACME_EMAIL
#   ADMIN_EMAILS, ADMIN_USER_IDS
#
# A naive `env=os.environ` would let the AI dump every one of those with
# a single `bash` call. We replace it with a strict allow-list: anything
# not on the list is removed, even if a future config knob forgets to
# add itself to the deny rules.
#
# DO NOT add a secret to the allow-list without thinking through "is it
# OK for the AI's bash to read this?". Items here today fall into three
# buckets:
#
#   1. Linux fundamentals (PATH, HOME, USER, …) — bash/git/npm need them.
#   2. Vertex / Gemini auth — pi's HTTP client + the typst-tools.ts
#      extension's sub-LLM calls need them. Vertex uses ADC (no
#      JSON key), so the only secret here is GEMINI_API_KEY which is
#      project-scoped.
#   3. pi's own runtime config (PI_*).
#   4. Typst font/cache paths.
_PI_ENV_ALLOW: frozenset[str] = frozenset({
    # Linux essentials.
    "PATH", "HOME", "USER", "LOGNAME", "SHELL", "TERM",
    "LANG", "LANGUAGE", "TZ", "TMPDIR", "PWD",
    "LC_ALL", "LC_CTYPE", "LC_MESSAGES",
    # Node / npm — pi is a Node CLI; npm needs these to find its cache.
    "NODE_ENV", "NODE_PATH", "NPM_CONFIG_CACHE",
    # Vertex AI — ADC is picked up from the GCE metadata server (no
    # JSON key file), so only the project / location need to flow.
    "GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION",
    "GOOGLE_GENAI_USE_VERTEXAI",
    "GOOGLE_APPLICATION_CREDENTIALS",  # honored only when set explicitly
    # Gemini fallback (used by the typst-tools.ts sub-LLM web_search /
    # search_docs router when Vertex 429s). Project-scoped key, but
    # still a credential — the AI's bash CAN read it. This is the
    # one allow-list item to consider stripping later if you decide
    # the Vertex-only path is sufficient.
    "GEMINI_API_KEY",
    # Typst.
    "TYPST_FONT_PATHS", "TYPST_PACKAGE_CACHE_PATH",
    "XDG_CACHE_HOME", "XDG_DATA_HOME", "XDG_CONFIG_HOME",
    "FONTCONFIG_PATH",
})


# Explicit deny — even if a key matches a wildcard prefix below, these
# always get stripped. Belt-and-suspenders for the most-sensitive ones.
_PI_ENV_DENY: frozenset[str] = frozenset({
    "CLERK_SECRET_KEY",
    "CLERK_WEBHOOK_SECRET",
    "CLERK_PUBLISHABLE_KEY",
    "STRIPE_SECRET_KEY",
    "STRIPE_WEBHOOK_SECRET",
    "STRIPE_PRICE_STARTER",
    "STRIPE_PRICE_PRO",
    "STRIPE_PRICE_MAX",
    "STRIPE_PUBLISHABLE_KEY",
    "CLOUDFLARE_API_TOKEN",
    "ACME_EMAIL",
    "JWT_SECRET",
    "JWT_PRIVATE_KEY",
    "ADMIN_EMAILS",
    "ADMIN_USER_IDS",
    "DATABASE_URL", "DB_PASSWORD",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
})


# Wildcard prefixes that are allowed THROUGH unless on the explicit
# deny list. PI_* covers all of pi's runtime knobs (PI_PROVIDER,
# PI_MODEL, PI_PERMISSION_MODE, PI_TYPST_*, …).
_PI_ENV_ALLOW_PREFIXES: tuple[str, ...] = ("PI_",)


def _scrub_env_for_pi(full_env: dict[str, str]) -> dict[str, str]:
    """
    Filter `full_env` down to only keys pi (and its bash subprocesses)
    are allowed to see.

    Rule order:
      1. Drop everything in _PI_ENV_DENY.
      2. Keep everything in _PI_ENV_ALLOW.
      3. Keep keys whose name starts with any _PI_ENV_ALLOW_PREFIXES
         entry, UNLESS the full key is in _PI_ENV_DENY.
      4. Drop everything else.

    This means a freshly-added secret like NEW_PROVIDER_API_KEY does
    NOT leak by default — you have to add it to the allow-list
    explicitly, with a comment justifying why bash should see it.
    """
    out: dict[str, str] = {}
    for key, value in full_env.items():
        if key in _PI_ENV_DENY:
            continue
        if key in _PI_ENV_ALLOW:
            out[key] = value
            continue
        if any(key.startswith(p) for p in _PI_ENV_ALLOW_PREFIXES):
            out[key] = value
    return out


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

    def __init__(
        self,
        session_id: str,
        *,
        workspace_path: Path,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        session_dir: Optional[Path] = None,
        permission_mode: str = "approve_risky",
        permission_mode_file: Optional[Path] = None,
    ):
        self.session_id = session_id
        # Per-session sandbox the subprocess will cwd into. Caller (Registry)
        # is responsible for ensuring it exists and has the agent's required
        # symlinks (extensions/, guides/, .pi/, AGENTS.md, package.json).
        self.workspace_path = Path(workspace_path)
        if not self.workspace_path.exists():
            raise FileNotFoundError(
                f"workspace_path does not exist: {self.workspace_path}"
            )
        # Where pi persists its own session JSONL. Defaults to a per-session
        # folder under web/data/chats/ when caller doesn't supply one.
        self.session_dir = Path(session_dir) if session_dir else SESSIONS_ROOT / session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)
        # Stamp 2770 1000:1000 so the sandbox-uid pi can write its
        # JSONL without EACCES, while the backend still reaches it
        # via secondary-group membership for backups / audit reads.
        stamp_sandbox_dir(self.session_dir)

        # Source env.sh first (gives us PI_PROVIDER, PI_MODEL defaults +
        # all pi runtime knobs), THEN scrub down to the allow-list so
        # CLERK_SECRET_KEY, STRIPE_SECRET_KEY, CLOUDFLARE_API_TOKEN, etc.
        # are NOT inherited by pi (and therefore not by bash). See the
        # _PI_ENV_ALLOW / _PI_ENV_DENY sets at module top.
        full_env = _load_env_sh()
        env = _scrub_env_for_pi(full_env)
        # Per-session overrides win over env.sh defaults.
        self._provider = provider or env.get("PI_PROVIDER", "anthropic-vertex")
        self._model = model or env.get("PI_MODEL", "claude-opus-4-7")
        # anthropic-vertex needs location pinned to "global" for opus-4-7 (per patches/PATCH.md).
        if self._provider == "anthropic-vertex":
            env.setdefault("PI_VERTEX_ANTHROPIC_LOCATION", "global")

        # The permission extension reads PI_PERMISSION_MODE on startup. We pin
        # it here so each spawned pi inherits the user's preference (or the
        # plan default the caller chose). Validation happens inside the
        # extension; we just clamp obvious typos to the safe default.
        mode = (permission_mode or "approve_risky").strip().lower()
        if mode not in {"auto", "approve_risky", "approve_all"}:
            mode = "approve_risky"
        env["PI_PERMISSION_MODE"] = mode
        self._permission_mode = mode

        # PI_PERMISSION_MODE_FILE lets the extension re-read the user's
        # current mode on every tool_call, so flipping the picker in the
        # browser immediately affects the running pi (no respawn). We
        # write the file here too in case the user has never changed
        # their default — the extension always finds a file to read
        # instead of having two code paths.
        if permission_mode_file is not None:
            try:
                permission_mode_file.parent.mkdir(parents=True, exist_ok=True)
                if not permission_mode_file.exists():
                    permission_mode_file.write_text(mode + "\n", encoding="utf-8")
                env["PI_PERMISSION_MODE_FILE"] = str(permission_mode_file)
            except Exception as exc:
                print(
                    f"[pi_session {session_id}] WARN: permission_mode_file unusable ({exc}); "
                    "live mode swaps will not work for this session",
                    file=sys.stderr,
                )

        self._env = env
        self._proc: Optional[asyncio.subprocess.Process] = None
        self._closed = False
        self._stderr_task: Optional[asyncio.Task] = None

    # ── lifecycle ───────────────────────────────────────────────────────────
    async def start(self) -> None:
        if self._proc is not None:
            return

        # Base argv for pi --mode rpc. Built first so the setpriv prefix
        # below can be prepended cleanly.
        pi_argv = [
            "pi",
            "--mode", "rpc",
            "--provider", self._provider,
            "--model", self._model,
            "--session-dir", str(self.session_dir),
            "--extension", "./extensions/typst-tools.ts",
            # Permission gate. Reads PI_PERMISSION_MODE from env, asks the
            # user via ctx.ui.select (which RPC mode forwards to us as
            # extension_ui_request frames). See routes/chat_ws.py for the
            # backend-side bridge that translates those frames into
            # permission_request WS events.
            "--extension", "./extensions/permission.ts",
        ]

        # ── Sandbox drop ───────────────────────────────────────────
        # When PI_SANDBOX_UID is set (production), we wrap the pi
        # invocation in `setpriv` so pi (and every bash subprocess
        # the AI spawns) runs as uid 1000, distinct from the backend's
        # uid 1100. The backend keeps unrestricted access to
        # billing.db / registry.json / users/, the AI gets nothing.
        #
        # Flags:
        #   --reuid / --regid       drop to the sandbox identity
        #   --clear-groups          discard supplementary groups so
        #                           the AI's bash isn't accidentally
        #                           a member of `app` via inheritance
        #   --no-new-privs          set PR_SET_NO_NEW_PRIVS so any
        #                           subsequent execve cannot gain new
        #                           privileges via setuid bits. Pairs
        #                           with the container's
        #                           `security_opt: no-new-privileges:true`.
        #
        # If the sandbox isn't active (laptop dev, or container missing
        # CAP_SETUID), we run pi directly under the backend uid the
        # same way v1.0 did. The `sandbox_active()` probe takes care
        # of detecting a missing capability so we don't blow up at
        # exec time with a confusing "setpriv: permission denied".
        if sandbox_active():
            cmd = [
                _SETPRIV,
                "--reuid", str(SANDBOX_UID),
                "--regid", str(SANDBOX_GID),
                "--clear-groups",
                "--no-new-privs",
                *pi_argv,
            ]
            # Override HOME so $HOME points at the sandbox user's
            # tmpfs home (mounted at /home/sandbox by the compose
            # file). Without this, pi/npm/git would still try
            # /home/app and hit EACCES.
            self._env["HOME"] = "/home/sandbox"
            self._env["USER"] = "sandbox"
            self._env["LOGNAME"] = "sandbox"
        else:
            cmd = pi_argv

        # asyncio.StreamReader defaults to a 64 KB line limit. pi RPC events
        # routinely exceed that (e.g. tool_execution_end for a `write` of a
        # multi-KB file ships the full content as one JSON line). Bump to 16 MB
        # to comfortably hold any reasonable single tool result.
        self._proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(self.workspace_path),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self._env,
            limit=16 * 1024 * 1024,
        )
        self._stderr_task = asyncio.create_task(self._drain_stderr())

        print(
            f"[pi_session {self.session_id}] spawned pid={self._proc.pid} "
            f"provider={self._provider} model={self._model} "
            f"permission_mode={self._permission_mode} "
            f"sandbox={'on' if sandbox_active() else 'off'} "
            f"sandbox_uid={SANDBOX_UID if sandbox_active() else 'shared'} "
            f"cwd={self.workspace_path} chats={self.session_dir}",
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
