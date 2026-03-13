"""Resolve the base release tag for benchmarking comparison.

Given a release tag such as ``v3.6.0``, computes the expected base tag
according to the following rules:

- ``vX.Y.Z`` where Z > 0: base = ``vX.Y.0`` (first patch in same minor)
- ``vX.Y.0`` where Y > 0: base = ``vX.(Y-1).0`` (previous minor's first)
- ``vX.0.0``: base = ``v(X-1).0.0`` (previous major's first release)

If the computed base tag does not exist in the repository, a warning is
printed to stderr and nothing is printed to stdout (graceful skip).

Usage::

    python scripts/resolve_base_ref.py --tag v3.6.0
"""

from __future__ import annotations

import argparse
import re
import sys

import git


def parse_version(tag: str) -> tuple[int, int, int]:
    """Parse a semantic version tag into its numeric components.

    Args:
        tag: A version string such as ``v3.6.0``.

    Returns:
        A tuple ``(major, minor, patch)`` of integers.

    Raises:
        ValueError: If *tag* does not match the expected ``vX.Y.Z`` format.
    """
    match = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)", tag)
    if not match:
        raise ValueError(f"Tag {tag!r} does not match expected vX.Y.Z format")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def compute_base_tag(major: int, minor: int, patch: int) -> str:
    """Compute the expected base tag for a given release version.

    Args:
        major: Major version component.
        minor: Minor version component.
        patch: Patch version component.

    Returns:
        The expected base tag string (e.g. ``v3.5.0``).

    Raises:
        ValueError: If the version is ``v0.0.0`` and no valid base can be
            derived.
    """
    if patch > 0:
        return f"v{major}.{minor}.0"
    if minor > 0:
        return f"v{major}.{minor - 1}.0"
    if major > 0:
        return f"v{major - 1}.0.0"
    raise ValueError("Cannot determine base tag for v0.0.0")


def tag_exists(repo: git.Repo, tag_name: str) -> bool:
    """Check whether a tag exists in the given repository.

    Args:
        repo: A :class:`git.Repo` instance representing the local repo.
        tag_name: The tag name to look up (e.g. ``v3.5.0``).

    Returns:
        ``True`` if the tag exists, ``False`` otherwise.
    """
    return any(t.name == tag_name for t in repo.tags)


def resolve(tag: str, repo_path: str = ".") -> str | None:
    """Resolve the base tag for *tag* in the repository at *repo_path*.

    Args:
        tag: The new release tag (e.g. ``v3.6.0``).
        repo_path: Path to the git repository root. Defaults to the current
            working directory.

    Returns:
        The base tag string if it exists in the repository, or ``None`` if
        no valid base tag could be found or computed.
    """
    try:
        major, minor, patch = parse_version(tag)
    except ValueError as exc:
        print(f"warning: {exc}", file=sys.stderr)
        return None

    try:
        base_tag = compute_base_tag(major, minor, patch)
    except ValueError as exc:
        print(f"warning: {exc}", file=sys.stderr)
        return None

    repo = git.Repo(repo_path)
    if tag_exists(repo, base_tag):
        return base_tag

    print(f"warning: base tag {base_tag!r} does not exist in the repository; skipping comparison", file=sys.stderr)
    return None


def main() -> None:
    """Entry point for the resolve_base_ref CLI.

    Parses ``--tag`` from argv, resolves the base tag, prints it to stdout
    if found, and exits 0 in all cases (including graceful skip).
    """
    parser = argparse.ArgumentParser(description="Resolve the base release tag for benchmark comparison.")
    parser.add_argument("--tag", required=True, help="The new release tag, e.g. v3.6.0")
    args = parser.parse_args()

    base = resolve(args.tag)
    if base:
        print(base)


if __name__ == "__main__":
    main()
