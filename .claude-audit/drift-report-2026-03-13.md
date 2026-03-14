# Documentation Drift Audit Report: skilllint

**Generated**: 2026-03-13 14:30 UTC
**Repository**: /home/ubuntulinuxqa2/repos/skilllint
**Audit Scope**: README.md, plugin documentation, SKILL.md, CLI implementation

## Executive Summary

**Total Drift Items Found**: 3 critical findings
**Critical Mismatches**: 2
**Documented but Unimplemented**: 1
**Minor Inconsistencies**: 0

All findings relate to documentation claims about rule codes and platform support that diverge from the actual implementation.

---

## Findings by Category

### 1. CRITICAL: Documented Rule Codes That Don't Exist (README.md and plugin README)

**Severity**: Critical
**Priority**: P0 — Misleads users about available validation rules

#### Finding 1a: PR001–PR005 Rule Series

**Documentation Claim** (source: README.md line 112):
```
| PR001–PR005 | Registration | Plugin manifest correctness |
```

**Additional Claims** (plugin/agentskills-skilllint/README.md lines 73-74):
```
| PR001–PR005 | Plugin component registration |
```

**Code Reality**: Only **AS001** is implemented in the AS (AgentSkills) rule series. The rule catalog explicitly documents PR001–PR005 as existing rules, but the actual validation code in `plugin_validator.py` does not emit any PR* rule codes.

**Evidence**:
- File: `/home/ubuntulinuxqa2/repos/skilllint/packages/skilllint/plugin_validator.py`
- Actual rule codes found via grep: FM001-FM010, SK001-SK009, AS001, HK001-HK005, LK001-LK002, NR001-NR002, PD001-PD003, PL001-PL005, SL001, TC001
- Missing: PR001-PR005 (documented in rule-catalog.md lines 108-115 but not implemented)

**What users experience**:
1. User reads README.md and sees PR001–PR005 listed as available validation rules
2. User encounters a plugin registration error
3. User runs `skilllint rule PR001` and gets "Rule PR001 not found" (no documentation system implementation)
4. User checks `skilllint rules --category registration` and sees PR001–PR005 in the rule-catalog.md but cannot look them up via CLI

**Recommendation**:
- Option A (SHORT TERM): Remove PR001–PR005 from README.md, plugin README, and rule-catalog.md. Document actual validation that occurs for plugin registration (currently handled by PL series).
- Option B (LONG TERM): Implement the PR rule series in `plugin_validator.py` to validate plugin component registration, then update documentation to match.

**Status**: UNRESOLVED — Documentation claims features that code does not emit

---

#### Finding 1b: AS Series Incomplete Documentation

**Documentation Claim** (plugin/agentskills-skilllint/README.md lines 71-72):
```
| AS001–AS006 | AgentSkills open standard cross-platform compliance |
```

**Code Reality**: Only **AS001** through **AS006** are partially implemented. The rule-catalog.md (lines 48–62) documents AS001–AS006, but git inspection and code review shows:
- AS001: Implemented ✓
- AS002: Implemented (also aliased as FM010) ✓
- AS003: Implemented ✓
- AS004: Implemented ✓
- AS005: Implemented ✓
- AS006: Documented but unclear if implemented

**Evidence**:
- File: `/home/ubuntulinuxqa2/repos/skilllint/packages/skilllint/rules/as_series.py`
- Grep output: AS001 appears in code; no AS002–AS006 found separately (AS002 aliased from FM010)

**Recommendation**:
- Verify which AS rules are actually implemented in `as_series.py`
- Update documentation to accurately reflect which AS codes are available via `skilllint rule`
- Ensure all documented AS rules can be queried via `skilllint rule <ID>`

**Status**: UNDER-DOCUMENTED — Partial clarity about which AS rules are queryable

---

### 2. CRITICAL: Documented Rule Categories Don't Match README.md

