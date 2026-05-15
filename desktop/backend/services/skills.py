"""
Skills — markdown documents the LLM consults per turn.

Three sources, one resolver:

1. Bundled `compile-loop` skill auto-generated per workspace based on the
   user's actual machine env (typst/quarto/R/node versions, fonts visible,
   files in cwd). Written to `<workspace>/.digi-setu/skills/compile-loop/SKILL.md`
   on first prompt and refreshed when stale.

2. Workspace-local user skills under `<workspace>/.digi-setu/skills/<name>/SKILL.md`.

3. Global user skills under `~/.digi-setu/skills/<name>/SKILL.md`.

A workspace-root `AGENTS.md` is also generated (build/run commands, detected
toolchain) and prepended to every turn. Skills with `auto: surface` whose
`triggers` match the user's prompt are auto-loaded. Anything else loads only
when the user `@-mentions` the skill name in their prompt.

The format mirrors `.sage-ai/` from ai-pre-review-poc-lite — YAML front-matter
plus markdown body — so users who already use that convention can drop the same
files into a Digi Setu workspace and they work.
"""

from __future__ import annotations

import asyncio
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# ── Layout ────────────────────────────────────────────────────────────

WORKSPACE_SKILLS_DIR = ".digi-setu/skills"
WORKSPACE_AGENTS_MD = ".digi-setu/AGENTS.md"
GLOBAL_SKILLS_DIR_NAME = "skills"   # under ~/.digi-setu/skills/
AUTO_REFRESH_AFTER_SECS = 7 * 24 * 3600  # re-probe once a week


def global_skills_dir() -> Path:
    """`~/.digi-setu/skills/` — user-attached skills available in every workspace."""
    return Path.home() / ".digi-setu" / GLOBAL_SKILLS_DIR_NAME


# ── Front-matter parser ───────────────────────────────────────────────

_FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.DOTALL)
_MENTION_RE = re.compile(r"(?<![\w@])@([a-zA-Z0-9][a-zA-Z0-9_\-]{0,63})")


def _parse_front_matter(text: str) -> tuple[dict[str, Any], str]:
    """Return (front_matter_dict, body). If no front-matter, returns ({}, text).

    We only need a tiny subset: `name`, `description`, `auto`, `flow`, and
    `triggers` (a YAML list). No full YAML parser — keeps the bundle smaller
    and avoids a runtime dep on PyYAML.
    """
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
    """Return distinct `@<name>` references in the user's message."""
    seen: list[str] = []
    for raw in _MENTION_RE.findall(text or ""):
        name = raw.strip().lower()
        if name and name not in seen:
            seen.append(name)
    return seen


# ── Skill data model ───────────────────────────────────────────────────


@dataclass
class Skill:
    name: str
    description: str
    body: str
    source: str  # "bundled" | "workspace" | "global"
    auto: str = ""   # "surface" → load on trigger match; "flow_entry" → always
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
    """Read `<skill_dir>/SKILL.md`. Returns None on any parse failure."""
    md = skill_dir / "SKILL.md"
    if not md.exists():
        return None
    try:
        text = md.read_text(encoding="utf-8")
    except OSError:
        return None
    meta, body = _parse_front_matter(text)
    name = (meta.get("name") or skill_dir.name).strip()
    description = (meta.get("description") or "").strip()
    triggers_raw = meta.get("triggers") or []
    triggers = [t for t in triggers_raw if isinstance(t, str) and t.strip()]
    return Skill(
        name=name.lower(),
        description=description,
        body=body.strip(),
        source=source,
        auto=(meta.get("auto") or "").strip(),
        triggers=triggers,
        path=md,
    )


def _scan_skills_dir(root: Path, source: str) -> list[Skill]:
    """Read every `<root>/<name>/SKILL.md` under `root`."""
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


# ── Env probe ──────────────────────────────────────────────────────────


@dataclass
class EnvProfile:
    workspace: Path
    typst_version: str = ""
    typst_path: str = ""
    quarto_version: str = ""
    quarto_path: str = ""
    rscript_version: str = ""
    node_version: str = ""
    fonts_sample: list[str] = field(default_factory=list)
    files_listing: list[str] = field(default_factory=list)
    has_qmd: bool = False
    has_quarto_yml: bool = False
    has_typ: bool = False
    has_tex: bool = False


