# Feature Context: Comprehensive Claude Code Plugin Linter

## Document Metadata

- **Generated**: 2026-02-13
- **Input Type**: complex_requirement_document
- **Source**: User feature request with official schemas and backlog issues
- **Status**: DISCOVERY_COMPLETE

---

## Original Request

Extend `./plugins/plugin-creator/scripts/plugin_validator.py` (2934+ lines) into a comprehensive `ruff`-like static analysis linter that validates ALL 7 component types in the Claude Code plugin ecosystem against official schemas.

**Official Schema Sources (already fetched and verified)**:
- Skills (SKILL.md) — 10 frontmatter fields
- Commands — SAME schema as skills
- Agents — 12 frontmatter fields
- Hooks (hooks.json) — nested JSON structure with 15 event types
- Plugin manifest (plugin.json) — component paths and metadata
- MCP config (.mcp.json) — server definitions
- LSP config (.lsp.json) — language server definitions

**Known Issues (from backlog, verified 2026-02-13)**:
1. UX: report counts validators not files (lines 2928-2931)
2. SK005 fires on commands (DescriptionValidator has no file-type awareness, line 1802)
3. Hooks not recognized (FileType has no HOOK variant, lines 141-165)
4. Dead code in _resolve_skill_reference nested pattern (lines 904-911)

---

## Core Intent Analysis

### WHO (Target Users)

- **Plugin developers** — need confidence their plugins meet schema requirements
- **Pre-commit hooks** — need fast validation to block invalid commits
- **CI/CD pipelines** — need machine-parseable validation reports
- **Marketplace reviewers** — need comprehensive quality assessment

### WHAT (Desired Outcome)

A single comprehensive static analysis tool that validates all Claude Code plugin components against official schemas with actionable error messages.

### WHEN (Trigger Conditions)

- Before committing plugin changes (pre-commit hook)
- During plugin development (manual validation)
- Before marketplace submission (quality gate)
- In CI/CD pipelines (automated checks)

### WHY (Problem Being Solved)

**Current Pain Points**:
1. **Incomplete coverage** — no validation for hooks, MCP, LSP configs
2. **Type confusion** — validator treats commands as skills, no file-type-specific validation
3. **UX issues** — reports count validators not files, unclear which file has problems
4. **Scattered validation** — bash scripts + Python scripts + Claude CLI commands, no unified tool

**Impact**: Plugin developers ship broken configs, marketplace receives invalid plugins, users encounter runtime errors from malformed schemas.

---

## Codebase Research

### Similar Patterns Found

#### Pattern 1: Existing Validator Architecture

- **Location**: `plugins/plugin-creator/scripts/plugin_validator.py:249-286`
- **Relevance**: Protocol-based validator pattern with validate/can_fix/fix methods
- **Reusable**:
  - Validator protocol interface
  - ValidationResult/ValidationIssue data models
  - Error code generation and documentation URL linking
  - Rich console output with color support

#### Pattern 2: FileType Detection

- **Location**: `plugins/plugin-creator/scripts/plugin_validator.py:138-165`
- **Relevance**: Enum-based file type classification
- **Gap**: No HOOK, MCP_CONFIG, LSP_CONFIG variants
- **Reusable**: detect_file_type() static method pattern

#### Pattern 3: Token-Based Complexity Measurement

- **Location**: `plugins/plugin-creator/scripts/plugin_validator.py:1939-2122` (ComplexityValidator class)
- **Relevance**: Uses tiktoken library for accurate AI cost estimation
- **Reusable**:
  - Token counting via tiktoken encoding
  - Threshold-based status determination (ok/warning/error)
  - Frontmatter vs body token separation

#### Pattern 4: Pydantic Schema Validation

- **Location**: `plugins/plugin-creator/scripts/plugin_validator.py:1030-1236`
- **Relevance**: Type-safe frontmatter validation with field validators
- **Reusable**:
  - SkillFrontmatter, AgentFrontmatter, CommandFrontmatter models
  - CSV normalization validators
  - Colon validation in descriptions (FM009)
  - Pattern validation for names (FM010)

### Existing Infrastructure

**9 Validator Classes** (lines 249-2713):
1. Validator (Protocol) — interface definition
2. ProgressiveDisclosureValidator — checks for references/examples/scripts dirs
3. InternalLinkValidator — markdown link validity
4. NamespaceReferenceValidator — cross-plugin references (Skill(), Task(), @agent, /command)
5. FrontmatterValidator — Pydantic schema validation
6. NameFormatValidator — name field pattern checking
7. DescriptionValidator — description quality (length, trigger phrases)
8. ComplexityValidator — token-based skill complexity
9. PluginStructureValidator — plugin.json schema and component paths

