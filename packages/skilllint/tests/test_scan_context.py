"""Unit tests for ScanContext, KNOWN_PROVIDER_DIRS, PLUGIN_FILTER_TYPE_MAP, and detect_scan_context.

Coverage scope:
- detect_scan_context: All three return values (PLUGIN, PROVIDER, BARE) and precedence
- KNOWN_PROVIDER_DIRS: Type and membership
- PLUGIN_FILTER_TYPE_MAP: Keys, values, and no-recursion invariant
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from skilllint.scan_runtime import (
    KNOWN_PROVIDER_DIRS,
    PLUGIN_FILTER_TYPE_MAP,
    PluginManifest,
    ScanContext,
    _discover_plugin_paths,
    _discover_provider_paths,
    _discover_validatable_paths,
    _parse_plugin_manifest,
    _resolve_filter_and_expand_paths,
    detect_scan_context,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestDetectScanContext:
    """Tests for detect_scan_context() context classification.

    Strategy: exercise each branch of the decision tree using real filesystem
    structures via tmp_path.  No mocking — the function only tests path
    existence and directory name, so real paths are the simplest approach.
    """

    def test_plugin_json_presence_yields_plugin_context(self, tmp_path: Path) -> None:
        """Directory with .claude-plugin/plugin.json is classified as PLUGIN.

        Tests: detect_scan_context PLUGIN branch
        How: Create .claude-plugin/plugin.json inside tmp_path, then call detect_scan_context
        Why: Plugin directories must be distinguished from bare or provider dirs
             so validators know to apply plugin-specific rules
        """
        # Arrange
        (tmp_path / ".claude-plugin").mkdir()
        (tmp_path / ".claude-plugin" / "plugin.json").write_text("{}")

        # Act
        result = detect_scan_context(tmp_path)

        # Assert
        assert result == ScanContext.PLUGIN

    def test_dot_claude_directory_name_yields_provider_context(self, tmp_path: Path) -> None:
        """A directory named .claude is classified as PROVIDER.

        Tests: detect_scan_context PROVIDER branch for .claude
        How: Create a .claude subdirectory and pass it to detect_scan_context
        Why: Claude Code stores provider-level agents/skills inside .claude;
             validators apply provider rules there
        """
        # Arrange
        provider_dir = tmp_path / ".claude"
        provider_dir.mkdir()

        # Act
        result = detect_scan_context(provider_dir)

        # Assert
        assert result == ScanContext.PROVIDER

    def test_dot_cursor_directory_name_yields_provider_context(self, tmp_path: Path) -> None:
        """A directory named .cursor is classified as PROVIDER.

        Tests: detect_scan_context PROVIDER branch for .cursor
        How: Create a .cursor directory and call detect_scan_context on it
        Why: Cursor stores its agents inside .cursor; must be treated as a provider
        """
        # Arrange
        provider_dir = tmp_path / ".cursor"
        provider_dir.mkdir()

        # Act
        result = detect_scan_context(provider_dir)

        # Assert
        assert result == ScanContext.PROVIDER

    def test_dot_gemini_directory_name_yields_provider_context(self, tmp_path: Path) -> None:
        """A directory named .gemini is classified as PROVIDER.

        Tests: detect_scan_context PROVIDER branch for .gemini
        How: Create a .gemini directory and call detect_scan_context on it
        Why: Gemini stores its context files inside .gemini; treated as a provider
        """
        # Arrange
        provider_dir = tmp_path / ".gemini"
        provider_dir.mkdir()

        # Act
        result = detect_scan_context(provider_dir)

        # Assert
        assert result == ScanContext.PROVIDER

    def test_dot_codex_directory_name_yields_provider_context(self, tmp_path: Path) -> None:
        """A directory named .codex is classified as PROVIDER.

        Tests: detect_scan_context PROVIDER branch for .codex
        How: Create a .codex directory and call detect_scan_context on it
        Why: Codex provider directories must receive provider-level validation
        """
        # Arrange
        provider_dir = tmp_path / ".codex"
        provider_dir.mkdir()

        # Act
        result = detect_scan_context(provider_dir)

        # Assert
        assert result == ScanContext.PROVIDER

    def test_regular_directory_yields_bare_context(self, tmp_path: Path) -> None:
        """A regular directory (no plugin marker, no provider name) is BARE.

        Tests: detect_scan_context BARE fallback branch
        How: Pass an empty tmp_path with no special markers or name
        Why: Bare directories trigger generic scan discovery rules, not
             plugin- or provider-specific rules
        """
        # Arrange — tmp_path is already a plain directory with no markers

        # Act
        result = detect_scan_context(tmp_path)

        # Assert
        assert result == ScanContext.BARE

    def test_plugin_json_takes_precedence_over_provider_name(self, tmp_path: Path) -> None:
        """PLUGIN classification wins over PROVIDER when plugin.json exists inside a provider dir.

        Tests: detect_scan_context precedence — PLUGIN check runs before PROVIDER check
        How: Create a .claude subdirectory that also contains .claude-plugin/plugin.json,
             then call detect_scan_context on that subdirectory
        Why: A plugin installed inside a provider directory should be validated as a
             plugin, not as a bare provider tree — precedence must be deterministic
        """
        # Arrange
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / ".claude-plugin").mkdir()
        (claude_dir / ".claude-plugin" / "plugin.json").write_text("{}")

        # Act
        result = detect_scan_context(claude_dir)

        # Assert
        assert result == ScanContext.PLUGIN

    def test_plugin_json_directory_without_file_is_bare(self, tmp_path: Path) -> None:
        """A .claude-plugin directory that lacks plugin.json does not trigger PLUGIN.

        Tests: detect_scan_context does not false-positive on partial plugin structure
        How: Create only the .claude-plugin directory without plugin.json inside it
        Why: The classifier checks for the json file specifically; the dir alone is
             not sufficient evidence of a plugin
        """
        # Arrange
        (tmp_path / ".claude-plugin").mkdir()
        # Intentionally do NOT create plugin.json

        # Act
        result = detect_scan_context(tmp_path)

        # Assert
        assert result == ScanContext.BARE


class TestKnownProviderDirs:
    """Tests for the KNOWN_PROVIDER_DIRS constant.

    Strategy: verify type, immutability, and membership for every expected value.
    These tests act as a contract — if a provider is removed or renamed, a test
    will fail and force an explicit review.
    """

    def test_is_frozenset(self) -> None:
        """KNOWN_PROVIDER_DIRS is a frozenset.

        Tests: KNOWN_PROVIDER_DIRS type
        How: isinstance check
        Why: frozenset communicates immutability and enables O(1) membership tests
        """
        assert isinstance(KNOWN_PROVIDER_DIRS, frozenset)

    def test_contains_dot_claude(self) -> None:
        """KNOWN_PROVIDER_DIRS includes .claude.

        Tests: .claude membership
        How: in operator
        Why: .claude is the primary Claude Code provider directory
        """
        assert ".claude" in KNOWN_PROVIDER_DIRS

    def test_contains_dot_cursor(self) -> None:
        """KNOWN_PROVIDER_DIRS includes .cursor.

        Tests: .cursor membership
        How: in operator
        Why: .cursor is the Cursor IDE provider directory
        """
        assert ".cursor" in KNOWN_PROVIDER_DIRS

    def test_contains_dot_gemini(self) -> None:
        """KNOWN_PROVIDER_DIRS includes .gemini.

        Tests: .gemini membership
        How: in operator
        Why: .gemini is the Google Gemini provider directory
        """
        assert ".gemini" in KNOWN_PROVIDER_DIRS

    def test_contains_dot_codex(self) -> None:
        """KNOWN_PROVIDER_DIRS includes .codex.

        Tests: .codex membership
        How: in operator
        Why: .codex is the Codex provider directory
        """
        assert ".codex" in KNOWN_PROVIDER_DIRS


class TestPluginFilterTypeMap:
    """Tests for the PLUGIN_FILTER_TYPE_MAP constant.

    Strategy: verify required keys exist, patterns match specification, and
    no pattern uses ** recursion (which would allow crossing skill boundaries).
    """

    def test_contains_agents_key(self) -> None:
        """PLUGIN_FILTER_TYPE_MAP has an 'agents' entry.

        Tests: agents key presence
        How: in operator
        Why: The --filter-type=agents path must resolve for plugin roots
        """
        assert "agents" in PLUGIN_FILTER_TYPE_MAP

    def test_contains_skills_key(self) -> None:
        """PLUGIN_FILTER_TYPE_MAP has a 'skills' entry.

        Tests: skills key presence
        How: in operator
        Why: The --filter-type=skills path must resolve for plugin roots
        """
        assert "skills" in PLUGIN_FILTER_TYPE_MAP

    def test_contains_commands_key(self) -> None:
        """PLUGIN_FILTER_TYPE_MAP has a 'commands' entry.

        Tests: commands key presence
        How: in operator
        Why: The --filter-type=commands path must resolve for plugin roots
        """
        assert "commands" in PLUGIN_FILTER_TYPE_MAP

    def test_agents_pattern_is_root_only(self) -> None:
        """PLUGIN_FILTER_TYPE_MAP['agents'] uses the root-only glob agents/*.md.

        Tests: agents pattern value
        How: equality check
        Why: Plugin agent discovery must not recurse into skills/*/agents/ to
             avoid matching skill-internal agent definitions
        """
        assert PLUGIN_FILTER_TYPE_MAP["agents"] == "agents/*.md"

    def test_skills_pattern_is_root_only(self) -> None:
        """PLUGIN_FILTER_TYPE_MAP['skills'] uses the root-only glob skills/*/SKILL.md.

        Tests: skills pattern value
        How: equality check
        Why: Plugin skill discovery must not recurse deeper than one level
        """
        assert PLUGIN_FILTER_TYPE_MAP["skills"] == "skills/*/SKILL.md"

    def test_commands_pattern_is_root_only(self) -> None:
        """PLUGIN_FILTER_TYPE_MAP['commands'] uses the root-only glob commands/*.md.

        Tests: commands pattern value
        How: equality check
        Why: Plugin command discovery must not recurse into subdirectories
        """
        assert PLUGIN_FILTER_TYPE_MAP["commands"] == "commands/*.md"

    @pytest.mark.parametrize("key", ["agents", "skills", "commands"])
    def test_no_pattern_uses_double_star_recursion(self, key: str) -> None:
        """No PLUGIN_FILTER_TYPE_MAP pattern uses ** recursion.

        Tests: absence of ** in all plugin filter patterns
        How: Check each pattern string for the ** glob operator
        Why: Recursive globs in plugin filter patterns would match files inside
             nested skill directories, violating the plugin boundary contract
        """
        pattern = PLUGIN_FILTER_TYPE_MAP[key]
        assert "**" not in pattern, f"Pattern for {key!r} ({pattern!r}) must not use ** recursion"