def _run(cmd: list[str], *, cwd: Optional[Path] = None, timeout: float = 8.0) -> str:
    """Run a command, return stdout (best-effort). Empty string on failure."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            check=False,
            text=True,
            cwd=str(cwd) if cwd else None,
            timeout=timeout,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""
    if result.returncode != 0 and not result.stdout:
        # `quarto --version` writes to stdout but uses non-zero on some
        # platforms — accept stdout anyway, only treat genuinely-empty
        # output as failure.
        return ""
    return (result.stdout or "").strip()


def _which(binary: str) -> str:
    path = shutil.which(binary)
    return path or ""


async def probe_env(workspace: Path) -> EnvProfile:
    """Probe the user's machine + workspace for everything the skill needs."""

    def _sync() -> EnvProfile:
        profile = EnvProfile(workspace=workspace)
        profile.typst_path = _which("typst")
        if profile.typst_path:
            profile.typst_version = _run([profile.typst_path, "--version"])
            fonts_raw = _run([profile.typst_path, "fonts"])
            profile.fonts_sample = [
                ln.strip() for ln in fonts_raw.splitlines() if ln.strip()
            ][:40]
        profile.quarto_path = _which("quarto")
        if profile.quarto_path:
            profile.quarto_version = _run([profile.quarto_path, "--version"])
        rscript = _which("Rscript") or _which("Rscript.exe")
        if rscript:
            profile.rscript_version = _run([rscript, "--version"])
        node = _which("node")
        if node:
            profile.node_version = _run([node, "--version"])

        try:
            entries = sorted(p.name for p in workspace.iterdir() if not p.name.startswith("."))
        except OSError:
            entries = []
        profile.files_listing = entries[:60]
        lower = {n.lower() for n in entries}
        profile.has_quarto_yml = any(n in lower for n in ("_quarto.yml", "_quarto.yaml"))
        profile.has_qmd = any(n.endswith(".qmd") for n in lower)
        profile.has_typ = any(n.endswith(".typ") for n in lower)
        profile.has_tex = any(n.endswith(".tex") for n in lower)
        return profile

    return await asyncio.to_thread(_sync)


# ── Seeder: render AGENTS.md + compile-loop SKILL.md ──────────────────


def _render_agents_md(profile: EnvProfile) -> str:
    p = profile
    lines: list[str] = []
    lines.append("# AGENTS.md")
    lines.append("")
    lines.append("Auto-generated by Digi Setu Desktop. Edit freely — Digi Setu")
    lines.append("will not overwrite this file once you change it.")
    lines.append("")
    lines.append("## Workspace")
    lines.append("")
    lines.append(f"- **Folder**: `{p.workspace}`")
    if p.files_listing:
        sample = ", ".join(p.files_listing[:10])
        lines.append(f"- **Sample contents**: {sample}")
    lines.append("")
    lines.append("## Toolchain on this machine")
    lines.append("")
    rows: list[tuple[str, str, str]] = []
    rows.append(("typst", p.typst_version or "—", p.typst_path or "(not found)"))
    rows.append(("quarto", p.quarto_version or "—", p.quarto_path or "(not found)"))
    rows.append(("Rscript", p.rscript_version.splitlines()[0] if p.rscript_version else "—", _which("Rscript") or "(not found)"))
    rows.append(("node", p.node_version or "—", _which("node") or "(not found)"))
    lines.append("| Tool | Version | Path |")
    lines.append("|------|---------|------|")
    for name, ver, path in rows:
        lines.append(f"| {name} | {ver} | `{path}` |")
    lines.append("")
    lines.append("## How to render documents in this workspace")
    lines.append("")
    if p.has_qmd or p.has_quarto_yml:
        lines.append("- Quarto project detected (`.qmd` or `_quarto.yml`).")
        lines.append("  - Full render:  `quarto render <file>.qmd --to typst`")
        lines.append("  - Watch mode:   `quarto preview <file>.qmd`")
        lines.append("  - Quarto bundles its own typst — do NOT compile the generated `.typ` with the system typst.")
    if p.has_typ:
        lines.append("- Raw Typst sources detected (`.typ`).")
        lines.append("  - Compile:      `typst compile <file>.typ <file>.pdf`")
        lines.append("  - PNG render:   `typst compile <file>.typ <file>-{n}.png --format png --ppi 144`")
    if not (p.has_qmd or p.has_typ or p.has_quarto_yml):
        lines.append("- No `.qmd`, `.typ`, or `_quarto.yml` detected in the workspace root yet.")
        lines.append("  Most Typst work starts by creating one — see `skills/compile-loop/SKILL.md` for the loop.")
    lines.append("")
    lines.append("## Conventions")
    lines.append("")
    lines.append("- Write Typst sources at the workspace root or under a project subfolder.")
    lines.append("- Drop generated PDFs / PNGs into a sibling folder named after the source.")
    lines.append("- Treat secrets (`.env`, `~/.ssh`, `~/.aws`) as off-limits unless the user names them explicitly.")
    lines.append("")
    lines.append("## Verify before answering")
    lines.append("")
    lines.append("- The `AGENTS.md` and `skills/` files are a snapshot — re-read source files via `read` before quoting from them.")
    lines.append("- When this workspace's environment changes (new tool installed, new files added), say so and refresh skills via Settings.")
    return "\n".join(lines).rstrip() + "\n"


