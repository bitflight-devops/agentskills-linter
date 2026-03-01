"""Shared pytest fixtures for plugin-validator tests.

Provides reusable test fixtures for:
- CLI runner setup
- Sample skill/agent/plugin directories
- Invalid frontmatter samples
- Broken link samples
"""

from __future__ import annotations

import importlib.util
import os
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from typer.testing import CliRunner, Result

if TYPE_CHECKING:
    from collections.abc import Generator


# Load the plugin_validator module directly from its path using importlib so
# tests can run without relying on it being installed as a package.
_VALIDATOR_PATH = Path(__file__).parent.parent / "plugin_validator.py"
spec = importlib.util.spec_from_file_location("plugin_validator", _VALIDATOR_PATH)
if spec and spec.loader:
    plugin_validator = importlib.util.module_from_spec(spec)
    sys.modules["plugin_validator"] = plugin_validator
    spec.loader.exec_module(plugin_validator)

_ANSI_ESCAPE = re.compile(rb"\x1b\[[0-9;]*[mGKHFJA-Z]")


class _PlainCliRunner(CliRunner):
    """CliRunner that strips ANSI escape codes from captured output.

    Click 8.x no longer strips ANSI from result.stdout. GitHub Actions sets
    FORCE_COLOR=1, causing Rich to emit ANSI codes regardless of NO_COLOR or
    stream-TTY status. Stripping at the byte level is the only reliable fix.
    """

    def invoke(self, *args: Any, **kwargs: Any) -> Result:
        """Invoke CLI and strip ANSI codes from stdout/stderr bytes."""
        result = super().invoke(*args, **kwargs)
        result.stdout_bytes = _ANSI_ESCAPE.sub(b"", result.stdout_bytes)
        if result.stderr_bytes is not None:
            result.stderr_bytes = _ANSI_ESCAPE.sub(b"", result.stderr_bytes)
        return result


@pytest.fixture
def cli_runner() -> CliRunner:
    """Provide CliRunner configured for testing.

    Returns:
        _PlainCliRunner that strips ANSI escape codes
        from captured output for environment-independent string assertions.
    """
    return _PlainCliRunner()


@pytest.fixture
def sample_skill_dir(tmp_path: Path) -> Path:
    """Create sample skill directory with valid SKILL.md.

    Args:
        tmp_path: Pytest temporary directory fixture

    Returns:
        Path to skill directory containing valid SKILL.md
    """
    skill_dir = tmp_path / "test-skill"
    skill_dir.mkdir()

    # Create valid SKILL.md
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("""---
description: Use this skill when you need a test skill for validation
tools: Read, Write, Grep
model: sonnet
---

# Test Skill

This is a test skill with valid frontmatter.

## Usage

Use this skill for testing purposes.
""")

    return skill_dir


@pytest.fixture
def sample_agent_dir(tmp_path: Path) -> Path:
    """Create sample agent directory with valid agent.md.

    Args:
        tmp_path: Pytest temporary directory fixture

    Returns:
        Path to directory containing valid agent.md
    """
    agent_dir = tmp_path / "agents"
    agent_dir.mkdir()

    # Create valid agent file
    agent_md = agent_dir / "test-agent.md"
    agent_md.write_text("""---
name: test-agent
description: Use this agent when testing validation workflows
tools: Read, Grep
model: sonnet
---

# Test Agent Prompt

This agent is for testing purposes.

Follow these steps:
1. Read the input
2. Process the data
3. Return results
""")

    return agent_dir


