## [LINTING] ty: invalid-argument-type in test_reporters.py

- **Source**: Pre-existing issue discovered during linting session (2026-03-11)
- **Tool**: ty (red-knot type checker)
- **Rule**: invalid-argument-type
- **Locations**:
  - `packages/skilllint/tests/test_reporters.py:37` — `code="FM001"` expects `ErrorCode`, got `Literal["FM001"]`
  - `packages/skilllint/tests/test_reporters.py:53` — `code="FM004"` expects `ErrorCode`, got `Literal["FM004"]`
- **Linter message**: `Argument is incorrect: Expected 'ErrorCode', found 'Literal["FM001"]'`
- **Root cause**: `ValidationIssue.code` is typed as `ErrorCode` (a StrEnum). Test code passes string literals instead of `ErrorCode("FM001")` enum members. ty is stricter than mypy about StrEnum literal coercion.
- **Impact**: advisory (test files only, does not affect production)
- **Recommended fix**: Use `ErrorCode("FM001")` or `ErrorCode.FM001` in test constructors.
- **Added**: 2026-03-11
