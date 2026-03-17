#!/usr/bin/env bash
# verify-s06.sh — Verify external repo scan exit codes match S04 baseline
#
# Exit codes expected:
#   claude-plugins-official: 1 (genuine FM003/FM005 errors)
#   skills: 1 (FM003 errors)
#   claude-code-plugins: 0 (warnings only)
#
# This script exits 0 on success, 1 on any mismatch.

set -euo pipefail

OFFICIAL_REPO="/home/ubuntulinuxqa2/repos/claude-plugins-official"
SKILLS_REPO="/home/ubuntulinuxqa2/repos/skills"
PLUGINS_REPO="/home/ubuntulinuxqa2/repos/claude-code-plugins"

errors=0

echo "=== S06 External Scan Verification ==="
echo ""

# Scan claude-plugins-official — expect exit code 1
echo "Scanning claude-plugins-official..."
set +e
uv run python -m skilllint.plugin_validator check "$OFFICIAL_REPO" >/dev/null 2>&1
official_exit=$?
set -e
echo "  Exit code: $official_exit (expected: 1)"
if [[ "$official_exit" -ne 1 ]]; then
    echo "  ❌ FAIL: Expected exit code 1, got $official_exit"
    errors=$((errors + 1))
else
    echo "  ✓ OK"
fi
echo ""

# Scan skills — expect exit code 1
echo "Scanning skills..."
set +e
uv run python -m skilllint.plugin_validator check "$SKILLS_REPO" >/dev/null 2>&1
skills_exit=$?
set -e
echo "  Exit code: $skills_exit (expected: 1)"
if [[ "$skills_exit" -ne 1 ]]; then
    echo "  ❌ FAIL: Expected exit code 1, got $skills_exit"
    errors=$((errors + 1))
else
    echo "  ✓ OK"
fi
echo ""

# Scan claude-code-plugins — expect exit code 0
echo "Scanning claude-code-plugins..."
set +e
uv run python -m skilllint.plugin_validator check "$PLUGINS_REPO" >/dev/null 2>&1
plugins_exit=$?
set -e
echo "  Exit code: $plugins_exit (expected: 0)"
if [[ "$plugins_exit" -ne 0 ]]; then
    echo "  ❌ FAIL: Expected exit code 0, got $plugins_exit"
    errors=$((errors + 1))
else
    echo "  ✓ OK"
fi
echo ""

# Summary
echo "=== Summary ==="
if [[ "$errors" -eq 0 ]]; then
    echo "All exit codes match expected values."
    exit 0
else
    echo "$errors repo(s) had unexpected exit codes."
    exit 1
fi
