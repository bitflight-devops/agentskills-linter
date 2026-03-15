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

### R001 — Generate a task-level demo video from real run evidence
- Class: primary-user-loop
- Status: active
- Description: An operator can generate a summary video for a task using real evidence produced by the system, not a manually assembled edit.
- Why it matters: Task-level replay is the foundation for proving long-running work visually without supervising it second by second.
- Source: user
- Primary owning slice: M002/S04
- Supporting slices: M002/S01, M002/S02, M002/S03, M002/S05
- Validation: mapped
- Notes: This is the core first-use case and the base primitive for higher-level slice and milestone videos.

### R002 — Build demo narratives from truthful evidence only
- Class: constraint
- Status: active
- Description: Generated demos must reflect only real recordings, logs, dashboard captures, prompts, task steps, and state transitions actually produced by the system.
- Why it matters: The user explicitly does not want fake or synthetic misrepresentation; trust is the product.
- Source: user
- Primary owning slice: M002/S02
- Supporting slices: M002/S03, M002/S05
- Validation: mapped
- Notes: Missing evidence must be handled honestly in the narrative.

### R003 — Accept partial-but-real evidence bundles
- Class: continuity
- Status: active
- Description: The first version of the pipeline must generate usable videos from incomplete but real evidence bundles and improve as richer capture assets become available.
- Why it matters: The video system needs to start working before capture completeness is perfect, or it will become blocked behind infrastructure hardening.
- Source: user
- Primary owning slice: M002/S01
- Supporting slices: M002/S02, M002/S03, M002/S05
- Validation: mapped
- Notes: Output should surface what evidence was present versus missing.

### R004 — Include existing dashboard capture and literal tmux footage
- Class: integration
- Status: active
- Description: Task demos must be able to incorporate the existing vm-pilot dashboard and literal recordings of tmux panes as they appeared.
- Why it matters: These are the core truth surfaces the user wants viewers to see.
- Source: user
- Primary owning slice: M002/S02
- Supporting slices: M002/S03, M002/S05
- Validation: mapped
- Notes: Remotion is for transitions, overlays, pacing, and explanation around real footage.

### R005 — Preserve the task summary narrative contract
- Class: core-capability
- Status: active
- Description: Every generated task video must be able to show task request, clarified structure/instructions, execution evidence, notable issues, resolution path, final state/outcome, carry-forward state, elapsed effort/time compression context, human steering moments, and complete/blocked/handed-off status.
- Why it matters: Without this contract, videos risk becoming generic montages instead of operational summaries.
- Source: user
- Primary owning slice: M002/S03
- Supporting slices: M002/S05
- Validation: mapped
- Notes: This defines what makes a task video useful to operators and QA.

### R006 — Show where human steering happened
- Class: failure-visibility
- Status: active
- Description: Generated demos must identify when inspector feedback or user guidance altered the run or the outcome.
- Why it matters: The user wants to show not just automation, but how automation was steered.
- Source: user
- Primary owning slice: M002/S03
- Supporting slices: M002/S05
- Validation: mapped
- Notes: Steering moments should be tied to evidence, not inferred vaguely.

### R007 — Make task outcome state explicit
- Class: operability
- Status: active
- Description: Generated demos must clearly communicate whether the task completed, blocked, or handed off, and what state is available for the next step.
- Why it matters: Operators need replay that supports continuation, not just retrospective viewing.
- Source: user
- Primary owning slice: M002/S03
- Supporting slices: M002/S05
- Validation: mapped
- Notes: Final state must be concrete enough to support downstream work.

### R008 — Use an extendable evidence directory and input model
- Class: quality-attribute
- Status: active
- Description: The demo pipeline must use a stable, extendable evidence bundle shape and directory convention so richer assets can be added later without redesigning the workflow.
- Why it matters: The user wants this to scale from task videos into slice, milestone, and broader product demos.
- Source: inferred
- Primary owning slice: M002/S01
- Supporting slices: M002/S04
- Validation: mapped
- Notes: This should be designed for forward extension, not one-off task demos.

### R009 — Run video generation as an agent-driven background workflow
- Class: operability
- Status: active
- Description: Video generation should run as a background-capable agent workflow that can be steered and iterated on, not as a manual editing sidecar.
- Why it matters: The user wants demos generated alongside the work, with feedback and revision possible without turning the process into hand-editing.
- Source: user
- Primary owning slice: M002/S04
- Supporting slices: M002/S05
- Validation: mapped
- Notes: The workflow should surface diagnostics when generation fails.

### R010 — Support real task-demo proof from repo evidence
- Class: launchability
- Status: active
- Description: The milestone must end with at least one real task in this system rendered into a truthful summary video artifact from actual repo evidence.
- Why it matters: Without a real proof artifact, the milestone would only establish pieces, not the promised capability.
- Source: user
- Primary owning slice: M002/S05
- Supporting slices: none
- Validation: mapped
- Notes: Partial evidence is acceptable if the output stays honest about coverage.

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

