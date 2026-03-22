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
    assert _violations_with_code(violations, "AS001") != [], "Expected AS001 violation for name 'My_Skill!'"


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
    assert _violations_with_code(violations, "AS003") != [], "Expected AS003 violation when description is missing"


# ---------------------------------------------------------------------------
# AS004: description must not contain HTML tags
# ---------------------------------------------------------------------------


def test_as004_description_unquoted_colon(tmp_path: pathlib.Path):
    """description containing unquoted colon produces AS004 error."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        textwrap.dedent("""\
            ---
            name: my-skill
            description: Use this: for examples Context: testing
            ---

            Body content.
        """)
    )
    violations = check_skill_md(skill_md)
    assert _violations_with_code(violations, "AS004") != [], (
        "Expected AS004 violation when description contains unquoted colons"
    )
    # Check that fix is provided
    as004 = _violations_with_code(violations, "AS004")[0]
    assert "fix" in as004, "AS004 should provide a fix suggestion"
    assert "Wrap description in quotes" in as004["fix"]


def test_as004_angle_brackets_allowed(tmp_path: pathlib.Path):
    """description with angle brackets but no colons should NOT trigger AS004."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        textwrap.dedent("""\
            ---
            name: my-skill
            description: Use this for <testing> purposes only
            ---

            Body content.
        """)
    )
    violations = check_skill_md(skill_md)
    assert _violations_with_code(violations, "AS004") == [], "AS004 should NOT fire for angle brackets without colons"


# ---------------------------------------------------------------------------
# AS005: SKILL.md body token count warning (> TOKEN_WARNING_THRESHOLD tokens)
# ---------------------------------------------------------------------------


def test_as005_body_token_count_warning(tmp_path: pathlib.Path):
    """SKILL.md body exceeding TOKEN_WARNING_THRESHOLD tokens produces AS005 warning."""
    import tiktoken

    from skilllint.token_counter import TOKEN_WARNING_THRESHOLD

    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"

    # Build body text that exceeds TOKEN_WARNING_THRESHOLD tokens.
    # "word " is 2 tokens (word + space) in cl100k_base; repeat enough times
    # to comfortably exceed the threshold.
    enc = tiktoken.get_encoding("cl100k_base")
    unit = "The quick brown fox jumps over the lazy dog. "
    unit_tokens = len(enc.encode(unit))
    repeats = (TOKEN_WARNING_THRESHOLD // unit_tokens) + 50
    body_text = unit * repeats

    assert len(enc.encode(body_text)) > TOKEN_WARNING_THRESHOLD, (
        "Test setup: body must exceed TOKEN_WARNING_THRESHOLD tokens"
    )

    skill_md.write_text(
        textwrap.dedent("""\
            ---
            name: my-skill
            description: A skill with a very long body that exceeds the token warning threshold.
            ---

        """)
        + body_text
        + "\n"
    )
    violations = check_skill_md(skill_md)
    as005 = _violations_with_code(violations, "AS005")
    assert as005 != [], "Expected AS005 violation when body exceeds TOKEN_WARNING_THRESHOLD tokens"
    assert as005[0].get("severity") in ("warning", "warn", "error"), (
        f"Expected AS005 severity to be warning or error, got: {as005[0].get('severity')}"
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


# ---------------------------------------------------------------------------
# AS007: wildcard patterns in tools field produce an error
# ---------------------------------------------------------------------------


def _make_skill_with_tools(tmp_path: pathlib.Path, tools_block: str) -> pathlib.Path:
    """Write a minimal valid SKILL.md with the given tools: block and return its path.

    The tools_block is inserted verbatim between the description line and the
    closing '---' delimiter. It must not be indented (textwrap.dedent would
    strip indentation from the surrounding template and corrupt list items).
    """
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir(exist_ok=True)
    skill_md = skill_dir / "SKILL.md"
    content = (
        "---\n"
        "name: my-skill\n"
        "description: A skill for tools field testing.\n" + tools_block + "\n---\n\nBody content.\n"
    )
    skill_md.write_text(content)
    return skill_md


def test_as007_wildcard_in_tools_list_produces_error(tmp_path: pathlib.Path):
    """tools: list containing a wildcard entry produces AS007 error."""
    skill_md = _make_skill_with_tools(tmp_path, "tools:\n  - mcp__Ref__ref_read_url\n  - mcp__Ref__*")
    violations = check_skill_md(skill_md)
    as007 = _violations_with_code(violations, "AS007")
    assert as007 != [], "Expected AS007 violation for wildcard 'mcp__Ref__*'"
    assert as007[0]["severity"] == "error"
    assert "mcp__Ref__*" in as007[0]["message"]
    assert "fix" in as007[0]


def test_as007_wildcard_inline_tools_produces_error(tmp_path: pathlib.Path):
    """Inline comma-separated tools: containing a wildcard produces AS007 error."""
    skill_md = _make_skill_with_tools(tmp_path, "tools: mcp__Ref__ref_read_url, mcp__Ref__*")
    violations = check_skill_md(skill_md)
    as007 = _violations_with_code(violations, "AS007")
    assert as007 != [], "Expected AS007 violation for inline wildcard 'mcp__Ref__*'"
    assert as007[0]["severity"] == "error"


def test_as007_multiple_wildcards_produce_one_violation_each(tmp_path: pathlib.Path):
    """Each wildcard tool entry produces its own AS007 violation."""
    skill_md = _make_skill_with_tools(tmp_path, "tools:\n  - mcp__Ref__*\n  - mcp__*\n  - Read")
    violations = check_skill_md(skill_md)
    as007 = _violations_with_code(violations, "AS007")
    assert len(as007) == 2, f"Expected 2 AS007 violations for 2 wildcards, got: {len(as007)}"


def test_as007_explicit_tool_names_pass(tmp_path: pathlib.Path):
    """Explicit tool names without wildcards do not trigger AS007."""
    skill_md = _make_skill_with_tools(
        tmp_path, "tools:\n  - mcp__Ref__ref_read_url\n  - mcp__Ref__ref_search_documentation\n  - Bash"
    )
    violations = check_skill_md(skill_md)
    assert _violations_with_code(violations, "AS007") == [], (
        "AS007 must not fire for explicit tool names without wildcards"
    )


def test_as007_no_tools_field_passes(tmp_path: pathlib.Path):
    """SKILL.md without a tools: field produces no AS007 violation."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        textwrap.dedent("""\
            ---
            name: my-skill
            description: A skill without a tools field.
            ---

            Body content.
        """)
    )
    violations = check_skill_md(skill_md)
    assert _violations_with_code(violations, "AS007") == [], "AS007 must not fire when tools field is absent"


# ---------------------------------------------------------------------------
# AS008: MCP server discovery — exact match, case mismatch, unknown server
# ---------------------------------------------------------------------------

# Helper: write a .mcp.json in tmp_path with the given server names so that
# _discover_mcp_servers() finds them when scanning skill files under tmp_path.


def _write_mcp_json(directory: pathlib.Path, *server_names: str) -> None:
    """Write a .mcp.json containing the given server names into *directory*."""
    import json

    mcp_config = {"mcpServers": {name: {} for name in server_names}}
    (directory / ".mcp.json").write_text(json.dumps(mcp_config))


def test_as008_exact_match_discovered_server_passes(tmp_path: pathlib.Path):
    """Exact server name match against .mcp.json discovery produces no AS008 violation."""
    _write_mcp_json(tmp_path, "Ref")
    skill_md = _make_skill_with_tools(tmp_path, "tools:\n  - mcp__Ref__ref_search_documentation")
    violations = check_skill_md(skill_md)
    assert _violations_with_code(violations, "AS008") == [], (
        "AS008 must not fire when server 'Ref' exactly matches .mcp.json discovery"
    )


def test_as008_case_mismatch_with_discovered_server_produces_error(tmp_path: pathlib.Path):
    """Wrong-case server name against a discovered server produces AS008 error."""
    # .mcp.json declares 'Ref'; skill uses 'ref' (lowercase) — case mismatch
    _write_mcp_json(tmp_path, "Ref")
    skill_md = _make_skill_with_tools(tmp_path, "tools:\n  - mcp__ref__ref_search_documentation")
    violations = check_skill_md(skill_md)
    as008 = _violations_with_code(violations, "AS008")
    assert as008 != [], "Expected AS008 error for case mismatch 'mcp__ref__' vs discovered 'Ref'"
    assert as008[0]["severity"] == "error"
    assert "Ref" in as008[0]["message"], "AS008 message must show the correct canonical server name"
    assert "fix" in as008[0]


def test_as008_unknown_server_not_in_any_config_produces_warning(tmp_path: pathlib.Path):
    """MCP tool referencing a server absent from all config files produces AS008 warning."""
    # No .mcp.json written — server is entirely unknown
    skill_md = _make_skill_with_tools(tmp_path, "tools:\n  - mcp__someUnknownServer__some_tool")
    violations = check_skill_md(skill_md)
    as008 = _violations_with_code(violations, "AS008")
    assert as008 != [], "Expected AS008 warning for server not found in any config"
    assert as008[0]["severity"] == "warning"
    assert "someUnknownServer" in as008[0]["message"]


# ---------------------------------------------------------------------------
# AsSeriesValidator integration — agent file wiring
# ---------------------------------------------------------------------------
# These tests verify that AS007 and AS008 fire when AsSeriesValidator is used
# via the default validate_single_path code path (not --platform).
# AS002 must be suppressed for agent files because agents live directly in
# agents/ — the parent directory name is always "agents", not the agent name.
# ---------------------------------------------------------------------------


def _make_agent_md(tmp_path: pathlib.Path, tools_yaml: str) -> pathlib.Path:
    """Create an agents/bad-agent.md fixture under tmp_path.

    Args:
        tmp_path: Pytest temporary directory.
        tools_yaml: Raw YAML line(s) for the tools field (e.g. "tools: mcp__Ref__*").

    Returns:
        Path to the created agent .md file.
    """
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir(exist_ok=True)
    agent_md = agents_dir / "bad-agent.md"
    agent_md.write_text(
        textwrap.dedent(f"""\
            ---
            name: bad-agent
            description: Test agent for AsSeriesValidator integration.
            {tools_yaml}
            ---

            Agent body.
        """)
    )
    return agent_md


def test_as007_fires_on_agent_file_with_wildcard_via_validator(tmp_path: pathlib.Path):
    """AsSeriesValidator surfaces AS007 for wildcard tools on an agent .md file.

    This verifies the wiring in _get_validators_for_path: agent files must
    have AsSeriesValidator in their validator list so AS007 fires without
    requiring --platform.
    """
    from skilllint.plugin_validator import AsSeriesValidator

    agent_md = _make_agent_md(tmp_path, "tools: mcp__Ref__*, Read, Bash")
    result = AsSeriesValidator().validate(agent_md)
    codes = [i.field for i in result.errors + result.warnings + result.info]
    assert "AS007" in codes, f"Expected AS007 in AsSeriesValidator output for wildcard tool, got: {codes}"
    assert not result.passed, "AsSeriesValidator must not pass when a wildcard tool is present"


def test_as002_suppressed_for_agent_files_via_validator(tmp_path: pathlib.Path):
    """AsSeriesValidator does not emit AS002 for agent files.

    AS002 compares the name field against the parent directory name. For agents
    the parent is always 'agents/', which never matches the agent name. The
    validator must suppress AS002 for non-SKILL.md files to avoid false positives.
    """
    from skilllint.plugin_validator import AsSeriesValidator

    agent_md = _make_agent_md(tmp_path, "tools: Read")
    result = AsSeriesValidator().validate(agent_md)
    codes = [i.field for i in result.errors + result.warnings + result.info]
    assert "AS002" not in codes, f"AS002 must not fire for agent files, got: {codes}"


def test_as002_still_fires_for_skill_md_name_mismatch(tmp_path: pathlib.Path):
    """AsSeriesValidator emits AS002 for a SKILL.md whose name mismatches its directory.

    AS002 suppression must only apply to agent files. SKILL.md files in a
    directory named differently from their name field must still get AS002.
    """
    from skilllint.plugin_validator import AsSeriesValidator

    skill_dir = tmp_path / "wrong-dir"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        textwrap.dedent("""\
            ---
            name: correct-name
            description: A skill whose directory name does not match.
            ---

            Body content.
        """)
    )
    result = AsSeriesValidator().validate(skill_md)
    codes = [i.field for i in result.errors + result.warnings + result.info]
    assert "AS002" in codes, f"AS002 must still fire for SKILL.md with name/directory mismatch, got: {codes}"


def test_as008_hyphen_vs_underscore_unrecognized_server_produces_warning(tmp_path: pathlib.Path):
    """mcp__sequential-thinking__ is not a case-fold match for 'sequential_thinking' — produces AS008 warning."""
    # 'sequential-thinking' (hyphen) vs 'sequential_thinking' (underscore) differ by more than
    # case — case-folding won't unify them, so it falls through to "unknown server → warning".
    _write_mcp_json(tmp_path, "sequential_thinking")
    skill_md = _make_skill_with_tools(tmp_path, "tools:\n  - mcp__sequential-thinking__sequentialthinking")
    violations = check_skill_md(skill_md)
    as008 = _violations_with_code(violations, "AS008")
    assert as008 != [], "Expected AS008 warning for 'mcp__sequential-thinking__' (not a case-fold match)"
    assert as008[0]["severity"] == "warning"
    assert "sequential-thinking" in as008[0]["message"]


def test_as008_correct_server_with_discovered_context_passes(tmp_path: pathlib.Path):
    """Correct server name when that server is in .mcp.json produces no AS008 violation."""
    _write_mcp_json(tmp_path, "sequential_thinking")
    skill_md = _make_skill_with_tools(tmp_path, "tools:\n  - mcp__sequential_thinking__sequentialthinking")
    violations = check_skill_md(skill_md)
    assert _violations_with_code(violations, "AS008") == [], (
        "AS008 must not fire when server name exactly matches discovered 'sequential_thinking'"
    )


def test_as008_mixed_exact_and_case_mismatch_produces_one_error(tmp_path: pathlib.Path):
    """One case-mismatched and one correct tool produces exactly one AS008 violation."""
    _write_mcp_json(tmp_path, "Ref")
    skill_md = _make_skill_with_tools(
        tmp_path, "tools:\n  - mcp__ref__ref_read_url\n  - mcp__Ref__ref_search_documentation\n  - Bash"
    )
    violations = check_skill_md(skill_md)
    as008 = _violations_with_code(violations, "AS008")
    assert len(as008) == 1, f"Expected exactly 1 AS008 violation (the case mismatch), got: {len(as008)}"
    assert "mcp__ref__ref_read_url" in as008[0]["message"]


def test_as008_non_mcp_tools_are_ignored(tmp_path: pathlib.Path):
    """Non-MCP tool names (Bash, Read, Write) never trigger AS008."""
    skill_md = _make_skill_with_tools(tmp_path, "tools:\n  - Bash\n  - Read\n  - Write\n  - Edit")
    violations = check_skill_md(skill_md)
    assert _violations_with_code(violations, "AS008") == [], "AS008 must not fire for non-MCP tool names"
