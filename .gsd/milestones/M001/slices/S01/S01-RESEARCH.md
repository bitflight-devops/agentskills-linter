# S01: Rule Classification and Provider Schema Stack - Research

## Existing Codebase Artifacts

### Relevant Modules

1. `packages/skilllint/schemas/` - Contains JSON/YAML schemas but:
   - No versioning
   - Mixed structural/format rules
   - No provider differentiation
2. `packages/skilllint/plugin_validator.py` - Monolithic validator with:
   - 1897 lines (C901 complexity 15)
   - Hardcoded limits (`limits.MAX_SKILL_NAME_LENGTH`)
   - Mixed validation layers
3. `packages/skilllint/rule_registry.py` - New rule system with:
   - AS-series rule declarations
   - Basic provenance tracking (`source: "agent-skills.io"`)
4. `scripts/fetch_platform_docs.py` - Existing doc collector needs:
   - Schema extraction capability
   - Versioned artifact storage

### Code Insights

- Current schema files get outdated quickly
- No separation between base schema and provider overlays
- Provenance exists as freeform strings rather than structured metadata
- Validation errors surface rule codes but not source authority

## Prerequisite Analysis

### Upstream Sources

1. **Claude Code Spec** (primary candidate)
   - Docs: https://docs.anthropic.com/claude-code/skills
   - Schema: No official JSON Schema, examples in prose
   - Parser Source: Closed-source, need to reverse-engineer from examples
2. **Agent Skills IO Base Schema**
   - Existing `base-schema-v1.json`
   - Missing versioning semantics
   - No extension points for providers

### Technical Prerequisites

1. Schema composition semantics
   - ✅ Available via JSON Schema `allOf`
   - Needs URI resolution strategy for overlays
2. Provenance metadata format
   - 🟡 Derivable from SPDX/license patterns
   - Example structure:
