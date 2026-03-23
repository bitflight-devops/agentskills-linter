"""Tests for the ``skilllint docs`` CLI subcommand group.

Tests: All five ``docs`` subcommands: fetch, latest, sections, section, verify
How: Typer CliRunner invokes the main app with ``["docs", <subcommand>, ...]``
     while pytest-mock patches the vendor_cache functions at the
     ``skilllint.cli_docs`` import boundary so no network or filesystem
     access is ever performed.
Why: The docs subcommand group is a pure CLI adapter over vendor_cache.
     These tests verify that the adapter correctly translates vendor_cache
     return values and exceptions into exit codes and output, and that it
     forwards CLI flags as the correct keyword arguments.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

import skilllint.plugin_validator as plugin_validator
from skilllint.vendor_cache import CacheResult, CacheStatus, IntegrityResult, IntegrityStatus, NoCacheError

if TYPE_CHECKING:
    from pytest_mock import MockerFixture
    from typer.testing import CliRunner


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TEST_URL = "https://docs.example.com/en/docs/settings.md"
_TEST_PAGE = "settings"
_TEST_PATH = Path("/tmp/settings-2024-01-01-0000.md")


def _cache_result(status: CacheStatus, path: Path = _TEST_PATH) -> CacheResult:
    """Build a minimal CacheResult for a given status."""
    return CacheResult(path=path, status=status, page_name=_TEST_PAGE, url=_TEST_URL)


def _integrity_result(
    status: IntegrityStatus,
    computed_sha256: str = "abc123",
    expected_sha256: str | None = "abc123",
    computed_bytes: int = 100,
    expected_bytes: int | None = 100,
) -> IntegrityResult:
    """Build a minimal IntegrityResult for a given status."""
    return IntegrityResult(
        status=status,
        file_path=_TEST_PATH,
        computed_sha256=computed_sha256,
        expected_sha256=expected_sha256,
        computed_bytes=computed_bytes,
        expected_bytes=expected_bytes,
    )


# ---------------------------------------------------------------------------
# docs fetch
# ---------------------------------------------------------------------------


class TestDocsFetch:
    """Tests for the ``docs fetch`` subcommand.

    Scope: Exit codes, stdout path output, stderr status messages, and
    correct forwarding of --ttl / --force flags to fetch_or_cached.
    """

    def test_new_fetch_exits_zero_and_prints_path(self, cli_runner: CliRunner, mocker: MockerFixture) -> None:
        """First fetch (NEW status) exits 0 and writes the cached path to stdout.

        Tests: docs fetch success path for a brand-new page
        How: Mock fetch_or_cached returning CacheStatus.NEW; invoke CLI; check
             exit code and that the path string appears in stdout
        Why: Agents capture stdout to locate the cached file; a missing path
             would silently break downstream pipeline steps
        """
        # Arrange
        mock_fetch = mocker.patch("skilllint.cli_docs.fetch_or_cached")
        mock_fetch.return_value = _cache_result(CacheStatus.NEW)

        # Act
        result = cli_runner.invoke(plugin_validator.app, ["docs", "fetch", _TEST_URL])

        # Assert
        assert result.exit_code == 0
        assert str(_TEST_PATH) in result.output

    def test_fresh_cache_hit_exits_zero(self, cli_runner: CliRunner, mocker: MockerFixture) -> None:
        """Cache hit within TTL (FRESH status) exits 0 and prints the path.

        Tests: docs fetch when content is already fresh in cache
        How: Mock fetch_or_cached returning CacheStatus.FRESH; verify exit 0
        Why: FRESH is the happy path for repeated invocations — must not error
        """
        # Arrange
        mock_fetch = mocker.patch("skilllint.cli_docs.fetch_or_cached")
        mock_fetch.return_value = _cache_result(CacheStatus.FRESH)

        # Act
        result = cli_runner.invoke(plugin_validator.app, ["docs", "fetch", _TEST_URL])

        # Assert
        assert result.exit_code == 0
        assert str(_TEST_PATH) in result.output

    def test_refreshed_cache_exits_zero(self, cli_runner: CliRunner, mocker: MockerFixture) -> None:
        """Stale cache that was refreshed (REFRESHED status) exits 0.

        Tests: docs fetch when stale content was successfully re-fetched
        How: Mock fetch_or_cached returning CacheStatus.REFRESHED; verify exit 0
        Why: REFRESHED is a normal success path; must not be treated as error
        """
        # Arrange
        mock_fetch = mocker.patch("skilllint.cli_docs.fetch_or_cached")
        mock_fetch.return_value = _cache_result(CacheStatus.REFRESHED)

        # Act
        result = cli_runner.invoke(plugin_validator.app, ["docs", "fetch", _TEST_URL])

        # Assert
        assert result.exit_code == 0

    def test_unchanged_cache_exits_zero(self, cli_runner: CliRunner, mocker: MockerFixture) -> None:
        """Stale cache whose content is identical remotely (UNCHANGED) exits 0.

        Tests: docs fetch when remote content is identical to cached copy
        How: Mock fetch_or_cached returning CacheStatus.UNCHANGED; verify exit 0
        Why: UNCHANGED is a valid success path; sidecar was touched but no new file
        """
        # Arrange
        mock_fetch = mocker.patch("skilllint.cli_docs.fetch_or_cached")
        mock_fetch.return_value = _cache_result(CacheStatus.UNCHANGED)

        # Act
        result = cli_runner.invoke(plugin_validator.app, ["docs", "fetch", _TEST_URL])

        # Assert
        assert result.exit_code == 0

    def test_stale_fallback_exits_zero_with_warning(self, cli_runner: CliRunner, mocker: MockerFixture) -> None:
        """Network-unavailable stale fallback (STALE) exits 0 with a warning.

        Tests: docs fetch when network is down and stale cache is served
        How: Mock fetch_or_cached returning CacheStatus.STALE; verify exit 0
             and that a warning indicator appears in combined output
        Why: Offline fallback must not exit 1 — consumers should still get the
             cached path; the warning informs the caller of degraded freshness
        """
        # Arrange
        mock_fetch = mocker.patch("skilllint.cli_docs.fetch_or_cached")
        mock_fetch.return_value = _cache_result(CacheStatus.STALE)

        # Act
        result = cli_runner.invoke(plugin_validator.app, ["docs", "fetch", _TEST_URL])

        # Assert
        assert result.exit_code == 0
        # Path is still printed so downstream steps can proceed
        assert str(_TEST_PATH) in result.output
        # Warning indicator is present in the combined output
        assert "stale" in result.output.lower()

    def test_no_cache_error_exits_one_with_error_message(self, cli_runner: CliRunner, mocker: MockerFixture) -> None:
        """NoCacheError (no cache and network down) exits 1 with error output.

        Tests: docs fetch fatal failure path when no cache and no network
        How: Mock fetch_or_cached raising NoCacheError; verify exit code 1
             and that the URL appears in output
        Why: Exit 1 signals to CI and agent pipelines that the step failed;
             error details help diagnose connectivity issues
        """
        # Arrange
        mock_fetch = mocker.patch("skilllint.cli_docs.fetch_or_cached")
        mock_fetch.side_effect = NoCacheError(url=_TEST_URL, reason="connection refused")

        # Act
        result = cli_runner.invoke(plugin_validator.app, ["docs", "fetch", _TEST_URL])

        # Assert
        assert result.exit_code == 1
        assert _TEST_URL in result.output

    def test_force_flag_passes_force_true_to_fetch_or_cached(
        self, cli_runner: CliRunner, mocker: MockerFixture
    ) -> None:
        """--force flag causes force=True to be forwarded to fetch_or_cached.

        Tests: docs fetch --force CLI flag forwarding
        How: Mock fetch_or_cached; invoke with --force; inspect call kwargs
        Why: Misrouted flags silently defeat the intended cache-bypass behavior
        """
        # Arrange
        mock_fetch = mocker.patch("skilllint.cli_docs.fetch_or_cached")
        mock_fetch.return_value = _cache_result(CacheStatus.NEW)

        # Act
        cli_runner.invoke(plugin_validator.app, ["docs", "fetch", "--force", _TEST_URL])

        # Assert
        mock_fetch.assert_called_once()
        _, kwargs = mock_fetch.call_args
        assert kwargs.get("force") is True

    def test_ttl_option_is_forwarded_as_ttl_hours(self, cli_runner: CliRunner, mocker: MockerFixture) -> None:
        """--ttl value is forwarded as the ttl_hours keyword argument.

        Tests: docs fetch --ttl option forwarding
        How: Mock fetch_or_cached; invoke with --ttl 12; inspect call kwargs
        Why: Custom TTL values are silently ignored if the kwarg name is wrong
        """
        # Arrange
        mock_fetch = mocker.patch("skilllint.cli_docs.fetch_or_cached")
        mock_fetch.return_value = _cache_result(CacheStatus.FRESH)

        # Act
        cli_runner.invoke(plugin_validator.app, ["docs", "fetch", "--ttl", "12", _TEST_URL])

        # Assert
        mock_fetch.assert_called_once()
        _, kwargs = mock_fetch.call_args
        assert kwargs.get("ttl_hours") == pytest.approx(12.0)

    def test_default_force_is_false(self, cli_runner: CliRunner, mocker: MockerFixture) -> None:
        """Without --force the forwarded force kwarg is False.

        Tests: docs fetch default force=False behaviour
        How: Invoke without --force; inspect call kwargs
        Why: Confirms the default does not bypass cache
        """
        # Arrange
        mock_fetch = mocker.patch("skilllint.cli_docs.fetch_or_cached")
        mock_fetch.return_value = _cache_result(CacheStatus.FRESH)

        # Act
        cli_runner.invoke(plugin_validator.app, ["docs", "fetch", _TEST_URL])

        # Assert
        _, kwargs = mock_fetch.call_args
        assert kwargs.get("force") is False


# ---------------------------------------------------------------------------
# docs latest
# ---------------------------------------------------------------------------


class TestDocsLatest:
    """Tests for the ``docs latest`` subcommand.

    Scope: Exit codes and stdout path output when a cached file is or is not found.
    """

    def test_found_path_exits_zero_and_prints_path(self, cli_runner: CliRunner, mocker: MockerFixture) -> None:
        """When find_latest returns a Path, exits 0 and prints the path to stdout.

        Tests: docs latest success path
        How: Mock find_latest returning a Path; verify exit 0 and path in output
        Why: Agents capture stdout for the file path; missing output breaks pipelines
        """
        # Arrange
        cached = Path("/tmp/settings-2024-01-01-0000.md")
        mock_find = mocker.patch("skilllint.cli_docs.find_latest")
        mock_find.return_value = cached

        # Act
        result = cli_runner.invoke(plugin_validator.app, ["docs", "latest", "settings"])

        # Assert
        assert result.exit_code == 0
        assert str(cached) in result.output

    def test_not_found_exits_one(self, cli_runner: CliRunner, mocker: MockerFixture) -> None:
        """When find_latest returns None, exits 1.

        Tests: docs latest failure path when no cached file exists
        How: Mock find_latest returning None; verify exit code 1
        Why: Exit 1 signals the page has never been fetched; downstream steps
             can branch on this rather than receiving a blank path
        """
        # Arrange
        mock_find = mocker.patch("skilllint.cli_docs.find_latest")
        mock_find.return_value = None

        # Act
        result = cli_runner.invoke(plugin_validator.app, ["docs", "latest", "settings"])

        # Assert
        assert result.exit_code == 1

    def test_page_name_forwarded_to_find_latest(self, cli_runner: CliRunner, mocker: MockerFixture) -> None:
        """The page_name argument is forwarded verbatim to find_latest.

        Tests: docs latest argument forwarding
        How: Invoke with a distinct page name; assert find_latest called with it
        Why: Silent name transformation would look up the wrong cache entry
        """
        # Arrange
        mock_find = mocker.patch("skilllint.cli_docs.find_latest")
        mock_find.return_value = Path("/tmp/claude-code--settings-2024-01-01-0000.md")

        # Act
        cli_runner.invoke(plugin_validator.app, ["docs", "latest", "claude-code--settings"])

        # Assert
        mock_find.assert_called_once_with("claude-code--settings")


# ---------------------------------------------------------------------------
# docs sections
# ---------------------------------------------------------------------------


class TestDocsSections:
    """Tests for the ``docs sections`` subcommand.

    Scope: Stdout output of the section index table and argument forwarding.
    """

    def test_table_printed_to_stdout_exits_zero(self, cli_runner: CliRunner, mocker: MockerFixture) -> None:
        """format_section_index output is printed to stdout and exits 0.

        Tests: docs sections success path
        How: Mock format_section_index returning a table string; verify
             the string appears in stdout and exit code is 0
        Why: Section index output must be machine-readable from stdout
        """
        # Arrange
        table = "index  level  heading  lines\n-----  -----  -------  -----\n0      1      Intro    1-10"
        mock_fmt = mocker.patch("skilllint.cli_docs.format_section_index")
        mock_fmt.return_value = table

        # Act
        result = cli_runner.invoke(plugin_validator.app, ["docs", "sections", "/tmp/settings.md"])

        # Assert
        assert result.exit_code == 0
        assert table in result.output

    def test_file_path_forwarded_to_format_section_index(self, cli_runner: CliRunner, mocker: MockerFixture) -> None:
        """The file_path argument is forwarded as a Path to format_section_index.

        Tests: docs sections argument forwarding
        How: Invoke with a file path string; assert format_section_index
             called with the corresponding Path object
        Why: String-to-Path conversion must occur before delegation
        """
        # Arrange
        mock_fmt = mocker.patch("skilllint.cli_docs.format_section_index")
        mock_fmt.return_value = "index  level  heading  lines"

        # Act
        cli_runner.invoke(plugin_validator.app, ["docs", "sections", "/tmp/settings.md"])

        # Assert
        mock_fmt.assert_called_once_with(Path("/tmp/settings.md"))


# ---------------------------------------------------------------------------
# docs section
# ---------------------------------------------------------------------------


class TestDocsSection:
    """Tests for the ``docs section`` subcommand.

    Scope: Exit codes and stdout output when a heading is found or not found.
    """

    def test_found_section_exits_zero_and_prints_text(self, cli_runner: CliRunner, mocker: MockerFixture) -> None:
        """When read_section returns text, exits 0 and prints the section text.

        Tests: docs section success path
        How: Mock read_section returning a non-empty string; verify exit 0
             and the text appears in stdout
        Why: Section text is consumed by agent pipelines; wrong exit code
             or missing output breaks downstream processing
        """
        # Arrange
        section_text = "## Installation\n\nRun `pip install foo`.\n"
        mock_read = mocker.patch("skilllint.cli_docs.read_section")
        mock_read.return_value = section_text

        # Act
        result = cli_runner.invoke(plugin_validator.app, ["docs", "section", "/tmp/settings.md", "Installation"])

        # Assert
        assert result.exit_code == 0
        assert "Installation" in result.output

    def test_not_found_exits_one(self, cli_runner: CliRunner, mocker: MockerFixture) -> None:
        """When read_section returns None, exits 1.

        Tests: docs section failure path when heading does not exist
        How: Mock read_section returning None; verify exit code 1
        Why: Exit 1 allows callers to detect a missing section without
             parsing stdout for an empty string
        """
        # Arrange
        mock_read = mocker.patch("skilllint.cli_docs.read_section")
        mock_read.return_value = None

        # Act
        result = cli_runner.invoke(plugin_validator.app, ["docs", "section", "/tmp/settings.md", "NonExistentHeading"])

        # Assert
        assert result.exit_code == 1

    def test_file_path_and_heading_forwarded_to_read_section(
        self, cli_runner: CliRunner, mocker: MockerFixture
    ) -> None:
        """Both file_path and heading arguments are forwarded to read_section.

        Tests: docs section argument forwarding
        How: Invoke with specific path and heading; assert read_section
             called with Path object and heading string
        Why: Argument misrouting would silently look up the wrong section
        """
        # Arrange
        mock_read = mocker.patch("skilllint.cli_docs.read_section")
        mock_read.return_value = "## Config\n\nSome content.\n"

        # Act
        cli_runner.invoke(plugin_validator.app, ["docs", "section", "/tmp/settings.md", "Config"])

        # Assert
        mock_read.assert_called_once_with(Path("/tmp/settings.md"), "Config")


# ---------------------------------------------------------------------------
# docs verify
# ---------------------------------------------------------------------------


class TestDocsVerify:
    """Tests for the ``docs verify`` subcommand.

    Scope: Exit codes for INTACT, MODIFIED, and UNVERIFIABLE integrity statuses.
    """

    def test_intact_exits_zero(self, cli_runner: CliRunner, mocker: MockerFixture) -> None:
        """INTACT integrity status exits 0.

        Tests: docs verify success path when file matches its sidecar
        How: Mock verify_integrity returning INTACT IntegrityResult; verify exit 0
        Why: Exit 0 signals to callers that the cached file is trustworthy
        """
        # Arrange
        mock_verify = mocker.patch("skilllint.cli_docs.verify_integrity")
        mock_verify.return_value = _integrity_result(IntegrityStatus.INTACT)

        # Act
        result = cli_runner.invoke(plugin_validator.app, ["docs", "verify", str(_TEST_PATH)])

        # Assert
        assert result.exit_code == 0

    def test_intact_output_contains_sha256(self, cli_runner: CliRunner, mocker: MockerFixture) -> None:
        """INTACT output includes the computed SHA-256 digest.

        Tests: docs verify INTACT stdout content
        How: Mock verify_integrity with a known sha256; check it appears in output
        Why: The digest in stdout lets callers record or compare the value
        """
        # Arrange
        mock_verify = mocker.patch("skilllint.cli_docs.verify_integrity")
        mock_verify.return_value = _integrity_result(
            IntegrityStatus.INTACT, computed_sha256="deadbeef1234", expected_sha256="deadbeef1234"
        )

        # Act
        result = cli_runner.invoke(plugin_validator.app, ["docs", "verify", str(_TEST_PATH)])

        # Assert
        assert "deadbeef1234" in result.output

    def test_modified_exits_one(self, cli_runner: CliRunner, mocker: MockerFixture) -> None:
        """MODIFIED integrity status exits 1.

        Tests: docs verify failure path when file differs from sidecar
        How: Mock verify_integrity returning MODIFIED; verify exit code 1
        Why: Exit 1 signals the cache entry has been tampered with or corrupted;
             callers must not use the file without re-fetching
        """
        # Arrange
        mock_verify = mocker.patch("skilllint.cli_docs.verify_integrity")
        mock_verify.return_value = _integrity_result(
            IntegrityStatus.MODIFIED,
            computed_sha256="aaaaaa",
            expected_sha256="bbbbbb",
            computed_bytes=99,
            expected_bytes=100,
        )

        # Act
        result = cli_runner.invoke(plugin_validator.app, ["docs", "verify", str(_TEST_PATH)])

        # Assert
        assert result.exit_code == 1

    def test_unverifiable_exits_one(self, cli_runner: CliRunner, mocker: MockerFixture) -> None:
        """UNVERIFIABLE integrity status (no sidecar) exits 1.

        Tests: docs verify failure path when no .meta.json sidecar is present
        How: Mock verify_integrity returning UNVERIFIABLE; verify exit code 1
        Why: Without a sidecar the hash cannot be checked; exit 1 prevents
             silent use of an unverified file
        """
        # Arrange
        mock_verify = mocker.patch("skilllint.cli_docs.verify_integrity")
        mock_verify.return_value = _integrity_result(
            IntegrityStatus.UNVERIFIABLE, expected_sha256=None, expected_bytes=None
        )

        # Act
        result = cli_runner.invoke(plugin_validator.app, ["docs", "verify", str(_TEST_PATH)])

        # Assert
        assert result.exit_code == 1

    def test_file_path_forwarded_to_verify_integrity(self, cli_runner: CliRunner, mocker: MockerFixture) -> None:
        """The file_path argument is forwarded as a Path to verify_integrity.

        Tests: docs verify argument forwarding
        How: Invoke with a specific path string; assert verify_integrity
             called with the corresponding Path object
        Why: String-to-Path conversion must occur before delegation;
             passing a raw string would silently fail type checks at runtime
        """
        # Arrange
        mock_verify = mocker.patch("skilllint.cli_docs.verify_integrity")
        mock_verify.return_value = _integrity_result(IntegrityStatus.INTACT)
        target = "/tmp/some-page-2024-06-01-1200.md"

        # Act
        cli_runner.invoke(plugin_validator.app, ["docs", "verify", target])

        # Assert
        mock_verify.assert_called_once_with(Path(target))