def _render_compile_loop_skill(profile: EnvProfile) -> str:
    p = profile
    triggers: list[str] = ["render", "compile", "pdf", "preview", "build", "make"]
    fonts_block = ""
    if p.fonts_sample:
        fonts_block = "## Fonts visible to typst\n\n" + "\n".join(
            f"- {fn}" for fn in p.fonts_sample[:25]
        ) + "\n\n"
    quarto_block = ""
    if p.has_qmd or p.has_quarto_yml:
        triggers += ["quarto", "qmd"]
        quarto_block = (
            "## Quarto rendering (detected in this workspace)\n\n"
            "Use Quarto's bundled typst, not the system typst:\n\n"
            "```bash\n"
            "quarto render <file>.qmd --to typst\n"
            "```\n\n"
            "If `_quarto.yml` pins typst formatting (font size, paper, "
            "template), respect those values — overriding them per-file "
            "is the most common source of pagination breakage.\n\n"
        )
    elif p.has_typ:
        quarto_block = (
            "## Raw Typst rendering (detected in this workspace)\n\n"
            "```bash\n"
            "SRC=path/to/doc.typ\n"
            "BASE=$(basename \"$SRC\" .typ)\n"
            "OUT=$(dirname \"$SRC\")/$BASE\n"
            "mkdir -p \"$OUT\"\n"
            "typst compile \"$SRC\" \"$OUT/$BASE.pdf\"\n"
            "typst compile --format png --ppi 144 \"$SRC\" \"$OUT/$BASE-{n}.png\"\n"
            "```\n\n"
        )
    trig_block = "\n".join(f"  - \"{t}\"" for t in triggers)
    header = (
        "---\n"
        "name: compile-loop\n"
        f"description: \"How to render documents in this workspace — toolchain detected on {time.strftime('%Y-%m-%d')}.\"\n"
        "flow: any\n"
        "auto: surface\n"
        "triggers:\n"
        f"{trig_block}\n"
        "---\n\n"
    )
    body = (
        "# Compile loop — this workspace\n\n"
        f"Workspace folder: `{p.workspace}`\n\n"
        f"Typst: `{p.typst_version or 'not installed'}` "
        f"(path `{p.typst_path or '—'}`)\n"
        f"Quarto: `{p.quarto_version or 'not installed'}` "
        f"(path `{p.quarto_path or '—'}`)\n\n"
        f"{quarto_block}"
        "## The loop\n\n"
        "1. `search_docs(detailed_brief, package)` — first tool call for any Typst question. "
        "Write a paragraph, not keywords.\n"
        "2. Validate the answer against `guides/<pkg>-<ver>/src/` (if vendored in this workspace).\n"
        "3. Write the `.typ` (or edit the `.qmd`).\n"
        "4. Compile using the recipe above. Drop artifacts into a sibling folder.\n"
        "5. `read` the PNG back. Confirm the change actually took effect.\n"
        "6. Hand off the path + a one-line summary.\n\n"
        "rc=0 ≠ correct. The compiler returning 0 means syntax was legal, not that "
        "the visual outcome matches what the user asked for. Always inspect pixels.\n\n"
        f"{fonts_block}"
    ).rstrip() + "\n"
    return header + body


def _is_user_edited(path: Path) -> bool:
    """Heuristic: skip overwrite if file shows signs of user authoring.

    We treat any non-auto-generated content (no `Auto-generated by Digi Setu`
    sentinel near the top, OR explicit `# Edited by user` marker) as user-owned.
    """
    try:
        head = path.read_text(encoding="utf-8")[:600]
    except OSError:
        return False
    if "Edited by user" in head:
        return True
    return "Auto-generated by Digi Setu" not in head


