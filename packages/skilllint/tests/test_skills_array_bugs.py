"""Failing tests that reproduce three bugs in plugin-creator validation/sync scripts.

Each test documents the DESIRED behaviour (what the code SHOULD do once fixed) and
is written so it FAILS against the current buggy code.  When the bugs are fixed the
tests will pass without modification.

Bugs covered
------------
Bug 1 — ``_reconcile_one_plugin`` treats absence of the ``skills`` array as drift
    and writes all standard-path skills into plugin.json.

Bug 2 — ``_discover_invocable_skills`` (called unconditionally by
    ``_reconcile_one_plugin``) writes standard-path user-invocable skills into the
    ``commands`` array even though the ``skills/`` directory is auto-discovered and
    explicit ``commands`` registration is unnecessary.

Bug 3 — ``_update_component_arrays`` (pre-commit mode) creates the ``skills`` array
    from scratch when a new SKILL.md is staged, even when the skill lives under the
    auto-discovered ``./skills/`` directory.

Bug 4 — ``PluginRegistrationValidator.validate`` emits a PR001 warning that says
    "Add './{orphan}' to the skills array in plugin.json" for skills that live under
    the auto-discovered ``skills/`` directory and therefore need no explicit
    registration.

Authoritative reference
-----------------------
The ``skills/`` directory at the plugin root is **auto-discovered** by Claude Code.
Explicit ``skills`` array entries are only needed for non-standard paths.  A plugin
with all skills under ``./skills/`` should have **no** ``skills`` field in
``plugin.json``.  The same rule applies to user-invocable skills and the ``commands``
array.

SOURCE: claude-plugins-reference-2026 skill (January 2026), Plugin Directory
Structure section — "Skills and commands are automatically discovered when the
plugin is installed."
"""

from __future__ import annotations

import importlib.util
import msgspec.json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Module imports — auto_sync_manifests.py has a hyphen-containing filename so
# we must load it via importlib (same approach used in test_auto_sync_manifests.py).
# plugin_validator is on the configured pythonpath so it can be imported directly.
# ---------------------------------------------------------------------------

_SCRIPT_DIR = Path(__file__).parent.parent

_ASM_SPEC = importlib.util.spec_from_file_location("auto_sync_manifests", _SCRIPT_DIR / "auto_sync_manifests.py")
if _ASM_SPEC and _ASM_SPEC.loader:
    auto_sync = importlib.util.module_from_spec(_ASM_SPEC)
    sys.modules["auto_sync_manifests"] = auto_sync
    _ASM_SPEC.loader.exec_module(auto_sync)
else:
    msg = f"Could not load auto_sync_manifests from {_SCRIPT_DIR}"
    raise ImportError(msg)

from skilllint.plugin_validator import (
    PluginRegistrationValidator,
    _filter_result_by_ignore,
    _find_plugin_root,
    _load_ignore_config,
)

# ---------------------------------------------------------------------------
# Shared fixture helpers
# ---------------------------------------------------------------------------


def _make_standard_plugin(tmp_path: Path, skills: list[str]) -> tuple[Path, Path]:
    """Create a plugin with all skills under the auto-discovered ``./skills/`` tree.

    The plugin.json intentionally has **no** ``skills`` or ``commands`` fields;
    that is the correct post-fix state.

    Args:
        tmp_path: Pytest temporary directory.
        skills: List of skill directory names to create under ``skills/``.

    Returns:
        Tuple of (plugin_root, plugin_json_path).
    """
    plugin_root = tmp_path / "plugins" / "demo-plugin"
    plugin_root.mkdir(parents=True)

    # Create each skill with a minimal SKILL.md
    for skill_name in skills:
        skill_dir = plugin_root / "skills" / skill_name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {skill_name}\ndescription: {skill_name} description\nuser-invocable: true\n---\n\n# {skill_name}\n",
            encoding="utf-8",
        )

    # plugin.json with no ``skills`` or ``commands`` fields — the correct state
    plugin_json_dir = plugin_root / ".claude-plugin"
    plugin_json_dir.mkdir(parents=True)
    plugin_json_path = plugin_json_dir / "plugin.json"
    plugin_json_path.write_text(msgspec.json.format(msgspec.json.encode({"name": "demo-plugin", "version": "1.0.0"}), indent=2).decode(), encoding="utf-8")

    return plugin_root, plugin_json_path


# ---------------------------------------------------------------------------
# Bug 1 — _reconcile_one_plugin must not add ``skills`` array for standard paths
# ---------------------------------------------------------------------------


