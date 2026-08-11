"""Hermes Agent skill bundle conformance."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "hermes-insight"
SKILL = SKILL_DIR / "SKILL.md"


def _field(text: str, name: str) -> str:
    match = re.search(rf"(?m)^{re.escape(name)}:\s*[\"']?(.+?)[\"']?\s*$", text)
    assert match, f"missing frontmatter field: {name}"
    return match.group(1).strip().strip("\"'")


def test_skill_matches_hermes_progressive_disclosure_conventions():
    text = SKILL.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    closing = text.find("\n---\n", 4)
    assert closing > 0
    frontmatter = text[4:closing]
    body = text[closing + 5 :].strip()

    assert _field(frontmatter, "name") == "hermes-insight"
    description = _field(frontmatter, "description")
    assert len(description) <= 60
    assert description.endswith(".")
    assert _field(frontmatter, "version")
    assert _field(frontmatter, "author")
    assert _field(frontmatter, "license") == "MIT"
    assert "platforms:" in frontmatter
    assert "metadata:" in frontmatter
    assert "tags:" in frontmatter
    assert "related_skills:" in frontmatter
    assert "requires_toolsets: [hermes_insight]" in frontmatter
    assert body

    positions = [
        body.index(f"## {section}")
        for section in (
            "When to Use",
            "Prerequisites",
            "How to Run",
            "How It Works",
            "Quick Reference",
            "Procedure",
            "Pitfalls",
            "Verification",
        )
    ]
    assert positions == sorted(positions)
    assert "/home/" not in text
    assert "../" not in text
    assert "automatic_skill_write=false" in body


def test_skill_reference_and_installer_bundle_are_complete():
    text = SKILL.read_text(encoding="utf-8")
    reference = SKILL_DIR / "references" / "AGENT-GUIDE.md"
    assert reference.is_file()
    assert "references/AGENT-GUIDE.md" in text

    installer = (ROOT / "scripts" / "install_for_hermes.sh").read_text(encoding="utf-8")
    assert 'cp -a "$ROOT/skills/hermes-insight" "$SKILL_DST"' in installer
    assert "SKILL.md + references" in installer


def test_filesystem_skill_is_the_supported_teaching_surface():
    plugin = (
        ROOT / "hermes_plugin" / "hermes_insight_plugin" / "__init__.py"
    ).read_text(encoding="utf-8")
    assert 'toolset="hermes_insight"' in plugin
    assert "register_system_prompt" not in plugin
    assert "system_prompt_append" not in plugin
