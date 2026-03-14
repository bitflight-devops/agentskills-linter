# M001: Versioned Provider Schema and Rule Authority Pipeline

**Vision:** skilllint ships a maintainable, versioned schema and rule-authority stack that can validate Claude Code, Cursor, Codex, and AgentSkills-compatible content against provider-specific contracts, explain where each rule came from, and keep bundled validation artifacts refreshable without hand-editing opaque JSON snapshots.

## Success Criteria

- `skilllint` can validate the same repository against at least Claude Code, Cursor, and Codex using provider-specific bundled schema artifacts rather than one mixed contract.
- Validation output and rule metadata expose authoritative provenance for provider-backed checks so a maintainer can trace a rule or schema field back to its source artifact.
- The schema refresh path can regenerate or update versioned provider artifacts and the packaged CLI still loads those artifacts successfully after installation-style access.
- The milestone can be demonstrated end-to-end by exercising the real CLI against representative fixtures and seeing provider-specific results from bundled assets, not hardcoded-only behavior.

## Key Risks / Unknowns

- Provider contracts are currently stored as per-platform snapshots with inconsistent provenance structure, which can make downstream validation logic unverifiable and hard to evolve.
- The monolithic validator mixes structural, format, and provider concerns, so introducing provider-aware contracts may regress existing rule behavior if boundaries are not made explicit.
- Packaged runtime access uses `importlib.resources`, so any new versioned artifact layout must still work from the installed CLI path, not just from the repo checkout.

## Proof Strategy

- Provider contract normalization and authority tracing → retire in S01 by proving real schema/rule metadata can identify platform-specific constraints and their source authority.
- Provider-aware CLI validation without breaking brownfield behavior → retire in S02 by proving real `skilllint check` runs route through the new schema/rule stack on representative fixtures.
- Installed-runtime artifact loading and refreshability → retire in S04 by proving the assembled refresh/load/validate path works end-to-end through the real CLI/runtime entrypoint.

## Verification Classes

- Contract verification: pytest coverage for schema loading, rule metadata, provider routing, and artifact structure; static checks for real exported loaders and versioned schema files.
- Integration verification: real `skilllint check` executions against platform fixtures plus refresh/generation commands that write bundled artifacts consumed by the CLI.
- Operational verification: packaged-resource loading via `importlib.resources` continues working after artifact layout changes; no manual file patching required to update provider snapshots.
- UAT / human verification: none required if the CLI, packaged artifact loading, and fixture-backed integration paths are all exercised successfully.

## Milestone Definition of Done

This milestone is complete only when all are true:

- All slice deliverables are complete and each provider-facing slice leaves behind a demoable CLI capability.
- Shared schema, provenance, and rule-authority components are actually wired into `skilllint` rather than existing as parallel unused assets.
- The real entrypoint (`skilllint check` and any refresh/generation command introduced for schema artifacts) exists and is exercised against representative fixtures.
- Success criteria are re-checked against live CLI behavior and packaged artifact loading, not just artifact presence.
- Final integrated acceptance scenarios pass for at least Claude Code, Cursor, and Codex validation using the assembled system.

## Requirement Coverage

- Covers: none explicitly tracked — `.gsd/REQUIREMENTS.md` is missing, so this roadmap is planned in legacy compatibility mode using repository docs, existing research, and current code seams as the capability contract.
- Partially covers: none.
- Leaves for later: broader plugin-validator decomposition beyond schema/rule authority boundaries, additional third-party adapters, and any UI/documentation polish not required for the CLI capability.
- Orphan risks: without `.gsd/REQUIREMENTS.md`, there is no authoritative Active requirement list to mechanically map; milestone scope is inferred from existing M001 research and current codebase direction.

## Slices

- [x] **S01: Provider schema contracts and authority metadata** `risk:high` `depends:[]`
  > After this: maintainers can inspect versioned provider contract artifacts and rule metadata that clearly distinguish shared vs provider-specific constraints and cite their source authority.

- [x] **S02: Provider-aware CLI validation on real fixtures** `risk:high` `depends:[S01]`
  > After this: `skilllint check` can run against representative Claude Code, Cursor, and Codex fixtures through the new provider-aware contract path and produce truthful provider-specific validation results.

- [x] **S03: Refreshable schema ingestion and brownfield migration** `risk:medium` `depends:[S01]`
  > After this: maintainers can refresh or regenerate bundled provider schema artifacts through a supported repo workflow, and the brownfield codebase consumes the new artifact layout without hand-maintained duplication.

- [ ] **S04: End-to-end packaged integration proof** `risk:medium` `depends:[S02,S03]`
  > After this: the assembled refresh → bundled artifact load → CLI validation flow is proven through the real runtime path, showing installed-style resource loading and cross-provider validation working together end-to-end.

## Boundary Map

### S01 → S02

Produces:
- `packages/skilllint/schemas/<provider>/vN.json` versioned provider contract files with stable top-level metadata for provider id, schema version, and provenance payloads.
- `packages/skilllint/rule_registry.py` or adjacent rule metadata surface that can answer a rule's authority/source in structured form instead of freeform strings only.
- A normalized contract boundary defining which constraints are shared AgentSkills rules versus provider-overlay rules.
- Tests or fixture assertions that lock the metadata shape expected by downstream validation.

Consumes:
- Existing bundled provider snapshot files under `packages/skilllint/schemas/`.
- Existing AS-series and validator rule declarations as the brownfield source of current behavior.

### S01 → S03

Produces:
- A versioned artifact convention and provenance schema that refresh tooling can write without guessing file layout.
- Source-authority metadata fields suitable for generated artifacts from provider docs or repo research.

Consumes:
- Existing research on schema gaps and provenance weaknesses from `slices/S01/S01-RESEARCH.md`.

### S02 → S04

Produces:
- Real CLI/provider routing from `skilllint check --platform ...` into the new contract stack.
- Representative integration fixtures and assertions proving provider-specific validation results.
- Stable validation output that includes provider/rule authority evidence for downstream end-to-end proof.

Consumes from S01:
- Versioned provider contracts.
- Structured rule/source authority metadata.

### S03 → S04

Produces:
- Supported refresh/regeneration command or script workflow for bundled provider artifacts.
- Brownfield migration of loader paths so packaged resources resolve the new versioned layout.
- Artifact-generation verification that refreshed outputs remain consumable by tests and the CLI.

Consumes from S01:
- Versioned artifact convention.
- Provenance metadata shape.

### S04 → Milestone Complete

Produces:
- End-to-end acceptance evidence showing refreshable artifacts, packaged loading, and cross-provider CLI validation all work together.
- The final proof record used to re-check milestone success criteria.

Consumes from S02:
- Provider-aware CLI validation path and fixtures.

Consumes from S03:
- Refreshable artifact workflow and packaged loader migration.
