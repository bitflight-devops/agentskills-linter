# S01: Validator seam map and boundary extraction

## Research Summary

- The validation logic for `skilllint` resides in `packages/skilllint/plugin_validator.py`.
- It currently operates as a "brownfield validator" monolith that contains multiple validator classes implementing the `Validator(Protocol)`.
- The entrypoint `plugin_validator.py` is quite large (over 5000 lines).
- Discovery and scan orchestration appear to be intertwined with individual validator logic. 
- Validation logic spans: frontmatter, structure, complexity, links, progressive disclosure, namespaces, hooks, plugin registration, names, and descriptions.

## Key Findings

- The monolith contains many concerns: validator implementations, CLI reporting (`Reporter` classes), and helpers for path discovery, YAML parsing, and issue formatting.
- `Validator(Protocol)` defines the seam for individual validators (`validate`, `can_fix`, `fix`).
- Discovery, currently implicit, needs to be made explicit (R012, R015-R017).
- Validation and reporting are mixed within the same file (e.g., `ConsoleReporter`, `CIReporter` inside `plugin_validator.py`).
- The validator classes are tightly coupled to the monolithic file structure.

## Risks and Unknowns

- High risk that internal dependencies (YAML helpers, error codes, logic helpers) are deeply shared, making decomposition non-trivial (R012).
- Scan orchestration seam is currently not clearly defined; validator classes seem to be triggered for individual files/directories independently, but orchestrator logic might be hidden in higher-level functions like `validate_with_claude` or `validate_file`.
- Official-repo scan truth (M002 Goal) depends on cleaning up the existing validator boundaries first.

## Plan

1. Map the monolithic file boundaries and identify internal seams to extract.
2. Outline the decomposition plan for Validator, Reporting, and Orchestration.
3. Establish cleaner module boundaries to support the M002 requirements (scan discovery and separator-of-concerns).
4. Extract key components (Validation, Reporting, Discovery) into dedicated modules.
