# Requirements

This file is the explicit capability and coverage contract for the project.

Use it to track what is actively in scope, what has been validated by completed work, what is intentionally deferred, and what is explicitly out of scope.

Guidelines:
- Keep requirements capability-oriented, not a giant feature wishlist.
- Requirements should be atomic, testable, and stated in plain language.
- Every **Active** requirement should be mapped to a slice, deferred, blocked with reason, or moved out of scope.
- Each requirement should have one accountable primary owner and may have supporting slices.
- Research may suggest requirements, but research does not silently make them binding.
- Validation means the requirement was actually proven by completed work and verification, not just discussed.

## Active

### R012 — Decompose remaining validator monolith into explicit layers
- Class: quality-attribute
- Status: active
- Description: The remaining brownfield validator logic must be split into clearer internal modules so maintainers no longer default to editing one monolithic validator path.
- Why it matters: Architectural drift back into one dominant validator file makes future rule and schema work harder to reason about and easier to break.
- Source: user
- Primary owning slice: M002/S01
- Supporting slices: M002/S02, M002/S03
- Validation: mapped
- Notes: This is about internal ownership and maintainability, not new end-user functionality.

### R013 — Separate schema validation from lint-rule validation cleanly
- Class: core-capability
- Status: active
- Description: The system must clearly distinguish schema/frontmatter/shape validation from lint-style and semantic rule validation.
- Why it matters: Without a hard boundary, detection behavior becomes muddy and false positives are hard to diagnose.
- Source: user
- Primary owning slice: M002/S02
- Supporting slices: M002/S04, M002/S06
- Validation: mapped
- Notes: This includes classification of hard failures versus second-level findings.

### R014 — Clarify provider-specific vs shared rule ownership
- Class: quality-attribute
- Status: active
- Description: The linter must make it obvious whether a constraint is shared across providers, provider-specific, schema-backed, or rule-backed.
- Why it matters: Provider-specific behavior becomes hard to trace when ownership is implicit or mixed.
- Source: user
- Primary owning slice: M002/S02
- Supporting slices: M002/S05
- Validation: mapped
- Notes: Traceability matters both in code structure and in docs.

### R015 — Use manifest-driven scanning when plugin manifests explicitly enumerate components
- Class: integration
- Status: active
- Description: When a plugin manifest explicitly lists agents, commands, skills, or hooks, `skilllint` must use that manifest as the source of truth for scan target selection.
- Why it matters: Scan correctness depends on following the plugin's declared structure when that declaration exists.
- Source: user
- Primary owning slice: M002/S03
- Supporting slices: M002/S04, M002/S06
- Validation: mapped
- Notes: Detection correctness comes before autofix correctness.

### R016 — Use documented auto-discovery when plugin manifests omit component arrays
- Class: integration
- Status: active
- Description: When plugin manifests do not explicitly enumerate components, `skilllint` must follow the documented plugin auto-discovery protocol to decide what to scan.
- Why it matters: Real plugin repos rely on discovery behavior, and getting that wrong creates false positives and false negatives.
- Source: user
- Primary owning slice: M002/S03
- Supporting slices: M002/S04, M002/S06
- Validation: mapped
- Notes: The documented plugin behavior is part of the compatibility contract.

### R017 — Use structure-based discovery for unmanifested provider directories
- Class: integration
- Status: active
- Description: When scanning `.claude/`, `.agent/`, `.agents/`, `.gemini/`, or `.cursor/` trees outside a plugin manifest context, `skilllint` must use provider-known directory structure rather than expecting a manifest.
- Why it matters: These directory trees are valid scan roots but do not have plugin manifests to consult.
- Source: user
- Primary owning slice: M002/S03
- Supporting slices: M002/S04, M002/S06
- Validation: mapped
- Notes: This requirement is specifically about discovery and target selection.

### R018 — Detect official-repo content without unjustified schema/frontmatter hard failures
- Class: launchability
- Status: active
- Description: Scans of official external repos must not produce schema/frontmatter hard failures unless those failures are supported by current authority or proven runtime behavior.
- Why it matters: External repo scans are the proving ground for whether the linter is detecting reality or enforcing hallucinated constraints.
- Source: user
- Primary owning slice: M002/S04
- Supporting slices: M002/S06
- Validation: validated
- Notes: FM004/FM007/AS004 downgraded to warnings; remaining hard failures (FM003/FM005) are genuine schema violations documented in S04-FINDINGS.md.

