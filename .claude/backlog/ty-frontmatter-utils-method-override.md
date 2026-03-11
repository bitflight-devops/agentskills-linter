## [LINTING] ty: invalid-method-override in frontmatter_utils.py

- **Source**: Pre-existing issue discovered during linting session (2026-03-11)
- **Tool**: ty (red-knot type checker)
- **Rule**: invalid-method-override
- **Locations**:
  - `packages/skilllint/frontmatter_utils.py:62` — `RuamelYAMLHandler.load` override
  - `packages/skilllint/frontmatter_utils.py:74` — `RuamelYAMLHandler.export` override
- **Linter message**: `Invalid override of method 'load' / 'export' — Definition is incompatible with BaseHandler.load / YAMLHandler.export`
- **Root cause**: `RuamelYAMLHandler.load` accepts `**kwargs: Unpack[_YAMLHandlerKwargs]` but `BaseHandler.load` only accepts `(self, fm: str) -> dict[str, Any]`. Similarly for `export`. This violates the Liskov Substitution Principle per ty's analysis.
- **Impact**: blocking (ty exits nonzero)
- **Recommended fix**: Align method signatures with the base class, or use `@override` with compatible signatures.
- **Added**: 2026-03-11
