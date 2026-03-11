# Cursor Schema Audit

**Schema under audit**: `packages/skilllint/schemas/cursor/v1.json`
**Source**: `.claude/vendor/cursor/rules.md` (stored as raw HTML — not parseable; live `https://cursor.com/docs/rules` used as authoritative reference)
**Audit date**: 2026-03-10

---

## Scope Note

The schema covers two sections: `mdc` (Cursor's native `.mdc` rule file frontmatter) and `skill_md` (agentskills.io-specific `SKILL.md` frontmatter). The Cursor vendor documentation at `https://cursor.com/docs/rules` is authoritative only for the `mdc` section. The `skill_md` section is explicitly scoped to agentskills.io conventions — the schema title reads "Cursor SKILL.md Frontmatter (agentskills.io)" — and has no Cursor vendor documentation to audit against. Findings 1–6 cover `mdc`. Findings 7–9 cover `skill_md`.

---

## Findings

### mdc section

**1. Field: `description`**

- **Schema says**: `{ "type": "string", "minLength": 1 }`
- **Docs say**: "Use `.mdc` files with frontmatter to specify `description` and `globs` for more control over when rules are applied." Described as a string value presented to the Agent to decide if an intelligently-applied rule should be active. No minimum length is stated.
- **Required?** Docs do not mark it mandatory. Schema `required: []` — not required.
- **Verdict**: PASS. Type is correct (string). `minLength: 1` prevents empty strings and is not contradicted by the docs. Required status correct (optional).

---

**2. Field: `globs`**

- **Schema says**: `{ "oneOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}] }`
- **Docs say**: The only documented frontmatter example is:
  ```
  ---
  globs:
  alwaysApply: false
  ---
  ```
  The field is shown with no value assigned. The docs state "specify `description` and `globs` for more control over when rules are applied" and reference glob patterns generically ("e.g., `**/*.py`") in the Team Rules section, but provide no type specification (string, array, or both) for the `globs` field in Project Rules frontmatter.
- **Required?** Docs do not mark it mandatory. Schema `required: []` — not required.
- **Verdict**: FAIL — type is UNVERIFIABLE. The schema asserts `string | string[]` but the docs provide no type specification for this field. The only frontmatter example shows `globs:` with no value. The `oneOf [string, array]` choice is an undocumented assumption. If Cursor's parser accepts only one form, the schema could pass files Cursor rejects (or fail files Cursor accepts). Required status correct (optional).

---

**3. Field: `alwaysApply`**

- **Schema says**: `{ "type": "boolean" }`
- **Docs say**: "If alwaysApply is true, the rule will be applied to every chat session. Otherwise, the description of the rule will be presented to the Cursor Agent to decide if it should be applied."
- **Required?** Docs do not mark it mandatory. Schema `required: []` — not required.
- **Verdict**: PASS. Type is correct (boolean). Required status correct (optional).

---

**4. `required` array — mdc**

- **Schema says**: `"required": []` — no fields are required.
- **Docs say**: No fields are described as mandatory. Usage language is consistently optional: "specify `description` and `globs` for more control."
- **Verdict**: PASS. No fields are incorrectly marked required.

---

**5. `additionalProperties: false` — mdc**

- **Schema says**: `"additionalProperties": false` — any frontmatter key beyond `description`, `globs`, `alwaysApply` will fail validation.
- **Docs say**: "Each rule is a markdown file with frontmatter metadata and content. The frontmatter metadata is used to control how the rule is applied." Only three fields are documented: `description`, `globs`, `alwaysApply`. The docs make no statement permitting or prohibiting additional frontmatter properties.
- **Verdict**: PASS on documented surface. All three documented fields are represented. No additional fields are named in the docs that the schema would wrongly reject. `additionalProperties: false` is conservative and consistent with the documented field set.

---

**6. Missing documented fields — mdc**

- **Schema covers**: `description`, `globs`, `alwaysApply`
- **Docs document**: `description`, `globs`, `alwaysApply` — no additional fields documented.
- **Verdict**: PASS. No documented fields are absent from the schema.

---

### skill_md section

**7–9. Fields: `name`, `description`, `license`, `metadata` / required / additionalProperties**

- **Schema says**: `name` (string, minLength:1, maxLength:64), `description` (string, minLength:1, maxLength:1024), `license` (string), `metadata` (object). Required: `name`, `description`. `additionalProperties: true`.
- **Docs say**: No Cursor vendor documentation covers `SKILL.md` frontmatter. The schema title explicitly states "(agentskills.io)" — this section is governed by agentskills.io conventions, not Cursor vendor docs.
- **Verdict**: OUT OF SCOPE for Cursor vendor audit. Should be audited against agentskills.io documentation separately.

---

## Vendor Documentation Quality Note

The file `.claude/vendor/cursor/rules.md` is stored as raw, unminified HTML from a Next.js application. It is not parseable as markdown and cannot serve as a documentation source for schema auditing. This audit used the live page at `https://cursor.com/docs/rules`. The vendor file should be replaced with a plain-text or markdown extract of the rendered documentation content, or the fetch script should strip HTML.

---

## Summary Verdict

**FAIL**

One finding: `globs` type. The docs show `globs:` with no value in the only frontmatter example and provide no type specification (string vs. array vs. both). The schema's `oneOf [string, array]` is an assumption not supported by any statement in the Cursor vendor documentation.

All other `mdc` findings PASS. The `skill_md` section is out of scope for Cursor vendor documentation.
