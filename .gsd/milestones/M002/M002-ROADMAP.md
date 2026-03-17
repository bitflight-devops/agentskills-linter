# M002: Validator Decomposition and Scan-Truth Hardening

**Vision:** `skilllint` becomes a maintainable, trustworthy detector rather than a brownfield validator monolith with mixed responsibilities and uncertain constraints. This milestone clarifies schema-vs-rule boundaries, makes provider/shared ownership traceable, fixes scan target selection semantics, and proves detection truth against real external repos without hiding genuine upstream issues.

## Success Criteria

- Maintainers can look at a constraint and tell whether it belongs in schema, a provider overlay, or a lint rule without guessing.
- Directory scans select the right files based on manifest-driven enumeration, documented plugin auto-discovery, or provider-known directory structure depending on the scan root.
- Official external repo scans no longer produce unjustified schema/frontmatter hard failures; any remaining hard failures are explainable and reviewable as likely real findings.
- Maintainer docs include concrete worked examples for schema updates, provider overlays, lint rules, and provenance metadata.
- The real `uv run skilllint check ...` path is used to prove the milestone, not just internal helper tests.

## Key Risks / Unknowns

- Hard failures in official repos may reflect a mix of real issues, stale constraints, and hallucinated rules — if we do not classify them correctly, we will either weaken the linter incorrectly or keep shipping false positives.
- Scan/discovery behavior currently spans plugin manifests, auto-discovery, and structure-only provider trees — if we do not model those separately, external scans will remain inconsistent.
- The validator monolith may hide more shared responsibilities than current seams suggest — decomposition could stall if responsibilities are not mapped before extraction.
- Docs may oversimplify architecture in ways that encourage new work to drift back into the wrong layer.

## Proof Strategy

- Validator monolith and ownership confusion → retire in S01 by proving the remaining responsibilities are mapped and extracted into clearer internal boundaries.
- Schema-vs-rule and provider/shared ambiguity → retire in S02 by proving constraints route through explicit ownership seams and maintainers have a consistent model.
- Scan target confusion → retire in S03 by proving manifest-driven, auto-discovery, and structure-only scans select the intended files.
- Official-repo hard-failure truth → retire in S04 by classifying disputed hard failures using docs, runtime behavior, and implementation evidence.
- Maintainer documentation drift → retire in S05 by proving each extension path has a worked example tied to the post-refactor architecture.
- Real CLI regression risk → retire in S06 by proving external repo scans still work through `skilllint check` and remaining findings are reportable rather than hidden.

## Verification Classes

- Contract verification: pytest coverage for module boundaries, discovery behavior, rule ownership, and report classification.
- Integration verification: real `uv run skilllint check ...` executions against internal fixtures and external repos.
- Operational verification: local scan commands over neighboring external repos produce trustworthy hard-failure behavior and reviewable findings.
- UAT / human verification: human review of remaining official-repo findings after the truth pass to decide whether they are genuine upstream issues.

## Milestone Definition of Done

This milestone is complete only when all are true:

- All slice deliverables are complete and each slice leaves behind a demoable detection or maintainer capability.
- Internal validator boundaries are actually wired into the real CLI path rather than existing as parallel abstractions.
- Directory scanning behaves correctly for plugin manifests, plugin auto-discovery, and provider structure-only trees.
- Official external repo scans no longer produce unjustified schema/frontmatter hard failures.
- Any remaining official-repo hard failures are surfaced as reviewable findings rather than silently absorbed into compatibility behavior.
- Maintainer docs with worked examples exist for schema updates, provider overlays, lint rules, and provenance metadata.
- Final integrated scan verification passes through the real `uv run skilllint check ...` entrypoint.

## Requirement Coverage

- Covers: R012, R013, R014, R015, R016, R017, R018, R019, R020, R021, R022, R023, R024, R025
- Partially covers: none
- Leaves for later: R026, R027, R028
- Orphan risks: none if the official-repo truth pass produces a reviewable findings report.

## Slices

- [ ] **S01: Validator seam map and boundary extraction** `risk:high` `depends:[]`
  > After this: the repo has explicit internal validator boundaries and the monolith no longer owns every major responsibility by default.

- [ ] **S02: Constraint ownership routing cleanup** `risk:high` `depends:[S01]`
  > After this: schema-backed constraints, provider overlays, and lint rules follow a clear ownership model in code and tests.

- [ ] **S03: Scan target discovery contract** `risk:high` `depends:[S01]`
  > After this: directory scans correctly select files using manifest enumeration, documented auto-discovery, or provider-known structure depending on context.

- [ ] **S04: Official-repo hard-failure truth pass** `risk:high` `depends:[S02,S03]`
  > After this: disputed hard failures from official-repo scans are classified as justified constraint, provider-specific constraint, legacy rule, recommendation-only rule, or likely hallucinated rule with evidence.

- [ ] **S05: Maintainer extension-path documentation** `risk:medium` `depends:[S02,S03,S04]`
  > After this: maintainers have worked examples showing how to add a schema update, provider overlay, lint rule, and provenance metadata in the post-refactor structure.

- [ ] **S06: External scan proof and findings report** `risk:medium` `depends:[S04,S05]`
  > After this: real CLI scans against external repos act as regression proof for correct detection, and any remaining real official-repo failures are clearly reported for review.

## Boundary Map

### S01 → S02
Produces:
- Extracted validator ownership seams for scan orchestration, schema/frontmatter validation, lint-rule execution, and reporting.
- Updated internal module boundaries that reduce direct dependency on one monolithic validator path.
- Tests that lock the extracted seams as real behavior rather than comments or TODOs.

Consumes:
- nothing (first slice)

### S01 → S03
Produces:
- A stable scan orchestration layer or equivalent explicit seam where target selection logic can live.
- Brownfield map of current scan entrypoints and responsibility boundaries.

Consumes:
- nothing (first slice)

### S02 → S04
Produces:
- Explicit ownership model for schema/frontmatter rules, provider overlays, and shared lint rules.
- A classification model for hard failures vs second-level findings.
- Rule/provenance surfaces that make disputed constraints traceable.

Consumes from S01:
- Extracted validator boundaries.

### S03 → S04
Produces:
- Deterministic scan target selection for manifest-driven plugins, plugin auto-discovery, and provider structure-only roots.
- Tests or fixtures that prove which files are in-scope for each scan mode.

Consumes from S01:
- Scan orchestration seam.

### S02 → S05
Produces:
- Stable ownership rules that documentation can teach truthfully.
- Real examples of where schema, provider overlay, and lint rule logic now live.

Consumes from S01:
- Extracted validator boundaries.

### S03 → S05
Produces:
- Stable discovery semantics that documentation can describe without caveats.

Consumes from S01:
- Scan orchestration seam.

### S04 → S06
Produces:
- Classified official-repo failure families with evidence-backed decisions.
- A list of remaining hard failures that should remain visible for human review.

Consumes from S02:
- Ownership and rule classification model.

Consumes from S03:
- Correct scan target selection behavior.

### S05 → S06
Produces:
- Maintainer docs aligned with the final architecture and detection model.

Consumes from S02:
- Ownership model.

Consumes from S03:
- Discovery model.