def seed_workspace_skills(workspace: Path, profile: EnvProfile, *, force: bool = False) -> None:
    """Write `.digi-setu/AGENTS.md` and `.digi-setu/skills/compile-loop/SKILL.md`.

    Respects user edits — if either file is missing our sentinel and `force` is
    False, we leave it alone.
    """
    workspace.mkdir(parents=True, exist_ok=True)
    base = workspace / ".digi-setu"
    base.mkdir(parents=True, exist_ok=True)

    agents_md = base / "AGENTS.md"
    if force or not agents_md.exists() or not _is_user_edited(agents_md):
        try:
            agents_md.write_text(_render_agents_md(profile), encoding="utf-8")
        except OSError as exc:
            print(f"[skills] could not write {agents_md}: {exc}", file=sys.stderr)

    skill_dir = base / "skills" / "compile-loop"
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_md = skill_dir / "SKILL.md"
    if force or not skill_md.exists() or not _is_user_edited(skill_md):
        try:
            skill_md.write_text(_render_compile_loop_skill(profile), encoding="utf-8")
        except OSError as exc:
            print(f"[skills] could not write {skill_md}: {exc}", file=sys.stderr)

    # Always touch a global skills dir so the user has somewhere to drop files.
    try:
        global_skills_dir().mkdir(parents=True, exist_ok=True)
    except OSError:
        pass


def needs_refresh(workspace: Path) -> bool:
    """True when AGENTS.md is missing or older than AUTO_REFRESH_AFTER_SECS."""
    target = workspace / WORKSPACE_AGENTS_MD
    if not target.exists():
        return True
    try:
        age = time.time() - target.stat().st_mtime
    except OSError:
        return True
    return age > AUTO_REFRESH_AFTER_SECS


async def ensure_workspace_skills(workspace: Path, *, force: bool = False) -> EnvProfile:
    """Probe + seed in one call. Cheap to invoke repeatedly — checks staleness."""
    if not force and not needs_refresh(workspace):
        # Still need to return *something* for callers that want the profile,
        # but skip the expensive probe.
        return EnvProfile(workspace=workspace)
    profile = await probe_env(workspace)
    seed_workspace_skills(workspace, profile, force=force)
    return profile


# ── Loader: gather skills for one turn ────────────────────────────────


def list_all_skills(workspace: Path) -> list[Skill]:
    """All skills visible to this workspace, in priority order.

    Priority (last wins on name collision): global → workspace.
    """
    skills: list[Skill] = []
    skills.extend(_scan_skills_dir(global_skills_dir(), "global"))
    skills.extend(_scan_skills_dir(workspace / WORKSPACE_SKILLS_DIR, "workspace"))
    deduped: dict[str, Skill] = {}
    for sk in skills:
        deduped[sk.name] = sk
    return list(deduped.values())


def list_skills_summary(workspace: Path) -> list[dict[str, Any]]:
    """Lightweight list for the `/api/skills` endpoint."""
    return [sk.to_dict() for sk in list_all_skills(workspace)]


def _read_agents_md(workspace: Path) -> str:
    target = workspace / WORKSPACE_AGENTS_MD
    if not target.exists():
        return ""
    try:
        return target.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _matches_trigger(prompt: str, triggers: list[str]) -> bool:
    if not triggers:
        return False
    lc = prompt.lower()
    return any(t.lower() in lc for t in triggers if t.strip())


def assemble_turn_prefix(workspace: Path, user_message: str) -> str:
    """Build the text we prepend to the user's prompt for this turn.

    Order: AGENTS.md → auto-loaded skills (flow_entry, or surface+trigger-match)
    → explicitly @-mentioned skills. Deduplicates by skill name.
    """
    chunks: list[str] = []
    agents = _read_agents_md(workspace)
    if agents:
        chunks.append(f"<workspace-agents-md>\n{agents}\n</workspace-agents-md>")

    skills = list_all_skills(workspace)
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


def _format_skill_chunk(skill: Skill) -> str:
    return (
        f"<skill name=\"{skill.name}\" source=\"{skill.source}\">\n"
        f"{skill.body}\n"
        f"</skill>"
    )


# ── Public helpers used by routes ─────────────────────────────────────


def upload_global_skill(name: str, body: str) -> Path:
    """Write a user-uploaded skill into the global skills dir."""
    safe = re.sub(r"[^a-zA-Z0-9_\-]+", "-", name.strip().lower()).strip("-")
    if not safe:
        raise ValueError("invalid skill name")
    target_dir = global_skills_dir() / safe
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "SKILL.md"
    target.write_text(body, encoding="utf-8")
    return target


def delete_global_skill(name: str) -> bool:
    safe = re.sub(r"[^a-zA-Z0-9_\-]+", "-", name.strip().lower()).strip("-")
    if not safe:
        return False
    target_dir = global_skills_dir() / safe
    if not target_dir.is_dir():
        return False
    shutil.rmtree(target_dir, ignore_errors=True)
    return True


__all__ = [
    "Skill",
    "EnvProfile",
    "parse_mentions",
    "probe_env",
    "seed_workspace_skills",
    "ensure_workspace_skills",
    "needs_refresh",
    "list_all_skills",
    "list_skills_summary",
    "assemble_turn_prefix",
    "upload_global_skill",
    "delete_global_skill",
    "global_skills_dir",
]
