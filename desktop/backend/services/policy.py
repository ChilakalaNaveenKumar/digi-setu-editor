"""
Defence-in-depth safety policy for the desktop sidecar.

Three concerns live here:

  1. **bash command policy** — block obviously-hostile shell
     invocations the model might be coaxed into running. The desktop
     app runs on the user's actual machine (no container, no kernel
     namespace, no egress firewall), so the layers below kick in
     before pi-coding-agent's upstream `permission-gate` extension
     even sees the command:
         - cloud-metadata SSRF probes (IMDS exfiltration; reachable
           if the user happens to run Digi Setu on a cloud VM)
         - cryptominer / DDoS / brute-force binary names (would burn
           the user's electricity / get them firewalled by their ISP
           on someone else's behalf)

  2. **filesystem deny-list** — paths the backend must never serve to
     the SPA's file-tree / read endpoints, even if the user picked a
     parent directory that happens to contain them. The model's
     `read` tool goes through pi's own protected-paths extension; the
     SPA-facing routes (file tree, file_ops) consult this list
     directly.

  3. **secret scrubber** — last-line scrub of any high-entropy
     token-shaped string in streamed model output and tool results.
     Desktop's SQLite / shadow-git logs persist on the user's disk;
     even a one-shot leak of a key into a saved JSONL is durable.

Where the trust boundary actually lives:
    - The pi process runs unprivileged under the user's own UID; OS
      file permissions are the primary enforcement.
    - Pi's upstream `protected-paths` extension blocks model writes
      to `.env`, `.git/`, `node_modules/`.
    - Pi's upstream `permission-gate` extension prompts the user
      before `rm -rf`, `sudo`, `chmod 777`.
    - The desktop APPEND_SYSTEM.md tells the model to stay inside
      the active workspace and to not touch SSH/AWS/GCP credential
      files unless the user named them in the current turn.
This module is the host-side belt to those suspenders: a final
content-based filter the routes layer applies before tool calls and
streamed events leave the sidecar.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


# ── bash command policy ───────────────────────────────────────────
# Patterns are evaluated against the FULL command line, not per-arg.
# Each rule has (regex, why) so the rejection message is actionable
# (the user sees *why* the model's command was blocked, not just
# "denied").
@dataclass(frozen=True)
class _BashRule:
    pattern: re.Pattern[str]
    reason: str


_BASH_RULES: tuple[_BashRule, ...] = (
    # ── Cloud metadata / SSRF — IMDS credential theft ────────────
    # Most desktop installs are on laptops where these IPs route
    # nowhere, but some users will run Digi Setu on a cloud VM
    # (Codespaces, GitHub Actions self-hosted, GCE workstation).
    # Reaching these endpoints is always a hostile signal — the
    # tokens they expose belong to the host's IAM identity, not the
    # user's project. Block at the bash layer so the model can't
    # tunnel via curl/wget/python.
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
    # ── Cryptominer / DDoS hints ────────────────────────────────
    # Burning the user's electricity (and their laptop's CPU
    # lifespan) on someone else's mining pool is theft from them.
    # Same rationale for DDoS / brute-force tools — those hurt the
    # user's IP reputation when their ISP gets the abuse complaint.
    _BashRule(
        re.compile(r"\b(?:xmrig|t-rex|nbminer|ethminer|cgminer|phoenixminer|teamredminer)\b", re.I),
        "blocked: cryptocurrency miner (would burn the user's CPU/electricity for someone else)",
    ),
    _BashRule(
        re.compile(r"\b(?:hping3|slowloris|loic|hulk|goldeneye)\b", re.I),
        "blocked: DDoS/flooding tool (would attack a third party from the user's IP)",
    ),
    # NOTE: We deliberately do NOT block:
    #     - sudo / su / doas — the user is on their own machine; the
    #       upstream permission-gate extension prompts before these
    #       run, which is the right surface for the consent decision.
    #     - apt/brew/npm/pip/cargo install — legitimate developer
    #       workflow on a user's own laptop. The model writes to the
    #       active workspace by default; system-wide installs need
    #       sudo, which the permission-gate already gates.
    #     - curl … | sh — fine on the user's own machine if they
    #       asked for it. The permission-gate prompts on the sudo
    #       half if the install needs root.
    #     - editing ~/.bashrc, /etc/, crontab, systemctl — again,
    #       prompted by permission-gate when sudo is involved;
    #       editing dotfiles is the user's own house.
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
# requested path, cause file_ops / file-tree to 403. The model's
# read tool goes through pi's protected-paths extension, but the
# SPA-facing routes can be hit directly (e.g. user dragged a path
# into the file tree picker), so we check them too.
#
# Rule of thumb for what goes here: paths that contain credentials
# the user did NOT explicitly volunteer in the current turn. If
# they paste a literal `~/.ssh/id_rsa` into the chat, that's their
# call; we don't second-guess explicit text. We do refuse to
# enumerate/serve those paths automatically via file ops.
_FS_DENY_SUBSTRINGS: tuple[str, ...] = (
    # System credential stores — cross-platform unix layout
    "/etc/shadow",
    "/etc/sudoers",
    "/etc/passwd-",     # backup of /etc/passwd (often world-readable but writes to it shouldn't go through us)
    "/private/etc/sudoers",  # macOS canonical path
    # User credential dotfiles
    "/.aws/credentials",
    "/.aws/config",
    "/.config/gcloud/application_default_credentials.json",
    "/.config/gcloud/legacy_credentials/",
    "/.ssh/id_rsa",
    "/.ssh/id_ed25519",
    "/.ssh/id_dsa",
    "/.ssh/id_ecdsa",
    "/.ssh/identity",
    "/.gnupg/private-keys-v1.d/",
    "/.gnupg/secring.gpg",
    "/.netrc",
    "/.pypirc",
    "/.npmrc",
    "/.cargo/credentials.toml",
    "/.docker/config.json",
    "/.kube/config",
    # Browser secrets (macOS / Linux profile DBs)
    "/Library/Application Support/Google/Chrome/Default/Cookies",
    "/Library/Application Support/Google/Chrome/Default/Login Data",
    "/Library/Application Support/Firefox/Profiles/",
    "/.config/google-chrome/Default/Cookies",
    "/.mozilla/firefox/",
    # Production-style env files outside the active workspace
    ".env.production",
    ".env.local",
    # Generic per-user secret directories (case-insensitive substring
    # match catches them anywhere in the path)
    "/.password-store/",
    "/.secrets/",
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
# High-confidence prefixes for the secret types we'd actually have
# in a developer's filesystem / environment / shell history. Tuned
# to skip random base64 chunks (which are common in legitimate
# output) and only fire on known-shape API tokens.
_SECRET_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    # Anthropic — has to come BEFORE the generic sk_ pattern because
    # the prefix overlaps. (Anthropic uses `sk-ant-`; Stripe uses
    # `sk_live_` / `sk_test_`.) Order matters.
    (re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}"), "[REDACTED anthropic-key]"),
    # Stripe AND Clerk both use `sk_live_` / `sk_test_` — we can't
    # distinguish without reading the embedded base32 (Stripe
    # encodes the account id; Clerk doesn't). Use a generic label so
    # we don't lie to the user about which system the key belongs to.
    (re.compile(r"\bsk_(?:live|test)_[A-Za-z0-9_-]{16,}"), "[REDACTED secret-key]"),
    (re.compile(r"\bpk_live_[A-Za-z0-9_-]{16,}"), "[REDACTED clerk-publishable]"),
    (re.compile(r"\brk_live_[A-Za-z0-9_-]{16,}"), "[REDACTED stripe-restricted-key]"),
    (re.compile(r"\bwhsec_[A-Za-z0-9_-]{16,}"), "[REDACTED webhook-secret]"),
    # PEM-armoured private keys (RSA / EC / generic / OpenSSH)
    (
        re.compile(
            r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
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

    The streamed payloads we scrub are kilobytes at worst, so the
    O(len(text)) per-pattern cost is acceptable in the hot path.
    """
    if not text:
        return text
    out = text
    for pat, replacement in _SECRET_PATTERNS:
        out = pat.sub(replacement, out)
    return out