### R019 — Provide evidence-driven rule-truth evaluation for disputed constraints
- Class: failure-visibility
- Status: active
- Description: For disputed rules, the project must gather evidence from provider docs, runtime behavior, and current implementation before deciding whether a rule is real, legacy, provider-specific, recommendation-only, or hallucinated.
- Why it matters: The user wants the project to blame itself first and avoid hardening invented rules into architecture.
- Source: user
- Primary owning slice: M002/S04
- Supporting slices: M002/S05, M002/S06
- Validation: validated
- Notes: Classification documented in plugin_validator.py code comments and S04-FINDINGS.md with runtime evidence.

### R020 — Document how to add a schema update
- Class: admin/support
- Status: active
- Description: Maintainer docs must show a concrete worked example of how to update or add schema-backed validation.
- Why it matters: Docs should teach the correct extension path instead of forcing contributors to reverse-engineer the architecture.
- Source: user
- Primary owning slice: M002/S05
- Supporting slices: none
- Validation: mapped
- Notes: Example should reflect the post-refactor structure, not the legacy monolith.

### R021 — Document how to add a provider overlay
- Class: admin/support
- Status: active
- Description: Maintainer docs must show a concrete worked example of how to implement a provider-specific overlay.
- Why it matters: Provider-specific behavior is one of the main areas the user wants to keep traceable.
- Source: user
- Primary owning slice: M002/S05
- Supporting slices: none
- Validation: mapped
- Notes: Example should make shared vs provider-specific responsibility obvious.

### R022 — Document how to add a new lint rule
- Class: admin/support
- Status: active
- Description: Maintainer docs must show a concrete worked example of how to add a new lint rule in the correct layer.
- Why it matters: Contributors need to know when something belongs in a lint rule rather than schema or provider overlay logic.
- Source: user
- Primary owning slice: M002/S05
- Supporting slices: none
- Validation: mapped
- Notes: This is documentation for detection behavior, not autofix behavior.

### R023 — Document how to add provenance metadata
- Class: admin/support
- Status: active
- Description: Maintainer docs must show how to attach and surface provenance metadata for schemas and rules.
- Why it matters: Docs lagging behind architecture would cause people to guess wrong about traceability.
- Source: user
- Primary owning slice: M002/S05
- Supporting slices: none
- Validation: mapped
- Notes: Provenance must remain explicit and machine-readable.

### R024 — Prove behavior through real CLI scans on external repos
- Class: operability
- Status: active
- Description: The milestone must prove its detection behavior using real `uv run skilllint check ...` scans against external repos, not just synthetic internal fixtures.
- Why it matters: The user explicitly wants confidence grounded in official ecosystem content.
- Source: user
- Primary owning slice: M002/S06
- Supporting slices: M002/S04
- Validation: mapped
- Notes: Initial focus is `../skills`, `../claude-plugins-official`, and `../claude-code-plugins`.

### R025 — Preserve user-facing CLI scan behavior while refactoring internals
- Class: continuity
- Status: active
- Description: Internal decomposition must not break the real `skilllint check` entrypoint or make scan behavior less predictable for users.
- Why it matters: Architecture cleanup is only useful if the real tool remains dependable.
- Source: inferred
- Primary owning slice: M002/S06
- Supporting slices: M002/S01, M002/S02, M002/S03
- Validation: mapped
- Notes: The milestone should prove this with real CLI verification rather than code inspection alone.

## Validated

### R011 — Provider-aware packaged CLI validation for skilllint
- Class: integration
- Status: validated
- Description: The packaged CLI can validate provider-specific skill content using bundled versioned schema artifacts with authority metadata.
- Why it matters: This is the completed capability delivered by M001 and remains part of the repo’s current state.
- Source: execution
- Primary owning slice: M001/S04
- Supporting slices: M001/S01, M001/S02, M001/S03
- Validation: validated
- Notes: Proven by packaged E2E tests and milestone completion artifacts.

## Deferred