class TestPluginManifest:
    """Tests for the PluginManifest dataclass property and immutability.

    Strategy: verify the is_manifest_driven property logic for each field
    independently, confirm all-None produces False, and verify the dataclass
    is frozen so callers cannot mutate it after construction.
    """

    def test_all_none_fields_is_not_manifest_driven(self, tmp_path: Path) -> None:
        """PluginManifest with all None fields reports is_manifest_driven as False.

        Tests: PluginManifest.is_manifest_driven property — all-None branch
        How: Construct PluginManifest with only plugin_root set, check property
        Why: A manifest with no declared entries is indistinguishable from an
             absent manifest; callers must not treat it as manifest-driven
        """
        # Arrange
        m = PluginManifest(plugin_root=tmp_path)

        # Act / Assert
        assert m.is_manifest_driven is False

    def test_agents_field_set_is_manifest_driven(self, tmp_path: Path) -> None:
        """PluginManifest with agents list set reports is_manifest_driven as True.

        Tests: PluginManifest.is_manifest_driven — agents branch
        How: Construct with agents=["agents/main.md"], check property
        Why: A non-None agents list signals an explicit manifest declaration
        """
        # Arrange
        m = PluginManifest(plugin_root=tmp_path, agents=["agents/main.md"])

        # Act / Assert
        assert m.is_manifest_driven is True

    def test_commands_field_set_is_manifest_driven(self, tmp_path: Path) -> None:
        """PluginManifest with commands list set reports is_manifest_driven as True.

        Tests: PluginManifest.is_manifest_driven — commands branch
        How: Construct with commands=["commands/run.md"], check property
        Why: A non-None commands list signals an explicit manifest declaration
        """
        # Arrange
        m = PluginManifest(plugin_root=tmp_path, commands=["commands/run.md"])

        # Act / Assert
        assert m.is_manifest_driven is True

    def test_skills_field_set_is_manifest_driven(self, tmp_path: Path) -> None:
        """PluginManifest with skills list set reports is_manifest_driven as True.

        Tests: PluginManifest.is_manifest_driven — skills branch
        How: Construct with skills=["skills/my-skill"], check property
        Why: A non-None skills list signals an explicit manifest declaration
        """
        # Arrange
        m = PluginManifest(plugin_root=tmp_path, skills=["skills/my-skill"])

        # Act / Assert
        assert m.is_manifest_driven is True

    def test_manifest_is_frozen(self, tmp_path: Path) -> None:
        """PluginManifest raises on attribute mutation after construction.

        Tests: PluginManifest immutability (frozen dataclass)
        How: Attempt to assign to m.agents after construction; expect AttributeError or TypeError
        Why: Frozen dataclasses prevent accidental state mutation; callers must
             construct a new instance rather than modifying an existing one
        """
        # Arrange
        m = PluginManifest(plugin_root=tmp_path)

        # Act / Assert
        with pytest.raises((AttributeError, TypeError)):
            m.agents = ["should_fail"]  # ty: ignore[invalid-assignment]