@pytest.fixture
def sample_plugin_dir(tmp_path: Path) -> Path:
    """Create sample plugin directory with plugin.json.

    Args:
        tmp_path: Pytest temporary directory fixture

    Returns:
        Path to plugin directory containing .claude-plugin/plugin.json
    """
    plugin_dir = tmp_path / "test-plugin"
    plugin_dir.mkdir()

    # Create .claude-plugin directory
    claude_plugin = plugin_dir / ".claude-plugin"
    claude_plugin.mkdir()

    # Create valid plugin.json
    plugin_json = claude_plugin / "plugin.json"
    plugin_json.write_text("""{
  "name": "test-plugin",
  "version": "1.0.0",
  "skills": ["./skills/test-skill/"],
  "agents": ["./agents/test-agent.md"]
}
""")

    # Create skills directory with valid skill
    skills_dir = plugin_dir / "skills" / "test-skill"
    skills_dir.mkdir(parents=True)
    (skills_dir / "SKILL.md").write_text("""---
description: Test skill for plugin validation
---

# Test Skill

This is a test skill.
""")

    # Create agents directory with valid agent
    agents_dir = plugin_dir / "agents"
    agents_dir.mkdir()
    (agents_dir / "test-agent.md").write_text("""---
name: test-agent
description: Test agent for validation
---

# Test Agent

This is a test agent.
""")

    return plugin_dir


@pytest.fixture
def invalid_frontmatter_samples() -> dict[str, str]:
    """Provide samples of invalid frontmatter for testing.

    Returns:
        Dictionary mapping error scenario to invalid frontmatter content
    """
    return {
        "missing_delimiters": "description: No frontmatter delimiters\n\n# Content",
        "yaml_array_tools": """---
description: Test with YAML array tools
tools:
  - Read
  - Write
---

# Content
""",
        "multiline_description": """---
description: >-
  This is a multiline description
  that spans multiple lines
---

# Content
""",
        "unquoted_colon": """---
description: This has: a colon without quotes
---

# Content
""",
        "uppercase_name": """---
name: Test-Skill
description: Test skill
---

# Content
""",
        "underscore_name": """---
name: test_skill
description: Test skill
---

# Content
""",
        "missing_required_agent_fields": """---
name: test-agent
---

# Agent without description
""",
        "invalid_model": """---
description: Test skill
model: gpt-4
---

# Invalid model name
""",
    }


@pytest.fixture
def broken_link_samples(tmp_path: Path) -> dict[str, tuple[Path, str]]:
    """Provide samples with broken links for testing.

    Args:
        tmp_path: Pytest temporary directory fixture

    Returns:
        Dictionary mapping scenario to (file_path, content) tuple
    """
    skill_dir = tmp_path / "link-test-skill"
    skill_dir.mkdir()

    # Create reference file that exists
    refs_dir = skill_dir / "references"
    refs_dir.mkdir()
    (refs_dir / "existing.md").write_text("# Existing Reference\n")

    samples: dict[str, tuple[Path, str]] = {}

    # Broken link to non-existent file
    samples["broken_link"] = (
        skill_dir / "SKILL.md",
        """---
description: Test skill with broken link
---

# Test Skill

See [broken link](./references/missing.md) for details.
""",
    )

    # Link without ./ prefix
    samples["missing_prefix"] = (
        skill_dir / "SKILL.md",
        """---
description: Test skill with missing prefix
---

# Test Skill

See [no prefix](references/existing.md) for details.
""",
    )

    # Valid link
    samples["valid_link"] = (
        skill_dir / "SKILL.md",
        """---
description: Test skill with valid link
---

# Test Skill

See [good link](./references/existing.md) for details.
""",
    )

    # External link (should be ignored)
    samples["external_link"] = (
        skill_dir / "SKILL.md",
        """---
description: Test skill with external link
---

# Test Skill

See [external](https://example.com) for details.
""",
    )

    return samples


@pytest.fixture
def no_color_env() -> Generator[None, None, None]:
    """Set NO_COLOR=1 environment variable for tests.

    Yields:
        None (environment variable is set during test)
    """
    original = os.environ.get("NO_COLOR")
    os.environ["NO_COLOR"] = "1"
    yield
    if original is None:
        os.environ.pop("NO_COLOR", None)
    else:
        os.environ["NO_COLOR"] = original


@pytest.fixture
def mock_frontmatter_file(tmp_path: Path) -> Path:
    """Create temporary file with frontmatter for testing.

    Args:
        tmp_path: Pytest temporary directory fixture

    Returns:
        Path to file with frontmatter
    """
    test_file = tmp_path / "test.md"
    test_file.write_text("""---
name: test-skill
description: Test skill for validation
tools: Read, Write
---

# Test Content

This is test content.
""")
    return test_file