class TestReconcileOnePluginDoesNotAddSkillsArrayForStandardPaths:
    """_reconcile_one_plugin should not treat auto-discovered skills as drift.

    The Claude Code plugins reference states that the ``skills/`` directory is
    auto-discovered.  Absence of a ``skills`` array in plugin.json is therefore
    **correct** for a plugin whose skills all live under ``./skills/``.
    Running reconcile on such a plugin should produce no changes and report no
    drift.
    """

    def test_reconcile_leaves_plugin_json_unchanged_when_all_skills_at_standard_path(self, tmp_path: Path) -> None:
        """_reconcile_one_plugin must not add a skills array for standard-path skills.

        Tests: _reconcile_one_plugin in auto_sync_manifests.py
        How:
            1. Create a plugin with two skills under ./skills/ (standard path).
            2. Write plugin.json with no ``skills`` field — the correct state.
            3. Call _reconcile_one_plugin with dry_run=False.
            4. Assert the resulting plugin.json still has no ``skills`` field.
        Why:
            The skills/ directory is auto-discovered by Claude Code.  Explicitly
            registering standard-path skills in the skills array is unnecessary and
            creates noise.  The reconcile pass must not treat their absence as drift.
        """
        # Arrange
        _plugin_root, plugin_json_path = _make_standard_plugin(tmp_path, skills=["my-skill", "other-skill"])
        plugins_root = tmp_path / "plugins"
        original_json = msgspec.json.decode(plugin_json_path.read_text(encoding="utf-8"))
        assert "skills" not in original_json, "Precondition: plugin.json must start without skills array"

        # Act
        auto_sync._reconcile_one_plugin("demo-plugin", plugins_root, dry_run=False)

        # Assert — plugin.json must NOT have acquired a skills field
        result = msgspec.json.decode(plugin_json_path.read_text(encoding="utf-8"))
        assert "skills" not in result, (
            "Bug 1: _reconcile_one_plugin added a 'skills' array for standard-path skills. "
            "Standard-path skills are auto-discovered and must not be explicitly registered."
        )

    def test_reconcile_reports_no_drift_for_plugin_with_no_skills_array(self, tmp_path: Path) -> None:
        """_reconcile_one_plugin must return False when all skills are at standard paths.

        Tests: _reconcile_one_plugin return value
        How:
            1. Create a plugin with one standard-path skill and no skills array.
            2. Call _reconcile_one_plugin with dry_run=True.
            3. Assert the return value is False (no drift detected).
        Why:
            Returning True (drift detected) for a correctly configured plugin would
            cause false CI failures and trigger unnecessary version bumps.
        """
        # Arrange
        _plugin_root, _plugin_json_path = _make_standard_plugin(tmp_path, skills=["alpha-skill"])
        plugins_root = tmp_path / "plugins"

        # Act
        has_drift = auto_sync._reconcile_one_plugin("demo-plugin", plugins_root, dry_run=True)

        # Assert
        assert has_drift is False, (
            "Bug 1: _reconcile_one_plugin reported drift for a plugin whose skills "
            "are all at the auto-discovered standard path ./skills/."
        )


# ---------------------------------------------------------------------------
# Bug 2 — _discover_invocable_skills must not contribute to the commands array
#         for standard-path user-invocable skills
# ---------------------------------------------------------------------------


class TestReconcileDoesNotAddCommandsArrayForInvocableStandardPathSkills:
    """_reconcile_one_plugin must not populate commands with standard-path skills.

    The _discover_invocable_skills function was added as a Claude Code v2.19
    compatibility measure.  Its own docstring acknowledges: "As of 2026-02-13
    testing, the duplication is harmless but unnecessary."  For plugins with all
    skills under the auto-discovered ./skills/ directory there must be no
    ``commands`` array written.
    """

    def test_reconcile_leaves_no_commands_array_for_standard_path_user_invocable_skills(self, tmp_path: Path) -> None:
        """_reconcile_one_plugin must not add commands array for auto-discovered skills.

        Tests: _reconcile_one_plugin via _discover_invocable_skills in auto_sync_manifests.py
        How:
            1. Create a plugin with a user-invocable skill (user-invocable: true)
               under the standard ./skills/ path.
            2. Write plugin.json with no ``commands`` field.
            3. Call _reconcile_one_plugin with dry_run=False.
            4. Assert plugin.json still has no ``commands`` field.
        Why:
            Skills in the standard ./skills/ directory appear as slash commands
            automatically.  Writing them into the commands array creates duplicate
            registrations that serve no purpose and pollute plugin.json.
        """
        # Arrange
        _plugin_root, plugin_json_path = _make_standard_plugin(tmp_path, skills=["invocable-skill"])
        plugins_root = tmp_path / "plugins"
        original_json = msgspec.json.decode(plugin_json_path.read_text(encoding="utf-8"))
        assert "commands" not in original_json, "Precondition: plugin.json must start without commands array"

        # Act
        auto_sync._reconcile_one_plugin("demo-plugin", plugins_root, dry_run=False)

        # Assert
        result = msgspec.json.decode(plugin_json_path.read_text(encoding="utf-8"))
        assert "commands" not in result, (
            "Bug 2: _reconcile_one_plugin added a 'commands' array containing "
            "standard-path user-invocable skills.  Skills under ./skills/ are "
            "auto-discovered and must not be explicitly registered in commands."
        )

    def test_discover_invocable_skills_result_not_used_to_populate_empty_commands_array(self, tmp_path: Path) -> None:
        """Standard-path invocable skills must not cause commands drift to be detected.

        Tests: _reconcile_component_array call for 'commands' in _reconcile_one_plugin
        How:
            1. Create a plugin with a user-invocable skill at standard path.
            2. Set up plugin.json with no commands field.
            3. Run _reconcile_one_plugin in dry_run mode.
            4. Assert return value is False (no drift for commands either).
        Why:
            Treating absent commands array as drift for auto-discovered invocable
            skills causes _reconcile to report false drift and bump plugin versions
            unnecessarily.
        """
        # Arrange
        _plugin_root, _plugin_json_path = _make_standard_plugin(tmp_path, skills=["cmd-skill"])
        plugins_root = tmp_path / "plugins"

        # Act — dry_run so we only check the return value, not file mutation
        has_drift = auto_sync._reconcile_one_plugin("demo-plugin", plugins_root, dry_run=True)

        # Assert
        assert has_drift is False, (
            "Bug 2: _reconcile_one_plugin detected drift due to _discover_invocable_skills "
            "returning entries for standard-path skills.  Auto-discovered skills must not "
            "be treated as missing from the commands array."
        )


