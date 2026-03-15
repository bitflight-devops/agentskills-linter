# M002: Task-Level Demo Generation from Real Evidence

**Vision:** This milestone gives the system a truthful, agent-driven way to generate task summary videos from real run evidence — especially dashboard capture, literal tmux footage, task instructions, issues, steering moments, and final state — so long-running QA and automation work can be replayed visually without manual editing.

## Success Criteria

- An operator can trigger generation of a task-level demo video from a real task’s evidence bundle.
- The generated video uses real dashboard and tmux evidence when present and handles missing evidence honestly instead of fabricating it.
- The generated video communicates task request, clarified instructions, execution evidence, notable issues, resolution path, elapsed effort, steering moments, outcome state, and carry-forward state.
- At least one real task from this repo is rendered into a usable summary video artifact through the full workflow.

## Key Risks / Unknowns

- The evidence trail needed for task demos may exist only partially or inconsistently, which could make the first pipeline fragile or tempt manual patching.
- The repo currently lacks a Remotion workspace and video runtime path, so the first milestone crosses a new runtime boundary.
- Literal dashboard/tmux footage may be too unwieldy without a strong narrative contract, causing videos to become noisy or unwatchable.
- A task-summary abstraction that ignores human steering or carry-forward state would miss what the user actually needs for QA replay.

## Proof Strategy

- Partial and inconsistent evidence can still produce truthful task demos → retire in S01 by proving a stable task evidence bundle contract that distinguishes present versus missing assets.
- Real dashboard/tmux footage can be consumed in-repo without faking context → retire in S02 by proving a Remotion composition can ingest literal media and annotate missing evidence honestly.
- The task-summary narrative can stay useful instead of becoming a montage → retire in S03 by proving the required task video contract renders coherently from structured evidence plus real media.
- The workflow can be operator- and agent-friendly instead of editor-driven → retire in S04 by proving a real “generate demo of task” workflow exists with diagnostics.
- The assembled system works on a real task, not just fixtures → retire in S05 by proving an end-to-end render from repo evidence.

## Verification Classes

- Contract verification: schema/fixture checks for task evidence bundle shape, narrative fields, and presence-versus-missing asset handling.
- Integration verification: real media ingestion and render execution through a Remotion workspace using repo evidence.
- Operational verification: background-capable generate-demo workflow emits useful diagnostics and produces render artifacts in a real local run.
- UAT / human verification: a human can watch the real proof video and judge whether it is truthful and useful for replay, but milestone progress should not depend on subjective polish alone.

## Milestone Definition of Done

This milestone is complete only when all are true:

- All slice deliverables are complete and each slice leaves behind a demoable increment.
- The evidence bundle contract, media ingest, narrative composition, and generate-demo workflow are actually wired together.
- A real entrypoint for generating a task demo exists and is exercised against repo evidence.
- Success criteria are re-checked against a real rendered task video, not just mocked assets or static files.
- Final integrated acceptance passes for at least one real task summary video generated from this system’s evidence.

## Requirement Coverage

- Covers: R001, R002, R003, R004, R005, R006, R007, R008, R009, R010
- Partially covers: none
- Leaves for later: R012, R013, R014, R015, R016, R017
- Orphan risks: none if the evidence bundle convention is designed for later extension beyond task-level demos.

## Slices

- [ ] **S01: Task evidence contract and bundle convention** `risk:high` `depends:[]`
  > After this: a task can be represented as a structured evidence bundle that truthfully records which narrative fields and media assets exist versus which are missing.

- [ ] **S02: Remotion workspace and real media ingest** `risk:high` `depends:[S01]`
  > After this: the repo can load real dashboard capture and literal tmux footage into a Remotion composition with honest handling for incomplete evidence.

- [ ] **S03: Task summary narrative composition** `risk:high` `depends:[S01,S02]`
  > After this: a task evidence bundle can render into a watchable summary composition showing request, execution, issues, steering, elapsed effort, outcome, and carry-forward state.

- [ ] **S04: Generate-demo task workflow** `risk:medium` `depends:[S03]`
  > After this: an operator or agent can trigger “generate demo of task” through a real workflow and get artifacts plus failure diagnostics.

- [ ] **S05: End-to-end real task demo proof** `risk:medium` `depends:[S03,S04]`
  > After this: at least one real task in this system renders into a truthful summary video artifact from repo evidence through the full pipeline.

## Boundary Map

### S01 → S02

Produces:
- `TaskDemoEvidence` contract describing task request, clarified instructions, execution events, issues, steering moments, outcome state, carry-forward state, elapsed effort, and evidence asset references.
- Evidence bundle directory convention for task demos, including how present and missing assets are represented.
- Validation fixtures or tests that lock the bundle shape and missing-evidence semantics.

Consumes:
- nothing (first slice)

### S01 → S03

Produces:
- Stable narrative field names and task video contract inputs.
- Time compression metadata and outcome-state vocabulary (`complete`, `blocked`, `handoff` or equivalent).

Consumes:
- nothing (first slice)

### S02 → S03

Produces:
- In-repo Remotion workspace capable of loading task bundle media assets.
- Media ingest helpers/components for dashboard capture and literal tmux footage.
- Honest placeholder/annotation behavior for missing or partial evidence.

Consumes from S01:
- `TaskDemoEvidence` contract.
- Evidence bundle directory convention.

### S03 → S04

Produces:
- Task summary composition API/props contract suitable for render automation.
- Renderable composition that expresses the task narrative contract over real evidence.

Consumes from S01:
- Narrative fields and evidence bundle shape.

Consumes from S02:
- Media ingest components and workspace runtime.

### S03 → S05

Produces:
- Verified task summary rendering behavior and output expectations.

Consumes from S01:
- Task evidence bundles.

Consumes from S02:
- Real media ingestion.

### S04 → S05

Produces:
- CLI/agent workflow contract for “generate demo of task”.
- Artifact locations and diagnostic surfaces for successful or failed renders.

Consumes from S03:
- Task summary composition contract.

### S05 → Milestone Complete

Produces:
- End-to-end acceptance evidence that a real task can be rendered into a truthful summary video from repo evidence.
- The proof artifact used to re-check milestone success criteria.

Consumes from S03:
- Task summary composition.

Consumes from S04:
- Generate-demo workflow.
