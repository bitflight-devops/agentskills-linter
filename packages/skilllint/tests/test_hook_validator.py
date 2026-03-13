"""Unit tests for HookValidator and hook file type detection.

Tests:
- FileType.detect_file_type() for hooks.json, .js and .cjs in hooks/
- HookValidator on hooks.json files (HK001-HK003)
- HOOK_SCRIPT files validated without UNKNOWN error (no content validation)
"""

from __future__ import annotations

import msgspec.json
from typing import TYPE_CHECKING

import pytest

from skilllint.plugin_validator import FileType, HookValidator

if TYPE_CHECKING:
    from pathlib import Path


class TestDetectFileType:
    """Test detect_file_type for hook files."""

    def test_hooks_json_detected_as_hook_config(self, tmp_path: Path) -> None:
        """Test hooks.json is detected as HOOK_CONFIG.

        Tests: FileType detection for hooks.json
        How: Create hooks/hooks.json, call detect_file_type
        Why: Ensure hooks.json files are routed to HookValidator
        """
        hooks_dir = tmp_path / "hooks"
        hooks_dir.mkdir()
        hooks_json = hooks_dir / "hooks.json"
        hooks_json.write_text("{}")

        result = FileType.detect_file_type(hooks_json)
        assert result == FileType.HOOK_CONFIG

    def test_js_in_hooks_dir_detected_as_hook_script(self, tmp_path: Path) -> None:
        """Test .js file in hooks/ directory is detected as HOOK_SCRIPT.

        Tests: FileType detection for .js hook scripts
        How: Create hooks/my-hook.js, call detect_file_type
        Why: HOOK_SCRIPT routes hook scripts away from UNKNOWN so they do not
             trigger the 'cannot determine file type' error in _validate_single_path
        """
        hooks_dir = tmp_path / "hooks"
        hooks_dir.mkdir()
        hook_js = hooks_dir / "my-hook.js"
        hook_js.write_text("#!/usr/bin/env node\nconsole.log('hook');")

        result = FileType.detect_file_type(hook_js)
        assert result == FileType.HOOK_SCRIPT

    def test_cjs_in_hooks_dir_detected_as_hook_script(self, tmp_path: Path) -> None:
        """Test .cjs file in hooks/ directory is detected as HOOK_SCRIPT.

        Tests: FileType detection for .cjs hook scripts
        How: Create hooks/my-hook.cjs, call detect_file_type
        Why: Claude Code hooks are commonly .cjs files; must be HOOK_SCRIPT not UNKNOWN
        """
        hooks_dir = tmp_path / "hooks"
        hooks_dir.mkdir()
        hook_cjs = hooks_dir / "my-hook.cjs"
        hook_cjs.write_text("#!/usr/bin/env node\nconsole.log('hook');")

        result = FileType.detect_file_type(hook_cjs)
        assert result == FileType.HOOK_SCRIPT

    def test_js_outside_hooks_dir_not_detected_as_hook(self, tmp_path: Path) -> None:
        """Test .js file outside hooks/ directory is detected as UNKNOWN.

        Tests: FileType detection scope limitation
        How: Create scripts/util.js, call detect_file_type
        Why: Only .js/.cjs files inside a hooks/ directory are HOOK_SCRIPT
        """
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        util_js = scripts_dir / "util.js"
        util_js.write_text("console.log('util');")

        result = FileType.detect_file_type(util_js)
        assert result == FileType.UNKNOWN

    def test_hooks_json_at_top_level_detected(self, tmp_path: Path) -> None:
        """Test hooks.json at any path level is detected as HOOK_CONFIG.

        Tests: FileType detection for hooks.json regardless of parent dir name
        How: Create top-level hooks.json, call detect_file_type
        Why: hooks.json filename is sufficient for identification
        """
        hooks_json = tmp_path / "hooks.json"
        hooks_json.write_text("{}")

        result = FileType.detect_file_type(hooks_json)
        assert result == FileType.HOOK_CONFIG


