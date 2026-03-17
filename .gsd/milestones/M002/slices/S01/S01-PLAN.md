# S01: Validator seam map and boundary extraction

**Goal:** Extract explicit internal seams for path discovery/scan expansion, validator composition/execution, and result reporting so `packages/skilllint/plugin_validator.py` no longer owns every major responsibility by default.
**Demo:** The real `skilllint check` path still runs, but the CLI layer delegates through extracted internal modules for scan expansion, validation-loop execution, and reporting instead of keeping those responsibilities monolithically inside `plugin_validator.py`.

## Must-Haves

- `plugin_validator.py` stops being the default home for scan expansion, reporting, and validation-loop orchestration.
- The extracted seams are real runtime wiring used by `skilllint check`, not parallel abstractions or dead helper modules.
- Tests lock the new boundaries so later slices can build S02 ownership cleanup and S03 discovery cleanup on top of them.

## Proof Level

- This slice proves: contract
- Real runtime required: yes
- Human/UAT required: no

## Verification

- `uv run pytest packages/skilllint/tests/test_cli.py -q`
- `uv run pytest packages/skilllint/tests/test_provider_validation.py -q`
- `uv run python -m skilllint.plugin_validator check packages/skilllint/tests/fixtures/claude_code/valid_skill.md --no-color`

## Observability / Diagnostics

- Runtime signals: per-file validation results still flow through `ValidationResult` and existing reporter output.
- Inspection surfaces: `skilllint check`, CLI test suite, provider validation tests.
- Failure visibility: extracted seams should preserve existing error exit codes and file-grouped reporting behavior.
- Redaction constraints: none.

## Integration Closure

- Upstream surfaces consumed: `packages/skilllint/plugin_validator.py`, `packages/skilllint/adapters/*`, `packages/skilllint/tests/test_cli.py`, `packages/skilllint/tests/test_provider_validation.py`
- New wiring introduced in this slice: CLI delegates into extracted scan/discovery, validation execution, and reporter modules.
- What remains before the milestone is truly usable end-to-end: S02 must separate schema vs rule ownership; S03 must harden discovery semantics beyond the generic seam extracted here.

## Tasks

- [x] **T01: Extract reporting types and implementations out of `plugin_validator.py`** `est:45m`
  - Why: Reporter protocol plus `ConsoleReporter`/`CIReporter`/`SummaryReporter` are a large independent responsibility block and a clean first seam.
  - Files: `packages/skilllint/plugin_validator.py`, `packages/skilllint/reporting.py`, `packages/skilllint/tests/test_cli.py`
  - Do: Move the `Reporter` protocol and reporter implementations into a dedicated module; keep behavior and output contracts intact; update the CLI path to import and use the extracted reporters without changing user-facing output semantics.
  - Verify: `uv run pytest --no-cov packages/skilllint/tests/test_reporters.py packages/skilllint/tests/test_cli.py -q`
  - Done when: reporter classes no longer live in `plugin_validator.py` and CLI tests still pass with unchanged exit-code behavior.

- [ ] **T02: Extract scan expansion and validation-loop orchestration seams** `est:1h`
  - Why: `_discover_validatable_paths`, `_resolve_filter_and_expand_paths`, and `_run_validation_loop` are the core orchestration seam S03 will need; keeping them embedded in the monolith blocks later discovery work.
  - Files: `packages/skilllint/plugin_validator.py`, `packages/skilllint/scan_runtime.py`, `packages/skilllint/tests/test_cli.py`
  - Do: Move generic directory expansion and run-loop orchestration into a dedicated runtime module; preserve the current behavior for plugin roots, bare directories, filters, ignore patterns, summary handling, and exit codes; keep `check_cmd` wired through the extracted runtime.
  - Verify: `uv run pytest packages/skilllint/tests/test_cli.py -q`
  - Done when: the CLI entrypoint delegates through the extracted runtime module and the real command still expands paths and exits exactly as before.

- [ ] **T03: Lock seam boundaries with focused regression coverage and real-entrypoint proof** `est:45m`
  - Why: S01 only counts if the extracted seams are exercised by the actual CLI path and remain safe for S02/S03 to build on.
  - Files: `packages/skilllint/tests/test_cli.py`, `packages/skilllint/tests/test_provider_validation.py`, `packages/skilllint/plugin_validator.py`
  - Do: Add or update tests that prove the CLI still routes through the extracted runtime, reporter selection still works, and provider validation still composes correctly with the refactored entrypoint; keep tests focused on the boundary contracts, not internal implementation trivia.
  - Verify: `uv run pytest packages/skilllint/tests/test_cli.py packages/skilllint/tests/test_provider_validation.py -q && uv run python -m skilllint.plugin_validator check packages/skilllint/tests/fixtures/valid_skill/SKILL.md --no-color`
  - Done when: tests pass and the real module-entrypoint command proves the extracted seams are active in runtime, not dead code.

## Files Likely Touched

- `packages/skilllint/plugin_validator.py`
- `packages/skilllint/reporting.py`
- `packages/skilllint/scan_runtime.py`
- `packages/skilllint/tests/test_cli.py`
- `packages/skilllint/tests/test_provider_validation.py`
