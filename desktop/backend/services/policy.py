"""
Defence-in-depth policy layer.

Three concerns live here:

  1. **bash command policy** — block obviously-dangerous shell
     invocations the AI might be coaxed into running. With the
     per-session container architecture (Phase 6) the kernel
     namespace + egress proxy do most of the heavy lifting, so this
     layer focuses on:
         - host-level metadata SSRF attempts (defense in depth — the
           container subnet can't route to 169.254.169.254 anyway,
           but we want to log the *attempt* and refuse the bash call
           before it hits the network)
         - cryptominers (waste of the user's billed compute)
         - container-escape probes (`docker socket`, `nsenter`,
           `mount /proc/host`, etc.)
     Most "global install" / "curl|sh" / "apt install" rules from
     the dual-uid era have been REMOVED — those are now legitimate
     and useful inside the user's per-session container, where the
     installs evaporate on chat close anyway.

  2. **filesystem deny-list** — paths the backend (uid 1100) must
     never serve to the SPA's file-tree / read endpoints. The AI's
     bash now lives in a separate per-session container with its own
     mount namespace; bind mounts only expose `/workspace`. So this
     list is mostly relevant for the file-tree route which still
     reads from the host filesystem.

  3. **secret scrubber** — last-line scrub of any high-entropy
     token-shaped string in streamed model output. If the agent ever
     actually does manage to read a secret, we don't want it to leak
     back into the rendered chat (or, worse, into the saved JSONL
     log that ships to the next session as context).

This module is **advisory** for tools we don't fully wrap (i.e.
pi's own bash) — it's authoritative for the routes/file_ops paths
the SPA hits directly. The OS-level enforcement layers (kernel
namespaces, nftables egress firewall, MITM auth proxy) are
documented in deploy/HARDENING.md and are what actually keep a
determined attacker out.
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
    # ── Container escape probes ─────────────────────────────────
    # The per-session container has cap_drop ALL + a small cap_add
    # set that does NOT include CAP_SYS_ADMIN, CAP_NET_ADMIN, or
    # CAP_SYS_PTRACE. These tools won't actually do anything inside
    # the container, but the AI trying to invoke them at all is a
    # signal of hostile intent — refuse and log.
    _BashRule(
        re.compile(r"\b(?:nsenter|unshare\s+--mount|mount\s+--bind\s+/proc/\d+)"),
        "blocked: container-escape probe (cap_drop ALL + read-only host paths neutralise these anyway)",
    ),
    _BashRule(
        re.compile(r"/var/run/docker\.sock|/host/proc|/host/sys|/host/etc"),
        "blocked: docker-socket or host-namespace path (container has none of these mounted)",
    ),
    # ── Network exfiltration via raw IPs ────────────────────────
    # Egress proxy already rejects raw-IP CONNECTs (allow-list is by
    # hostname), but blocking at the bash layer gives a clearer
    # error message than "connection refused".
    _BashRule(
        re.compile(r"\bcurl\b[^\n;]*\bhttp[s]?://[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}"),
        "blocked: curl to a raw IP — egress allow-list rejects this; "
        "if the user provided a URL, ask for the hostname instead",
    ),
    # ── Cryptominer hints ───────────────────────────────────────
    # The user IS billed for compute inside the container. Mining
    # crypto via their session would burn their plan's credits on
    # something they didn't ask for. This rule predates per-session
    # containers and remains relevant.
    _BashRule(
        re.compile(r"\b(?:xmrig|t-rex|nbminer|ethminer|cgminer|phoenixminer|teamredminer)\b", re.I),
        "blocked: cryptocurrency miner (would burn the user's billed compute budget)",
    ),
    # NOTE: With per-session container architecture the following
    # bash patterns are now ALLOWED (they were blocked in the dual-
    # uid era). The container is ephemeral and namespace-isolated;
    # what the AI does inside is the user's choice.
    #     - sudo / su / doas — sudo NOPASSWD is configured on purpose
    #     - apt/yum/dnf/brew/snap install — pkg installs are fine
    #     - npm install -g, yarn global add, pip --user — fine
    #     - curl … | sh, bash <(curl …) — fine, container is throwaway
    #     - editing ~/.bashrc, /etc/, crontab, systemctl — fine, all
    #       container-local and gone on chat close
    #     - cat /etc/shadow — fine, the container's shadow file is
    #       generated at image build time and contains no real users
    # The trust boundary moved from "regex on bash strings" to
    # "kernel namespaces + egress allow-list" — we no longer need
    # to play whack-a-mole on bash patterns for these.
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
