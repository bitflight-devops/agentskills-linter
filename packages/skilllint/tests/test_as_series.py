"""
Test stubs for AS-series agentskills.io rule validation (AS001 through AS006).

Wave 0 TDD scaffold — all tests fail RED (ImportError) until plan 02-02
creates the skilllint.rules.as_series module.

Test IDs map to VALIDATION.md task ID 2-05-01 for traceability.
"""

from __future__ import annotations

import pathlib
import textwrap

# This import fails RED until plan 02-02 creates the module.
from skilllint.rules.as_series import check_skill_md

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def _violations_with_code(violations: list[dict], code: str) -> list[dict]:
    """Filter violations list by rule code."""
    return [v for v in violations if v.get("code") == code]


# ---------------------------------------------------------------------------
# AS001: name format — lowercase alphanumeric + hyphens only
# ---------------------------------------------------------------------------


def test_as001_name_format_valid(tmp_path: pathlib.Path):
    """name 'my-skill' passes AS001 (no violation produced)."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        textwrap.dedent("""\
            ---
            name: my-skill
            description: A valid skill description.
            ---

            Body content.
        """)
    )
    violations = check_skill_md(skill_md)
    assert _violations_with_code(violations, "AS001") == [], (
        f"Expected no AS001 violations for valid name, got: {violations}"
    )


def test_as001_name_format_invalid(tmp_path: pathlib.Path):
    """name 'My_Skill!' produces AS001 error."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        textwrap.dedent("""\
            ---
            name: My_Skill!
            description: A skill with an invalid name.
            ---

            Body content.
        """)
    )
    violations = check_skill_md(skill_md)
    assert _violations_with_code(violations, "AS001") != [], (
        "Expected AS001 violation for name 'My_Skill!'"
    )


# ---------------------------------------------------------------------------
# AS002: name matches parent directory name
# ---------------------------------------------------------------------------


def test_as002_name_matches_directory(tmp_path: pathlib.Path):
    """name 'foo' in directory 'bar/' produces AS002 error."""
    skill_dir = tmp_path / "bar"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        textwrap.dedent("""\
            ---
            name: foo
            description: Name does not match directory name bar.
            ---

            Body content.
        """)
    )
    violations = check_skill_md(skill_md)
    assert _violations_with_code(violations, "AS002") != [], (
        "Expected AS002 violation when name 'foo' does not match directory 'bar'"
    )


# ---------------------------------------------------------------------------
# AS003: description must be present and non-empty
# ---------------------------------------------------------------------------


def test_as003_description_present(tmp_path: pathlib.Path):
    """Missing description field produces AS003 error."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        textwrap.dedent("""\
            ---
            name: my-skill
            ---

            Body content.
        """)
    )
    violations = check_skill_md(skill_md)
    assert _violations_with_code(violations, "AS003") != [], (
        "Expected AS003 violation when description is missing"
    )


# ---------------------------------------------------------------------------
# AS004: description must not contain HTML tags
# ---------------------------------------------------------------------------


def test_as004_description_no_html(tmp_path: pathlib.Path):
    """description containing '<b>' produces AS004 error."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        textwrap.dedent("""\
            ---
            name: my-skill
            description: A skill with <b>bold</b> HTML in the description.
            ---

            Body content.
        """)
    )
    violations = check_skill_md(skill_md)
    assert _violations_with_code(violations, "AS004") != [], (
        "Expected AS004 violation when description contains HTML tags"
    )


# ---------------------------------------------------------------------------
# AS005: SKILL.md body length warning (> 500 lines)
# ---------------------------------------------------------------------------


def test_as005_body_length_warning(tmp_path: pathlib.Path):
    """SKILL.md body with 501 lines produces AS005 warning."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    # 501 body lines after the frontmatter
    body_lines = "\n".join(f"Line {i}" for i in range(1, 502))
    skill_md.write_text(
        textwrap.dedent("""\
            ---
            name: my-skill
            description: A skill with a very long body that exceeds 500 lines.
            ---

        """)
        + body_lines
        + "\n"
    )
    violations = check_skill_md(skill_md)
    as005 = _violations_with_code(violations, "AS005")
    assert as005 != [], "Expected AS005 warning when body exceeds 500 lines"
    assert as005[0].get("severity") in ("warning", "warn"), (
        f"Expected AS005 to be a warning, got severity: {as005[0].get('severity')}"
    )


# ---------------------------------------------------------------------------
# AS006: eval_queries.json absence info notice
# ---------------------------------------------------------------------------


def test_as006_no_eval_queries_info(tmp_path: pathlib.Path):
    """SKILL.md directory without eval_queries.json produces AS006 info."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        textwrap.dedent("""\
            ---
            name: my-skill
            description: A skill without eval queries.
            ---

            Body content.
        """)
    )
    # No eval_queries.json in skill_dir
    violations = check_skill_md(skill_md)
    as006 = _violations_with_code(violations, "AS006")
    assert as006 != [], "Expected AS006 info when eval_queries.json is absent"
    assert as006[0].get("severity") in ("info", "information"), (
        f"Expected AS006 to be info severity, got: {as006[0].get('severity')}"
    )
