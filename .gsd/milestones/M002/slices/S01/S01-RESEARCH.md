
# S01: Validator seam map and boundary extraction — Research

## Objectives

- Map the internal boundaries of the current `plugin_validator.py` monolith.
- Identify the core responsibilities currently bundled together (scan orchestration, schema/frontmatter validation, lint-rule execution, reporting).
- Define seams for future extraction into separate modules.

## Current State Observations

- `plugin_validator.py` (5500+ lines) acts as the monolithic entrypoint for almost all validation logic.
- It contains classes for every validator type: `ProgressiveDisclosureValidator`, `InternalLinkValidator`, `NamespaceReferenceValidator`, `SymlinkTargetValidator`, `FrontmatterValidator`, `NameFormatValidator`, `DescriptionValidator`, `ComplexityValidator`, `PluginRegistrationValidator`, `PluginStructureValidator`, and `HookValidator`.
- The file also includes CLI orchestration, helper functions for YAML parsing, error handling, and registry logic.
- Rule authority and provenance logic seem coupled within this file or closely adjacent in registry modules.

## Key Risks / Unknowns

- The density of `plugin_validator.py` implies high coupling. Attempting to extract single validators might reveal hidden dependencies on CLI state, YAML helpers, or global adapter registry.
- Scan orchestration logic is currently buried in the file's primary flow, making dependency on it for CLI scan target selection ambiguous.
- The distinction between schema-backed validation and custom lint rule validation is currently obscured by the shared `Validator` protocol implementation.

## Research Findings

- Scan orchestration, schema/frontmatter validation, rule execution, and reporting are all currently fused in `plugin_validator.py`.
- The large number of validator classes (each 100-300+ lines) indicates the logic for each individual validator is likely extractable, but context-dependent helpers (like `_yaml_safe`, `_dump_yaml`, etc.) are currently global/shared.

## Plan

- Perform a dependency graph analysis of `plugin_validator.py`.
- Define module boundaries:
    - `skilllint.orchestration` (scan target discovery)
    - `skilllint.validation.schemas` (schema/frontmatter constraints)
    - `skilllint.validation.rules` (custom lint rule logic)
    - `skilllint.reporting` (issue management)
- Create a map of existing validator-to-dependency relationships to guide the actual code move in T01.

## Skills Used

- `rg`, `find`, `read` for dependency exploration.

## Forward Intelligence

- The shared utility functions (`_safe_load_yaml`, `_dump_yaml`, etc.) are used by nearly every validator. Moving these into a shared utils module is a prerequisite for extracting any validator class.
- The `Validator` protocol requires `validate`, `can_fix`, and `fix`. Any extracted module must adhere to this to avoid breaking the existing registry.

S01 researched.
