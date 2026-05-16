"""
PiSession — owns one `pi --mode rpc` subprocess and its JSONL plumbing.

Single responsibility: spawn pi for a given (session_id, workspace_path)
pair, expose two queues (events out, commands in), and clean up on close.
Knows nothing about Vue or WebSockets — that's app.py's job.

Two runtime backends, selected by PI_SESSION_RUNTIME env (auto-detected
when unset):

    PI_SESSION_RUNTIME=docker
        Production. Each chat spawns a per-chat Docker container from
        the `pi-session` image. The container has root inside (with
        sudo NOPASSWD for the AI's bash), full kernel-namespace
        isolation, and an egress-firewalled network that funnels
        every outbound TCP through the backend's egress proxy
        (services/egress_proxy.py) where the auth/allow-list policy
        lives. Container is destroyed (--rm) when the chat closes.

    PI_SESSION_RUNTIME=subprocess
        Operator's laptop / CI smoke test. Spawn pi as a regular
        subprocess (no setpriv, no container). Faster iteration, no
        isolation. NEVER used in production.

    PI_SESSION_RUNTIME=auto (default)
        Probe /var/run/docker.sock at start-time. If reachable AND the
        pi-session image is locally available, use docker. Else fall
        back to subprocess. The probe runs ONCE on first PiSession
        start and the result is cached for the process lifetime.

The `cwd` of the spawned subprocess is the **workspace_path** the caller
supplies. In docker runtime this is bind-mounted at /workspace inside
the container; in subprocess runtime it's used as-is. Either way, pi's
filesystem-touching tools (write/edit/read/bash) live entirely inside
that path.
"""

from __future__ import annotations

import asyncio
import json
import os
import shlex
import shutil
import sys
from pathlib import Path
from typing import Any, AsyncIterator, Optional

from config import DATA_ROOT, PROJECT_ROOT  # noqa: E402
from services.container_pool import (  # noqa: E402
    LABEL_APP_KEY,
    LABEL_APP_VALUE,
    LABEL_CREATED_AT,
    LABEL_SESSION_ID,
    LABEL_USER_ID,
)

SESSIONS_ROOT = DATA_ROOT / "chats"


# ── Runtime selection ────────────────────────────────────────────────
# Decide once per process whether to use docker or subprocess. The
# answer rarely changes between PiSession spawns (it depends on the
# host environment, not per-call inputs), so caching is fine.
_RUNTIME_CACHE: Optional[str] = None


def _detect_runtime() -> str:
    """
    Return "docker" or "subprocess". Memoised after first call.

    Resolution order:
      1. PI_SESSION_RUNTIME env var (explicit override, wins)
      2. /var/run/docker.sock present AND `docker info` succeeds AND
         the pi-session image exists locally → "docker"
      3. Fall back to "subprocess".
    """
    global _RUNTIME_CACHE
    if _RUNTIME_CACHE is not None:
        return _RUNTIME_CACHE

    explicit = os.environ.get("PI_SESSION_RUNTIME", "").strip().lower()
    if explicit in ("docker", "subprocess"):
        _RUNTIME_CACHE = explicit
        print(f"[pi_session] runtime={_RUNTIME_CACHE} (explicit env)", file=sys.stderr)
        return _RUNTIME_CACHE

    sock = Path("/var/run/docker.sock")
    if not sock.exists():
        _RUNTIME_CACHE = "subprocess"
        print("[pi_session] runtime=subprocess (no /var/run/docker.sock)", file=sys.stderr)
        return _RUNTIME_CACHE

    docker_bin = shutil.which("docker")
    if not docker_bin:
        _RUNTIME_CACHE = "subprocess"
        print("[pi_session] runtime=subprocess (no `docker` binary in PATH)", file=sys.stderr)
        return _RUNTIME_CACHE

    # Probe with `docker info` — this exercises the socket AND auth.
    # 5s timeout because dockerd can be slow on first call after boot.
    try:
        import subprocess as _sp
        _sp.run(
            [docker_bin, "info", "--format", "{{.ID}}"],
            check=True,
            capture_output=True,
            timeout=5.0,
        )
    except (FileNotFoundError, _sp.CalledProcessError, _sp.TimeoutExpired) as exc:
        _RUNTIME_CACHE = "subprocess"
        print(f"[pi_session] runtime=subprocess (docker info failed: {exc})", file=sys.stderr)
        return _RUNTIME_CACHE

    # Probe for the pi-session image. Don't require :latest specifically
    # because remote-deploy.sh tags both :<sha> and :latest at deploy
    # time but a fresh VM might briefly have only the :<sha> tag.
    image = os.environ.get("PI_SESSION_IMAGE", "pi-session:latest")
    try:
        _sp.run(
            [docker_bin, "image", "inspect", image],
            check=True,
            capture_output=True,
            timeout=5.0,
        )
    except (_sp.CalledProcessError, _sp.TimeoutExpired) as exc:
        _RUNTIME_CACHE = "subprocess"
        print(
            f"[pi_session] runtime=subprocess (image {image} not found locally: {exc.stderr if hasattr(exc, 'stderr') else exc})",
            file=sys.stderr,
        )
        return _RUNTIME_CACHE

    _RUNTIME_CACHE = "docker"
    print(f"[pi_session] runtime=docker (image {image} ready)", file=sys.stderr)
    return _RUNTIME_CACHE


# ── Docker config ────────────────────────────────────────────────────
# Tunables read from env at module load. All optional — defaults work
# for the digi-setu.com VM out of the box.

PI_SESSION_IMAGE = os.environ.get("PI_SESSION_IMAGE", "pi-session:latest")