**23 Error Codes** across 6 categories:
- FM001-FM010: Frontmatter errors (10 codes)
- SK001-SK007: Skill errors (7 codes)
- LK001-LK002: Link errors (2 codes)
- PD001-PD003: Progressive disclosure (3 codes)
- PL001-PL005: Plugin errors (5 codes)
- NR001-NR002: Namespace reference errors (2 codes)

**Test Coverage** (11 test files):
- test_frontmatter_validator.py
- test_name_format_validator.py
- test_description_validator.py
- test_complexity_validator.py
- test_internal_link_validator.py
- test_progressive_disclosure_validator.py
- test_plugin_structure_validator.py
- test_token_counting.py
- test_cli.py
- test_external_tools.py
- test_auto_sync_manifests.py

### Code References

- `plugins/plugin-creator/scripts/plugin_validator.py:71-109` — error code constants
- `plugins/plugin-creator/scripts/plugin_validator.py:138-165` — FileType enum
- `plugins/plugin-creator/scripts/plugin_validator.py:249-286` — Validator protocol
- `plugins/plugin-creator/scripts/plugin_validator.py:1030-1236` — Pydantic models
- `plugins/plugin-creator/scripts/plugin_validator.py:2928-2931` — UX issue: report counts validators not files
- `plugins/plugin-creator/scripts/plugin_validator.py:1802` — SK005 fires on commands (no file-type awareness)
- `plugins/plugin-creator/scripts/plugin_validator.py:904-911` — dead code in nested skill reference resolution

---

## Use Scenarios

### Scenario 1: Plugin Developer Pre-Commit

**Actor**: Developer modifying a skill
**Trigger**: `git commit` with staged SKILL.md changes
**Goal**: Validate changes before commit succeeds
**Expected Outcome**:
- Pre-commit hook runs validator
- Reports errors with file:line references
- Blocks commit if errors found
- Passes silently if valid

### Scenario 2: Marketplace Submission Review

**Actor**: Marketplace reviewer
**Trigger**: Developer submits plugin for listing
**Goal**: Verify plugin meets all schema requirements
**Expected Outcome**:
- Validator runs against all 7 component types
- Generates comprehensive report with scores
- Flags any non-standard patterns
- Provides improvement suggestions

### Scenario 3: CI/CD Pipeline Validation

**Actor**: CI/CD automation
**Trigger**: Pull request opened with plugin changes
**Goal**: Automated quality gate
**Expected Outcome**:
- Machine-parseable output (JSON/SARIF)
- Non-zero exit code on failure
- GitHub annotations on specific lines
- Summary comment on PR

### Scenario 4: Developer Manual Validation

**Actor**: Developer creating new hook configuration
**Trigger**: `uv run plugin_validator.py hooks.json`
**Goal**: Verify hook config before testing
**Expected Outcome**:
- Validates against 15 event type schemas
- Checks matcher regex validity
- Validates hook type fields (command/prompt/agent)
- Reports unknown event types or malformed hooks

---

## Gap Analysis

### Identified Gaps

| # | Category | Gap Description | Impact |
|---|----------|-----------------|--------|
| 1 | Component Coverage | No validation for hooks.json structure | Broken hooks fail at runtime, no pre-commit detection |
| 2 | Component Coverage | No validation for .mcp.json schema | Invalid MCP configs silently fail, server doesn't start |
| 3 | Component Coverage | No validation for .lsp.json schema | LSP server connections fail, no diagnostics available |
| 4 | File Type Detection | FileType enum missing HOOK, MCP_CONFIG, LSP_CONFIG | Cannot dispatch to appropriate validator |
| 5 | Type-Specific Validation | DescriptionValidator fires SK005 on commands | False positives, commands don't need trigger phrases |
| 6 | UX | Report counts validators not files | Developer sees "9 validators passed" instead of "5 files validated" |
| 7 | Error Codes | No HK, MC, LS prefixes for new component types | Inconsistent error categorization |
| 8 | Dead Code | Nested skill reference resolution unreachable | Maintenance burden, confusing to future developers |
| 9 | Test Coverage | No tests for hook/MCP/LSP validation | Cannot verify new validators work correctly |
| 10 | Schema Sources | Hook/MCP/LSP schemas hardcoded or undocumented | Schema drift risk, no single source of truth |

---

## Questions Requiring Resolution

### Q1: Schema Source of Truth

- **Category**: Integration
- **Gap**: Where are the official hook/MCP/LSP schemas defined?
- **Question**: Should validator embed schemas, fetch from Claude Code CLI, or reference external files?
- **Options**:
  - A) Embed schemas in validator code (fastest, risk of drift)
  - B) Parse schemas from Claude Code installation (accurate, complex discovery)
  - C) Reference `.schema.json` files in plugin (maintainable, requires schema files)
- **Why It Matters**: Schema drift causes false positives/negatives. Wrong schema source = unreliable validation.
- **Resolution**: _pending_

