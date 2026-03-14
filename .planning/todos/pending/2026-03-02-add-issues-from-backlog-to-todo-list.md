---
created: 2026-03-02T13:58:43.905Z
title: Add issues from backlog to todo list
area: planning
files:
  - docs/plans/tasks-1-plugin-linter/1-filetype-enum-extension.md
  - docs/plans/tasks-1-plugin-linter/2-error-code-constants-definition.md
  - docs/plans/tasks-1-plugin-linter/3-file-type-detection-enhancement.md
  - docs/plans/tasks-1-plugin-linter/4-hookconfig-pydantic-models.md
  - docs/plans/tasks-1-plugin-linter/5-mcpconfig-pydantic-models.md
  - docs/plans/tasks-1-plugin-linter/6-lspconfig-pydantic-models.md
  - docs/plans/tasks-1-plugin-linter/7-agentfrontmatter-enum-models.md
  - docs/plans/tasks-1-plugin-linter/8-hookconfigvalidator-implementation.md
  - docs/plans/tasks-1-plugin-linter/9-mcpconfigvalidator-implementation.md
---

## Problem

The skilllint repo has 9 open GitHub issues (migrated from Jamie-BitFlight/claude_skills)
and a 25-task implementation plan (22 tasks not-started) but no GSD-style .planning/todos
tracking them. Future sessions have no structured entry point — just raw issue numbers and
task files to hunt through.

Issues in bitflight-devops/skilllint:
- #3  plugin-validator: UX and coverage gaps (from claude_skills#131)
- #4  plugin-validator: pre-commit output is too noisy (from claude_skills#130)
- #5  Configurable Token Thresholds (from claude_skills#119)
- #6  Add PR003/PR004 test coverage (from claude_skills#103)
- #7  Remove dead code and triplicated regex (from claude_skills#102)
- #8  Extract claude-plugin-lint to standalone PyPI package (from claude_skills#93 — done)
- #9  Plugin Validation & Scaffolding MCP (from claude_skills#253)
- #10 holistic-linting: Linting Orchestration MCP (from claude_skills#256)
- #11 SAM: Replace validate-task-file.sh with Python validator (from claude_skills#106)

25-task plan: docs/plans/tasks-1-plugin-linter/ — tasks 1–11 are implementation, 15–21 tests,
22–25 docs/config/integration. Tasks 12–14 closed (already implemented).

## Solution

Create individual GSD todos for each actionable issue and unstarted task group, or process them
in /gsd:new-milestone to build a structured milestone. Issue #8 can be closed immediately
(already done by this repo existing).
