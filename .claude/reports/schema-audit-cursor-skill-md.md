# Cursor skill_md Section Audit

**Schema under audit**: `packages/skilllint/schemas/cursor/v1.json` — `file_types.skill_md`
**Standard audited against**: agentskills.io open standard (SKILL.md frontmatter specification)
**Audit date**: 2026-03-10

---

## Source(s) Found

### Primary in-repo source

- **`.planning/phases/02-platform-adapters/02-RESEARCH.md`** — Section "agentskills.io Open Standard — SKILL.md frontmatter fields"
  - Cited source: `agentskills.io/specification`
  - Recorded confidence: HIGH — "verified via agentskills.io/specification"
  - Research date: 2026-03-09

### Supporting in-repo source

- **`.planning/phases/02-platform-adapters/02-CONTEXT.md`** line 54 — lists `compatibility` and `allowed-tools` as agentskills.io frontmatter fields used by Cursor
  - Status: these fields appear in pre-research planning notes but are absent from the confirmed spec field list in 02-RESEARCH.md. Verification was either not completed or the fields were found to be Cursor-specific extensions, not base-spec fields.

### agentskills.io specification — vendor status

The agentskills.io specification is **not vendored** in this repo. No local copy of `agentskills.io/specification` exists to audit against directly. All findings are based on the in-repo research record (02-RESEARCH.md), which is itself based on a live fetch performed 2026-03-09.

### Real SKILL.md samples examined

| File | Frontmatter fields present |
|------|---------------------------|
| `plugins/claude-opus-4-5-migration/skills/claude-opus-4-5-migration/SKILL.md` | `name`, `description` |
| `plugins/frontend-design/skills/frontend-design/SKILL.md` | `name`, `description`, `license` |
| `plugins/hookify/skills/writing-rules/SKILL.md` | `name`, `description`, `version` |
| `plugins/plugin-dev/skills/skill-development/SKILL.md` | `name`, `description`, `version` |

---

## Findings

### `name`

**Schema**: `{ "type": "string", "minLength": 1, "maxLength": 64 }`, required

**Spec (02-RESEARCH.md)**: "required; identifier, lowercase alphanumeric + hyphens, must match parent directory name"

**Verdict**: DOCUMENTED — required status correct, maxLength:64 correct. Pattern constraint (`^[a-z0-9][a-z0-9-]*[a-z0-9]$`) is enforced by AS001 at runtime, not the JSON Schema — intentional architecture split.

---

### `description`

**Schema**: `{ "type": "string", "minLength": 1, "maxLength": 1024 }`, required

**Spec (02-RESEARCH.md)**: "required; max 1024 chars, no `<` or `>`, trigger-oriented"

**Verdict**: DOCUMENTED — required status correct, maxLength:1024 correct. The `<`/`>` exclusion is delegated to AS004 at runtime — same intentional split.

---

### `license`

**Schema**: `{ "type": "string" }`, optional

**Spec (02-RESEARCH.md)**: "optional; license identifier"

**Real sample**: `frontend-design/SKILL.md` has `license: Complete terms in LICENSE.txt` — free text, not SPDX. Spec says "identifier" without constraining format, schema has no format constraint. Consistent.

**Verdict**: DOCUMENTED — optional status correct, type correct. PASS.

---

### `metadata`

**Schema**: `{ "type": "object" }`, optional

**Spec (02-RESEARCH.md)**: "optional; object with `author`, `version`, etc."

**Real sample observation**: No sampled SKILL.md uses a `metadata` object. Two files use `version: 0.1.0` as a top-level frontmatter field, not nested under `metadata`. This is permitted silently by `additionalProperties: true`.

**Verdict**: DOCUMENTED — type correct, optional status correct. The top-level `version` pattern observed in real files is a known extension, not a schema defect.

---

### `additionalProperties: true`

**Spec**: The agentskills.io standard is extensible. 02-CONTEXT.md notes Cursor uses platform-specific fields beyond the base spec (`compatibility`, `allowed-tools`).

**Verdict**: CORRECT — `additionalProperties: true` is the right representation for an extensible spec.

---

### `compatibility` and `allowed-tools` (not in schema properties)

**In schema**: absent from `properties`
**In 02-CONTEXT.md**: listed as agentskills.io fields Cursor uses
**In 02-RESEARCH.md**: absent from confirmed spec fields

**Verdict**: UNVERIFIABLE from in-repo sources. Since `additionalProperties: true`, these fields pass validation if present. Whether they should be explicitly documented in `properties` requires direct verification against `agentskills.io/specification`.

**Action required**: Vendor the agentskills.io specification (add to `.claude/vendor/` via `scripts/fetch_platform_docs.py`) to enable authoritative verification.

---

## Recommended Changes

No correctness changes required. All four documented spec fields (`name`, `description`, `license`, `metadata`) are represented with correct types and required/optional status.

Two advisories:

1. **`compatibility` and `allowed-tools`**: Cannot resolve without direct access to `agentskills.io/specification`. Add agentskills.io to the vendor fetch script.

2. **Top-level `version`**: Observed in 2/4 real SKILL.md samples. Passes silently via `additionalProperties: true`. No blocking change needed; worth documenting as a known Claude Code extension.
