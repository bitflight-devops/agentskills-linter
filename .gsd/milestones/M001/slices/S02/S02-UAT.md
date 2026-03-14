# S02: Provider-aware CLI validation on real fixtures — UAT

**Milestone:** M001
**Written:** 2026-03-14

## UAT Type

- UAT mode: live-runtime
- Why this mode is sufficient: This slice modifies the CLI behavior and validation logic. The proof requires running the actual CLI tool against real fixture files and verifying structured output, which cannot be captured via artifact inspection alone.

## Preconditions

- skilllint is installed (via `.venv/bin/skilllint`)
- Python 3.11+ environment with skilllint package importable
- Test fixtures exist under `packages/skilllint/tests/fixtures/{claude_code,cursor,codex}/`

## Smoke Test

```bash
.venv/bin/skilllint check --platform claude-code packages/skilllint/tests/fixtures/claude_code/valid_skill.md
# Expected: exits 0, produces output showing validation passed
```

## Test Cases

### 1. Claude Code Platform Validation

1. Run `.venv/bin/skilllint check --platform claude-code packages/skilllint/tests/fixtures/claude_code/`
2. **Expected:** Exit code 0, output shows validation results for claude_code fixtures

### 2. Cursor Platform Validation

1. Run `.venv/bin/skilllint check --platform cursor packages/skilllint/tests/fixtures/cursor/`
2. **Expected:** Exit code 0, output shows validation results for cursor fixtures

### 3. Codex Platform Validation

1. Run `.venv/bin/skilllint check --platform codex packages/skilllint/tests/fixtures/codex/`
2. **Expected:** Exit code 0, output shows validation results for codex fixtures

### 4. Different Platforms Produce Different Results

1. Run `.venv/bin/skilllint check --platform claude-code packages/skilllint/tests/fixtures/claude_code/invalid-skill/SKILL.md`
2. Run `.venv/bin/skilllint check --platform cursor packages/skilllint/tests/fixtures/claude_code/invalid-skill/SKILL.md`
3. **Expected:** Both show AS001/AS002 violations (shared rules), but potentially different additional rules based on provider-specific constraints

### 5. Invalid Platform Error Message

1. Run `.venv/bin/skilllint check --platform not-a-real-provider packages/skilllint/tests/fixtures/claude_code/`
2. **Expected:** Exit code 2, error message includes "Unknown platform" and lists valid choices (claude-code, codex, cursor)

### 6. Authority Provenance in Violations

1. Run this Python code:
   ```python
   from pathlib import Path
   from skilllint.adapters import load_adapters
   from skilllint.plugin_validator import validate_file

   adapters = {a.id(): a for a in load_adapters()}
   path = Path('packages/skilllint/tests/fixtures/claude_code/invalid-skill/SKILL.md')
   violations = validate_file(path, adapters, platform_override='claude_code')
   
   as001 = [v for v in violations if v.get('code') == 'AS001'][0]
   print('Authority:', as001.get('authority'))
   ```
2. **Expected:** Output shows `{'origin': 'agentskills.io', 'reference': '/specification#skill-naming'}`

### 7. constraint_scopes Observable via DEBUG Logging

1. Run with DEBUG logging:
   ```bash
   python -c "
   import logging
   logging.basicConfig(level=logging.DEBUG)
   from pathlib import Path
   from skilllint.adapters import load_adapters
   from skilllint.plugin_validator import validate_file
   
   adapters = {a.id(): a for a in load_adapters()}
   path = Path('packages/skilllint/tests/fixtures/claude_code/invalid-skill/SKILL.md')
   validate_file(path, adapters, platform_override='claude_code')
   " 2>&1 | grep constraint
   ```
2. **Expected:** Log line shows `constraint_scopes={'shared', 'provider_specific'}` (or similar)

## Edge Cases

### Empty Fixture Directory

1. Run `.venv/bin/skilllint check --platform claude-code packages/skilllint/tests/fixtures/` (root fixtures dir)
2. **Expected:** Exits 0, reports no files found or skips gracefully

### Missing SKILL.md File Extension

1. Run `.venv/bin/skilllint check --platform claude-code packages/skilllint/tests/fixtures/claude_code/valid_skill.md` (not SKILL.md)
2. **Expected:** AS-series rules may not fire (they require SKILL.md filename), but other validation still runs

## Failure Signals

- Exit code 2 with "No such option: --platform" — platform flag not wired
- Exit code 0 but no platform-specific output — routing not working
- Authority field missing from violation dicts — provenance not wired
- "Unknown platform" error missing valid choices list — error message incomplete

## Requirements Proved By This UAT

No explicit requirements — `.gsd/REQUIREMENTS.md` is missing.

The UAT proves the slice goal: `skilllint check --platform <provider>` routes through the new provider-aware contract path and produces provider-specific validation results with authority provenance visible.

## Not Proven By This UAT

- Schema refresh/regeneration workflow (S03)
- Packaged runtime artifact loading (S04)
- Full constraint_scope-based rule filtering (infrastructure exists but not actively filtering)

## Notes for Tester

- The `--platform` flag uses kebab-case (claude-code, codex, cursor) in CLI but adapters use snake_case internally (claude_code, codex, cursor) — the conversion happens in the CLI layer
- AS-series rules only fire on files named exactly `SKILL.md`, not arbitrary .md files
- Violation severity: error vs warning vs info — authority metadata appears on all severity levels when the rule has it defined