class TestParsePluginManifest:
    """Tests for _parse_plugin_manifest() JSON parsing and error handling.

    Strategy: use real file I/O via tmp_path for all cases — no mocking.
    Covers the happy path (full JSON, partial JSON), absent file, invalid
    JSON, and the critical absent-key-is-None-not-empty-list invariant.
    """

    def test_full_plugin_json_populates_all_fields(self, tmp_path: Path) -> None:
        """plugin.json with all three keys populates agents, commands, and skills.

        Tests: _parse_plugin_manifest — full JSON happy path
        How: Write plugin.json with agents/commands/skills arrays, parse, assert all fields
        Why: Full manifests must round-trip without loss
        """
        # Arrange
        (tmp_path / ".claude-plugin").mkdir()
        (tmp_path / ".claude-plugin" / "plugin.json").write_text(
            '{"agents": ["agents/main.md"], "commands": ["commands/run.md"], "skills": ["skills/review"]}'
        )

        # Act
        manifest = _parse_plugin_manifest(tmp_path)

        # Assert
        assert manifest.agents == ["agents/main.md"]
        assert manifest.commands == ["commands/run.md"]
        assert manifest.skills == ["skills/review"]

    def test_empty_plugin_json_returns_all_none_fields(self, tmp_path: Path) -> None:
        """plugin.json with empty object {} produces all-None fields.

        Tests: _parse_plugin_manifest — empty JSON object
        How: Write plugin.json containing {}, parse, assert all three fields are None
        Why: An empty manifest must not invent empty lists; None signals absence
        """
        # Arrange
        (tmp_path / ".claude-plugin").mkdir()
        (tmp_path / ".claude-plugin" / "plugin.json").write_text("{}")

        # Act
        manifest = _parse_plugin_manifest(tmp_path)

        # Assert
        assert manifest.agents is None
        assert manifest.commands is None
        assert manifest.skills is None

    def test_partial_plugin_json_only_agents_populates_agents(self, tmp_path: Path) -> None:
        """plugin.json with only agents key populates agents and leaves others None.

        Tests: _parse_plugin_manifest — partial JSON (agents only)
        How: Write JSON with agents key only, parse, assert agents populated and
             commands/skills are None
        Why: Partial manifests are valid; absent keys must not default to []
        """
        # Arrange
        (tmp_path / ".claude-plugin").mkdir()
        (tmp_path / ".claude-plugin" / "plugin.json").write_text('{"agents": ["agents/x.md"]}')

        # Act
        manifest = _parse_plugin_manifest(tmp_path)

        # Assert
        assert manifest.agents == ["agents/x.md"]
        assert manifest.commands is None
        assert manifest.skills is None

    def test_missing_plugin_json_returns_all_none_manifest(self, tmp_path: Path) -> None:
        """Absent .claude-plugin/plugin.json produces all-None fields and preserves plugin_root.

        Tests: _parse_plugin_manifest — missing file branch
        How: Call with tmp_path that has no .claude-plugin directory at all
        Why: Missing manifest is a valid state; function must not raise and must
             return a usable PluginManifest with the original root preserved
        """
        # Arrange — tmp_path has no .claude-plugin directory

        # Act
        manifest = _parse_plugin_manifest(tmp_path)

        # Assert
        assert manifest.agents is None
        assert manifest.commands is None
        assert manifest.skills is None
        assert manifest.plugin_root == tmp_path

    def test_invalid_json_returns_all_none_manifest(self, tmp_path: Path) -> None:
        """Malformed plugin.json produces all-None fields without raising.

        Tests: _parse_plugin_manifest — invalid JSON error handling
        How: Write syntactically invalid JSON, parse, assert all fields are None
        Why: A corrupt manifest must not crash the scan; the function must degrade
             gracefully so valid skills in the same plugin still get validated
        """
        # Arrange
        (tmp_path / ".claude-plugin").mkdir()
        (tmp_path / ".claude-plugin" / "plugin.json").write_text("NOT VALID JSON {{{")

        # Act
        manifest = _parse_plugin_manifest(tmp_path)

        # Assert
        assert manifest.agents is None
        assert manifest.commands is None
        assert manifest.skills is None

    def test_absent_keys_are_none_not_empty_list(self, tmp_path: Path) -> None:
        """Missing keys in plugin.json produce None, not an empty list.

        Tests: _parse_plugin_manifest — absent-key-is-None invariant
        How: Write JSON with only skills key, parse, assert agents and commands are None
             (not []) and skills is populated
        Why: Callers distinguish "key absent" from "key present but empty" via None vs [].
             An empty list would incorrectly signal that the manifest declared zero entries.
        """
        # Arrange
        (tmp_path / ".claude-plugin").mkdir()
        (tmp_path / ".claude-plugin" / "plugin.json").write_text('{"skills": ["skills/foo"]}')

        # Act
        manifest = _parse_plugin_manifest(tmp_path)

        # Assert
        assert manifest.agents is None  # absent, not []
        assert manifest.commands is None  # absent, not []
        assert manifest.skills == ["skills/foo"]


