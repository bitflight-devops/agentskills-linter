# Schema Audit: Codex Platform Schema v1

**Schema under audit**: `packages/skilllint/schemas/codex/v1.json`
**Audit date**: 2026-03-10

## Sources Consulted

1. `packages/skilllint/schemas/codex/v1.json` — schema under audit
2. `.claude/vendor/codex/AGENTS.md` — vendor AGENTS.md (is the Rust/codex-rs developer guidelines file; not the user-facing AGENTS.md specification)
3. `.claude/vendor/codex/codex-rs/config.md` — redirects to `../docs/config.md`; that path does not exist in the vendor clone
4. `.claude/vendor/codex/codex-rs/execpolicy/README.md` — canonical documentation for the `.rules` prefix_rule format
5. `.claude/vendor/codex/codex-rs/execpolicy-legacy/README.md` — legacy policy format (separate system)
6. `.claude/vendor/codex/codex-cli/README.md` — user-facing AGENTS.md description (Memory & project docs section)
7. `.claude/vendor/codex/docs/agents_md.md` — vendor doc stub for AGENTS.md
8. `.claude/vendor/codex/codex-rs/protocol/src/prompts/base_instructions/default.md` — agent prompt containing AGENTS.md spec
9. `.claude/vendor/codex/codex-rs/tui/prompt_for_init_command.md` — AGENTS.md generation prompt (recommended structure)
10. `.claude/vendor/codex/codex-rs/core/src/config/schema.md` — config schema generation notes
11. `.claude/vendor/codex/codex-rs/core/src/config_loader/README.md` — config loader documentation

---

## Findings

### Finding 1 — agents_md / x-non-empty

**Schema says** (`file_types.agents_md`):
```json
{
  "x-non-empty": true,
  "description": "AGENTS.md must exist and contain non-empty content"
}
```

**Docs say** (`codex-cli/README.md`, Memory & project docs section):
> "You can give Codex extra instructions and guidance using `AGENTS.md` files."
> Example given: `- Always respond with emojis` / `- Only use git commands when explicitly requested`

**Docs say** (`codex-rs/protocol/src/prompts/base_instructions/default.md`):
> "Repos often contain AGENTS.md files. These files can appear anywhere within the repository."
> No minimum content structure is specified.

**Verdict**: PASS with qualification. The `x-non-empty` constraint is consistent with Codex's usage — an empty AGENTS.md provides no guidance. The docs do not specify any structural requirements beyond the file being present and containing text. The schema correctly avoids imposing any structural validation beyond non-emptiness.

Note: The vendor root `AGENTS.md` is actually Rust developer guidelines for the codex-rs codebase — not the specification for the AGENTS.md format used by end users. This is a documentation sourcing ambiguity, not a schema defect.

---

### Finding 2 — prefix_rule / known_fields

**Schema says** (`file_types.prefix_rule`):
```json
{
  "known_fields": ["pattern", "decision", "justification", "match", "not_match"]
}
```

**Docs say** (`codex-rs/execpolicy/README.md`):
```starlark
prefix_rule(
    pattern = ["cmd", ["alt1", "alt2"]],
    decision = "prompt",
    justification = "explain why this rule exists",
    match = [["cmd", "alt1"], "cmd alt2"],
    not_match = [["cmd", "oops"], "cmd alt3"],
)
```

**Verdict**: PASS. The schema's `known_fields` list exactly matches the documented `prefix_rule` argument list. Every field named in the docs appears in `known_fields`, and no extra fields appear that are absent from the docs.

---

### Finding 3 — prefix_rule / valid_decisions

**Schema says**: `"valid_decisions": ["allow", "prompt", "forbidden"]`

**Docs say** (`codex-rs/execpolicy/README.md`):
> "`decision` defaults to `allow`; valid values: `allow`, `prompt`, `forbidden`."

**Verdict**: PASS. Exact match.

---

### Finding 4 — prefix_rule / required_fields

**Schema says**: `"required_fields": ["pattern"]`

**Docs say**: `pattern` is the first positional parameter in every example. All other parameters are marked optional with `?` in the documented signature (`decision?`, `justification?`, `match?`, `not_match?`).

**Verdict**: PASS. Marking `pattern` as the sole required field is consistent with the docs.

---

### Finding 5 — host_executable: documented callable not in schema

**Schema says**: `known_fields` on `prefix_rule` does not include `host_executable`.

**Docs say** (`codex-rs/execpolicy/README.md`):
```starlark
host_executable(
    name = "git",
    paths = ["/opt/homebrew/bin/git", "/usr/bin/git"],
)
```
`host_executable` is a separate top-level Starlark callable in `.rules` files, not a field of `prefix_rule`.

**Verdict**: GAP — not a schema error, but an omission. The `.rules` format supports two top-level callables (`prefix_rule` and `host_executable`) and the schema only covers one. A file using only `host_executable(...)` entries would not be validated. This is an undocumented gap, not an incorrect constraint. Should be tracked for a future schema addition.

---

### Finding 6 — x-no-extra: not used; no valid fields rejected

**Schema says**: The key `x-no-extra` does not appear anywhere in `v1.json`.

**Verdict**: PASS. The schema does not use `x-no-extra`, so it cannot reject any documented fields. Correct approach given that execpolicy is still in preview.

---

### Finding 7 — x-experimental flag accuracy

**Schema says**: `"x-experimental": true`

**Docs say** (`codex-rs/execpolicy/README.md`):
> "Note: `execpolicy` commands are still in preview. The API may have breaking changes in the future."

**Verdict**: PASS. The experimental marker is accurate.

---

## Summary Verdict

**PASS with one documented gap**

All validated constraints are accurate and consistent with official vendor documentation. No documented fields are incorrectly rejected; no schema constraints conflict with what the docs describe as valid.

The one gap (Finding 5) is that `host_executable`, the second top-level callable in the `.rules` format, has no coverage in the schema. This is an omission — the schema silently ignores `host_executable` entries rather than validating or rejecting them. Given that the format is in preview, this gap is low risk but should be tracked.