# Docker network the per-session container joins. Created at
# pi-prepare.service boot time (see deploy/systemd/pi-prepare.service).
# All containers in this network can reach the backend's egress proxy
# at 172.30.0.1:1080 but cannot reach the host's other interfaces (the
# nftables rules in deploy/nftables/pi-egress.nft enforce this at the
# kernel layer, not just the docker network policy).
PI_EGRESS_NETWORK = os.environ.get("PI_EGRESS_NETWORK", "pi-egress")

# Address the backend's egress proxy is reachable on FROM INSIDE the
# per-session container. The bridge gateway IP is the standard docker
# trick for "container talks to host"; we pin a non-default subnet so
# users can't accidentally collide with our network in their own setups.
# Must match deploy/systemd/pi-egress-network.service (PI_EGRESS_GATEWAY)
# and deploy/nftables/pi-egress.nft (define pi_egress_gateway).
PI_EGRESS_PROXY_HOST = os.environ.get("PI_EGRESS_PROXY_HOST", "172.30.16.1")
PI_EGRESS_PROXY_PORT = os.environ.get("PI_EGRESS_PROXY_PORT", "1080")

# Path on the HOST where the MITM CA cert lives. Phase 5 (Vertex auth
# proxy) generates this lazily on first proxy boot if missing. The
# backend bind-mounts this file (read-only) into every per-session
# container at /etc/pi/mitm-ca.crt and points NODE_EXTRA_CA_CERTS /
# CURL_CA_BUNDLE / SSL_CERT_FILE at it via the entrypoint.
PI_MITM_CA_PATH = os.environ.get(
    "PI_MITM_CA_PATH", "/srv/pi/state/proxy/mitm-ca.crt"
)

# Resource caps for each per-session container. Conservative defaults
# matching the operator's "$BILLING_VM_USERS_AT_ONCE concurrent users
# on a single VM" sizing. Bump in stack.env for higher-end plans.
PI_SESSION_MEM_LIMIT = os.environ.get("PI_SESSION_MEM_LIMIT", "1g")
PI_SESSION_CPU_LIMIT = os.environ.get("PI_SESSION_CPU_LIMIT", "1.0")
PI_SESSION_PIDS_LIMIT = os.environ.get("PI_SESSION_PIDS_LIMIT", "512")
PI_SESSION_NOFILE_LIMIT = os.environ.get("PI_SESSION_NOFILE_LIMIT", "4096")

# Shared @preview package cache so typst doesn't re-download cetz /
# fletcher / etc. for every fresh chat container. Bind-mounted RW into
# the per-session container (uid 1000 owns this on the host so the
# container's uid 1000 has write access without needing chown).
PI_TYPST_CACHE_HOST_PATH = os.environ.get(
    "PI_TYPST_CACHE_HOST_PATH", "/srv/pi/data/typst-packages"
)


# ── Env allow-list ───────────────────────────────────────────────────
# pi spawns bash, npm, git, typst, etc. as direct subprocesses; every
# one of them inherits pi's environment. The env we pass pi (and
# therefore through to bash) is the env the AI sees with `printenv`.
#
# In docker runtime we deliberately pass a much SMALLER set than the
# subprocess runtime needed — the container's own ENV directives
# (Dockerfile.session) provide all the Linux fundamentals (PATH, HOME,
# LANG, …), Typst paths, proxy config, etc. We only inject the
# per-session bits the backend chooses dynamically (provider, model,
# permission mode, Gemini key when present).
#
# In subprocess runtime we keep the broader allow-list because pi
# inherits the operator's full environment.
_PI_ENV_ALLOW_SUBPROCESS: frozenset[str] = frozenset({
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
    "GOOGLE_APPLICATION_CREDENTIALS",
    # Gemini fallback for the typst-tools.ts sub-LLM router.
    "GEMINI_API_KEY",
    # Typst.
    "TYPST_FONT_PATHS", "TYPST_PACKAGE_CACHE_PATH",
    "XDG_CACHE_HOME", "XDG_DATA_HOME", "XDG_CONFIG_HOME",
    "FONTCONFIG_PATH",
})

# Explicit deny — even if a key matches a wildcard prefix below, these
# always get stripped. Belt-and-suspenders for the most-sensitive ones.
# The docker runtime's container image NEVER receives any of these
# regardless of the host backend's environment, because we only pass
# explicitly-listed keys via -e flags.
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
})

# BYOK API keys that desktop users may put in ~/.digi-setu/.env. In
# web mode these stay denied (the cloud relay never wants the user's
# direct keys leaking into the container). In desktop+BYOK mode we
# allow whichever key matches the picked model — see services.byok
# for the per-provider scrubbing.
_PI_ENV_BYOK_KEYS: frozenset[str] = frozenset({
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
})

_PI_ENV_ALLOW_PREFIXES: tuple[str, ...] = ("PI_",)


def _scrub_env_for_subprocess(full_env: dict[str, str]) -> dict[str, str]:
    """Subprocess runtime: drop secrets, keep PI_*/GOOGLE_*/etc.

    In desktop+BYOK mode, BYOK API keys (ANTHROPIC_API_KEY,
    OPENAI_API_KEY, …) are allowed through because they're the
    user's own credentials — the whole point of BYOK. The per-call
    scrubbing in services.byok then prunes keys irrelevant to the
    picked model so an Anthropic call doesn't see the user's OpenAI
    key, etc.
    """
    from config import BYOK_MODE  # local import to avoid cycles at module load

    out: dict[str, str] = {}
    for key, value in full_env.items():
        if key in _PI_ENV_DENY:
            continue
        if key in _PI_ENV_BYOK_KEYS:
            if BYOK_MODE:
                out[key] = value
            continue
        if key in _PI_ENV_ALLOW_SUBPROCESS:
            out[key] = value
            continue
        if any(key.startswith(p) for p in _PI_ENV_ALLOW_PREFIXES):
            out[key] = value
    return out


