"""
Defence-in-depth policy layer.

Three concerns live here:

  1. **bash command policy** — block obviously-dangerous shell
     invocations the AI might be coaxed into running (extracting
     metadata-server tokens, reading /etc/shadow, modifying
     .bashrc for prompt-injection persistence, sudo, etc.).

  2. **filesystem deny-list** — paths the AI must never read or
     write even from within its sandbox cwd. We can't fully prevent
     it without OS-level controls (chroot/namespaces; landing in
     v1.1 with the runuser sandbox), but the bash wrapper can short-
     circuit obvious attempts and the read/write tools (which we
     proxy via services/file_ops.py) can refuse the path.

  3. **secret scrubber** — last-line scrub of any high-entropy
     token-shaped string in streamed model output. If the agent ever
     actually does manage to read a secret, we don't want it to leak
     back into the rendered chat (or, worse, into the saved JSONL
     log that ships to the next session as context).

This module is **advisory** for tools we don't fully wrap (i.e.
pi's own bash) — it's authoritative for the routes/file_ops paths
the SPA hits directly. The OS-level enforcement layer (firewall,
filesystem perms, runuser drop) is documented in deploy/README.md
and is what actually keeps a determined attacker out.

Decisions encoded here are based on the public threat-research read
in May 2026:
  - SANDBOXESCAPEBENCH (arXiv 2603.02277) — frontier LLMs *can*
    exploit container escapes when given shell access.
  - GCP IMDS SSRF (Tenable, 2026) — default service account + the
    metadata server is the #1 GCP credential-theft path; block at
    the network layer AND prompt-warn the agent.
  - "PromptMink" / slopsquatting (InfoWorld, 2026) — AI agents
    auto-install hallucinated package names; force a confirmation
    flow before any global install. We refuse the most common
    install incantations here and the system prompt teaches the
    agent to ask first.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


# ── bash command policy ───────────────────────────────────────────
# Patterns are evaluated against the FULL command line, not per-arg.
# Each rule has (regex, why) so the rejection message is actionable
# (the user sees *why* the agent's command was blocked, not just
# "denied").
@dataclass(frozen=True)
class _BashRule:
    pattern: re.Pattern[str]
    reason: str


_BASH_RULES: tuple[_BashRule, ...] = (
    # ── Cloud metadata / SSRF — IMDS credential theft ────────────
    _BashRule(
        re.compile(r"\b169\.254\.169\.254\b"),
        "blocked: cloud-metadata IP (would expose VM IAM tokens)",
    ),
    _BashRule(
        re.compile(r"\bmetadata\.google\.internal\b", re.I),
        "blocked: GCP metadata hostname (would expose VM IAM tokens)",
    ),
    _BashRule(
        re.compile(r"\b(?:fd00:ec2::254|metadata\.aws|169\.254\.170\.2)\b", re.I),
        "blocked: AWS/ECS metadata endpoint",
    ),
    # ── Privilege escalation ────────────────────────────────────
    _BashRule(
        re.compile(r"(?:^|\s|;|&&|\|\|)(?:sudo|su|doas)\b"),
        "blocked: privilege escalation (sudo/su/doas)",
    ),
    _BashRule(
        re.compile(r"\b(?:setcap|chmod\s+[+]?[us]\b|chown\s+root\b)"),
        "blocked: capability/ownership change",
    ),
    # ── Persistence (rewriting shell init or cron) ──────────────
    _BashRule(
        re.compile(
            r">\s*~?/?\.(?:bashrc|zshrc|profile|bash_profile|zprofile)\b"
        ),
        "blocked: shell-init rewrite (persistence vector)",
    ),
    _BashRule(
        re.compile(r"\bcrontab\b|\bsystemctl\b|\bservice\s+\w+\s+(?:start|stop|enable)"),
        "blocked: scheduler / service management",
    ),
    # ── Sensitive system paths the AI should never read ─────────
    # `(?:cat|grep|…)\s+(?:\S+\s+)?/etc/…` allows trailing flags or
    # search-pattern arguments before the path: "grep root /etc/passwd"
    # is just as bad as "cat /etc/passwd".
    _BashRule(
        re.compile(
            r"\b(?:cat|less|head|tail|grep|awk|sed|strings|hexdump|xxd)"
            r"(?:\s+-\S+)*"           # any number of -flag args
            r"(?:\s+\S+)*"            # then any number of non-flag args (e.g. a regex pattern)
            r"\s+/etc/(?:shadow|passwd|sudoers|gshadow)\b"
        ),
        "blocked: system credential file",
    ),
    _BashRule(
        re.compile(r"/srv/pi/state\b|/opt/pi\b|/etc/secrets?\b"),
        "blocked: server-private path (operator secrets live here)",
    ),
    # ── Container/host introspection ────────────────────────────
    _BashRule(
        re.compile(r"\b(?:docker|kubectl|nsenter|unshare|mount\s|umount\s)\b"),
        "blocked: container/host management tool",
    ),
    # ── Network exfiltration patterns ───────────────────────────
    _BashRule(
        re.compile(r"\bnc\s+-[le]|\bncat\s+-[le]|\b/dev/tcp/"),
        "blocked: raw socket / netcat listener (exfil vector)",
    ),
    _BashRule(
        re.compile(r"\bcurl\b[^\n;]*\bhttp[s]?://[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}"),
        "blocked: curl to a raw IP — egress allow-list rejects this; "
        "if the user provided a URL, ask for the hostname instead",
    ),
    # ── Global package installs (slopsquatting + cryptominer
    #    risk; force a workspace-local install instead) ──────────
    # We can't use `\b-g\b` because `-` isn't a word char so `\b`
    # never matches before it. `(?:^|\s)-g(?=\s|$)` looks for `-g`
    # as a stand-alone token instead. We also catch the long form.
    _BashRule(
        re.compile(
            r"\bnpm\s+(?:install|i|add|isntall)\b[^\n;]*"
            r"(?:(?:^|\s)-g(?=\s|$)|--global\b)"
        ),
        "blocked: `npm install -g/--global` (use a workspace-local install instead)",
    ),
    _BashRule(
        re.compile(r"\byarn\s+global\s+add\b"),
        "blocked: `yarn global add` (use a workspace-local install instead)",
    ),
    _BashRule(
        re.compile(r"\bpip\s+install\b[^\n;]*\b--user\b"),
        "blocked: `pip install --user` (writes outside workspace; install into a venv)",
    ),
    _BashRule(
        re.compile(r"\b(?:apt|apt-get|yum|dnf|brew|snap)\s+(?:install|add|update|upgrade)\b"),
        "blocked: system package manager (no root, no persistent state)",
    ),
    # ── Common eval-from-stream patterns ────────────────────────
    # Both curl AND wget can pipe into a shell; cover both.
    _BashRule(
        re.compile(r"\b(?:curl|wget|fetch)\b[^\n;]*\|\s*(?:bash|sh|zsh|fish|python\d?|node|perl|ruby)\b"),
        "blocked: download-pipe-shell (downloads + executes opaque content)",
    ),
    _BashRule(
        re.compile(r"\bbase64\s+-d[^\n;]*\|\s*(?:bash|sh|zsh|python|node)\b"),
        "blocked: base64-decode | shell (obfuscated execution)",
    ),
    # Process substitution variant: `bash <(curl …)` — same risk.
    _BashRule(
        re.compile(r"(?:bash|sh|zsh|python\d?)\s+<\(\s*(?:curl|wget|fetch)\b"),
        "blocked: shell <(curl …) (downloads + executes opaque content)",
    ),
    # ── Cryptominer hints ───────────────────────────────────────
    _BashRule(
        re.compile(r"\b(?:xmrig|t-rex|nbminer|ethminer|cgminer)\b", re.I),
        "blocked: cryptocurrency miner",
    ),
)


@dataclass(frozen=True)
class BashCheck:
    allowed: bool
    reason: Optional[str] = None
    matched_pattern: Optional[str] = None


def check_bash(cmd: str) -> BashCheck:
    """
    Evaluate a candidate shell command. Returns a BashCheck with
    `allowed=False` and a human-readable reason on the first match.

    The check is intentionally conservative: false positives are
    annoying ("denied your `sudo apt install` request"), false
    negatives are catastrophic. When users hit a false positive,
    they get a clear reason and can rephrase.
    """
    normalised = " ".join((cmd or "").strip().split())
    if not normalised:
        return BashCheck(allowed=True)
    for rule in _BASH_RULES:
        if rule.pattern.search(normalised):
            return BashCheck(
                allowed=False,
                reason=rule.reason,
                matched_pattern=rule.pattern.pattern,
            )
    return BashCheck(allowed=True)


# ── filesystem deny-list ─────────────────────────────────────────
# Substrings (case-insensitive) that, if present anywhere in a
# requested path, cause file_ops to 403. The OS-level enforcement
# layer (deploy/README) is what actually keeps these inaccessible;
# this is a last-line check so the SPA never even *asks* for them.
_FS_DENY_SUBSTRINGS: tuple[str, ...] = (
    "/srv/pi/state",
    "/opt/pi",
    "/etc/shadow",
    "/etc/passwd",
    "/etc/sudoers",
    "/.aws/",
    "/.config/gcloud/",
    ".env.production",
    ".env.local",
    "id_rsa",
    "id_ed25519",
)


def is_path_denied(path: str) -> Optional[str]:
    """Return a reason string if the path is denied, else None."""
    if not path:
        return None
    needle = path.lower()
    for sub in _FS_DENY_SUBSTRINGS:
        if sub.lower() in needle:
            return f"path matches deny-list pattern: {sub}"
    return None


# ── secret scrubber ──────────────────────────────────────────────
# High-confidence prefixes for the secret types we'd actually have on
# this server. Tuned to skip random base64 chunks (which are common
# in legitimate output) and only fire on known-shape API tokens.
_SECRET_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    # Anthropic — has to come BEFORE the generic sk_ pattern because
    # the prefix overlaps. (Anthropic uses `sk-ant-`; Stripe uses
    # `sk_live_` / `sk_test_`.) Order matters.
    (re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}"), "[REDACTED anthropic-key]"),
    # Stripe AND Clerk both use `sk_live_` / `sk_test_` — we can't
    # distinguish without reading the embedded base32 (Stripe
    # encodes the account id; Clerk doesn't). Use a generic label so
    # we don't lie to the operator about which system the key
    # belongs to.
    (re.compile(r"\bsk_(?:live|test)_[A-Za-z0-9_-]{16,}"), "[REDACTED secret-key]"),
    (re.compile(r"\bpk_live_[A-Za-z0-9_-]{16,}"), "[REDACTED clerk-publishable]"),
    (re.compile(r"\brk_live_[A-Za-z0-9_-]{16,}"), "[REDACTED stripe-restricted-key]"),
    (re.compile(r"\bwhsec_[A-Za-z0-9_-]{16,}"), "[REDACTED webhook-secret]"),
    # GCP service-account private key
    (
        re.compile(
            r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC )?PRIVATE KEY-----"
        ),
        "[REDACTED private-key]",
    ),
    # GCP OAuth access tokens look like ya29.<long base64>; the
    # prefix is distinctive enough to risk a regex.
    (re.compile(r"\bya29\.[A-Za-z0-9_-]{40,}"), "[REDACTED google-oauth-token]"),
    # AWS access key IDs (AKIA / ASIA for STS) and secret keys
    (re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), "[REDACTED aws-access-key]"),
    # GitHub tokens (classic + fine-grained)
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"), "[REDACTED github-token]"),
    # OpenAI API keys (sk-proj-… and sk-…)
    (re.compile(r"\bsk-proj-[A-Za-z0-9_-]{32,}"), "[REDACTED openai-key]"),
    # Slack bot/user tokens
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"), "[REDACTED slack-token]"),
    # Generic high-entropy JWT (three base64url chunks). The header
    # `eyJhbGciOi` decodes to `{"alg":"…` so we can be tighter than
    # the previous guess. Length floor 16 per chunk catches anything
    # signed with HS256 and beyond.
    (
        re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{16,}"),
        "[REDACTED jwt]",
    ),
)


def scrub_secrets(text: str) -> str:
    """
    Replace high-confidence secrets in `text` with a labelled
    placeholder. Idempotent and side-effect free.

    No micro-optimised early-out: the previous version short-
    circuited if the text had no `[`, `_`, or `.`, which silently
    skipped scrubbing for hyphen-using tokens (Anthropic, Slack,
    AWS). The `re.sub` calls themselves are O(len(text)) and the
    streamed payloads we scrub are kilobytes at worst, so the
    optimisation wasn't worth the bug.
    """
    if not text:
        return text
    out = text
    for pat, replacement in _SECRET_PATTERNS:
        out = pat.sub(replacement, out)
    return out