class TestDiscoverProviderPaths:
    """Tests for _discover_provider_paths() file discovery in provider directories.

    Strategy: use real file I/O via tmp_path for all cases — no mocking.
    Covers discovery of agents/**/*.md files, exclusion of non-agent directories,
    exclusion of non-markdown files, and sort order of the returned list.
    """

    def test_discovers_agent_in_agents_dir(self, tmp_path: Path) -> None:
        """A .md file directly inside agents/ is returned.

        Tests: _discover_provider_paths — agents/*.md discovery
        How: Create agents/my-agent.md in tmp_path, call function, assert path present
        Why: Provider directories store agents under agents/; the function must find them
        """
        # Arrange
        (tmp_path / "agents").mkdir()
        (tmp_path / "agents" / "my-agent.md").write_text("# Agent")

        # Act
        result = _discover_provider_paths(tmp_path)

        # Assert
        assert tmp_path / "agents" / "my-agent.md" in result

    def test_discovers_nested_agent_in_agents_subdir(self, tmp_path: Path) -> None:
        """agents/**/*.md discovers .md files nested inside agents/ subdirectories.

        Tests: _discover_provider_paths — recursive agents/**/*.md discovery
        How: Create agents/subdir/nested-agent.md, call function, assert path present
        Why: Providers may organise agents into subdirectories; ** recursion must find them
        """
        # Arrange
        (tmp_path / "agents" / "subdir").mkdir(parents=True)
        (tmp_path / "agents" / "subdir" / "nested-agent.md").write_text("# Nested")

        # Act
        result = _discover_provider_paths(tmp_path)

        # Assert
        assert tmp_path / "agents" / "subdir" / "nested-agent.md" in result

    def test_does_not_discover_commands(self, tmp_path: Path) -> None:
        """Provider path discovery does not include files from commands/.

        Tests: _discover_provider_paths — commands/ directory excluded
        How: Create commands/something.md, call function, assert path absent
        Why: The function only globs agents/**/*.md; commands/ is a distinct concept
             and must not be mixed into the provider agent list
        """
        # Arrange
        (tmp_path / "commands").mkdir()
        (tmp_path / "commands" / "something.md").write_text("# Cmd")

        # Act
        result = _discover_provider_paths(tmp_path)

        # Assert
        assert tmp_path / "commands" / "something.md" not in result

    def test_empty_provider_directory_returns_empty_list(self, tmp_path: Path) -> None:
        """A provider directory with no agents/ subdirectory returns an empty list.

        Tests: _discover_provider_paths — empty directory branch
        How: Call function on bare tmp_path with no children, assert result is []
        Why: Callers must receive an empty list (not None or exception) when no
             agents are present so iteration is always safe
        """
        # Arrange — tmp_path is empty

        # Act
        result = _discover_provider_paths(tmp_path)

        # Assert
        assert result == []

    def test_non_md_files_in_agents_dir_excluded(self, tmp_path: Path) -> None:
        """Non-.md files inside agents/ are not returned.

        Tests: _discover_provider_paths — .md extension filter
        How: Create agents/notes.txt, call function, assert path absent
        Why: The glob pattern is agents/**/*.md; only markdown files are valid
             agent definitions and non-markdown files must be ignored
        """
        # Arrange
        (tmp_path / "agents").mkdir()
        (tmp_path / "agents" / "notes.txt").write_text("text")

        # Act
        result = _discover_provider_paths(tmp_path)

        # Assert
        assert tmp_path / "agents" / "notes.txt" not in result

    def test_result_is_sorted(self, tmp_path: Path) -> None:
        """Returned paths are in sorted order regardless of filesystem order.

        Tests: _discover_provider_paths — sort guarantee
        How: Create agents/z.md and agents/a.md (reverse alphabetical), call function,
             assert result equals sorted(result)
        Why: Deterministic ordering ensures stable output across runs and platforms,
             preventing non-reproducible validator behaviour
        """
        # Arrange
        (tmp_path / "agents").mkdir()
        (tmp_path / "agents" / "z.md").write_text("Z")
        (tmp_path / "agents" / "a.md").write_text("A")

        # Act
        result = _discover_provider_paths(tmp_path)

        # Assert
        assert result == sorted(result)