def _load_env_sh() -> dict[str, str]:
    """
    Source digi-setu's scripts/env.sh in a child shell and capture the
    resulting environment. Used by the subprocess runtime to inherit the
    operator's interactive defaults. The docker runtime ignores this
    (the container has its own baked-in defaults).
    """
    env_sh = PROJECT_ROOT / "scripts" / "env.sh"
    if not env_sh.exists():
        return dict(os.environ)

    try:
        import subprocess

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


# ── Container env ────────────────────────────────────────────────────
# Tight allow-list of env keys we forward into per-session containers.
# Anything not here is NOT visible to the AI, regardless of the
# backend's own environment. The container's Dockerfile.session ENV
# directives provide Linux fundamentals (PATH, HOME, LANG, proxy
# config) so we don't need to forward those.
def _container_env(
    provider: str,
    model: str,
    permission_mode: str,
    permission_mode_file_in_container: Optional[str],
    backend_env: dict[str, str],
) -> dict[str, str]:
    out: dict[str, str] = {
        "PI_PROVIDER": provider,
        "PI_MODEL": model,
        "PI_PERMISSION_MODE": permission_mode,
        # Vertex configuration. The container's HTTPS_PROXY env
        # routes outbound HTTPS through the backend's MITM proxy,
        # which adds the Authorization header from the backend's ADC
        # before forwarding upstream. The container itself never
        # holds a Vertex token.
        "GOOGLE_CLOUD_PROJECT": backend_env.get("GOOGLE_CLOUD_PROJECT", ""),
        "GOOGLE_CLOUD_LOCATION": backend_env.get("GOOGLE_CLOUD_LOCATION", "global"),
        "GOOGLE_GENAI_USE_VERTEXAI": "true",
        # Tells the patched pi-ai (`hasVertexAdcCredentials`) to skip
        # the on-disk ADC check — the proxy handles auth, the
        # container has no creds. See patches/apply-edits.mjs §3b.
        "PI_TRUST_GCE_METADATA": "1",
        # Force gcp-metadata library to route via HTTP_PROXY by
        # using hostnames everywhere (including the IP fallback).
        # Without this the lib hits 169.254.169.254 directly →
        # nftables drops it → pi-ai dies. See the long-form rationale
        # in deploy/Dockerfile.session.
        "GCE_METADATA_HOST": "metadata.google.internal",
        "GCE_METADATA_IP": "metadata.google.internal",
        "METADATA_SERVER_DETECTION": "assume-present",
        # Gemini fallback for the typst-tools.ts sub-LLM router.
        # When set the router can fall through to AI Studio for
        # 429-prone Vertex hosts. Empty value is fine — typst-tools
        # treats it as "Gemini fallback disabled".
        "GEMINI_API_KEY": backend_env.get("GEMINI_API_KEY", ""),
        # Pin search_docs to Gemini Flash by default (Claude Haiku's
        # 200k context can't fit the typst corpus).
        "PI_TYPST_ROUTER_MODEL": backend_env.get(
            "PI_TYPST_ROUTER_MODEL", "gemini-3-flash-preview"
        ),
    }

    if permission_mode_file_in_container:
        out["PI_PERMISSION_MODE_FILE"] = permission_mode_file_in_container

    if provider == "anthropic-vertex":
        out["PI_VERTEX_ANTHROPIC_LOCATION"] = backend_env.get(
            "PI_VERTEX_ANTHROPIC_LOCATION", "global"
        )

    # Drop empty values — `docker run -e KEY=` with no value sets KEY
    # to empty inside the container, which can confuse libraries that
    # treat empty-string differently from unset (Anthropic SDK does
    # this for ANTHROPIC_API_KEY). Strip them so unset means unset.
    return {k: v for k, v in out.items() if v != ""}