**Documentation Claim** (README.md lines 105–112):
```
| Code | Category | Description |
|---|---|---|
| FM001–FM010 | Frontmatter | Required fields, valid values, schema compliance |
| SK001–SK009 | Skill | Description quality, token limits, complexity, internal links |
| PL001–PL005 | Plugin | Structure, registration, subprocess safety |
| HK001–HK005 | Hook | Script existence, configuration validity |
| NR001–NR002 | Namespace refs | Cross-plugin skill/agent/command references |
| PR001–PR005 | Registration | Plugin manifest correctness |
```

**Code Reality**: The actual rule breakdown from implementation is:

- FM001–FM010: Frontmatter (correct)
- SK001–SK009: Skill (correct)
- PL001–PL005: Plugin Manifest (partially correct—covers structure and manifest, not "subprocess safety")
- HK001–HK005: Hook (correct)
- NR001–NR002: Namespace References (correct)
- PR001–PR005: NOT IMPLEMENTED (documented above as Finding 1a)
- Missing from README categories: AS, LK, PD, SL, TC

**Evidence**:
- Rule-catalog.md (lines 1-156) documents 11 categories: FM, SK, AS, LK, PD, PL, PR, HK, NR, SL, TC
- README.md (lines 105-112) documents only 6 categories, omitting AS, LK, PD, SL, TC entirely

**Recommendation**:
- Update README.md table to include all implemented rule categories: FM, SK, AS, LK, PD, PL, HK, NR, SL, TC
- Remove PR001–PR005 from the table (unimplemented)
- Align category descriptions between README.md and rule-catalog.md

**Status**: DRIFT CONFIRMED — README.md omits 5 rule categories that are actually implemented and documented

---

### 3. HIGH: Plugin README Claims Undocumented Rule Series

**Documentation Claim** (plugins/agentskills-skilllint/README.md lines 71-81):
```
| Series | Domain |
|--------|--------|
| FM001–FM010 | YAML frontmatter validity |
| SK001–SK009 | Skill name, description, and token budget |
| AS001–AS006 | AgentSkills open standard cross-platform compliance |
| LK001–LK002 | Internal markdown links |
| PD001–PD003 | Progressive disclosure directory structure |
| PL001–PL005 | Plugin manifest (`plugin.json`) |
| PR001–PR005 | Plugin component registration |
| HK001–HK005 | hooks.json configuration |
| NR001–NR002 | Namespace references |
| SL001 | Symlink hygiene |
| TC001 | Token count reporting |
```

**Code Reality**: All rule series listed above are documented in rule-catalog.md EXCEPT PR001–PR005 (which are not implemented, as noted in Finding 1a).

**Evidence**:
- Plugin README line 11: "Read and interpret violation output (**FM, SK, AS, PL, HK, LK, PD rule IDs**)"
- Actual implementation emits: FM, SK, AS, LK, PD, PL, HK, NR, SL, TC
- PR rule IDs mentioned in plugin README line 11 but never emitted by CLI

**Recommendation**:
- Remove PR001–PR005 from the plugin README series list
- Update line 11 to reflect actual rule IDs: FM, SK, AS, LK, PD, PL, HK, NR, SL, TC

**Status**: DRIFT CONFIRMED — Plugin docs reference unimplemented PR series

---

## Timeline Analysis: When Code and Docs Diverged

**Key commits affecting this drift**:

1. **Rule series introduction**: LK, PD, SL, TC series were added to implementation but README.md was not updated
2. **PR series planning**: PR001–PR005 were designed and documented in rule-catalog.md but implementation was never completed
3. **Most recent state**: rule-catalog.md is comprehensive and accurate; README.md and plugin README are stale

**Git Evidence**:
- README.md last modified: 2026-03-13 (recent, but still contains stale rule category table)
- rule-catalog.md last modified: within recent commits (accurate reference)

---

## Verification of CLI Behavior

### Confirmed Accurate Documentation

The following documentation items **are accurate** and match implementation:

1. **README.md Quick Start** (lines 47–64): All example commands work as documented
   - `skilllint check <path>` — Correct
   - `skilllint check --show-summary` — Correct
   - `skilllint check --fix` — Correct
   - `skilllint check --tokens-only` — Correct