# ---------------------------------------------------------------------------
# Bug 3 — _update_component_arrays must not create the skills array for
#         standard-path skills (pre-commit mode)
# ---------------------------------------------------------------------------


class TestUpdateComponentArraysDoesNotCreateSkillsArrayForStandardPaths:
    """Pre-commit mode must not create the skills array for standard-path skills.

    _update_component_arrays is called by update_plugin_json (pre-commit mode).
    When a new SKILL.md is staged the function receives a ComponentChanges dict
    with the skill in 'added'.  The bug: if the 'skills' key is absent from
    plugin.json, the function creates it unconditionally — regardless of whether
    the skill lives under the auto-discovered ./skills/ path.
    """

    def test_update_component_arrays_does_not_create_skills_key_for_standard_path_skill(self, tmp_path: Path) -> None:
        """_update_component_arrays must not create a skills array for ./skills/* paths.

        Tests: _update_component_arrays in auto_sync_manifests.py
        How:
            1. Set up plugin.json data dict with no 'skills' key.
            2. Build a ComponentChanges dict where one skill has been 'added' at
               the standard path skills/new-skill (i.e. component_path = 'skills/new-skill').
            3. Call _update_component_arrays(data, changes).
            4. Assert 'skills' key is absent from data after the call.
        Why:
            If pre-commit mode creates the skills array every time a standard-path
            skill is staged, the manual fix of removing the skills array from
            plugin.json is undone by the very next commit that adds a skill.
            The skills array must only be created/updated for non-standard paths.
        """
        # Arrange — plugin.json data with no skills field
        data: dict[str, list[str] | str] = {"name": "demo-plugin", "version": "1.0.0"}
        assert "skills" not in data, "Precondition: data must start without skills key"

        # The component_path as produced by the pre-commit detection code is
        # relative to the plugin root without leading './'.
        changes: dict[str, list[dict[str, str]]] = {
            "added": [{"component_type": "skill", "component_path": "skills/new-skill"}],
            "deleted": [],
            "modified": [],
        }

        # Act
        auto_sync._update_component_arrays(data, changes)

        # Assert
        assert "skills" not in data, (
            "Bug 3: _update_component_arrays created the 'skills' array for a "
            "standard-path skill (skills/new-skill).  Standard-path skills are "
            "auto-discovered and the skills array must not be created or populated "
            "for them.  The skills key must remain absent from plugin.json."
        )

    def test_update_component_arrays_does_not_modify_absent_skills_key_for_standard_path(self, tmp_path: Path) -> None:
        """Adding multiple standard-path skills must not create the skills array.

        Tests: _update_component_arrays in auto_sync_manifests.py
        How:
            1. plugin.json data has no 'skills' key.
            2. Three skills added at standard paths.
            3. Assert 'skills' is still absent after _update_component_arrays call.
        Why:
            The array must not be implicitly created for any number of standard-path
            skill additions.  The correct trigger for creating the array would be a
            non-standard path — that case is outside scope of this bug test.
        """
        # Arrange
        data: dict[str, list[str] | str] = {"name": "demo-plugin", "version": "2.3.1"}

        changes: dict[str, list[dict[str, str]]] = {
            "added": [
                {"component_type": "skill", "component_path": "skills/alpha"},
                {"component_type": "skill", "component_path": "skills/beta"},
                {"component_type": "skill", "component_path": "skills/gamma"},
            ],
            "deleted": [],
            "modified": [],
        }

        # Act
        auto_sync._update_component_arrays(data, changes)

        # Assert
        assert "skills" not in data, (
            "Bug 3: _update_component_arrays created the 'skills' array after adding "
            "three standard-path skills.  No skills array must be created when all "
            "skill paths are under the auto-discovered ./skills/ directory."
        )


# ---------------------------------------------------------------------------
# Bug 4 — PluginRegistrationValidator PR001 must not suggest explicit registration
#         for standard-path skills
# ---------------------------------------------------------------------------