### Q2: Error Code Namespace Expansion

- **Category**: Scope
- **Gap**: Need error codes for 3 new component types
- **Question**: Add HK (hooks), MC (MCP), LS (LSP) prefixes with 001-010 codes each?
- **Options**:
  - A) Yes, add 30 new error codes (10 per category)
  - B) Reuse existing prefixes where semantically similar
  - C) Use single HC (hook config) prefix for all JSON configs
- **Why It Matters**: Error code organization affects documentation, error lookup, and developer experience.
- **Resolution**: _pending_

### Q3: File Type Detection Heuristics

- **Category**: Behavior
- **Gap**: How to detect hook/MCP/LSP config files?
- **Question**: Match by filename, path pattern, or content inspection?
- **Options**:
  - A) Exact filename match (`hooks.json`, `.mcp.json`, `.lsp.json`)
  - B) Path pattern (`*/hooks.json`, `*/.mcp.json`, etc.)
  - C) Content inspection (parse and check top-level keys)
- **Why It Matters**: Wrong detection = validator runs inappropriate checks or skips files entirely.
- **Resolution**: _pending_

### Q4: Validator Auto-Fix Capability

- **Category**: Behavior
- **Gap**: Should hook/MCP/LSP validators support auto-fix?
- **Question**: What can be auto-fixed in JSON configs vs what requires human decision?
- **Options**:
  - A) No auto-fix for JSON configs (too risky, complex structure)
  - B) Auto-fix simple issues (missing optional fields with defaults)
  - C) Interactive fix mode (prompt for corrections)
- **Why It Matters**: Auto-fix can corrupt complex nested structures if done incorrectly.
- **Resolution**: _pending_

### Q5: Command vs Skill Differentiation

- **Category**: Behavior
- **Gap**: Commands use same schema as skills but need different validation rules
- **Question**: How should DescriptionValidator handle commands?
- **Options**:
  - A) Skip SK005 (trigger phrase check) for commands
  - B) Different trigger phrase requirements for commands
  - C) Commands don't need descriptions (wrong, they do per schema)
- **Why It Matters**: Current behavior fires SK005 on valid commands, causing false positives.
- **Resolution**: _pending_

### Q6: Performance Constraints

- **Category**: User
- **Gap**: Pre-commit hook must be fast (<5s)
- **Question**: Should validator cache results, parallelize checks, or optimize file I/O?
- **Options**:
  - A) Cache validation results by file hash
  - B) Parallelize independent validators using multiprocessing
  - C) Read files once, pass content to all validators
  - D) No optimization, rely on Python speed
- **Why It Matters**: Slow pre-commit hooks get disabled by developers.
- **Resolution**: _pending_

### Q7: Report Format Requirements

- **Category**: Integration
- **Gap**: Different consumers need different output formats
- **Question**: Support multiple output formats (human, JSON, SARIF, GitHub annotations)?
- **Options**:
  - A) Human-readable only (Rich console output)
  - B) Add `--format json|sarif|github` flag
  - C) Always output all formats to different files
- **Why It Matters**: CI/CD and IDE integrations require machine-parseable formats.
- **Resolution**: _pending_

---

## Goals (Pending Resolution)

_These goals will be finalized after questions are resolved._

1. Extend FileType enum with HOOK, MCP_CONFIG, LSP_CONFIG variants
2. Create HookValidator class validating hooks.json against 15 event type schemas
3. Create MCPConfigValidator class validating .mcp.json server definitions
4. Create LSPConfigValidator class validating .lsp.json language server configs
5. Fix SK005 false positives by adding file-type awareness to DescriptionValidator
6. Fix UX issue: report file counts instead of validator counts
7. Remove dead code in NamespaceReferenceValidator._resolve_skill_reference
8. Add 30 new error codes (HK001-HK010, MC001-MC010, LS001-LS010)
9. Create comprehensive test suite for new validators (3 new test files)
10. Update ERROR_CODES.md with new error code documentation
11. Performance optimization: single file read, pass content to validators
12. Add --format flag for JSON/SARIF/GitHub output

---

## Next Steps

After questions are resolved:

1. Update "Resolution" fields in Questions section
2. Finalize Goals section with concrete acceptance criteria
3. Proceed to RT-ICA assessment (verify information completeness)
4. Then proceed to architecture design phase
5. Create task decomposition for implementation

---

## Risk Assessment

### High Risk Areas

**Schema Drift** — If validator embeds schemas that diverge from Claude Code's actual schemas, validation becomes unreliable.
- **Mitigation**: Reference official schema files or parse from Claude CLI

**Performance Regression** — Adding 3 new validators + JSON parsing could slow pre-commit hook.
- **Mitigation**: Benchmark current performance, set <5s budget, optimize file I/O