class PiSession:
    """
    One pi RPC subprocess. Lifecycle:

        s = PiSession(session_id="abc", workspace_path=Path(...))
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
        permission_mode: str = "auto",
        permission_mode_file: Optional[Path] = None,
        user_id: Optional[str] = None,
    ):
        self.session_id = session_id
        # user_id is ATTRIBUTION ONLY for the docker label set —
        # services/container_pool.py uses it to enforce the per-user
        # concurrency cap and assign orphan ownership. NOT a security
        # boundary by itself; the actual cross-tenant isolation comes
        # from the kernel namespaces of the per-session container.
        self.user_id = (user_id or "anonymous").replace(" ", "_")[:64]
        self.workspace_path = Path(workspace_path).resolve()
        if not self.workspace_path.exists():
            raise FileNotFoundError(
                f"workspace_path does not exist: {self.workspace_path}"
            )
        self.session_dir = Path(session_dir).resolve() if session_dir else (SESSIONS_ROOT / session_id).resolve()
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # Source env.sh once for both runtimes — provider/model defaults
        # come from there, even if the docker runtime later only forwards
        # a small subset.
        full_env = _load_env_sh()

        self._provider = provider or full_env.get("PI_PROVIDER", "anthropic-vertex")
        self._model = model or full_env.get("PI_MODEL", "claude-sonnet-4-6")

        # Accept canonical IDs (auto / approve_all / manual) AND
        # legacy aliases (ask, cautious, approve_risky) so a stale
        # spawn from an older client doesn't blow up; user_prefs.
        # normalize_permission_mode is the single source of truth.
        try:
            from services.user_prefs import normalize_permission_mode  # local import to avoid cycle
        except Exception:  # noqa: BLE001
            normalize_permission_mode = None  # type: ignore[assignment]
        cleaned: Optional[str] = None
        if normalize_permission_mode is not None:
            cleaned = normalize_permission_mode(permission_mode or "")
        self._permission_mode = cleaned or "auto"

        # Materialise the permission_mode_file with mode 0644 so the
        # container's sandbox uid (1000) can read it via the bind mount.
        # The mode token itself ("auto" / "approve_all" / "manual") is
        # not a secret — it's a UI preference — so widening read perms
        # does not leak anything sensitive.
        self._permission_mode_file_host: Optional[Path] = None
        if permission_mode_file is not None:
            try:
                permission_mode_file.parent.mkdir(parents=True, exist_ok=True)
                if not permission_mode_file.exists():
                    permission_mode_file.write_text(
                        self._permission_mode + "\n", encoding="utf-8"
                    )
                try:
                    os.chmod(permission_mode_file, 0o644)
                except OSError:
                    pass
                self._permission_mode_file_host = permission_mode_file.resolve()
            except Exception as exc:
                print(
                    f"[pi_session {session_id}] WARN: permission_mode_file unusable ({exc}); "
                    "live mode swaps will not work for this session",
                    file=sys.stderr,
                )

        self._backend_env = full_env  # captured for container env build
        self._proc: Optional[asyncio.subprocess.Process] = None
        self._closed = False
        self._stderr_task: Optional[asyncio.Task] = None
        self._runtime: str = _detect_runtime()
        # Container name — short, deterministic, easy to grep in
        # `docker ps`. Truncated session_id keeps it under Docker's
        # 64-char name limit comfortably.
        short_sid = session_id.replace("/", "_").replace(":", "_")[:48]
        self._container_name = f"pi-sess-{short_sid}"

    # ── lifecycle ───────────────────────────────────────────────────────────
    async def start(self) -> None:
        if self._proc is not None:
            return

        if self._runtime == "docker":
            cmd = self._build_docker_cmd()
            cwd: Optional[str] = None
            spawn_env: Optional[dict[str, str]] = None
        else:
            cmd, cwd, spawn_env = self._build_subprocess_cmd()

        # asyncio.StreamReader defaults to a 64 KB line limit. pi RPC
        # events routinely exceed that (a `write` of a multi-KB file
        # ships the full content as one JSON line). Bump to 16 MB.
        self._proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=spawn_env,
            limit=16 * 1024 * 1024,
        )
        self._stderr_task = asyncio.create_task(self._drain_stderr())

        print(
            f"[pi_session {self.session_id}] spawned runtime={self._runtime} "
            f"pid={self._proc.pid} provider={self._provider} model={self._model} "
            f"permission_mode={self._permission_mode} "
            f"container={self._container_name if self._runtime == 'docker' else '-'} "
            f"cwd={self.workspace_path} chats={self.session_dir}",
            file=sys.stderr,
        )

    def _build_docker_cmd(self) -> list[str]:
        """
        Construct the `docker run -i --rm …` argv for spawning a
        per-chat container. The container is destroyed when the
        process exits (--rm) so we don't accumulate dead containers
        in `docker ps -a` even if the backend crashes.

        Volume mounts:
          /workspace        rw  user content (host: workspace_path)
          /session          rw  pi's session JSONL (host: session_dir)
          /home/sandbox/.cache/typst rw shared @preview cache
          /etc/pi/permission_mode  ro live permission mode file
          /etc/pi/mitm-ca.crt      ro backend's MITM CA cert (Phase 5)

        Network: pi-egress (created at boot by pi-prepare). All
        outbound traffic is forced through the backend's egress proxy
        at PI_EGRESS_PROXY_HOST:PI_EGRESS_PROXY_PORT by host nftables
        rules — see deploy/nftables/pi-egress.nft.
        """
        permission_mode_file_in_container: Optional[str] = None
        volume_args: list[str] = []

        # Workspace: the user's content. The host parent dir's SGID
        # (mode 2770 gid=1000) makes new files inside inherit gid 1000
        # so the backend's `app` user can rw them via secondary group
        # membership for GCS sync / audit / billing.
        volume_args += [
            "--volume",
            f"{self.workspace_path}:/workspace:rw",
        ]
        # Per-session JSONL.
        volume_args += [
            "--volume",
            f"{self.session_dir}:/session:rw",
        ]

        # Shared typst @preview cache. Optional — if the host path
        # doesn't exist (laptop dev) skip the mount and the container
        # will populate its own ephemeral cache.
        typst_cache = Path(PI_TYPST_CACHE_HOST_PATH)
        if typst_cache.exists():
            volume_args += [
                "--volume",
                f"{typst_cache}:/home/sandbox/.cache/typst:rw",
            ]

        # Permission mode file (live UI preference). Bind-mount the
        # FILE (not its parent dir), read-only — the extension just
        # reads on every tool_call, the backend writes from the host
        # side.
        if self._permission_mode_file_host and self._permission_mode_file_host.is_file():
            permission_mode_file_in_container = "/etc/pi/permission_mode"
            volume_args += [
                "--volume",
                f"{self._permission_mode_file_host}:/etc/pi/permission_mode:ro",
            ]

        # MITM CA cert (Phase 5). Bind-mounted read-only; the
        # entrypoint copies it onto the system trust store + sets
        # NODE_EXTRA_CA_CERTS so node fetch trusts the proxy's
        # leaf certs for *.aiplatform.googleapis.com.
        mitm_ca = Path(PI_MITM_CA_PATH)
        if mitm_ca.exists():
            volume_args += [
                "--volume",
                f"{mitm_ca}:/etc/pi/mitm-ca.crt:ro",
            ]

        # ── Env injection ──────────────────────────────────────────
        env_args: list[str] = []
        for key, value in _container_env(
            provider=self._provider,
            model=self._model,
            permission_mode=self._permission_mode,
            permission_mode_file_in_container=permission_mode_file_in_container,
            backend_env=self._backend_env,
        ).items():
            env_args += ["--env", f"{key}={value}"]

        # ── Resource caps ──────────────────────────────────────────
        cap_args = [
            "--memory", PI_SESSION_MEM_LIMIT,
            "--memory-swap", PI_SESSION_MEM_LIMIT,
            "--cpus", PI_SESSION_CPU_LIMIT,
            "--pids-limit", PI_SESSION_PIDS_LIMIT,
            "--ulimit", f"nofile={PI_SESSION_NOFILE_LIMIT}:{PI_SESSION_NOFILE_LIMIT}",
        ]

        # ── Capabilities ───────────────────────────────────────────
        # Drop ALL, then add back the minimum needed for sudo + apt
        # install + chown of newly-extracted package files. See
        # Dockerfile.session header for the full rationale on each.
        secopt_args = [
            "--cap-drop", "ALL",
            "--cap-add", "CHOWN",
            "--cap-add", "FOWNER",
            "--cap-add", "SETUID",
            "--cap-add", "SETGID",
            "--cap-add", "DAC_OVERRIDE",
            "--cap-add", "DAC_READ_SEARCH",
            "--cap-add", "NET_BIND_SERVICE",
            # MUST be false because sudo requires the setuid bit; see
            # Dockerfile.session header for the trade-off discussion.
            "--security-opt", "no-new-privileges=false",
        ]

        # ── pi argv (passed as CMD, image's ENTRYPOINT prepends
        # tini + entrypoint-session.sh which drops to uid 1000) ────
        #
        # `--continue` is critical for chat continuity across pi
        # respawns. Every time the user clicks Stop OR the WS
        # disconnects mid-turn we kill pi (see chat_ws.py — pi has no
        # in-band "abort current turn" frame in RPC mode, so we have
        # to terminate the process). The next user prompt then spawns
        # a fresh pi container. Without `--continue`, that fresh pi
        # calls SessionManager.create() and starts a brand-new
        # session JSONL — every prior user message and assistant
        # response becomes invisible to the model. Symptom users
        # hit: "I sent a message, hit Stop, sent another, then asked
        # 'what have we discussed' → pi has no memory of the first
        # message at all." `--continue` swaps that for
        # SessionManager.continueRecent() which resumes the most-
        # recent valid session file in /session, so pi sees every
        # committed prior turn (pi writes user messages immediately
        # on receipt, so even the prompt that triggered the Stop is
        # in there).
        # Pi's bundled example extensions live inside the
        # pi-coding-agent npm install at:
        #   /opt/pi-session/node_modules/@mariozechner/pi-coding-agent/examples/extensions/
        # (See deploy/Dockerfile.session — `npm i @mariozechner/pi-coding-agent`
        # under /opt/pi-session puts the whole package there, examples
        # included.) We load the safe + agent-quality ones here; the
        # SPA already handles every event shape they emit (tool calls
        # render as generic tool cards, `extension_ui_request` is
        # intercepted by chat_ws.py for the permission modal).
        _PI_EXAMPLES_IN_CONTAINER = (
            "/opt/pi-session/node_modules/@mariozechner/pi-coding-agent/examples/extensions"
        )
        pi_argv = [
            "pi",
            "--mode", "rpc",
            "--provider", self._provider,
            "--model", self._model,
            "--session-dir", "/session",
            "--continue",
            "--extension", "/opt/pi-session/extensions/typst-tools.ts",
            "--extension", "/opt/pi-session/extensions/permission.ts",
            # Safety extensions — protected-paths blocks writes to
            # .env / .git/ / node_modules/, permission-gate prompts
            # before rm -rf / sudo / chmod 777.
            "--extension", f"{_PI_EXAMPLES_IN_CONTAINER}/protected-paths.ts",
            "--extension", f"{_PI_EXAMPLES_IN_CONTAINER}/permission-gate.ts",
            # Quality-of-life extensions:
            #   trigger-compact → auto-compact when context > 100k
            #     tokens; without it long chats hit hard limit.
            #   git-checkpoint  → git stash before every turn so
            #     /fork can rewind; no-op outside a git repo.
            #   todo            → native `todo` tool for multi-step
            #     plans; state persists in session entries.
            #   subagent        → spawn isolated sub-agents for
            #     scoped work without trashing main context.
            #   structured-output → terminator tool for JSON answers
            #     (saves one LLM round-trip per structured reply).
            #   handoff         → `/handoff <goal>` to start a fresh
            #     focused chat with relevant context summarised.
            "--extension", f"{_PI_EXAMPLES_IN_CONTAINER}/trigger-compact.ts",
            "--extension", f"{_PI_EXAMPLES_IN_CONTAINER}/git-checkpoint.ts",
            "--extension", f"{_PI_EXAMPLES_IN_CONTAINER}/todo.ts",
            "--extension", f"{_PI_EXAMPLES_IN_CONTAINER}/subagent/index.ts",
            "--extension", f"{_PI_EXAMPLES_IN_CONTAINER}/structured-output.ts",
            "--extension", f"{_PI_EXAMPLES_IN_CONTAINER}/handoff.ts",
            # ── NOTE: do NOT pass `--tools <allowlist>` here ─────────
            # `--tools` is a HARD allowlist that filters BOTH built-in
            # and extension tools (see pi-coding-agent
            # dist/core/agent-session.js, `_refreshToolRegistry`:
            # the `if (allowedToolNames) {…}` branch shadows the
            # `else if (includeAllExtensionTools)` branch). Passing
            # the previous `read,bash,edit,write,grep,find,ls` list
            # silently filtered out every extension tool we just
            # registered (todo, subagent, search_docs, web_search,
            # read_doc, …) — the model would self-report "no todo /
            # no subagent" even though the extensions loaded fine.
            # By omitting `--tools` we get the default 4 built-ins
            # (read/bash/edit/write) PLUS every extension tool. The
            # native grep/find/ls fall back to `bash grep` / `bash
            # find` / `bash ls`, which is slower but functional;
            # caught while debugging on 2026-05-16.
        ]

        # ── Labels for container_pool.py ───────────────────────────
        # Used for orphan cleanup on backend restart, per-user
        # concurrency cap enforcement, and debug correlation.
        from datetime import datetime, timezone
        created_at = datetime.now(timezone.utc).isoformat()
        label_args = [
            "--label", f"{LABEL_APP_KEY}={LABEL_APP_VALUE}",
            "--label", f"{LABEL_USER_ID}={self.user_id}",
            "--label", f"{LABEL_SESSION_ID}={self.session_id}",
            "--label", f"{LABEL_CREATED_AT}={created_at}",
        ]

        # Map the human-readable name `pi-proxy` to the docker bridge
        # gateway IP. The Dockerfile.session bakes HTTPS_PROXY=http://
        # pi-proxy:1080 into the image so neither the AI nor curious
        # `env` calls ever see the raw 172.30.16.1 — they get a stable
        # symbolic name even if the operator changes the bridge subnet
        # (deploy/systemd/pi-egress-network.service is the source of
        # truth for the IP, and pi_session.py reads it from env).
        host_args = ["--add-host", f"pi-proxy:{PI_EGRESS_PROXY_HOST}"]

        return [
            "docker", "run",
            "-i",                     # keep STDIN open (RPC stdio)
            "--rm",                   # delete container on exit
            "--name", self._container_name,
            "--network", PI_EGRESS_NETWORK,
            "--workdir", "/workspace",
            *host_args,
            *label_args,
            *volume_args,
            *env_args,
            *cap_args,
            *secopt_args,
            # No DNS override — the egress proxy handles DNS resolution
            # upstream of the container's TCP path.
            PI_SESSION_IMAGE,
            *pi_argv,
        ]

    def _build_subprocess_cmd(self) -> tuple[list[str], str, dict[str, str]]:
        """
        Subprocess runtime (laptop dev / CI smoke). Spawns pi as a
        regular subprocess with the operator's env. No isolation —
        DO NOT USE IN PRODUCTION.
        """
        env = _scrub_env_for_subprocess(self._backend_env)

        # ── BYOK rerouting (desktop only) ────────────────────────────
        # If we're in BYOK mode AND the picked model has a route via
        # one of the user's keys, swap the cloud-relay provider
        # (anthropic-vertex / google-vertex) for the direct provider
        # (anthropic / google / openai) and prune env vars from
        # *other* providers so a Claude call doesn't see the user's
        # OpenAI key. This MUST run before the cloud-relay default
        # injection below — once we go BYOK we don't want our project
        # id silently riding along.
        from config import BYOK_MODE  # local import: avoid cycles
        from services.byok import byok_provider_for, byok_subprocess_env  # noqa: E402
        from services.models_registry import get_model  # noqa: E402

        active_provider = self._provider
        spec = get_model(self._model)
        if BYOK_MODE and spec is not None:
            pick = byok_provider_for(spec)
            if pick is not None:
                env = byok_subprocess_env(spec, env)
                active_provider = pick[1]
                # Mutate self._provider so later code paths (cmd
                # arg list, _container_env if it ever ran in this
                # branch) see the updated value too. Subprocess is
                # the only path that hits this in desktop today.
                self._provider = active_provider

        # Per-session overrides win over env.sh defaults.
        if active_provider == "anthropic-vertex":
            env.setdefault("PI_VERTEX_ANTHROPIC_LOCATION", "global")

        # Vertex on a GCE VM (laptop dev usually doesn't hit this; the
        # operator runs `gcloud auth application-default login` which
        # writes ~/.config/gcloud/application_default_credentials.json
        # so the on-disk ADC heuristic in pi-ai succeeds normally).
        if (
            env.get("GOOGLE_GENAI_USE_VERTEXAI", "").lower() == "true"
            and env.get("GOOGLE_CLOUD_PROJECT")
        ):
            env.setdefault("PI_TRUST_GCE_METADATA", "1")

        env["PI_PERMISSION_MODE"] = self._permission_mode
        if self._permission_mode_file_host:
            env["PI_PERMISSION_MODE_FILE"] = str(self._permission_mode_file_host)

        # ── Internal HTTP back-channel for the read_doc tool ────────────
        #
        # The pi child needs to call /api/internal/extract-md (markitdown
        # extraction for binary docs). Stuff PI_SIDECAR_URL +
        # PI_INTERNAL_TOKEN into the spawn env so the JS extension knows
        # where to POST. Only wires up for the subprocess runtime — the
        # docker-container runtime (web prod) lives in a separate
        # network namespace where 127.0.0.1 doesn't reach the host.
        # For that path read_doc silently degrades (the agent falls
        # back to the builtin `read`); a future change can route via
        # the egress proxy or expose the host gateway.
        try:
            from services.internal_auth import get_backend_base_url, get_internal_token

            env["PI_SIDECAR_URL"] = get_backend_base_url()
            env["PI_INTERNAL_TOKEN"] = get_internal_token()
        except Exception as _exc:  # noqa: BLE001
            import sys as _sys

            print(
                f"[pi_session] WARN: internal-auth wiring failed ({_exc}); "
                "read_doc tool disabled for this session",
                file=_sys.stderr,
            )

        # ── Desktop runtime override ─────────────────────────────────
        # When the Tauri shell launches the backend it sets two env
        # vars pointing at the bundled Node + pi-coding-agent install
        # so we don't depend on whatever Node/pi the user has on PATH
        # (or doesn't). The bundled extensions live next to the
        # bundled pi tree so absolute paths work regardless of which
        # folder the user picked.
        #
        # Layout (set up by desktop/pi-runtime/install-pi.sh):
        #   PI_DESKTOP_NODE_BIN = <vendor>/node-<plat>/bin/node
        #   PI_DESKTOP_PI_DIR   = <vendor>/pi  (contains node_modules/.bin/pi)
        #   <vendor>/extensions/typst-tools.ts
        #   <vendor>/extensions/permission.ts
        #
        # In web mode neither var is set so we fall through to the
        # `pi` PATH lookup, exactly as before.
        desktop_node = env.get("PI_DESKTOP_NODE_BIN", "").strip()
        desktop_pi_dir = env.get("PI_DESKTOP_PI_DIR", "").strip()
        # Names of the bundled pi example-extensions we want to load
        # in any subprocess path (desktop runtime AND dev fallback).
        # See docker branch above for what each one does. Loading them
        # in subprocess too keeps the AI's available-tools surface in
        # parity across docker / subprocess / desktop — without it the
        # model self-reports "no todo / no subagent" in subprocess
        # mode (caught while testing on 2026-05-16).
        #
        # IMPORTANT: pi's stock `protected-paths.ts` is INTENTIONALLY
        # omitted here. It only blocks .env / .git/ / node_modules/
        # which is fine for the docker runtime (where the container
        # has no $HOME secrets to begin with) but woefully thin for
        # subprocess mode (where pi runs with the operator's full
        # filesystem access — `~/.ssh/`, `~/.pi/agent/auth.json`,
        # `~/.aws/credentials`, browser cookies, …). We swap it for
        # our hardened `extensions/desktop-protected-paths.ts` which
        # also gates `bash` (the obvious bypass — pi's stock guard
        # leaves `bash cat ~/.ssh/id_rsa` wide open).
        _QOL_EXTENSIONS: tuple[str, ...] = (
            # protected-paths.ts deliberately replaced — see comment above.
            "permission-gate.ts",
            "trigger-compact.ts",
            "git-checkpoint.ts",
            "todo.ts",
            "subagent/index.ts",
            "structured-output.ts",
            "handoff.ts",
        )

        if desktop_node and desktop_pi_dir:
            from pathlib import Path as _Path
            _pi_dir = _Path(desktop_pi_dir)
            _vendor_root = _pi_dir.parent
            # The npm-installed shim is a node script; we invoke it as
            # `node <pi-shim>` to avoid relying on the shebang (which
            # points at /usr/bin/env node — fine on Mac, fails inside
            # a sandboxed app bundle on Win).
            # The package's `bin` field points at `dist/cli.js`, which
            # is what `node_modules/.bin/pi` symlinks to. We invoke
            # that file directly because the symlink doesn't survive a
            # Tauri bundle copy on Windows (NTFS junction limitations
            # vs the npm-created reparse point).
            _pi_pkg = _pi_dir / "node_modules" / "@mariozechner" / "pi-coding-agent"
            _pi_shim = _pi_pkg / "dist" / "cli.js"
            _examples = _pi_pkg / "examples" / "extensions"
            _ext_typst = _vendor_root / "extensions" / "typst-tools.ts"
            _ext_perm = _vendor_root / "extensions" / "permission.ts"
            cmd = [
                desktop_node,
                str(_pi_shim),
                "--mode", "rpc",
                "--provider", self._provider,
                "--model", self._model,
                "--session-dir", str(self.session_dir),
                # `--continue` resumes the most recent session file
                # in --session-dir on respawn, so the model keeps
                # full conversation context after Stop / disconnect
                # (where we kill pi). See the docker-mode block
                # above for the full rationale.
                "--continue",
                # See the "NOTE: do NOT pass `--tools <allowlist>`"
                # comment in the docker branch above. The same hazard
                # applies here — passing it filters out every
                # extension tool we register.
            ]
            if _ext_typst.exists():
                cmd += ["--extension", str(_ext_typst)]
            if _ext_perm.exists():
                cmd += ["--extension", str(_ext_perm)]
            # Hardened path-guard — replaces pi's stock protected-paths.ts.
            # Lives next to the bundled pi tree in the desktop runtime
            # (`<vendor>/extensions/desktop-protected-paths.ts`). Falls
            # back to the repo-root copy if the vendor file is missing
            # (only relevant when an operator runs the web backend with
            # PI_DESKTOP_* env vars pointing at a hand-rolled vendor
            # layout — unusual but worth supporting).
            _ext_hardened = _vendor_root / "extensions" / "desktop-protected-paths.ts"
            if not _ext_hardened.is_file():
                _ext_hardened = (
                    _Path(__file__).resolve().parent.parent.parent.parent
                    / "extensions" / "desktop-protected-paths.ts"
                )
            if _ext_hardened.is_file():
                cmd += ["--extension", str(_ext_hardened)]
            for _name in _QOL_EXTENSIONS:
                _p = _examples / _name
                if _p.is_file():
                    cmd += ["--extension", str(_p)]
            # NODE_PATH lets jiti / require resolve the extensions'
            # deps (@google/genai, typebox, …) which live next to the
            # bundled pi install, not in the user's picked folder.
            env["NODE_PATH"] = str(_pi_dir / "node_modules")
            return cmd, str(self.workspace_path), env

        # ── Dev fallback (laptop dev, no PI_DESKTOP_* vars) ──────────
        # Resolve pi's package install on disk so we can absolute-path
        # the example extensions; otherwise the relative `./extensions/`
        # paths point at the operator's checkout (typst-tools, permission)
        # but we have no way to address the npm-installed examples
        # except via absolute paths. We discover the package by
        # following `which pi` → realpath → walk up to the pkg root.
        from pathlib import Path as _Path
        import shutil as _shutil
        _pi_bin = _shutil.which("pi")
        _examples_dir: Optional[_Path] = None
        if _pi_bin:
            try:
                _real = _Path(_pi_bin).resolve()
                # …/dist/cli.js or …/dist/cli.mjs depending on version
                _candidate = _real.parent.parent / "examples" / "extensions"
                if _candidate.is_dir():
                    _examples_dir = _candidate
            except OSError:
                pass

        # Repo-root absolute path to our hardened path-guard, which
        # SUPERSEDES pi's stock examples/extensions/protected-paths.ts.
        # Without this, local-dev subprocess mode runs with pi's anemic
        # `.env / .git / node_modules` blocklist, leaving `~/.pi/`,
        # `~/.ssh/`, browser cookies, etc. wide open to the AI.
        _repo_root_dev = _Path(__file__).resolve().parent.parent.parent.parent
        _hardened_paths = _repo_root_dev / "extensions" / "desktop-protected-paths.ts"

        cmd = [
            "pi",
            "--mode", "rpc",
            "--provider", self._provider,
            "--model", self._model,
            "--session-dir", str(self.session_dir),
            # See the docker-mode `--continue` rationale above.
            "--continue",
            "--extension", "./extensions/typst-tools.ts",
            "--extension", "./extensions/permission.ts",
            # See the "NOTE: do NOT pass `--tools <allowlist>`" comment
            # in the docker branch above.
        ]
        if _hardened_paths.is_file():
            cmd += ["--extension", str(_hardened_paths)]
        if _examples_dir is not None:
            for _name in _QOL_EXTENSIONS:
                _p = _examples_dir / _name
                if _p.is_file():
                    cmd += ["--extension", str(_p)]
        return cmd, str(self.workspace_path), env

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True

        if self._proc is None:
            return

        # Polite shutdown: close stdin so pi exits cleanly.
        try:
            if self._proc.stdin and not self._proc.stdin.is_closing():
                self._proc.stdin.close()
        except Exception:
            pass

        # Grace period for the container/process to exit normally.
        try:
            await asyncio.wait_for(self._proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            print(
                f"[pi_session {self.session_id}] grace period elapsed, killing",
                file=sys.stderr,
            )
            if self._runtime == "docker":
                # `docker kill` sends SIGKILL to PID 1 inside the
                # container; with --rm this also tears the container
                # down. We still call `self._proc.kill()` afterwards
                # in case the docker CLI itself is hung waiting.
                try:
                    import subprocess as _sp
                    _sp.run(
                        ["docker", "kill", self._container_name],
                        check=False,
                        capture_output=True,
                        timeout=5.0,
                    )
                except Exception:
                    pass
            self._proc.kill()
            await self._proc.wait()

        # Belt-and-suspenders cleanup: even on clean shutdown, if the
        # container somehow survived (--rm should remove it but a
        # dockerd race or aborted exit could leave it hanging) force
        # a remove. Never block on this — the chat is over.
        if self._runtime == "docker":
            try:
                import subprocess as _sp
                _sp.run(
                    ["docker", "rm", "-f", self._container_name],
                    check=False,
                    capture_output=True,
                    timeout=3.0,
                )
            except Exception:
                pass

        if self._stderr_task and not self._stderr_task.done():
            self._stderr_task.cancel()

    async def terminate(self) -> None:
        """Force-kill the pi subprocess immediately, bypassing the 5s grace
        period used by `close()`. This is what an interactive abort needs:
        when the user clicks stop, the in-flight HTTP request to Vertex /
        Anthropic must be dropped at the OS level *now*, not after a polite
        stdin-close handshake that waits for the LLM round-trip to finish
        on its own.

        Idempotent — second call after the process already exited is a
        no-op. Marks the session closed so `close()` won't double-kill.
        """
        if self._closed:
            return
        self._closed = True
        if self._proc is None:
            return

        if self._runtime == "docker":
            try:
                import subprocess as _sp
                _sp.run(
                    ["docker", "kill", self._container_name],
                    check=False,
                    capture_output=True,
                    timeout=2.0,
                )
            except Exception:
                pass
        try:
            self._proc.kill()
        except ProcessLookupError:
            pass
        except Exception:
            pass
        try:
            await asyncio.wait_for(self._proc.wait(), timeout=2.0)
        except asyncio.TimeoutError:
            pass

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
        while True:
            line = await stdout.readline()
            if not line:
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
