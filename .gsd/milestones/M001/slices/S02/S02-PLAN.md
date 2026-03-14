# S02: Provider-aware CLI validation on real fixtures

**Goal:** `skilllint check --platform` routes validation through S01's provider schema contracts, applies only rules matching the target provider's constraint_scope, and surfaces authority provenance in violation output.
**Demo:** Run `skilllint check --platform claude-code` and `--platform cursor` against representative fixtures and get different, provider-specific validation results with authority metadata visible.

## Must-Haves

- Validation path loads provider schema via `load_provider_schema()` and uses `constraint_scope` to filter which checks apply per provider
- AS-series rules have `authority` metadata populated via the `skilllint_rule` decorator
- Violation output includes authority provenance (origin + reference) when available
- Integration tests prove provider-specific routing on real fixtures for claude_code, cursor, and codex

## Proof Level

- This slice proves: integration
- Real runtime required: yes (real CLI invocation against fixtures)
- Human/UAT required: no

## Observability / Diagnostics

- **Runtime signals:** `--platform` flag triggers `load_provider_schema()` logging at DEBUG level via `logging.getLogger("skilllint.schemas")`. Constraint scope filtering emits INFO-level count of rules filtered in/out.
- **Inspection surfaces:** `skilllint check --platform <provider> --verbose` surfaces which rules are excluded by constraint_scope. Violation JSON output includes `authority` field when rule has provenance.
- **Failure visibility:** Invalid provider ID produces structured error with `--help` hint. Schema load failures surface file path and JSON parse error. Missing constraint_scope defaults to "shared" with warning.
- **Redaction:** Authority references may contain URLs; no secrets expected in this path.

## Verification

- `cd packages/skilllint && python -m pytest tests/test_provider_validation.py -v` — integration tests for provider-aware validation routing
- `skilllint check --platform claude-code packages/skilllint/tests/fixtures/claude_code/` exits successfully with provider-specific output
- `skilllint check --platform cursor packages/skilllint/tests/fixtures/cursor/` produces different results than claude-code
- `skilllint check --platform invalid-provider --help 2>&1 | grep -i "unknown provider"` — error path surfaces helpful message

## Integration Closure

- Upstream surfaces consumed: `schemas/__init__.py` (`load_provider_schema`, `get_provider_ids`), `rule_registry.py` (`RuleAuthority`, `skilllint_rule` authority kwarg), provider schema `v1.json` files with `constraint_scope`
- New wiring introduced in this slice: adapter → provider schema constraint_scope filtering, AS-series rule authority population, violation output provenance formatting
- What remains before the milestone is truly usable end-to-end: S03 (refresh tooling), S04 (packaged runtime proof)

## Tasks

- [x] **T01: Wire provider schema routing and authority into validation path** `est:2h`
  - Why: The adapters currently use `load_bundled_schema` and ignore S01's `constraint_scope` and `RuleAuthority`. This task connects the new schema/authority stack to the real validation flow.
  - Files: `packages/skilllint/adapters/claude_code/adapter.py`, `packages/skilllint/adapters/cursor/adapter.py`, `packages/skilllint/adapters/codex/adapter.py`, `packages/skilllint/rules/as_series.py`, `packages/skilllint/plugin_validator.py`
  - Do: (1) Update adapters to load schemas via `load_provider_schema()` and expose constraint_scope metadata. (2) Add authority dicts to AS-series `@skilllint_rule` decorators. (3) Update violation output formatting to include authority provenance when present. (4) Add constraint_scope filtering so `--platform` restricts to provider-relevant checks.
  - Verify: `skilllint check --platform claude-code packages/skilllint/tests/fixtures/claude_code/valid_skill.md` runs without error and existing tests pass
  - Done when: Provider schema routing is wired, AS-series rules have authority metadata, and violation dicts include provenance fields

- [x] **T02: Integration tests proving provider-specific validation on real fixtures** `est:1h`
  - Why: The slice goal requires proving provider-aware routing actually produces different, truthful results per provider. Without integration tests, the wiring from T01 is unverified.
  - Files: `packages/skilllint/tests/test_provider_validation.py`
  - Do: (1) Write integration tests that call `validate_file()` with different platform_override values and assert provider-specific results. (2) Test that authority provenance appears in violation output. (3) Test that constraint_scope filtering produces different violation sets for the same file across providers. (4) Test the CLI entrypoint `skilllint check --platform` via subprocess on real fixture files.
  - Verify: `cd packages/skilllint && python -m pytest tests/test_provider_validation.py -v` — all tests pass
  - Done when: Tests demonstrate claude_code, cursor, and codex produce provider-specific validation results with authority metadata

## Files Likely Touched

- `packages/skilllint/adapters/claude_code/adapter.py`
- `packages/skilllint/adapters/cursor/adapter.py`
- `packages/skilllint/adapters/codex/adapter.py`
- `packages/skilllint/rules/as_series.py`
- `packages/skilllint/plugin_validator.py`
- `packages/skilllint/tests/test_provider_validation.py`
