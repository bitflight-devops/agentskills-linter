"""Fixtures for benchmark tests."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

_FIXTURE_ZIP_NAME = "benchmark-plugin-1000-skills.zip"


@pytest.fixture(scope="session")
def benchmark_plugin_zip() -> Path:
    """Return the path to the benchmark plugin zip fixture.

    The zip is expected at ``tests/fixtures/benchmark-plugin-1000-skills.zip``
    relative to the project root.  The test session is skipped if the file is
    absent so that the regular test suite is not disrupted.

    Returns:
        Absolute path to the benchmark zip archive.
    """
    project_root = Path(__file__).parent.parent.parent
    zip_path = project_root / "tests" / "fixtures" / _FIXTURE_ZIP_NAME
    if not zip_path.exists():
        pytest.skip(f"Benchmark fixture not found: {zip_path}")
    return zip_path


@pytest.fixture(scope="session")
def extracted_plugin_dir(tmp_path_factory: pytest.TempPathFactory, benchmark_plugin_zip: Path) -> Path:
    """Extract the benchmark zip and return the path to the plugin root.

    The archive is extracted once per test session into a shared temporary
    directory managed by ``tmp_path_factory``.

    Args:
        tmp_path_factory: pytest factory for session-scoped temp directories.
        benchmark_plugin_zip: Path to the zip archive (from the session fixture).

    Returns:
        Path to the directory that was extracted from the zip.
    """
    extract_root = tmp_path_factory.mktemp("bench-plugin", numbered=False)
    with zipfile.ZipFile(benchmark_plugin_zip) as zf:
        zf.extractall(extract_root)
    return extract_root


@pytest.fixture
def plugin_file_count(extracted_plugin_dir: Path) -> int:
    """Return the number of SKILL.md files inside the extracted plugin directory.

    Args:
        extracted_plugin_dir: Root of the extracted plugin tree.

    Returns:
        Count of ``SKILL.md`` files found recursively.
    """
    return sum(1 for p in extracted_plugin_dir.rglob("SKILL.md"))