### R012 — Generate slice-level recap videos
- Class: differentiator
- Status: deferred
- Description: The system can roll task evidence and outputs up into a slice-level recap video.
- Why it matters: Slice videos are the next layer above task summaries and support broader status communication.
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: Deferred until task-level pipeline is working.

### R013 — Generate milestone-level narrative videos
- Class: differentiator
- Status: deferred
- Description: The system can roll slice/task evidence into milestone-level narrative demos.
- Why it matters: This supports larger demonstrations and release/update storytelling.
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: Deferred until task and slice composition patterns stabilize.

### R014 — Rich QA and diagnostic story templates
- Class: admin/support
- Status: deferred
- Description: The system supports richer templates for installer verification, environment bring-up, cross-host communication proof, and inspector-driven diagnosis.
- Why it matters: These are high-value story types, but they build on the general task-demo foundation.
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: This is the likely focus of the next milestone after M002.

### R015 — Broader capture completeness and audit hardening
- Class: continuity
- Status: deferred
- Description: The traceability layer captures a richer, more complete pool of screens, terminals, events, state changes, and audit artifacts for demo generation.
- Why it matters: Better evidence improves the quality and fidelity of generated demos.
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: Not a prerequisite for proving the first partial-but-real pipeline.

### R016 — Feedback-driven video revision loop
- Class: operability
- Status: deferred
- Description: An operator can review a generated video, provide feedback, and steer an agent to revise it.
- Why it matters: The user wants background generation that can still be steered and improved.
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: Deferred until the initial generation pipeline exists.

### R017 — External-facing product demo generation
- Class: differentiator
- Status: deferred
- Description: The same evidence-driven pipeline can produce outward-facing demos that showcase wins and explain how hard problems were diagnosed by AI.
- Why it matters: This is a natural extension once internal replay and QA proof are working.
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: Secondary audience after internal QA/stakeholder use.

## Out of Scope

### R018 — Manual video editing as the primary workflow
- Class: anti-feature
- Status: out-of-scope
- Description: The demo system depends on a human manually assembling or editing each video as the normal path.
- Why it matters: This prevents the work from turning into a sidecar editing job disconnected from the run itself.
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: n/a
- Notes: Manual touch-ups may exist later, but not as the core contract.

### R019 — Fake or reconstructed terminal behavior without source evidence
- Class: anti-feature
- Status: out-of-scope
- Description: The system invents terminal behavior, states, or outcomes that were not captured in the evidence.
- Why it matters: This would violate the trust model the user explicitly wants.
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: n/a
- Notes: Remotion may explain and sequence evidence, but not fabricate it.

### R020 — Text-only summary videos detached from real recordings
- Class: anti-feature
- Status: out-of-scope
- Description: The system emits videos that are just text on a screen without grounding them in real dashboard, tmux, or other recorded evidence.
- Why it matters: The user wants to show the hard parts being automated, not just narrate them abstractly.
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: n/a
- Notes: Text overlays are allowed when attached to real evidence.

## Traceability

| ID | Class | Status | Primary owner | Supporting | Proof |
|---|---|---|---|---|---|
| R001 | primary-user-loop | active | M002/S04 | M002/S01, M002/S02, M002/S03, M002/S05 | mapped |
| R002 | constraint | active | M002/S02 | M002/S03, M002/S05 | mapped |
| R003 | continuity | active | M002/S01 | M002/S02, M002/S03, M002/S05 | mapped |
| R004 | integration | active | M002/S02 | M002/S03, M002/S05 | mapped |
| R005 | core-capability | active | M002/S03 | M002/S05 | mapped |
| R006 | failure-visibility | active | M002/S03 | M002/S05 | mapped |
| R007 | operability | active | M002/S03 | M002/S05 | mapped |
| R008 | quality-attribute | active | M002/S01 | M002/S04 | mapped |
| R009 | operability | active | M002/S04 | M002/S05 | mapped |
| R010 | launchability | active | M002/S05 | none | mapped |
| R011 | integration | validated | M001/S04 | M001/S01, M001/S02, M001/S03 | validated |
| R012 | differentiator | deferred | none | none | unmapped |
| R013 | differentiator | deferred | none | none | unmapped |
| R014 | admin/support | deferred | none | none | unmapped |
| R015 | continuity | deferred | none | none | unmapped |
| R016 | operability | deferred | none | none | unmapped |
| R017 | differentiator | deferred | none | none | unmapped |
| R018 | anti-feature | out-of-scope | none | none | n/a |
| R019 | anti-feature | out-of-scope | none | none | n/a |
| R020 | anti-feature | out-of-scope | none | none | n/a |

## Coverage Summary

- Active requirements: 10
- Mapped to slices: 10
- Validated: 1
- Unmapped active requirements: 0