class TestDiscoverPluginPaths:
    """Tests for _discover_plugin_paths() file discovery in plugin directories.

    Strategy: use real file I/O via tmp_path for all cases — no mocking.
    Covers convention-driven discovery (no manifest declarations), manifest-driven
    discovery (exact declared paths only), exclusion of skill-internal agent and
    command directories, and the sort/deduplication invariants of the return value.
    """

    # --- Convention-driven mode ---

    def test_convention_driven_discovers_root_agents(self, tmp_path: Path) -> None:
        """Convention mode discovers .md files directly under agents/.

        Tests: _discover_plugin_paths — convention-driven agents/*.md discovery
        How: Create agents/a.md and agents/b.md, pass all-None manifest, assert both paths present
        Why: Root-level agents/ is the primary plugin agent location; must be found
             without a manifest declaration
        """
        # Arrange
        (tmp_path / "agents").mkdir()
        (tmp_path / "agents" / "a.md").write_text("# A")
        (tmp_path / "agents" / "b.md").write_text("# B")
        manifest = PluginManifest(plugin_root=tmp_path)

        # Act
        result = _discover_plugin_paths(manifest)

        # Assert
        assert tmp_path / "agents" / "a.md" in result
        assert tmp_path / "agents" / "b.md" in result

    def test_convention_driven_discovers_commands(self, tmp_path: Path) -> None:
        """Convention mode discovers .md files directly under commands/.

        Tests: _discover_plugin_paths — convention-driven commands/*.md discovery
        How: Create commands/run.md, pass all-None manifest, assert path present
        Why: Root-level commands/ is the standard location for plugin command definitions
        """
        # Arrange
        (tmp_path / "commands").mkdir()
        (tmp_path / "commands" / "run.md").write_text("# Run")
        manifest = PluginManifest(plugin_root=tmp_path)

        # Act
        result = _discover_plugin_paths(manifest)

        # Assert
        assert tmp_path / "commands" / "run.md" in result

    def test_convention_driven_discovers_skill_md(self, tmp_path: Path) -> None:
        """Convention mode discovers SKILL.md files one level inside skills/.

        Tests: _discover_plugin_paths — convention-driven skills/*/SKILL.md discovery
        How: Create skills/my-skill/SKILL.md, pass all-None manifest, assert path present
        Why: The skills/*/SKILL.md pattern is the canonical skill entry point
        """
        # Arrange
        (tmp_path / "skills" / "my-skill").mkdir(parents=True)
        (tmp_path / "skills" / "my-skill" / "SKILL.md").write_text("# Skill")
        manifest = PluginManifest(plugin_root=tmp_path)

        # Act
        result = _discover_plugin_paths(manifest)

        # Assert
        assert tmp_path / "skills" / "my-skill" / "SKILL.md" in result

    def test_convention_driven_excludes_skill_internal_agents(self, tmp_path: Path) -> None:
        """Core false-positive scenario: skills/*/agents/ must never be discovered.

        Tests: _discover_plugin_paths — exclusion of skill-internal agents directories
        How: Create skills/my-skill/agents/helper.md, pass all-None manifest,
             assert that path is absent from the result
        Why: Plugin-level agents/*.md glob is root-only; skill-internal agent definitions
             are implementation details of a skill, not top-level plugin agents.
             Discovering them would produce false PA001/FM001 violations on skill agents.
        """
        # Arrange
        (tmp_path / "skills" / "my-skill" / "agents").mkdir(parents=True)
        (tmp_path / "skills" / "my-skill" / "agents" / "helper.md").write_text("# Helper")
        manifest = PluginManifest(plugin_root=tmp_path)

        # Act
        result = _discover_plugin_paths(manifest)

        # Assert
        assert tmp_path / "skills" / "my-skill" / "agents" / "helper.md" not in result

    def test_convention_driven_excludes_skill_internal_commands(self, tmp_path: Path) -> None:
        """Skill-internal commands/ directories must not be discovered in convention mode.

        Tests: _discover_plugin_paths — exclusion of skills/*/commands/ paths
        How: Create skills/my-skill/commands/internal.md, pass all-None manifest,
             assert that path is absent from the result
        Why: Plugin command discovery uses commands/*.md (root only); commands nested
             inside a skill directory are skill-scoped and must not receive plugin-level
             validation rules
        """
        # Arrange
        (tmp_path / "skills" / "my-skill" / "commands").mkdir(parents=True)
        (tmp_path / "skills" / "my-skill" / "commands" / "internal.md").write_text("# Cmd")
        manifest = PluginManifest(plugin_root=tmp_path)

        # Act
        result = _discover_plugin_paths(manifest)

        # Assert
        assert tmp_path / "skills" / "my-skill" / "commands" / "internal.md" not in result

    def test_convention_driven_includes_hooks_json_if_exists(self, tmp_path: Path) -> None:
        """Convention mode includes hooks/hooks.json when the file exists.

        Tests: _discover_plugin_paths — optional hooks/hooks.json inclusion
        How: Create hooks/hooks.json, pass all-None manifest, assert path present
        Why: hooks.json is a validatable plugin file; it must be included when present
             so hook validators can inspect its contents
        """
        # Arrange
        (tmp_path / "hooks").mkdir()
        (tmp_path / "hooks" / "hooks.json").write_text("{}")
        manifest = PluginManifest(plugin_root=tmp_path)

        # Act
        result = _discover_plugin_paths(manifest)

        # Assert
        assert tmp_path / "hooks" / "hooks.json" in result

    def test_convention_driven_includes_claude_md_if_exists(self, tmp_path: Path) -> None:
        """Convention mode includes CLAUDE.md when the file exists at plugin root.

        Tests: _discover_plugin_paths — optional CLAUDE.md inclusion
        How: Create CLAUDE.md at plugin root, pass all-None manifest, assert path present
        Why: CLAUDE.md is a validatable plugin file; validators check it for hook
             configuration and memory instructions
        """
        # Arrange
        (tmp_path / "CLAUDE.md").write_text("# Claude")
        manifest = PluginManifest(plugin_root=tmp_path)

        # Act
        result = _discover_plugin_paths(manifest)

        # Assert
        assert tmp_path / "CLAUDE.md" in result

    def test_convention_driven_always_includes_plugin_root(self, tmp_path: Path) -> None:
        """Convention mode always includes the plugin root directory itself.

        Tests: _discover_plugin_paths — plugin root always in result
        How: Pass an empty all-None manifest, assert tmp_path is in the result
        Why: The plugin root is included unconditionally so validators can inspect
             directory-level properties (e.g., presence of .claude-plugin/plugin.json)
        """
        # Arrange
        manifest = PluginManifest(plugin_root=tmp_path)

        # Act
        result = _discover_plugin_paths(manifest)

        # Assert
        assert tmp_path in result

    # --- Manifest-driven mode ---

    def test_manifest_driven_returns_only_declared_agents(self, tmp_path: Path) -> None:
        """Manifest mode returns only the agent paths declared in the manifest.

        Tests: _discover_plugin_paths — manifest-driven exact path restriction
        How: Create agents/main.md and agents/extra.md; declare only agents/main.md
             in the manifest; assert main.md present and extra.md absent
        Why: An explicit manifest overrides convention discovery; undeclared files
             must not be included so plugin authors control exactly what gets validated
        """
        # Arrange
        (tmp_path / "agents").mkdir()
        (tmp_path / "agents" / "main.md").write_text("# Main")
        (tmp_path / "agents" / "extra.md").write_text("# Extra")
        manifest = PluginManifest(plugin_root=tmp_path, agents=["agents/main.md"])

        # Act
        result = _discover_plugin_paths(manifest)

        # Assert
        assert tmp_path / "agents" / "main.md" in result
        assert tmp_path / "agents" / "extra.md" not in result

    def test_manifest_driven_resolves_skill_paths(self, tmp_path: Path) -> None:
        """Manifest mode resolves a declared skill directory to its SKILL.md child.

        Tests: _discover_plugin_paths — manifest-driven skills path resolution
        How: Declare skills=["skills/review"] in manifest, assert that
             tmp_path / "skills" / "review" / "SKILL.md" is in the result
        Why: Skill entries in plugin.json are directory references; the function
             resolves them to their SKILL.md child unconditionally. Using the path
             name rather than is_dir() means resolution works even when the skill
             directory does not yet exist on disk (missing = lint error, not silence).
        """
        # Arrange
        manifest = PluginManifest(plugin_root=tmp_path, skills=["skills/review"])

        # Act
        result = _discover_plugin_paths(manifest)

        # Assert
        assert tmp_path / "skills" / "review" / "SKILL.md" in result

    def test_manifest_driven_always_includes_plugin_root(self, tmp_path: Path) -> None:
        """Manifest mode always includes the plugin root directory.

        Tests: _discover_plugin_paths — plugin root in manifest-driven result
        How: Pass manifest with agents=["agents/x.md"], assert tmp_path in result
        Why: Plugin root inclusion is unconditional across both modes; validators
             that inspect directory structure must always receive the root
        """
        # Arrange
        manifest = PluginManifest(plugin_root=tmp_path, agents=["agents/x.md"])

        # Act
        result = _discover_plugin_paths(manifest)

        # Assert
        assert tmp_path in result

    def test_manifest_driven_includes_declared_skill_dir_even_when_skill_md_missing(self, tmp_path: Path) -> None:
        """Declared skill directory is included even when its SKILL.md does not exist.

        Tests: _discover_plugin_paths — manifest-driven unconditional inclusion for skills
        How: Declare skills=["skills/ghost-skill"] in manifest without creating the
             directory or SKILL.md; assert skills/ghost-skill/SKILL.md is in the result
        Why: Missing declared files are lint errors that downstream validators should
             flag. Silently dropping them would hide the error entirely. This is the
             intentional design difference between manifest-driven and convention-driven
             mode: convention uses globs (only existing files appear), manifest-driven
             adds declared paths unconditionally.
        """
        # Arrange — skill directory and SKILL.md deliberately not created
        manifest = PluginManifest(plugin_root=tmp_path, skills=["skills/ghost-skill"])

        # Act
        result = _discover_plugin_paths(manifest)

        # Assert — path present despite not existing on disk
        assert tmp_path / "skills" / "ghost-skill" / "SKILL.md" in result

    def test_manifest_driven_includes_declared_agent_even_when_file_missing(self, tmp_path: Path) -> None:
        """Declared agent file is included even when it does not exist on disk.

        Tests: _discover_plugin_paths — manifest-driven unconditional inclusion for agents
        How: Declare agents=["agents/ghost.md"] without creating the file;
             assert agents/ghost.md is in the result
        Why: Same intentional design as skills — a declared-but-missing path is a
             validation error for downstream validators, not a silent omission.
        """
        # Arrange — agent file deliberately not created
        manifest = PluginManifest(plugin_root=tmp_path, agents=["agents/ghost.md"])

        # Act
        result = _discover_plugin_paths(manifest)

        # Assert — path present despite not existing on disk
        assert tmp_path / "agents" / "ghost.md" in result

    def test_result_is_sorted_and_deduplicated(self, tmp_path: Path) -> None:
        """Return value is a sorted list with no duplicate entries.

        Tests: _discover_plugin_paths — sort and deduplication invariants
        How: Create agents/z.md and agents/a.md (reverse alphabetical order), call
             function, assert result equals sorted(result) and has no duplicates
        Why: Deterministic ordering ensures reproducible validator output across
             runs and platforms; duplicates would cause validators to process the
             same file twice, producing redundant or double-counted violations
        """
        # Arrange
        (tmp_path / "agents").mkdir()
        (tmp_path / "agents" / "z.md").write_text("Z")
        (tmp_path / "agents" / "a.md").write_text("A")
        manifest = PluginManifest(plugin_root=tmp_path)

        # Act
        result = _discover_plugin_paths(manifest)

        # Assert
        assert result == sorted(result)
        assert len(result) == len(set(result))