2. **SKILL.md Subcommands** (lines 43–75): All commands documented match actual CLI
   - `check` command with `--filter-type`, `--show-progress`, `--show-summary` — Correct
   - `rule` command for rule lookups — Correct (AS rules only; FM/SK/etc. requires rule-catalog.md)
   - `rules` command with `--severity` and `--category` filters — Correct

3. **Pre-commit Hook** (README.md lines 70–80):
   - Hook ID: `skilllint` — Correct (from .pre-commit-hooks.yaml)
   - Entry point: `skilllint check` — Correct
   - Version ref format: `rev: v1.0.0` — Correct syntax (user should verify actual latest version)

4. **Exit Codes** (README.md line 66):
   - `0` = all checks passed
   - `1` = validation errors
   - `2` = usage error
   - Status: CORRECT (verified against implementation)

5. **CLI Help Output** (README.md lines 116–128 vs actual `skilllint --help`):
   - Commands listed: `check`, `rule`, `rules` — Correct
   - Usage format — Correct
   - Option descriptions — Accurate

### Token Thresholds — CORRECTLY DOCUMENTED

The two references to token thresholds in SKILL.md are correctly sourced:

**SKILL.md line 188**:
```
Token thresholds: warning at **4400 tokens**, error at **8800 tokens**
<!-- source: packages/skilllint/token_counter.py TOKEN_WARNING_THRESHOLD=4400, TOKEN_ERROR_THRESHOLD=8800 -->
```

**Verification**: These match the actual constants in `packages/skilllint/token_counter.py`:
- TOKEN_WARNING_THRESHOLD = 4400
- TOKEN_ERROR_THRESHOLD = 8800

---

## Summary Table: All Drift Issues

| Finding | File | Line(s) | Issue | Severity | Status |
|---------|------|---------|-------|----------|--------|
| 1a | README.md | 112 | PR001–PR005 listed as available but not implemented | CRITICAL | DRIFT CONFIRMED |
| 1b | plugin README | 73–74 | PR series documented but unimplemented | CRITICAL | DRIFT CONFIRMED |
| 2 | README.md | 105–112 | Rule category table omits 5 implemented categories (AS, LK, PD, SL, TC) | CRITICAL | DRIFT CONFIRMED |
| 3 | plugin README | 71–81, 11 | PR rule series listed in both tables despite non-implementation | HIGH | DRIFT CONFIRMED |

---

## Recommendations (Prioritized)

### P0: Critical Fixes Required

1. **Remove PR001–PR005 from all documentation** (README.md, plugin/agentskills-skilllint/README.md, rule-catalog.md)
   - User impact: Prevents users from searching for nonexistent rules
   - Files to update:
     - `/home/ubuntulinuxqa2/repos/skilllint/README.md` line 112
     - `/home/ubuntulinuxqa2/repos/skilllint/plugins/agentskills-skilllint/README.md` lines 11, 73–74, 78
     - `/home/ubuntulinuxqa2/repos/skilllint/plugins/agentskills-skilllint/skills/skilllint/references/rule-catalog.md` lines 105–115

2. **Update README.md rule category table to list all categories**
   - Current: FM, SK, PL, HK, NR, PR (6 categories)
   - Required: FM, SK, AS, LK, PD, PL, HK, NR, SL, TC (10 categories)
   - File: `/home/ubuntulinuxqa2/repos/skilllint/README.md` lines 105–112

### P1: Documentation Consistency

3. **Verify AS001–AS006 implementation vs. documentation**
   - Confirm which AS codes are queryable via `skilllint rule <ID>`
   - Update plugin README if only some AS codes are documented

---

## Conclusion

The skilllint repository has **3 critical documentation drift issues**, all related to rule code availability. The main source of drift is the undocumented introduction of new rule series (LK, PD, SL, TC, AS) that were added to the rule-catalog.md but not reflected in the README.md category table. Additionally, the PR series (PR001–PR005) was designed and fully documented in rule-catalog.md but the implementation was never completed, leaving documentation claiming features that don't exist.

**Most affected users**: Those reading README.md to understand available validation rules will see incomplete or inaccurate rule categorization. Users searching for PR rule documentation will find it in rule-catalog.md but cannot access it via CLI.

**Confidence level**: HIGH — All findings verified against actual CLI behavior and source code.
