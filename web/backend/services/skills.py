"""
Skills — markdown documents the LLM consults per turn (web edition).

Web has a fixed container environment, so we don't auto-generate a
per-workspace compile-loop. Instead:

  - One **bundled** compile-loop skill ships with the app at
    `.pi/skills/compile-loop/SKILL.md` (PROJECT_ROOT). Loaded on every
    turn, no env probe needed — the container is the env.
  - **Per-Clerk-user uploaded** skills live at
    `<DATA_ROOT>/users/<sanitized_id>/skills/<name>/SKILL.md`. Visible
    across all of that user's workspaces; referenced via `@name`.

The on-disk file format mirrors the desktop side (and `.sage-ai/`):
YAML front-matter + markdown body. The parser, mention syntax, and
turn-prefix assembler all behave identically to
`desktop/backend/services/skills.py`.
"""

from __future__ import annotations

import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from config import DATA_ROOT, PROJECT_ROOT

# ── Layout ────────────────────────────────────────────────────────────

BUNDLED_SKILLS_DIR = PROJECT_ROOT / ".pi" / "skills"
USERS_DIR = DATA_ROOT / "users"
USER_SKILL_SUBDIR = "skills"

_SAFE_USER_ID = re.compile(r"[^A-Za-z0-9._-]")


def _user_skills_dir(user_id: str) -> Path:
    safe = _SAFE_USER_ID.sub("_", user_id or "")[:128] or "anon"
    return USERS_DIR / safe / USER_SKILL_SUBDIR


# ── Front-matter parser (copied from desktop side; kept in sync) ──────

_FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.DOTALL)
_MENTION_RE = re.compile(r"(?<![\w@])@([a-zA-Z0-9][a-zA-Z0-9_\-]{0,63})")


def _parse_front_matter(text: str) -> tuple[dict[str, Any], str]:
    m = _FRONT_MATTER_RE.match(text)
    if not m:
        return {}, text
    raw, body = m.group(1), m.group(2)
    meta: dict[str, Any] = {}
    current_list_key: Optional[str] = None
    for raw_line in raw.splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        stripped = line.lstrip()
        if stripped.startswith("- ") and current_list_key:
            item = stripped[2:].strip().strip('"').strip("'")
            if item:
                meta[current_list_key].append(item)
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if not value:
            meta[key] = []
            current_list_key = key
            continue
        current_list_key = None
        meta[key] = value.strip('"').strip("'")
    return meta, body


def parse_mentions(text: str) -> list[str]:
    seen: list[str] = []
    for raw in _MENTION_RE.findall(text or ""):
        name = raw.strip().lower()
        if name and name not in seen:
            seen.append(name)
    return seen


# ── Model + scanner ───────────────────────────────────────────────────


@dataclass
class Skill:
    name: str
    description: str
    body: str
    source: str  # "bundled" | "user"
    auto: str = ""
    triggers: list[str] = field(default_factory=list)
    path: Optional[Path] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "source": self.source,
            "auto": self.auto,
            "triggers": list(self.triggers),
        }


def _load_skill_from_path(skill_dir: Path, source: str) -> Optional[Skill]:
    md = skill_dir / "SKILL.md"
    if not md.exists():
        return None
    try:
        text = md.read_text(encoding="utf-8")
    except OSError:
        return None
    meta, body = _parse_front_matter(text)
    name = (meta.get("name") or skill_dir.name).strip()
    triggers_raw = meta.get("triggers") or []
    triggers = [t for t in triggers_raw if isinstance(t, str) and t.strip()]
    return Skill(
        name=name.lower(),
        description=(meta.get("description") or "").strip(),
        body=body.strip(),
        source=source,
        auto=(meta.get("auto") or "").strip(),
        triggers=triggers,
        path=md,
    )


def _scan_skills_dir(root: Path, source: str) -> list[Skill]:
    if not root.is_dir():
        return []
    out: list[Skill] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        sk = _load_skill_from_path(child, source)
        if sk is not None:
            out.append(sk)
    return out


# ── Public API ─────────────────────────────────────────────────────────


