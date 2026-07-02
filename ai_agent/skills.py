"""Skill discovery — Claude-Code-compatible SKILL.md folders.

A skill is a directory containing a SKILL.md file with YAML frontmatter:

    ---
    name: scrutinize
    description: Review a plan/PR/change with an outsider's eye.
    ---
    ...full instructions (loaded on demand)...

This matches the convention used by thananon/9arm-skills and Anthropic's
Agent Skills, so those skill folders can be dropped into any configured
skills directory.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class Skill:
    name: str
    description: str
    path: Path  # path to SKILL.md

    @property
    def directory(self) -> Path:
        return self.path.parent

    def body(self) -> str:
        """Full SKILL.md content minus the frontmatter block."""
        text = self.path.read_text(encoding="utf-8")
        _, body = split_frontmatter(text)
        return body.strip()


def split_frontmatter(text: str) -> tuple[dict, str]:
    """Return (frontmatter dict, body). Tolerates files without frontmatter."""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            meta = yaml.safe_load(parts[1]) or {}
            if isinstance(meta, dict):
                return meta, parts[2]
    return {}, text


def load_skill(skill_md: Path) -> Skill | None:
    try:
        meta, _ = split_frontmatter(skill_md.read_text(encoding="utf-8"))
    except OSError:
        return None
    name = str(meta.get("name") or skill_md.parent.name)
    description = str(meta.get("description") or "").strip()
    return Skill(name=name, description=description, path=skill_md)


def discover_skills(dirs: list[Path]) -> dict[str, Skill]:
    """Scan each directory recursively for */SKILL.md.

    Recursion supports collections that group skills under categories
    (e.g. 9arm-skills' skills/engineering/scrutinize/SKILL.md).
    Later directories win on name collisions, so a user dir can override
    a bundled skill.
    """
    found: dict[str, Skill] = {}
    for base in dirs:
        if not base.is_dir():
            continue
        for skill_md in sorted(base.rglob("SKILL.md")):
            skill = load_skill(skill_md)
            if skill is not None:
                found[skill.name] = skill
    return found
