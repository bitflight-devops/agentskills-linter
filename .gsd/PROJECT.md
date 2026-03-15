# Project

## What This Is

This repository contains `skilllint`, a Python-based linter for agent skill formats, plus GSD planning artifacts for evolving the project. The codebase now also has a second active direction: building an evidence-driven demo generation system that can turn real task execution artifacts into truthful summary videos.

## Core Value

The one thing that must work is trustworthy automation evidence: the system should both validate skill/plugin content correctly and make long-running work understandable afterward through truthful, replayable artifacts.

## Current State

- M001 is complete: `skilllint` validates provider-specific skill content using versioned bundled schemas and rule authority metadata.
- The repo is still primarily Python/CLI/test oriented.
- There is not yet a Remotion workspace or a task-demo generation pipeline in the repo.
- Requirements are now tracked explicitly in `.gsd/REQUIREMENTS.md`.

## Architecture / Key Patterns

- Python package under `packages/skilllint/` with CLI-oriented validation flows and strong pytest coverage.
- GSD artifacts under `.gsd/` track milestone context, roadmap, decisions, requirements, and execution state.
- New work for M002 will cross runtime boundaries: Python-side task evidence and repo artifacts feeding a Node/React/Remotion video generation workflow.
- The new demo pipeline is constrained to real evidence and should be extendable from task-level summaries into slice- and milestone-level narratives later.

## Capability Contract

See `.gsd/REQUIREMENTS.md` for the explicit capability contract, requirement status, and coverage mapping.

## Milestone Sequence

- [x] M001: Versioned Provider Schema and Rule Authority Pipeline — Provider-aware validation with versioned bundled schemas, provenance, and packaged runtime proof.
- [ ] M002: Task-Level Demo Generation from Real Evidence — Generate truthful task summary videos from real dashboard, tmux, and task evidence.
- [ ] M003: QA Storytelling and Rollup Demos — Expand into richer QA/diagnostic narratives and slice/milestone rollups.
- [ ] M004: Evidence Hardening and Demo Productization — Deepen capture completeness, revision workflows, and outward-facing demo generation.
