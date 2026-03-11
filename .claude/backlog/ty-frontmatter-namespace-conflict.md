## [LINTING] ty: unresolved-attribute in frontmatter_utils.py and cursor/adapter.py

- **Source**: Pre-existing issue discovered during linting session (2026-03-11)
- **Tool**: ty (red-knot type checker)
- **Rule**: unresolved-attribute
- **Locations**:
  - `packages/skilllint/adapters/cursor/adapter.py:57` — `frontmatter.load`
  - `packages/skilllint/frontmatter_utils.py:92` — `frontmatter.Post`
  - `packages/skilllint/frontmatter_utils.py:101` — `frontmatter.load`
  - `packages/skilllint/frontmatter_utils.py:104` — `frontmatter.Post`
  - `packages/skilllint/frontmatter_utils.py:113` — `frontmatter.loads`
  - `packages/skilllint/frontmatter_utils.py:116` — `frontmatter.Post`
  - `packages/skilllint/frontmatter_utils.py:125` — `frontmatter.dumps`
  - `packages/skilllint/frontmatter_utils.py:128` — `frontmatter.Post`
  - `packages/skilllint/frontmatter_utils.py:135` — `frontmatter.dump`
- **Linter message**: `Module 'frontmatter' has no member 'load'` (and similar for Post, loads, dumps, dump)
- **Root cause**: PyPI packages `frontmatter` (3.0.8) and `python-frontmatter` (1.1.0) both install into the `frontmatter` namespace. The `frontmatter` package shadows `python-frontmatter`'s exports (`load`, `Post`, `loads`, `dumps`, `dump`). This affects both runtime behavior and static analysis.
- **Impact**: blocking (ty exits nonzero)
- **Recommended fix**: Remove the `frontmatter>=3.0.8` dependency from pyproject.toml if it is not needed separately, or use explicit import paths to disambiguate.
- **Added**: 2026-03-11