### R026 — Expand compatibility validation to Codex plugin repos
- Class: differentiator
- Status: deferred
- Description: The scan-truth and compatibility proof should later include real Codex ecosystem repos.
- Why it matters: Codex support is part of the broader multi-provider direction, but not the first external proof target.
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: User explicitly said this can happen later.

### R027 — Expand compatibility validation to OpenCode plugin repos
- Class: differentiator
- Status: deferred
- Description: The scan-truth and compatibility proof should later include real OpenCode ecosystem repos.
- Why it matters: OpenCode support matters, but it is not required for the first architecture-and-detection milestone.
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: User explicitly said this can happen later.

### R028 — Add a repeatable automated probe harness around Claude CLI validation experiments
- Class: operability
- Status: deferred
- Description: The project may later automate Claude CLI runtime-probe experiments into a repeatable harness rather than relying on milestone-by-milestone manual investigation.
- Why it matters: This would improve long-term repeatability, but is not required to complete the current milestone.
- Source: inferred
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: For now, runtime probes are part of the evidence-gathering method, not a separate deliverable.

## Out of Scope

### R029 — Ensure autofix implementations are correct for newly clarified rules
- Class: anti-feature
- Status: out-of-scope
- Description: This milestone does not guarantee that autofix behavior is correct or updated for every rule whose detection behavior is clarified.
- Why it matters: This prevents scope creep into fix logic when the user only wants correct detection in this phase.
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: n/a
- Notes: Detection correctness comes first; autofix can follow later.

### R030 — Broaden scope into new lint-rule families unrelated to scan truth and architecture cleanup
- Class: anti-feature
- Status: out-of-scope
- Description: This milestone does not expand into unrelated new rule families just because the architecture is being cleaned up.
- Why it matters: Keeps the milestone focused on decomposition, scan truth, and maintainability.
- Source: inferred
- Primary owning slice: none
- Supporting slices: none
- Validation: n/a
- Notes: New rule families can be planned after the boundary cleanup if needed.

### R031 — Silence all warning-level findings in official repos
- Class: anti-feature
- Status: out-of-scope
- Description: This milestone does not require official repos to become completely warning-free.
- Why it matters: The user wants to inspect second-level findings rather than force the tool to absorb or hide them.
- Source: inferred
- Primary owning slice: none
- Supporting slices: none
- Validation: n/a
- Notes: Warnings may remain as long as they are truthful and reviewable.

## Traceability

| ID | Class | Status | Primary owner | Supporting | Proof |
|---|---|---|---|---|---|
| R012 | quality-attribute | active | M002/S01 | M002/S02, M002/S03 | mapped |
| R013 | core-capability | active | M002/S02 | M002/S04, M002/S06 | mapped |
| R014 | quality-attribute | active | M002/S02 | M002/S05 | mapped |
| R015 | integration | active | M002/S03 | M002/S04, M002/S06 | mapped |
| R016 | integration | active | M002/S03 | M002/S04, M002/S06 | mapped |
| R017 | integration | active | M002/S03 | M002/S04, M002/S06 | mapped |
| R018 | launchability | active | M002/S04 | M002/S06 | validated |
| R019 | failure-visibility | active | M002/S04 | M002/S05, M002/S06 | validated |
| R020 | admin/support | active | M002/S05 | none | mapped |
| R021 | admin/support | active | M002/S05 | none | mapped |
| R022 | admin/support | active | M002/S05 | none | mapped |
| R023 | admin/support | active | M002/S05 | none | mapped |
| R024 | operability | active | M002/S06 | M002/S04 | mapped |
| R025 | continuity | active | M002/S06 | M002/S01, M002/S02, M002/S03 | mapped |
| R011 | integration | validated | M001/S04 | M001/S01, M001/S02, M001/S03 | validated |
| R026 | differentiator | deferred | none | none | unmapped |
| R027 | differentiator | deferred | none | none | unmapped |
| R028 | operability | deferred | none | none | unmapped |
| R029 | anti-feature | out-of-scope | none | none | n/a |
| R030 | anti-feature | out-of-scope | none | none | n/a |
| R031 | anti-feature | out-of-scope | none | none | n/a |

## Coverage Summary

- Active requirements: 14
- Mapped to slices: 14
- Validated: 1
- Unmapped active requirements: 0