class TestIntegrationContextAwareDiscovery:
    """Integration tests for the full context-aware discovery pipeline.

    Strategy: exercise _discover_validatable_paths and _resolve_filter_and_expand_paths
    end-to-end with real filesystem structures via tmp_path.  No mocking.
    These tests verify that context detection, plugin manifest parsing, and
    path filtering all compose correctly across the full call chain.
    """

    def test_plugin_scan_excludes_skill_internal_agents(self, tmp_path: Path) -> None:
        """Plugin dir discovery must not return skills/*/agents/*.md paths.

        Tests: _discover_validatable_paths — full pipeline for PLUGIN context
        How: Create a plugin structure with root agents/, SKILL.md, and a
             skill-internal agents/ dir; assert root paths present, internal absent
        Why: Skill-internal agent files are implementation details of a skill and
             must never surface as top-level plugin agents; this is the core
             false-positive scenario the context-aware pipeline prevents
        """
        # Arrange
        (tmp_path / ".claude-plugin").mkdir()
        (tmp_path / ".claude-plugin" / "plugin.json").write_text("{}")
        (tmp_path / "agents").mkdir()
        (tmp_path / "agents" / "main.md").write_text("# Main Agent")
        (tmp_path / "skills" / "my-skill" / "agents").mkdir(parents=True)
        (tmp_path / "skills" / "my-skill" / "agents" / "helper.md").write_text("# Helper")
        (tmp_path / "skills" / "my-skill" / "SKILL.md").write_text("# Skill")

        # Act
        result = _discover_validatable_paths(tmp_path)

        # Assert
        assert tmp_path / "agents" / "main.md" in result
        assert tmp_path / "skills" / "my-skill" / "SKILL.md" in result
        assert tmp_path / "skills" / "my-skill" / "agents" / "helper.md" not in result

    def test_filter_type_agents_on_plugin_uses_root_only_glob(self, tmp_path: Path) -> None:
        """--filter-type=agents on a plugin dir must use agents/*.md, not **/agents/*.md.

        Tests: _resolve_filter_and_expand_paths — PLUGIN context uses PLUGIN_FILTER_TYPE_MAP
        How: Create a plugin with root agents/ and a skill-internal agents/ dir;
             call with filter_type='agents'; assert root agent present, internal absent
        Why: Recursive glob **/agents/*.md would cross skill boundaries and return
             skill-internal agent files, producing spurious PA001/FM001 violations
        """
        # Arrange
        (tmp_path / ".claude-plugin").mkdir()
        (tmp_path / ".claude-plugin" / "plugin.json").write_text("{}")
        (tmp_path / "agents").mkdir()
        (tmp_path / "agents" / "main.md").write_text("# Root Agent")
        (tmp_path / "skills" / "my-skill" / "agents").mkdir(parents=True)
        (tmp_path / "skills" / "my-skill" / "agents" / "helper.md").write_text("# Helper")

        # Act
        expanded, _ = _resolve_filter_and_expand_paths([tmp_path], None, "agents")

        # Assert
        assert tmp_path / "agents" / "main.md" in expanded
        assert tmp_path / "skills" / "my-skill" / "agents" / "helper.md" not in expanded

    def test_raw_filter_glob_overrides_scan_context(self, tmp_path: Path) -> None:
        """An explicit --filter glob bypasses context-aware discovery and matches everything.

        Tests: _resolve_filter_and_expand_paths — raw filter_glob path ignores context
        How: Create a plugin with a skill-internal agents/ dir; pass an explicit
             **/agents/*.md glob via filter_glob; assert the internal file is present
        Why: When the user provides an explicit glob, they opt out of context-aware
             scoping — the glob must be honoured literally regardless of scan context
        """
        # Arrange
        (tmp_path / ".claude-plugin").mkdir()
        (tmp_path / ".claude-plugin" / "plugin.json").write_text("{}")
        (tmp_path / "skills" / "my-skill" / "agents").mkdir(parents=True)
        (tmp_path / "skills" / "my-skill" / "agents" / "helper.md").write_text("# Helper")

        # Act
        expanded, _ = _resolve_filter_and_expand_paths([tmp_path], "**/agents/*.md", None)

        # Assert
        assert tmp_path / "skills" / "my-skill" / "agents" / "helper.md" in expanded

    def test_provider_scan_discovers_only_agents(self, tmp_path: Path) -> None:
        """Provider dir scan returns agents/**/*.md and excludes other directories.

        Tests: _discover_validatable_paths — full pipeline for PROVIDER context
        How: Create a .claude dir with agents/ and commands/; assert agents found,
             commands absent
        Why: Provider-level discovery is scoped exclusively to agents/**/*.md;
             commands are a distinct concept and must not be mixed into the agent list
        """
        # Arrange
        provider_dir = tmp_path / ".claude"
        (provider_dir / "agents").mkdir(parents=True)
        (provider_dir / "agents" / "my-agent.md").write_text("# Agent")
        (provider_dir / "commands").mkdir()
        (provider_dir / "commands" / "cmd.md").write_text("# Cmd")

        # Act
        result = _discover_validatable_paths(provider_dir)

        # Assert
        assert provider_dir / "agents" / "my-agent.md" in result
        assert provider_dir / "commands" / "cmd.md" not in result

    def test_bare_dir_with_nested_plugin_excludes_skill_internal_agents(self, tmp_path: Path) -> None:
        """In BARE context, nested plugin discovery honours plugin boundary rules.

        Tests: _discover_validatable_paths — BARE context delegates to plugin discovery
        How: Create a BARE dir containing a nested plugin with root agents/ and a
             skill-internal agents/ dir; assert root agent present, internal absent
        Why: The BARE dispatcher must invoke _discover_plugin_paths for nested plugins,
             which enforces root-only globs and never returns skill-internal agents
        """
        # Arrange
        plugin = tmp_path / "my-plugin"
        (plugin / ".claude-plugin").mkdir(parents=True)
        (plugin / ".claude-plugin" / "plugin.json").write_text("{}")
        (plugin / "agents").mkdir()
        (plugin / "agents" / "root-agent.md").write_text("# Root Agent")
        (plugin / "skills" / "my-skill" / "agents").mkdir(parents=True)
        (plugin / "skills" / "my-skill" / "agents" / "helper.md").write_text("# Helper")

        # Act
        result = _discover_validatable_paths(tmp_path)

        # Assert
        assert plugin / "agents" / "root-agent.md" in result
        assert plugin / "skills" / "my-skill" / "agents" / "helper.md" not in result

    def test_bare_dir_with_nested_provider_applies_provider_discovery(self, tmp_path: Path) -> None:
        """In BARE context, nested .claude/ dir uses provider-scoped discovery.

        Tests: _discover_validatable_paths — BARE context delegates to provider discovery
        How: Create a BARE dir containing a nested .claude/ with agents/ and commands/;
             assert agents present, commands absent
        Why: The BARE dispatcher must invoke _discover_provider_paths for nested provider
             dirs, which scopes discovery to agents/**/*.md only and excludes commands
        """
        # Arrange
        provider = tmp_path / ".claude"
        (provider / "agents").mkdir(parents=True)
        (provider / "agents" / "my-agent.md").write_text("# Agent")
        (provider / "commands").mkdir()
        (provider / "commands" / "cmd.md").write_text("# Cmd")

        # Act
        result = _discover_validatable_paths(tmp_path)

        # Assert
        assert provider / "agents" / "my-agent.md" in result
        assert provider / "commands" / "cmd.md" not in result

    def test_bare_context_skips_provider_inside_plugin_tree(self, tmp_path: Path) -> None:
        """Q2: provider dir nested inside a plugin tree is skipped — plugin takes precedence.

        Tests: _discover_validatable_paths — BARE context Q2 precedence rule
        How: Create a plugin tree that contains a .claude/ provider dir nested inside it;
             assert the plugin's own agent is discovered while the nested provider dir is
             not treated as a standalone provider
        Why: Architecture spec Q2 resolution states that when a provider dir is found
             inside a plugin tree, the plugin context takes precedence.  The provider dir
             is part of the plugin's content, not an independent provider root.  Without
             this rule, provider discovery would double-count paths already covered by
             plugin discovery and could surface internal plugin structure as top-level
             provider agents.
        """
        # Arrange — plugin with a .claude/ provider dir nested inside it
        plugin = tmp_path / "my-plugin"
        (plugin / ".claude-plugin").mkdir(parents=True)
        (plugin / ".claude-plugin" / "plugin.json").write_text("{}")
        (plugin / "agents").mkdir()
        (plugin / "agents" / "root-agent.md").write_text("# Root Agent")
        # .claude/ nested inside the plugin — should be treated as plugin content, not provider
        (plugin / ".claude" / "agents").mkdir(parents=True)
        (plugin / ".claude" / "agents" / "provider-agent.md").write_text("# Provider Agent")

        # Act
        result = _discover_validatable_paths(tmp_path)

        # Assert
        # The plugin's root agent must be discovered via plugin discovery
        assert plugin / "agents" / "root-agent.md" in result
        # .claude/ inside the plugin is NOT discovered as an independent provider;
        # plugin takes precedence (Q2 resolution)
        assert plugin / ".claude" / "agents" / "provider-agent.md" not in result

    def test_bare_context_discovers_provider_outside_plugin_tree(self, tmp_path: Path) -> None:
        """Provider dir outside any plugin tree is discovered normally.

        Tests: _discover_validatable_paths — BARE context provider discovery without Q2 suppression
        How: Create a standalone .claude/ provider dir with no plugin sibling; assert
             the provider's agent is included in the discovery result
        Why: The Q2 skip-logic must only suppress providers that are nested inside a
             plugin tree.  A .claude/ dir at the same level as — or outside — any plugin
             root must still be discovered as a provider.  This test confirms the
             positive path so that a future regression tightening the skip condition
             does not silently drop legitimate providers.
        """
        # Arrange — standalone .claude/ provider with no plugin anywhere nearby
        provider = tmp_path / ".claude"
        (provider / "agents").mkdir(parents=True)
        (provider / "agents" / "my-agent.md").write_text("# Agent")

        # Act
        result = _discover_validatable_paths(tmp_path)

        # Assert
        assert provider / "agents" / "my-agent.md" in result