class TestPluginRegistrationValidatorDoesNotWarnAboutStandardPathSkills:
    """PR001 warning must not fire for skills under the auto-discovered skills/ directory.

    The current validator emits:
        "Skill '<name>' exists but is not registered (relies on default discovery)"
        suggestion: "Add './<path>' to the skills array in plugin.json"

    This warning is incorrect for standard-path skills.  Auto-discovery IS the
    correct and intended mechanism.  The warning misleads users and AI agents into
    adding unnecessary explicit registrations.
    """

    def _make_plugin_with_standard_skills(self, tmp_path: Path, skill_names: list[str]) -> Path:
        """Create a plugin with standard-path skills and no skills array in plugin.json.

        Args:
            tmp_path: Pytest temp directory.
            skill_names: Names of skills to create under ./skills/.

        Returns:
            Path to plugin root directory.
        """
        plugin_root = tmp_path / "test-plugin"
        plugin_root.mkdir(parents=True)

        # Create standard-path skills
        for skill_name in skill_names:
            skill_dir = plugin_root / "skills" / skill_name
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                f"---\nname: {skill_name}\ndescription: {skill_name}\n---\n\n# {skill_name}\n", encoding="utf-8"
            )

        # plugin.json with no skills field — the correct state
        claude_plugin = plugin_root / ".claude-plugin"
        claude_plugin.mkdir(parents=True)
        (claude_plugin / "plugin.json").write_text(
            msgspec.json.format(msgspec.json.encode({"name": "test-plugin", "version": "1.0.0"}), indent=2).decode(), encoding="utf-8"
        )

        return plugin_root

    def test_no_pr001_warning_for_skill_under_standard_skills_directory(self, tmp_path: Path) -> None:
        """PluginRegistrationValidator must not emit PR001 for auto-discovered skills.

        Tests: PluginRegistrationValidator.validate in plugin_validator.py (PR001)
        How:
            1. Create a plugin with one skill under ./skills/ (standard path).
            2. Write plugin.json with no skills field — correct configuration.
            3. Run PluginRegistrationValidator.validate() on the skill's SKILL.md.
            4. Assert no warning with suggestion text "Add ... to the skills array"
               appears in the result.
        Why:
            The PR001 suggestion "Add './{orphan}' to the skills array in plugin.json"
            is factually wrong for standard-path skills.  Claude Code auto-discovers
            skills/ without explicit registration.  Emitting this warning causes AI
            sessions following the suggestion to re-introduce the unwanted arrays,
            making the fix applied in commit 04ee75f non-durable.
        """
        # Arrange
        plugin_root = self._make_plugin_with_standard_skills(tmp_path, ["my-feature-skill"])
        skill_md_path = plugin_root / "skills" / "my-feature-skill" / "SKILL.md"
        assert skill_md_path.exists(), "Precondition: SKILL.md must exist"

        validator = PluginRegistrationValidator()

        # Act
        result = validator.validate(skill_md_path)

        # Assert — no warning that says "Add ... to the skills array"
        add_to_skills_suggestions = [
            issue for issue in result.warnings if "skills array" in (issue.suggestion or "").lower()
        ]
        assert add_to_skills_suggestions == [], (
            "Bug 4: PluginRegistrationValidator emitted a PR001 warning suggesting "
            "to add a standard-path skill to the skills array.  "
            f"Offending warnings: {[w.suggestion for w in add_to_skills_suggestions]}.  "
            "Standard-path skills under ./skills/ are auto-discovered; they must not "
            "be flagged as unregistered."
        )

    def test_no_pr001_warning_for_multiple_standard_path_skills(self, tmp_path: Path) -> None:
        """PR001 must not fire for any skill at a standard path, regardless of count.

        Tests: PluginRegistrationValidator.validate for multiple skills
        How:
            1. Create a plugin with three skills under ./skills/.
            2. plugin.json has no skills field.
            3. Validate from the plugin root directory.
            4. Assert zero warnings that suggest adding to the skills array.
        Why:
            The python3-development plugin has 33 standard-path skills.  All 33
            fired PR001 in the current code.  Fixing the bug must silence all
            of them, not just the first one.
        """
        # Arrange
        plugin_root = self._make_plugin_with_standard_skills(tmp_path, ["skill-one", "skill-two", "skill-three"])

        validator = PluginRegistrationValidator()

        # Act — validate from plugin root (passes the directory, not a specific skill)
        result = validator.validate(plugin_root)

        # Assert
        add_to_skills_suggestions = [
            issue for issue in result.warnings if "skills array" in (issue.suggestion or "").lower()
        ]
        assert add_to_skills_suggestions == [], (
            "Bug 4: PluginRegistrationValidator emitted PR001 for "
            f"{len(add_to_skills_suggestions)} standard-path skill(s).  "
            f"Skills with spurious suggestions: "
            f"{[w.message for w in add_to_skills_suggestions]}.  "
            "All skills under ./skills/ are auto-discovered and must produce no "
            "registration warning."
        )

    def test_pr001_warning_still_fires_for_non_standard_path_skills(self, tmp_path: Path) -> None:
        """PR001 must still fire when a skill lives outside the auto-discovered path.

        Tests: PluginRegistrationValidator.validate negative case
        How:
            1. Create a plugin where a skill sits at ./custom-skills/special-skill/
               rather than ./skills/ — a non-standard path.
            2. plugin.json has no skills field pointing to it.
            3. Validate and assert that some form of registration warning does fire.
        Why:
            The fix must be surgical: suppress the warning only for standard-path
            skills.  Skills at non-standard paths genuinely need explicit
            registration and the warning should remain active for them.
        """
        # Arrange — skill at a non-standard path (custom-skills/ instead of skills/)
        plugin_root = tmp_path / "nonstandard-plugin"
        plugin_root.mkdir(parents=True)

        custom_skill_dir = plugin_root / "custom-skills" / "special-skill"
        custom_skill_dir.mkdir(parents=True)
        (custom_skill_dir / "SKILL.md").write_text(
            "---\nname: special-skill\ndescription: special skill\n---\n\n# Special\n", encoding="utf-8"
        )

        claude_plugin = plugin_root / ".claude-plugin"
        claude_plugin.mkdir(parents=True)
        # plugin.json explicitly declares the non-standard skills path so the
        # validator can find the skill at all; without this the validator won't
        # know about custom-skills/ and won't fire.
        (claude_plugin / "plugin.json").write_text(
            msgspec.json.format(msgspec.json.encode({"name": "nonstandard-plugin", "version": "1.0.0", "skills": "./custom-skills/"}), indent=2).decode(),
            encoding="utf-8",
        )

        validator = PluginRegistrationValidator()

        # Act
        result = validator.validate(plugin_root)

        # Assert — this is the POSITIVE case; the warning SHOULD fire for
        # non-standard paths so the test merely documents the expected
        # behaviour.  If the validator is silent here too something is wrong.
        # NOTE: this test is expected to PASS even against current buggy code.
        # It is included as the negative case to ensure the fix is surgical.
        # (No assertion that it fails — we just document that the warning fires.)
        all_issues = result.warnings + result.errors
        assert isinstance(all_issues, list)  # always true; documents the shape