def list_all_skills(user_id: str) -> list[Skill]:
    """Bundled skills + this user's uploaded skills. User wins on name collision."""
    skills: list[Skill] = []
    skills.extend(_scan_skills_dir(BUNDLED_SKILLS_DIR, "bundled"))
    skills.extend(_scan_skills_dir(_user_skills_dir(user_id), "user"))
    deduped: dict[str, Skill] = {}
    for sk in skills:
        deduped[sk.name] = sk
    return list(deduped.values())


def list_skills_summary(user_id: str) -> list[dict[str, Any]]:
    return [sk.to_dict() for sk in list_all_skills(user_id)]


def _matches_trigger(prompt: str, triggers: list[str]) -> bool:
    if not triggers:
        return False
    lc = prompt.lower()
    return any(t.lower() in lc for t in triggers if t.strip())


def _format_skill_chunk(skill: Skill) -> str:
    return (
        f"<skill name=\"{skill.name}\" source=\"{skill.source}\">\n"
        f"{skill.body}\n"
        f"</skill>"
    )


# Regex matching ONE leading skill chunk as emitted by `_format_skill_chunk`.
# The chunks are concatenated by `\n\n` and the whole prefix terminates with
# `\n\n` before the user's message, so allowing `\n*` to consume the
# separator lets us strip multiple chunks in a loop without a second pass.
# Anchored to start-of-string so a user who *types* `<skill ...>` mid-message
# is never silently rewritten.
_SKILL_PREFIX_RE = re.compile(
    r'^<skill name="[^"]*" source="[^"]*">\n.*?\n</skill>\n*',
    re.DOTALL,
)


def strip_skill_prefix(text: str) -> str:
    """
    Remove leading `<skill>...</skill>` blocks that `assemble_turn_prefix`
    prepended to a user message before sending it to pi.

    Why this exists: pi persists user prompts verbatim into its JSONL
    chat log, including whatever prefix the route added. When the SPA
    reloads history (page refresh, resume in a new tab, chat URL shared
    with a teammate), the augmented text would otherwise surface inside
    the user's own chat bubble — which leaks the skill body, bloats the
    visible turn, and makes the chat look corrupted.

    The model still sees the skill content because the prefix is
    inlined at the moment pi processes the prompt; only the post-hoc
    history reader strips it. In-body `<skill>` tags the user typed
    themselves are NOT touched (the regex is anchored to start).
    """
    if not text or not text.startswith("<skill "):
        return text
    out = text
    while True:
        m = _SKILL_PREFIX_RE.match(out)
        if not m:
            break
        out = out[m.end():]
    return out


def assemble_turn_prefix(user_id: str, user_message: str) -> str:
    """Auto-loaded bundled skills + matched-trigger skills + @mention skills."""
    chunks: list[str] = []
    skills = list_all_skills(user_id)
    by_name = {sk.name: sk for sk in skills}
    seen: set[str] = set()

    for sk in skills:
        if sk.auto == "flow_entry" or (
            sk.auto == "surface" and _matches_trigger(user_message, sk.triggers)
        ):
            seen.add(sk.name)
            chunks.append(_format_skill_chunk(sk))

    for mention in parse_mentions(user_message):
        if mention in seen:
            continue
        sk = by_name.get(mention)
        if sk is None:
            continue
        seen.add(mention)
        chunks.append(_format_skill_chunk(sk))

    if not chunks:
        return ""
    return "\n\n".join(chunks) + "\n\n"


def upload_user_skill(user_id: str, name: str, body: str) -> Path:
    safe = re.sub(r"[^a-zA-Z0-9_\-]+", "-", name.strip().lower()).strip("-")
    if not safe:
        raise ValueError("invalid skill name")
    target_dir = _user_skills_dir(user_id) / safe
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "SKILL.md"
    try:
        target.write_text(body, encoding="utf-8")
    except OSError as exc:
        print(f"[skills] write failed: {exc}", file=sys.stderr)
        raise
    return target


def delete_user_skill(user_id: str, name: str) -> bool:
    safe = re.sub(r"[^a-zA-Z0-9_\-]+", "-", name.strip().lower()).strip("-")
    if not safe:
        return False
    target_dir = _user_skills_dir(user_id) / safe
    if not target_dir.is_dir():
        return False
    shutil.rmtree(target_dir, ignore_errors=True)
    return True


__all__ = [
    "Skill",
    "parse_mentions",
    "list_all_skills",
    "list_skills_summary",
    "assemble_turn_prefix",
    "upload_user_skill",
    "delete_user_skill",
]