class TestBareDirectoryRegressionCompatibility:
    """Regression tests verifying bare directory discovery matches DEFAULT_SCAN_PATTERNS.

    Strategy: create real filesystem structures that cover every DEFAULT_SCAN_PATTERN
    entry and assert that _discover_validatable_paths returns all expected paths.
    No mocking — the function uses glob/Path operations on real files.

    These tests guard against regressions in the BARE context dispatcher introduced
    in Phase 2a, ensuring backward compatibility with the original DEFAULT_SCAN_PATTERNS
    scan behavior for directories that are not plugin or provider roots.
    """

    def test_bare_directory_discovers_all_default_scan_pattern_files(self, tmp_path: Path) -> None:
        """Bare directory discovery matches DEFAULT_SCAN_PATTERNS behavior.

        Tests: _discover_validatable_paths — BARE context DEFAULT_SCAN_PATTERNS fallback
        How: Create a tmp_path structure with files at various depths matching each
             DEFAULT_SCAN_PATTERN entry, call _discover_validatable_paths, assert all
             are present in the result.
        Why: The BARE dispatcher must preserve full DEFAULT_SCAN_PATTERNS coverage for
             directories that contain no plugin or provider subtrees, matching the
             pre-Phase-2a behavior exactly.
        """
        # Arrange — one file per DEFAULT_SCAN_PATTERN
        # Pattern: **/skills/*/SKILL.md
        (tmp_path / "skills" / "my-skill").mkdir(parents=True)
        (tmp_path / "skills" / "my-skill" / "SKILL.md").write_text("# Skill")

        # Pattern: **/agents/*.md
        (tmp_path / "agents").mkdir()
        (tmp_path / "agents" / "helper.md").write_text("# Helper")

        # Pattern: **/commands/*.md
        (tmp_path / "commands").mkdir()
        (tmp_path / "commands" / "run.md").write_text("# Run")

        # Pattern: **/hooks/hooks.json
        (tmp_path / "hooks").mkdir()
        (tmp_path / "hooks" / "hooks.json").write_text("{}")

        # Pattern: **/CLAUDE.md
        (tmp_path / "CLAUDE.md").write_text("# Claude")

        # Nested files at arbitrary depth — bare context preserves ** recursion
        (tmp_path / "subdir" / "agents").mkdir(parents=True)
        (tmp_path / "subdir" / "agents" / "nested-agent.md").write_text("# Nested")

        (tmp_path / "subdir" / "skills" / "other-skill").mkdir(parents=True)
        (tmp_path / "subdir" / "skills" / "other-skill" / "SKILL.md").write_text("# Other")

        # Act
        result = _discover_validatable_paths(tmp_path)

        # Assert — every file created must appear in the result
        assert tmp_path / "skills" / "my-skill" / "SKILL.md" in result
        assert tmp_path / "agents" / "helper.md" in result
        assert tmp_path / "commands" / "run.md" in result
        assert tmp_path / "hooks" / "hooks.json" in result
        assert tmp_path / "CLAUDE.md" in result
        assert tmp_path / "subdir" / "agents" / "nested-agent.md" in result
        assert tmp_path / "subdir" / "skills" / "other-skill" / "SKILL.md" in result

    def test_bare_directory_with_plugin_json_includes_plugin_root(self, tmp_path: Path) -> None:
        """Directory with .claude-plugin/plugin.json routes through PLUGIN context.

        Tests: _discover_validatable_paths — PLUGIN dispatch adds plugin root
        How: Create .claude-plugin/plugin.json at tmp_path root, call
             _discover_validatable_paths, assert tmp_path itself is in the result.
        Why: detect_scan_context returns PLUGIN when plugin.json is present, so
             _discover_plugin_paths is called — which unconditionally adds the plugin
             root to the result set (line 148 of scan_runtime.py).
        """
        # Arrange
        (tmp_path / ".claude-plugin").mkdir()
        (tmp_path / ".claude-plugin" / "plugin.json").write_text("{}")

        # Act
        result = _discover_validatable_paths(tmp_path)

        # Assert — plugin root itself must be present (added by _discover_plugin_paths)
        assert tmp_path in result

    def test_bare_directory_nested_plugin_root_in_results(self, tmp_path: Path) -> None:
        """For BARE dir with nested plugin, the plugin root appears in results.

        Tests: _discover_validatable_paths — BARE context delegates nested plugin discovery
        How: Create a subplugin/ directory containing .claude-plugin/plugin.json inside
             a BARE tmp_path, call _discover_validatable_paths, assert subplugin/ root
             is in the result.
        Why: The BARE dispatcher calls _discover_plugin_paths for each nested plugin,
             which adds the plugin root to discovered. The plugin root must be
             present so validators can apply plugin-level rules to it.
        """
        # Arrange
        nested_plugin = tmp_path / "subplugin"
        (nested_plugin / ".claude-plugin").mkdir(parents=True)
        (nested_plugin / ".claude-plugin" / "plugin.json").write_text("{}")

        # Act
        result = _discover_validatable_paths(tmp_path)

        # Assert — nested plugin root must be present
        assert nested_plugin in result