class TestHookConfigValidation:
    """Test HookValidator on hooks.json files."""

    def test_valid_hooks_json_passes(self, tmp_path: Path) -> None:
        """Test valid hooks.json passes validation.

        Tests: HookValidator happy path
        How: Write valid hooks.json with SubagentStop event, validate
        Why: Ensure well-formed hook configs pass without errors
        """
        hooks_json = tmp_path / "hooks.json"
        hooks_json.write_text(
            msgspec.json.encode({
                "hooks": {"SubagentStop": [{"hooks": [{"type": "prompt", "prompt": "Check the output"}]}]}
            }).decode()
        )

        validator = HookValidator()
        result = validator.validate(hooks_json)

        assert result.passed is True
        assert len(result.errors) == 0

    def test_invalid_json_fails_hk001(self, tmp_path: Path) -> None:
        """Test invalid JSON triggers HK001 error.

        Tests: JSON parse error handling
        How: Write malformed JSON, validate
        Why: Ensure clear error on unparseable hooks.json
        """
        hooks_json = tmp_path / "hooks.json"
        hooks_json.write_text("{not valid json}")

        validator = HookValidator()
        result = validator.validate(hooks_json)

        assert result.passed is False
        assert any(e.code == "HK001" for e in result.errors)

    def test_missing_hooks_key_fails_hk001(self, tmp_path: Path) -> None:
        """Test missing 'hooks' key triggers HK001 error.

        Tests: Top-level structure validation
        How: Write {"other": {}}, validate
        Why: hooks.json must have "hooks" as top-level key
        """
        hooks_json = tmp_path / "hooks.json"
        hooks_json.write_text(msgspec.json.encode({"other": {}}).decode())

        validator = HookValidator()
        result = validator.validate(hooks_json)

        assert result.passed is False
        assert any(e.code == "HK001" for e in result.errors)

    def test_invalid_event_type_fails_hk002(self, tmp_path: Path) -> None:
        """Test invalid event type triggers HK002 error.

        Tests: Event type validation
        How: Write {"hooks": {"InvalidEvent": [...]}}, validate
        Why: Only valid Claude Code event types should be accepted
        """
        hooks_json = tmp_path / "hooks.json"
        hooks_json.write_text(
            msgspec.json.encode({
                "hooks": {"InvalidEvent": [{"hooks": [{"type": "command", "command": "echo hi"}]}]}
            }).decode()
        )

        validator = HookValidator()
        result = validator.validate(hooks_json)

        assert result.passed is False
        assert any(e.code == "HK002" for e in result.errors)

    def test_valid_event_types_accepted(self, tmp_path: Path) -> None:
        """Test all valid event types are accepted.

        Tests: Complete event type coverage
        How: Write hooks.json with each valid event type, validate each
        Why: Ensure no false positives on valid event types
        """
        valid_events = ["PreToolUse", "PostToolUse", "Notification", "SubagentStop", "Stop"]

        for event in valid_events:
            hooks_json = tmp_path / "hooks.json"
            hooks_json.write_text(
                msgspec.json.encode({
                    "hooks": {event: [{"hooks": [{"type": "command", "command": "echo test"}]}]}
                }).decode()
            )

            validator = HookValidator()
            result = validator.validate(hooks_json)

            assert result.passed is True, f"Event type '{event}' should be valid"

    def test_invalid_hook_entry_fails_hk003(self, tmp_path: Path) -> None:
        """Test hook entry missing 'type' field triggers HK003 error.

        Tests: Hook entry type field validation
        How: Write hook entry without "type" field, validate
        Why: Each hook entry must specify its type
        """
        hooks_json = tmp_path / "hooks.json"
        hooks_json.write_text(
            msgspec.json.encode({"hooks": {"PreToolUse": [{"hooks": [{"command": "echo missing type"}]}]}}).decode()
        )

        validator = HookValidator()
        result = validator.validate(hooks_json)

        assert result.passed is False
        assert any(e.code == "HK003" for e in result.errors)

    def test_command_hook_missing_command_field_fails_hk003(self, tmp_path: Path) -> None:
        """Test command hook without 'command' field triggers HK003 error.

        Tests: Command hook field validation
        How: Write type "command" but omit "command" key, validate
        Why: Command hooks must have a command to execute
        """
        hooks_json = tmp_path / "hooks.json"
        hooks_json.write_text(msgspec.json.encode({"hooks": {"Stop": [{"hooks": [{"type": "command"}]}]}}).decode())

        validator = HookValidator()
        result = validator.validate(hooks_json)

        assert result.passed is False
        assert any(e.code == "HK003" for e in result.errors)

    def test_prompt_hook_missing_prompt_field_fails_hk003(self, tmp_path: Path) -> None:
        """Test prompt hook without 'prompt' field triggers HK003 error.

        Tests: Prompt hook field validation
        How: Write type "prompt" but omit "prompt" key, validate
        Why: Prompt hooks must have a prompt string
        """
        hooks_json = tmp_path / "hooks.json"
        hooks_json.write_text(
            msgspec.json.encode({"hooks": {"SubagentStop": [{"hooks": [{"type": "prompt"}]}]}}).decode()
        )

        validator = HookValidator()
        result = validator.validate(hooks_json)

        assert result.passed is False
        assert any(e.code == "HK003" for e in result.errors)

    def test_can_fix_returns_false(self) -> None:
        """Test can_fix() returns False.

        Tests: HookValidator auto-fix capability
        How: Call can_fix()
        Why: Hook validation cannot be auto-fixed
        """
        validator = HookValidator()
        assert validator.can_fix() is False

    def test_fix_raises_not_implemented(self, tmp_path: Path) -> None:
        """Test fix() raises NotImplementedError.

        Tests: HookValidator fix() contract
        How: Call fix(), expect NotImplementedError
        Why: Hook fixes require manual correction
        """
        validator = HookValidator()
        with pytest.raises(NotImplementedError):
            validator.fix(tmp_path / "hooks.json")

    def test_hooks_json_with_matcher_and_timeout(self, tmp_path: Path) -> None:
        """Test hooks.json with optional matcher and timeout fields passes.

        Tests: Optional fields are accepted
        How: Write hooks.json with matcher and timeout, validate
        Why: These optional fields should not cause validation errors
        """
        hooks_json = tmp_path / "hooks.json"
        hooks_json.write_text(
            msgspec.json.encode({
                "hooks": {
                    "PreToolUse": [
                        {
                            "matcher": "Bash",
                            "hooks": [{"type": "command", "command": "echo checking bash", "timeout": 5}],
                        }
                    ]
                }
            }).decode()
        )

        validator = HookValidator()
        result = validator.validate(hooks_json)

        assert result.passed is True
        assert len(result.errors) == 0