**Breaking Changes** — Fixing SK005 bug might reveal hundreds of existing violations in codebase.
- **Mitigation**: Add gradual rollout strategy, warn first then error

### Medium Risk Areas

**Test Coverage Gap** — No existing tests for hook/MCP/LSP validation means new code could be buggy.
- **Mitigation**: Write tests before implementation (TDD)

**Error Code Proliferation** — 30 new error codes means more documentation to maintain.
- **Mitigation**: Consolidate where possible, template error documentation

### Low Risk Areas

**Dead Code Removal** — Removing unreachable nested skill reference code is safe.
- **Evidence**: Code is after early return, never executed

**UX Fix** — Changing report count from validators to files is cosmetic.
- **Evidence**: No behavior change, only string formatting

---

## Technical Complexity Assessment

### Straightforward Components

1. **FileType enum extension** — Add 3 enum values, update detect_file_type()
2. **Dead code removal** — Delete lines 904-911 after verification
3. **UX report fix** — Change lines 2928-2931 to count validated files
4. **Error code constants** — Add 30 new constants following existing pattern

### Moderate Complexity Components

5. **SK005 file-type awareness** — Pass FileType to DescriptionValidator.validate()
6. **Hook validator** — Parse JSON, validate against 15 event type schemas
7. **MCP validator** — Validate required fields (command), optional fields (args/env)
8. **LSP validator** — Validate required fields (command, extensionToLanguage)

### High Complexity Components

9. **Hook matcher regex validation** — Must validate user-provided regex without executing
10. **Performance optimization** — Requires profiling, multiprocessing coordination
11. **Multiple output formats** — SARIF/GitHub annotations have complex schemas
12. **Schema source integration** — Parsing schemas from Claude CLI is complex discovery

---

## Dependencies on External Systems

- **Claude Code CLI** — May need to query for official schemas
- **Pre-commit framework** — Hook must follow pre-commit protocol
- **tiktoken library** — Already in use for token counting
- **pydantic** — Already in use for schema validation
- **pytest** — Test framework for new test suite

---

## Backward Compatibility Concerns

**CLI Interface** — Current invocation: `uv run plugin_validator.py <path>`
- New flags must not break existing usage
- Existing error codes must remain stable
- Exit codes must remain 0 (pass) or non-zero (fail)

**Pre-Commit Hook** — Currently configured in `.pre-commit-config.yaml`
- New validators must not slow hook below 5s threshold
- Must remain compatible with prek (pre-commit replacement)

**Error Code Documentation** — ERROR_CODES.md references URLs
- New error codes must follow existing URL pattern
- Old error codes must not change meaning

---

## Related Work

**Similar Tools in Python Ecosystem**:
- `ruff` — Fast Python linter (model: single binary, many rules)
- `mypy` — Type checker (model: plugin architecture)
- `pylint` — Comprehensive linter (model: checker classes with register/run)

**Existing Validation in Codebase**:
- `validate-skill-structure.sh` — REMOVED (logic ported to plugin_validator.py)
- `count-skill-lines.sh` — REMOVED (superseded by token metrics in plugin_validator.py)
- `validate-task-file.sh` — Task file validation
- `claude plugin validate` — Built-in CLI command (black box)

---

## Success Criteria

### Functional Requirements

- [ ] Validates all 7 component types (skills, commands, agents, hooks, plugin.json, .mcp.json, .lsp.json)
- [ ] Detects file types correctly (no false positives/negatives)
- [ ] Reports errors with file:line:column precision
- [ ] Provides actionable error messages with suggestions
- [ ] Auto-fixes safe issues when --fix flag used
- [ ] Returns exit code 0 on pass, non-zero on fail

### Performance Requirements

- [ ] Pre-commit hook completes in <5s for typical changes
- [ ] Validates entire plugin in <30s
- [ ] Memory usage <500MB for large plugins

### Quality Requirements

- [ ] Test coverage >80% for all new validators
- [ ] No false positives on valid plugins
- [ ] No false negatives on invalid plugins
- [ ] Error messages cite official schema documentation

### Usability Requirements

- [ ] Reports count files validated, not validators run
- [ ] Groups errors by file, not by validator
- [ ] Provides suggestions for fixing errors
- [ ] Links to ERROR_CODES.md for detailed explanations

---

## Open Research Questions

**Requires additional investigation**:

1. What is the exact JSON schema for hooks.json? (Need to parse official docs or examples)
2. What regex flavor does matcher field use? (Python re, PCRE, JavaScript?)
3. How does Claude Code resolve ${CLAUDE_PLUGIN_ROOT} in MCP command field?
4. Are there undocumented LSP fields we should validate or warn about?
5. What is the performance impact of adding 3 new validators? (Need benchmarking)
6. How many existing plugins will fail validation after SK005 fix? (Need to audit)

**Cannot be resolved during discovery phase** — requires experimentation or upstream documentation.