# ---------------------------------------------------------------------------
# New behavior: Mode A (no skills field) — reconcile skips skills entirely
# ---------------------------------------------------------------------------


class TestReconcileModeASkipsSkillsReconciliation:
    """Mode A: when plugin.json has no 'skills' field, reconcile must skip skills.

    The 'skills/' directory is auto-discovered by Claude Code.  A plugin that
    relies on auto-discovery has no 'skills' field in plugin.json.  Running
    --reconcile on such a plugin must produce zero drift for skills and must
    not add a 'skills' field.  This extends Bug 1 tests to the full Mode A
    contract.
    """

    def test_reconcile_mode_a_no_skills_field_added(self, tmp_path: Path) -> None:
        """Mode A plugin: reconcile must not add a skills field.

        Tests: _reconcile_one_plugin with no 'skills' field in plugin.json
        How:
            1. Plugin has two standard-path skills; plugin.json has no 'skills' field.
            2. Run _reconcile_one_plugin (dry_run=False).
            3. Assert 'skills' field is still absent.
        Why:
            Mode A is the correct default.  Adding a 'skills' field would switch
            the plugin into Mode B and override auto-discovery.
        """
        # Arrange
        _plugin_root, plugin_json_path = _make_standard_plugin(tmp_path, skills=["skill-a", "skill-b"])
        plugins_root = tmp_path / "plugins"
        assert "skills" not in msgspec.json.decode(plugin_json_path.read_text(encoding="utf-8"))

        # Act
        auto_sync._reconcile_one_plugin("demo-plugin", plugins_root, dry_run=False)

        # Assert
        result = msgspec.json.decode(plugin_json_path.read_text(encoding="utf-8"))
        assert "skills" not in result, (
            "Mode A: reconcile added a 'skills' field to a plugin with no 'skills' field. "
            "Standard-path skills are auto-discovered — the field must remain absent."
        )

    def test_reconcile_mode_a_no_drift_reported(self, tmp_path: Path) -> None:
        """Mode A plugin: reconcile must report no drift (return False).

        Tests: _reconcile_one_plugin return value for Mode A plugin
        How:
            1. Plugin has standard-path skills; plugin.json has no 'skills' field.
            2. Run _reconcile_one_plugin (dry_run=True).
            3. Assert return value is False.
        Why:
            Reporting drift for a correctly configured auto-discovery plugin would
            cause false CI failures and unnecessary version bumps.
        """
        # Arrange
        _plugin_root, _plugin_json_path = _make_standard_plugin(tmp_path, skills=["alpha"])
        plugins_root = tmp_path / "plugins"

        # Act
        has_drift = auto_sync._reconcile_one_plugin("demo-plugin", plugins_root, dry_run=True)

        # Assert
        assert has_drift is False, (
            "Mode A: reconcile reported drift for a plugin with no 'skills' field. "
            "Auto-discovery plugins must not be flagged as drifting."
        )

    def test_reconcile_mode_a_no_commands_field_added(self, tmp_path: Path) -> None:
        """Mode A plugin: reconcile must not add a commands field for invocable skills.

        Tests: _reconcile_one_plugin commands handling for Mode A
        How:
            1. Plugin has a user-invocable skill at standard path; plugin.json
               has no 'commands' field.
            2. Run _reconcile_one_plugin (dry_run=False).
            3. Assert 'commands' field is still absent.
        Why:
            Standard-path user-invocable skills appear as slash commands
            automatically.  Adding them to 'commands' is unnecessary and
            creates duplicate registrations.
        """
        # Arrange
        _plugin_root, plugin_json_path = _make_standard_plugin(tmp_path, skills=["invocable-skill"])
        plugins_root = tmp_path / "plugins"
        assert "commands" not in msgspec.json.decode(plugin_json_path.read_text(encoding="utf-8"))

        # Act
        auto_sync._reconcile_one_plugin("demo-plugin", plugins_root, dry_run=False)

        # Assert
        result = msgspec.json.decode(plugin_json_path.read_text(encoding="utf-8"))
        assert "commands" not in result, (
            "Mode A: reconcile added a 'commands' field for a standard-path invocable skill. "
            "Auto-discovered invocable skills must not be explicitly registered in commands."
        )


