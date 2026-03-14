# S02: Provider-aware CLI Validation Research

**Slice Goal:** Enable `skilllint check` to validate skills against provider-specific schema contracts using real fixtures, proving routing through new authority-aware validation stack.

## Key Dependencies
- Schema loading from S01 (`load_provider_schema`)
- Rule authority metadata infrastructure
- Existing validator entrypoints in `plugin_validator.py`

## Codebase Findings

### Validation Flow Constraints
1. Current validator applies all rules monolithically with no provider discrimination
2. CLI lacks --platform parameter for provider targeting
3. Fixture violations don't distinguish provider-specific vs shared rules

### Required Modifications
1. **CLI Argument**: Add `--platform` option using S01's `get_provider_ids()`
2. **Schema Routing**: Modify validator to load base + provider schema stack
3. **Rule Filtering**: Only apply rules matching provider constraint_scope
4. **Output Formatting**: Include authority provenance in violation messages

## Test Strategy
1. **Fixture Matrix**
   - Use existing `tests/fixtures/benchmark-plugin-violations.zip`
   - Add provider-specific violations matching Claude/Cursor/Codex schema constraints

2. **Validation Routing Checks**
   - Verify `--platform` flag loads correct schema stack
   - Confirm only provider-scoped rules fire for target platform

3. **Provenance Surfacing**
   - Validate error output shows authority URLs
   - Check `skilllint rule <id>` displays full provenance

## Risk Analysis

### Technical Risks
1. **Monolithic Validator Coupling**
   - Mitigation: Introduce RuleFilter class before schema routing

2. **CLI Output Format Stability**
   - Mitigation: Use existing violation.to_dict() pattern

3. **Schema Loading Performance**
   - Mitigation: Add schema caching decorator

## Required Artifacts
1. Provider-specific violation fixtures
2. Platform-aware validator integration test suite
3. Updated golden master output files

## Open Questions
1. Should we enforce exclusive provider selection (--platform required) or fall back to "shared" only?
2. How to handle providers with overlapping/conflicting schema constraints?

## Next Steps
1. Implement --platform CLI parameter (dependent on S01's get_provider_ids)
2. Create PlatformValidatorRouter class
3. Add constraint_scope filtering to RuleRegistry
4. Update violation formatting with authority metadata