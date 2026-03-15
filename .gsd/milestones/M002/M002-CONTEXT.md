# M002: Task-Level Demo Generation from Real Evidence — Context

**Gathered:** 2026-03-14
**Status:** Ready for planning

## Project Description

The user wants this system to generate truthful, visual demo artifacts from the work it already does. The first goal is not a generic promo video system — it is a task-level summary video pipeline that can show what happened during long-running, partly unsupervised QA and automation work.

The key evidence sources the user cares about are the existing vm-pilot dashboard and literal recordings of tmux sessions with the instructions being given. The video layer should use Remotion for transitions, overlays, pacing, and explanation between real scenes. It should not fake behavior, reconstruct terminal activity that was not captured, or collapse everything into text-only summaries detached from real evidence.

The user wants to be able to say effectively “generate demo of task” for any task in the system, and have the resulting video summarize the task request, clarified structure, execution effort, problems encountered, steering moments, outcome, and what carries forward. This should be designed to extend later into slice-level, milestone-level, and outward-facing product demos.

## Why This Milestone

Long-running QA and environment-automation workflows are not watched second by second. The operator needs a visual replay that shows what was done, where effort went, how problems were encountered and worked through, and what state the system ended in. This milestone establishes the first truthful task-summary video workflow so replay and proof become part of the system, not a separate editing project.

The user explicitly prefers proving first video generation from partial but real assets over waiting for perfect capture completeness. That means the milestone should prove a correct evidence-to-video pipeline now, while leaving room for richer capture coverage later.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Trigger generation of a task-level summary video from real task evidence already captured by the system.
- Watch a video that shows task request, instructions, dashboard/tmux evidence, issues, steering, elapsed effort, and resulting state.
- Use the video as replay/proof for internal QA and stakeholder review without manually editing it together.

### Entry point / environment

- Entry point: agent/CLI workflow for “generate demo of task”
- Environment: local dev with in-repo evidence assets and a Remotion workspace
- Live dependencies involved: Node.js, Remotion, local media assets, task/evidence metadata from this repo

## Completion Class

- Contract complete means: a stable task evidence bundle contract and task video summary contract exist and are exercised by tests and fixture/artifact checks.
- Integration complete means: real dashboard/tmux/task evidence can be consumed by a Remotion composition and rendered through a real generate-demo workflow.
- Operational complete means: video generation can run as a background-capable agent workflow with useful diagnostics, even when evidence is partial.

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- A real task in this system can be turned into a truthful summary video artifact using actual evidence from the repo.
- The video explicitly communicates outcome state, steering moments, time compression, and carry-forward state.
- The pipeline works without relying on manual assembly as the normal path.

## Risks and Unknowns

- Existing evidence may be incomplete or inconsistently structured — this matters because the first pipeline must stay truthful without becoming brittle.
- The repo is currently Python-first with no Remotion app scaffold — this matters because M002 crosses into a new Node/React/video runtime boundary.
- Literal tmux footage and dashboard captures may be operationally large or awkward to edit — this matters for pacing, render time, and composition design.
- A generic task-video contract may underfit the real QA stories the user cares about — this matters because the first abstraction could be too thin if it ignores steering and carry-forward state.

## Existing Codebase / Prior Art

- `packages/skilllint/` — Current Python CLI package and testing patterns; likely source of task/evidence metadata conventions or integration points.
- `.gsd/` artifacts — Existing structured planning, state, summary, and decision records that can inform task-level narrative inputs.
- `dist/skilllint-*.whl` and packaged E2E tests from M001 — Evidence the repo already supports cross-runtime proof culture and end-to-end acceptance testing.
- Remotion docs (`/docs/ai/skills`, `/docs/ai/claude-code`) — Prior art for skill-guided video generation and project setup.

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- R001 — Generate a task-level demo video from real run evidence.
- R002 — Build demo narratives from truthful evidence only.
- R003 — Accept partial-but-real evidence bundles.
- R004 — Include existing dashboard capture and literal tmux footage.
- R005 — Preserve the task summary narrative contract.
- R006 — Show where human steering happened.
- R007 — Make task outcome state explicit.
- R008 — Use an extendable evidence directory and input model.
- R009 — Run video generation as an agent-driven background workflow.
- R010 — Support real task-demo proof from repo evidence.

## Scope

### In Scope

- Task-level demo generation only.
- Evidence bundle shape and directory/input contract for task demos.
- Real media ingest for dashboard and literal tmux capture.
- Remotion-based task summary composition with overlays/transitions/explanation.
- A triggerable workflow for generating a task demo artifact.
- One real task-demo proof artifact from repo evidence.

### Out of Scope / Non-Goals

- Slice-level or milestone-level demo generation.
- Full capture completeness across all future evidence types.
- Manual-editor-first workflows.
- Fake or reconstructed behavior without source evidence.
- External-facing polish as the primary goal.

## Technical Constraints

- The first pipeline must work with partial but real assets.
- Real footage remains the source of truth; Remotion augments rather than replaces it.
- The repo now spans Python and Node/React/Remotion runtime concerns.
- Videos must surface missing evidence honestly rather than hide it.
- The workflow should be extendable so richer assets can be added later without redesigning the contract.

## Integration Points

- vm-pilot dashboard capture — primary real visual surface the video should show.
- tmux recordings — literal terminal evidence that must remain truthful.
- `.gsd/` task/slice/milestone artifacts — likely source of requests, steps, issues, and carry-forward narrative state.
- Agent workflow / CLI entrypoint — operator trigger for generating demos.
- Remotion workspace and rendering pipeline — video assembly and render runtime.

## Open Questions

- Where the evidence bundle should live (`evidence/demo/task-tracing` or similar) — current thinking: introduce a dedicated, extendable convention in S01.
- How much existing capture infrastructure already exists in-repo versus in adjacent systems — current thinking: S01/S02 should truthfully map what is already available and consume it without over-assuming.
- Whether the first render path should output only MP4 or also intermediate preview artifacts — current thinking: prove one solid render artifact first, then widen formats later.