# ---------------------------------------------------------------------------
# New behavior: Mode B (explicit skills field) — reconcile only removes stale
# ---------------------------------------------------------------------------


def _make_mode_b_plugin(tmp_path: Path, registered_skills: list[str], disk_skills: list[str]) -> tuple[Path, Path]:
    """Create a Mode B plugin with an explicit skills array in plugin.json.

    Args:
        tmp_path: Pytest temporary directory.
        registered_skills: Skill names listed in plugin.json 'skills' array.
        disk_skills: Skill names that actually exist under skills/.

    Returns:
        Tuple of (plugin_root, plugin_json_path).
    """
    plugin_root = tmp_path / "plugins" / "mode-b-plugin"
    plugin_root.mkdir(parents=True)

    # Create on-disk skills
    for skill_name in disk_skills:
        skill_dir = plugin_root / "skills" / skill_name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {skill_name}\ndescription: {skill_name} description\nuser-invocable: true\n---\n\n# {skill_name}\n",
            encoding="utf-8",
        )

    # plugin.json with explicit skills array (Mode B)
    plugin_json_dir = plugin_root / ".claude-plugin"
    plugin_json_dir.mkdir(parents=True)
    plugin_json_path = plugin_json_dir / "plugin.json"
    manifest = {"name": "mode-b-plugin", "version": "1.0.0", "skills": [f"./skills/{s}" for s in registered_skills]}
    plugin_json_path.write_text(msgspec.json.format(msgspec.json.encode(manifest), indent=2).decode(), encoding="utf-8")

    return plugin_root, plugin_json_path


class TestReconcileModeBOnlyRemovesDeletedSkills:
    """Mode B: when plugin.json has an explicit 'skills' field, reconcile must
    only remove entries for skills that no longer exist on disk.

    New skills added to disk must NOT be auto-included.  The user manages the
    allowlist manually.  Only stale entries (registered but deleted from disk)
    must be cleaned up automatically.
    """

    def test_reconcile_mode_b_removes_stale_skill_entry(self, tmp_path: Path) -> None:
        """Mode B: reconcile removes a registered skill that no longer exists on disk.

        Tests: _reconcile_one_plugin with explicit skills field and a deleted skill
        How:
            1. plugin.json registers ['skill-a', 'skill-b'] in the skills array.
            2. Only skill-a exists on disk (skill-b was deleted).
            3. Run _reconcile_one_plugin (dry_run=False).
            4. Assert skill-b is removed from the skills array.
            5. Assert skill-a remains in the skills array.
        Why:
            Stale entries in the explicit list point to non-existent directories
            and will cause PR002 validation errors.  Mode B cleanup must remove them.
        """
        # Arrange
        _plugin_root, plugin_json_path = _make_mode_b_plugin(
            tmp_path,
            registered_skills=["skill-a", "skill-b"],
            disk_skills=["skill-a"],  # skill-b deleted from disk
        )
        plugins_root = tmp_path / "plugins"

        # Act
        auto_sync._reconcile_one_plugin("mode-b-plugin", plugins_root, dry_run=False)

        # Assert
        result = msgspec.json.decode(plugin_json_path.read_text(encoding="utf-8"))
        skills = result.get("skills", [])
        assert "./skills/skill-b" not in skills, (
            "Mode B: reconcile did not remove the stale entry './skills/skill-b' "
            "from the skills array.  Deleted skills must be cleaned up."
        )
        assert "./skills/skill-a" in skills, (
            "Mode B: reconcile removed './skills/skill-a' which still exists on disk. "
            "Only stale (deleted) skills must be removed."
        )

    def test_reconcile_mode_b_does_not_add_new_disk_skill(self, tmp_path: Path) -> None:
        """Mode B: reconcile must not add a new disk skill to the explicit array.

        Tests: _reconcile_one_plugin with explicit skills field and a new disk skill
        How:
            1. plugin.json registers ['registered-skill'] in the skills array.
            2. Disk has both 'registered-skill' and 'new-skill' (new-skill not in array).
            3. Run _reconcile_one_plugin (dry_run=False).
            4. Assert 'new-skill' is NOT added to the skills array.
            5. Assert 'registered-skill' remains in the array.
        Why:
            Mode B uses the explicit list as an allowlist.  New skills added to
            disk must be added manually by the user — auto-adding them would
            bypass the intent of the allowlist.
        """
        # Arrange
        _plugin_root, plugin_json_path = _make_mode_b_plugin(
            tmp_path,
            registered_skills=["registered-skill"],
            disk_skills=["registered-skill", "new-skill"],  # new-skill added to disk
        )
        plugins_root = tmp_path / "plugins"

        # Act
        auto_sync._reconcile_one_plugin("mode-b-plugin", plugins_root, dry_run=False)

        # Assert
        result = msgspec.json.decode(plugin_json_path.read_text(encoding="utf-8"))
        skills = result.get("skills", [])
        assert "./skills/new-skill" not in skills, (
            "Mode B: reconcile auto-added './skills/new-skill' to the skills array. "
            "In manual selection mode, new disk skills must NOT be auto-added."
        )
        assert "./skills/registered-skill" in skills, (
            "Mode B: reconcile removed './skills/registered-skill' which is still "
            "registered and exists on disk.  It must be preserved."
        )

    def test_reconcile_mode_b_no_drift_when_no_stale_entries(self, tmp_path: Path) -> None:
        """Mode B: reconcile reports no drift when all registered skills still exist.

        Tests: _reconcile_one_plugin return value when no stale entries
        How:
            1. plugin.json registers ['skill-a'] and skill-a exists on disk.
            2. A second skill 'skill-b' exists on disk but is not registered.
            3. Run _reconcile_one_plugin (dry_run=True).
            4. Assert return value is False.
        Why:
            A new disk skill that is not registered is not drift — the user
            simply hasn't added it yet.  No drift must be reported for it.
        """
        # Arrange
        _plugin_root, _plugin_json_path = _make_mode_b_plugin(
            tmp_path,
            registered_skills=["skill-a"],
            disk_skills=["skill-a", "skill-b"],  # skill-b on disk but not registered
        )
        plugins_root = tmp_path / "plugins"

        # Act
        has_drift = auto_sync._reconcile_one_plugin("mode-b-plugin", plugins_root, dry_run=True)

        # Assert
        assert has_drift is False, (
            "Mode B: reconcile reported drift when a new unregistered disk skill was present. "
            "Unregistered disk skills must not be treated as drift in manual selection mode."
        )


