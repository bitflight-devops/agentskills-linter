# Project

## What This Is

This repository contains `skilllint`, a Python-based linter for agent skill formats, plus GSD planning artifacts for evolving the project. It validates skill and plugin content across provider ecosystems, loads bundled versioned provider schemas, and reports rule authority/provenance so maintainers can trace why a constraint exists.

## Core Value

The one thing that must work is trustworthy detection: `skilllint` should discover the right files, apply the right schema and rule boundaries, and report real issues with traceable authority — without hallucinated constraints or ecosystem-incompatible hard failures.

## Current State

- M001 is complete: `skilllint` validates provider-specific skill content using versioned bundled schemas and rule authority metadata.
- The repo is primarily Python/CLI/test oriented, with the main package under `packages/skilllint/`.
- Brownfield validator logic still retains too much responsibility in `plugin_validator.py`, especially around scan orchestration, rule layering, and discovery behavior.
- Real-world scans against external Claude ecosystem repos currently surface a mix of likely real issues, likely compatibility gaps, and possibly hallucinated or legacy constraints.
- Requirements are tracked explicitly in `.gsd/REQUIREMENTS.md`.

## Architecture / Key Patterns

- Python package under `packages/skilllint/` with CLI-oriented validation flows and strong pytest coverage.
- Provider adapters under `packages/skilllint/adapters/` expose platform-specific path patterns, applicable rules, constraint scopes, and schema access.
- Bundled provider schemas live under `packages/skilllint/schemas/<provider>/vN.json` and load through packaged-resource paths.
- Rule authority and provenance are surfaced through `packages/skilllint/rule_registry.py`.
- GSD artifacts under `.gsd/` track milestone context, roadmap, decisions, requirements, and execution state.

## Capability Contract

See `.gsd/REQUIREMENTS.md` for the explicit capability contract, requirement status, and coverage mapping.

## Milestone Sequence

- [x] M001: Versioned Provider Schema and Rule Authority Pipeline — Provider-aware validation with versioned bundled schemas, provenance, and packaged runtime proof.
- [ ] M002: Validator Decomposition and Scan-Truth Hardening — Split remaining validator responsibilities, correct scan/discovery behavior, and prove detection truth against real external repos.
