"""Unit tests for skill discovery and frontmatter parsing (no API key needed)."""

from pathlib import Path

from ai_agent.config import BUNDLED_SKILLS_DIR
from ai_agent.skills import discover_skills, load_skill, split_frontmatter


def make_skill(tmp_path: Path, name: str, description: str, body: str = "Do the thing.") -> Path:
    skill_dir = tmp_path / name
    skill_dir.mkdir(parents=True)
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n{body}\n",
        encoding="utf-8",
    )
    return skill_md


def test_split_frontmatter():
    meta, body = split_frontmatter("---\nname: x\ndescription: y\n---\nBody here")
    assert meta == {"name": "x", "description": "y"}
    assert body.strip() == "Body here"


def test_split_frontmatter_without_frontmatter():
    meta, body = split_frontmatter("Just a plain file")
    assert meta == {}
    assert body == "Just a plain file"


def test_load_skill_falls_back_to_dir_name(tmp_path):
    skill_dir = tmp_path / "mystery"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("No frontmatter at all", encoding="utf-8")
    skill = load_skill(skill_dir / "SKILL.md")
    assert skill.name == "mystery"
    assert skill.description == ""


def test_discover_skills_recursive_and_override(tmp_path):
    base = tmp_path / "bundled"
    make_skill(base / "engineering", "review", "bundled version")
    user = tmp_path / "user"
    make_skill(user, "review", "user version")
    make_skill(user, "extra", "another skill")

    skills = discover_skills([base, user])
    assert set(skills) == {"review", "extra"}
    # Later directory wins on collisions.
    assert skills["review"].description == "user version"


def test_skill_body_strips_frontmatter(tmp_path):
    skill_md = make_skill(tmp_path, "demo", "a demo", body="# Heading\nSteps.")
    skill = load_skill(skill_md)
    body = skill.body()
    assert body.startswith("# Heading")
    assert "description:" not in body


def test_bundled_scrutinize_skill_loads():
    skills = discover_skills([BUNDLED_SKILLS_DIR])
    assert "scrutinize" in skills
    assert skills["scrutinize"].description
    assert "Verdict" in skills["scrutinize"].body()