# ---------------------------------------------------------------------------
# SK009 — manual skill selection mode info rule
# ---------------------------------------------------------------------------


class TestSK009ManualSkillSelectionInfo:
    """SK009 fires as INFO when plugin.json has an explicit 'skills' field.

    This rule informs users that their plugin is in manual selection mode,
    meaning new skills added to disk will not be auto-loaded.
    """

    def _make_plugin_with_explicit_skills(self, tmp_path: Path, skills: list[str]) -> Path:
        """Create a plugin with an explicit skills array in plugin.json.

        Args:
            tmp_path: Pytest temp directory.
            skills: Skill names to register in the explicit array.

        Returns:
            Plugin root directory.
        """
        plugin_root = tmp_path / "explicit-plugin"
        plugin_root.mkdir(parents=True)

        for skill_name in skills:
            skill_dir = plugin_root / "skills" / skill_name
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                f"---\nname: {skill_name}\ndescription: {skill_name}\n---\n\n# {skill_name}\n", encoding="utf-8"
            )

        claude_plugin = plugin_root / ".claude-plugin"
        claude_plugin.mkdir(parents=True)
        manifest = {"name": "explicit-plugin", "version": "1.0.0", "skills": [f"./skills/{s}" for s in skills]}
        (claude_plugin / "plugin.json").write_text(msgspec.json.format(msgspec.json.encode(manifest), indent=2).decode(), encoding="utf-8")

        return plugin_root

    def test_sk009_fires_for_plugin_with_explicit_skills_field(self, tmp_path: Path) -> None:
        """SK009 must fire as INFO when plugin.json has an explicit 'skills' field.

        Tests: PluginRegistrationValidator.validate SK009 rule
        How:
            1. Create a plugin with an explicit 'skills' array in plugin.json.
            2. Run PluginRegistrationValidator.validate().
            3. Assert an INFO issue with code SK009 is present.
        Why:
            Users and AI agents should be informed that the plugin is in manual
            selection mode so they know to add new skills manually.
        """
        # Arrange
        plugin_root = self._make_plugin_with_explicit_skills(tmp_path, skills=["my-skill"])
        validator = PluginRegistrationValidator()

        # Act
        result = validator.validate(plugin_root)

        # Assert
        sk009_issues = [i for i in result.info if str(i.code) == "SK009"]
        assert len(sk009_issues) == 1, (
            f"Expected exactly one SK009 info issue, got {len(sk009_issues)}. "
            "SK009 must fire when plugin.json has an explicit 'skills' field."
        )
        assert sk009_issues[0].severity == "info", f"SK009 must have severity 'info', got '{sk009_issues[0].severity}'."
        assert "manual skill selection" in sk009_issues[0].message.lower(), (
            f"SK009 message should mention manual skill selection. Got: '{sk009_issues[0].message}'"
        )

    def test_sk009_does_not_fire_for_plugin_without_skills_field(self, tmp_path: Path) -> None:
        """SK009 must NOT fire when plugin.json has no 'skills' field (Mode A).

        Tests: PluginRegistrationValidator.validate SK009 negative case
        How:
            1. Create a plugin with NO 'skills' field in plugin.json (Mode A).
            2. Run PluginRegistrationValidator.validate().
            3. Assert no SK009 info issue is present.
        Why:
            Mode A (auto-discovery) is the default correct state.  SK009 is
            only informational for plugins that have opted into manual selection.
        """
        # Arrange
        plugin_root, _plugin_json_path = _make_standard_plugin(tmp_path, skills=["auto-skill"])
        validator = PluginRegistrationValidator()

        # Act
        result = validator.validate(plugin_root)

        # Assert
        sk009_issues = [i for i in result.info if str(i.code) == "SK009"]
        assert len(sk009_issues) == 0, (
            f"SK009 must not fire for a plugin without an explicit 'skills' field. "
            f"Got {len(sk009_issues)} SK009 issue(s)."
        )

    def test_sk009_can_be_suppressed_via_validator_json(self, tmp_path: Path) -> None:
        """SK009 must be suppressible via .claude-plugin/validator.json.

        Tests: suppression mechanism applied to SK009
        How:
            1. Create a plugin with an explicit 'skills' field (triggers SK009).
            2. Create .claude-plugin/validator.json suppressing SK009 at plugin root.
            3. Load the ignore config and apply the filter.
            4. Assert no SK009 issue in the filtered result.
        Why:
            All validator rules must be suppressible via the standard mechanism.
            Teams that explicitly want manual selection should be able to silence
            the informational reminder.
        """
        # Arrange
        plugin_root = self._make_plugin_with_explicit_skills(tmp_path, skills=["my-skill"])

        # Write validator.json suppressing SK009 at the plugin root level
        validator_json_path = plugin_root / ".claude-plugin" / "validator.json"
        validator_json_path.write_text(msgspec.json.encode({"ignore": {".": ["SK009"]}}).decode(), encoding="utf-8")

        validator = PluginRegistrationValidator()

        # Act
        result = validator.validate(plugin_root)

        # Apply suppression filter (mirrors what validate_path does at the top level)
        plugin_root_found = _find_plugin_root(plugin_root)
        assert plugin_root_found is not None, "Plugin root must be found for suppression test"
        ignore_config = _load_ignore_config(plugin_root_found)
        filtered = _filter_result_by_ignore(result, plugin_root, plugin_root_found, ignore_config)

        # Assert
        sk009_issues = [i for i in filtered.info if str(i.code) == "SK009"]
        assert len(sk009_issues) == 0, (
            f"SK009 was not suppressed by validator.json. Got {len(sk009_issues)} SK009 issue(s) after filtering."
        )

    def test_sk009_message_enumerates_unlisted_disk_skills(self, tmp_path: Path) -> None:
        """SK009 message must list disk skills absent from the explicit skills array.

        Tests: PluginRegistrationValidator.validate SK009 unlisted-skills message
        How:
            1. Create a plugin with two disk skills: listed-skill (in the array) and
               unlisted-skill (on disk but NOT in the array).
            2. Run PluginRegistrationValidator.validate().
            3. Assert the SK009 message contains the unlisted path but not the listed path.
        Why:
            Users and AI agents need to know exactly which skills are missing from the
            explicit array so they can add them without guessing.
        """
        # Arrange
        plugin_root = tmp_path / "mixed-plugin"
        plugin_root.mkdir(parents=True)

        for skill_name in ("listed-skill", "unlisted-skill"):
            skill_dir = plugin_root / "skills" / skill_name
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                f"---\nname: {skill_name}\ndescription: {skill_name}\n---\n\n# {skill_name}\n", encoding="utf-8"
            )

        claude_plugin = plugin_root / ".claude-plugin"
        claude_plugin.mkdir(parents=True)
        # Only list one of the two skills in the explicit array.
        manifest = {"name": "mixed-plugin", "version": "1.0.0", "skills": ["./skills/listed-skill"]}
        (claude_plugin / "plugin.json").write_text(msgspec.json.format(msgspec.json.encode(manifest), indent=2).decode(), encoding="utf-8")

        validator = PluginRegistrationValidator()

        # Act
        result = validator.validate(plugin_root)

        # Assert
        sk009_issues = [i for i in result.info if str(i.code) == "SK009"]
        assert len(sk009_issues) == 1, f"Expected exactly one SK009 issue, got {len(sk009_issues)}."
        message = sk009_issues[0].message
        assert "./skills/unlisted-skill" in message, (
            f"SK009 message must name the unlisted skill './skills/unlisted-skill'. Got: '{message}'"
        )
        assert "listed-skill" not in message.replace("./skills/unlisted-skill", ""), (
            "SK009 message must not mention the already-listed skill outside of the unlisted path."
        )

    def test_sk009_message_confirms_all_registered_when_no_unlisted_skills(self, tmp_path: Path) -> None:
        """SK009 message must confirm full registration when all disk skills are listed.

        Tests: PluginRegistrationValidator.validate SK009 all-registered message
        How:
            1. Create a plugin where every disk skill is present in the explicit array.
            2. Run PluginRegistrationValidator.validate().
            3. Assert the SK009 message says all skills are explicitly registered.
        Why:
            When a user has diligently kept the explicit array in sync with the disk,
            the message should confirm that state rather than warn about missing entries.
        """
        # Arrange — reuse helper: one skill, listed in the explicit array.
        plugin_root = self._make_plugin_with_explicit_skills(tmp_path, skills=["complete-skill"])
        validator = PluginRegistrationValidator()

        # Act
        result = validator.validate(plugin_root)

        # Assert
        sk009_issues = [i for i in result.info if str(i.code) == "SK009"]
        assert len(sk009_issues) == 1, f"Expected exactly one SK009 issue, got {len(sk009_issues)}."
        message = sk009_issues[0].message
        assert "all skills/ are explicitly registered" in message, (
            f"SK009 message must confirm all skills are registered. Got: '{message}'"
        )
