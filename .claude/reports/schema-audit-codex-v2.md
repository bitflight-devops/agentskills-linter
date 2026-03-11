---
# Codex Schema Audit v2

**Schema under audit**: `packages/skilllint/schemas/codex/v1.json`
**Audit date**: 2026-03-10

## Source files examined

- `packages/skilllint/schemas/codex/v1.json`
- `.claude/vendor/codex/codex-rs/execpolicy/README.md` — primary `.rules` language reference
- `.claude/vendor/codex/codex-rs/execpolicy-legacy/README.md` — legacy engine (separate, deprecated)
- `.claude/vendor/codex/codex-cli/README.md` — AGENTS.md documentation
- `.claude/vendor/codex/AGENTS.md` — Codex contributor instructions (no `.rules` language content)

---

## Findings

### 1. `host_executable` — GAP

`host_executable` is a documented, first-class callable in `.rules` files. The schema has no entry for it.

From `.claude/vendor/codex/codex-rs/execpolicy/README.md`:

```starlark
host_executable(
    name = "git",
    paths = [
        "/opt/homebrew/bin/git",
        "/usr/bin/git",
    ],
)
```

Fields: `name` (string, required — the basename), `paths` (list of strings, optional).

Schema entry: absent entirely.

**Verdict**: GAP — `host_executable` must be added.

---

### 2. `prefix_rule` `known_fields` — PASS

All five fields (`pattern`, `decision`, `justification`, `match`, `not_match`) are explicitly documented in the execpolicy README. No undocumented fields in schema. No documented fields missing.

---

### 3. `valid_decisions` — PASS

From execpolicy README: "`decision` defaults to `allow`; valid values: `allow`, `prompt`, `forbidden`." Exact match.

---

### 4. `required_fields: ["pattern"]` — PASS

`pattern` is the only field without a documented default or "optional" qualifier. All others: `decision` has a default (`allow`), `justification` is "optional human-readable rationale", `match`/`not_match` are supplementary.

---

### 5. `agents_md` `x-non-empty` — PASS

From `codex-cli/README.md`: "You can give Codex extra instructions and guidance using `AGENTS.md` files." No documentation states an empty AGENTS.md is valid or useful. Constraint is well-founded.

---

### 6. Other top-level callables — PASS

Exactly two callables exist: `prefix_rule` and `host_executable`. The legacy engine uses `define_program(...)` in `.policy` files — a separate deprecated format not targeted by this schema.

---

## Recommended changes

- **Add `host_executable` entry** to `file_types` in `packages/skilllint/schemas/codex/v1.json`:

```json
"host_executable": {
  "x-experimental": true,
  "known_fields": ["name", "paths"],
  "required_fields": ["name"]
}
```

`name` is required (the basename being registered). `paths` is optional per the README.

- No other changes needed.
