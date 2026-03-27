# AI Engineering Policy: Strict Typing and Typed Boundaries in Python

Version: 1.0
Applies to: Python 3.11+
Required libraries: [Pydantic](https://docs.pydantic.dev/), [Hypothesis](https://hypothesis.readthedocs.io/)

## 1. Purpose

This policy defines how we enforce strong typing in Python code. The goal is to keep unknown, weakly typed, or dynamically shaped data at the edges of the system and ensure that the internal codebase operates on validated, concrete types.

## 2. Core Rule

Inside the codebase, types must be explicit and enforced.

`Any`, `object`, and `cast()` are not general-purpose escape hatches. They are allowed only at typed boundaries where data enters the system without a trustworthy static shape, such as JSON, environment variables, tool output, LLM output, third-party API responses, file parsing, queues, and similar ingestion points. After crossing the boundary, the data must be validated and converted into a strongly typed internal model. **Pydantic is the required mechanism for this validation layer.** Pydantic is built around Python type hints, supports strict mode, supports validators and serializers, and includes `TypeAdapter` for validating annotated types directly.

## 3. Default Expectations

All internal modules must use precise annotations for function parameters, return values, variables, attributes, and containers.

The following are **forbidden** in normal application code:

- `Any`
- `object` used as a catch-all substitute for a real type
- `cast()` used to silence the type checker
- untyped `dict` or `list` values flowing through domain logic
- returning raw external payloads from internal service functions

The following are **required**:

- concrete domain models
- explicit unions where multiple shapes are valid
- `TypedDict`, dataclasses, or Pydantic models when structure matters
- validation at ingress, not downstream
- property-based tests for validators and adapters using Hypothesis

## 4. Typed Boundary Rule

A typed boundary is any function or module that accepts raw, external, or otherwise untrusted input.

Boundary code may temporarily use `Any`, `object`, or `cast()` only if **all** of the following are true:

1. The value originates outside the typed core.
2. The boundary function immediately validates the input.
3. The boundary function returns a concrete typed object.
4. No raw untyped value escapes the boundary.
5. Any use of `cast()` is justified by a prior runtime check, schema validation, or library guarantee.

`cast()` is not validation. It may only be used after a proof step. Python 3.11 added `typing.assert_type()` and `typing.reveal_type()` to help verify what a type checker infers during development, which makes it easier to prove or inspect narrowings instead of blindly forcing them.

## 5. Golden Path

Every new ingestion path must follow this sequence:

1. Accept raw input.
2. Validate and normalize raw input at the boundary.
3. Convert it into a **Pydantic model** or another explicitly typed internal object.
4. Return only the typed object.
5. Use only typed values in all downstream code.

In practice, this means:

- external `dict[str, Any]` in
- validated Pydantic model out
- typed domain code after that point

Pydantic supports this model directly through `BaseModel`, validators, strict mode, and `TypeAdapter` for validating annotated types without requiring a model class.

## 6. Required File and Naming Conventions

Boundary code must be isolated in dedicated files. Approved module names include:

- `*_validators.py`
- `*_adapters.py`
- `*_boundary.py`
- `*_ingest.py`
- `*_parsers.py`

In **this repository**, boundary modules also live under `packages/skilllint/boundary/` (same rules apply).

Approved function prefixes include:

- `parse_`
- `validate_`
- `decode_`
- `coerce_`
- `*_from_raw`

Examples:

- `parse_user_payload() -> UserPayload`
- `validate_order_event() -> OrderEvent`
- `decode_agent_response() -> AgentResponse`
- `tool_result_from_raw() -> ToolResult`

**Rule:** if a function accepts unknown shape, its name must make that fact obvious.

## 7. Linting and Repository Enforcement

Only approved boundary modules may contain narrow lint exclusions for `Any`.

Everywhere else:

- `Any` should fail linting
- unchecked `cast()` should fail review
- untyped boundary leakage should fail review
- domain modules should not import raw external payload types

**Recommended enforcement pattern:**

- boundary modules: narrowly scoped exceptions
- all other modules: strict no-`Any` policy

This is a policy boundary, not a suggestion.

### skilllint repository

CI (`.github/workflows/test.yml`) and `.pre-commit-config.yaml` run Astral **`ty check`** on `packages/` (configuration: `pyproject.toml` → `[tool.ty.environment]` / `[tool.ty.src]`). Use `uv run ty check packages/` locally. **`[tool.mypy]`** (effectively excluded) and **`[tool.basedpyright]`** (`typeCheckingMode = "off"`) stay that way on purpose: **ty** is the single type gate; mypy and Pyright/basedpyright overlap it and would create conflicting diagnostics and repeated configuration work if left active.

## 8. Pydantic Addendum

When Pydantic is available, improve the boundary process as follows:

### 8.1 Use Pydantic models as the default ingress contract

External payloads should be converted into `BaseModel` instances or validated typed structures immediately. Pydantic is explicitly designed for validation driven by type annotations.

### 8.2 Prefer strict validation at boundaries

Use Pydantic strict mode for boundary validation where silent coercion would hide producer errors. Pydantic documents both strict mode and lax mode, with strict mode preventing conversion-based acceptance.

### 8.3 Use `TypeAdapter` for typed values that do not need a full model

For `list[Foo]`, `dict[str, Bar]`, unions, and other annotated types, prefer `TypeAdapter` over hand-written validation logic. Pydantic exposes `TypeAdapter` specifically for validating annotated types directly.

### 8.4 Centralize custom validation in validators, not ad hoc checks

If special coercion or normalization is required, do it in Pydantic validators or serializers so validation behavior stays declarative and testable. Pydantic documents validators and serializers as core customization mechanisms.

### 8.5 Do not pass raw dicts past the model layer

Once a payload has been validated, pass the model or a typed domain object, not the original raw dictionary.

## 9. Hypothesis Addendum

When Hypothesis is available, improve the process as follows:

### 9.1 Property-test every boundary validator

Hypothesis is a property-based testing library for Python and is designed to generate a wide range of inputs, including edge cases you may not anticipate. Use it to test that validators either accept valid shapes or fail cleanly on invalid ones.

### 9.2 Generate data from types whenever possible

Hypothesis provides `from_type()` to infer a strategy from a Python type. Use this to keep tests aligned with declared types instead of manually duplicating shape assumptions in test code.

### 9.3 Type your strategies and composite generators

Hypothesis documents typed strategies using `SearchStrategy[T]` and shows how to annotate custom composite strategies using the generated value type. This lets test helpers participate in the same typing discipline as production code.

### 9.4 Use Ghostwriter to bootstrap boundary tests

Hypothesis Ghostwriter can generate starter tests. It should be used as a starting point for human-authored tests, especially when adding new boundary adapters.

## 10. Python-Version Addendum

### 10.1 When using Python 3.11, improve this process by doing these three things

1. Use `Self` for fluent APIs, alternate constructors, and methods that return the current class. This makes typed wrappers and typed builders cleaner and less error-prone. Python 3.11 added `Self` for exactly this use case.
2. Use `typing.assert_type()` in tests or type-check-only assertions to lock expected inferred types at critical boundaries. Python 3.11 added `assert_type()` for confirming a type checker's inferred type.
3. Use `typing.reveal_type()` during development when refactoring validators or removing `cast()` calls. Python 3.11 added `reveal_type()` to inspect inferred types.

### 10.2 When using Python 3.12, improve this process by doing these three things

1. Use PEP 695 generic parameter syntax for new generic validators, adapters, and helper functions. Python 3.12 introduced a more compact syntax for generic classes and functions.
2. Use the `type` statement for explicit type aliases instead of informal alias patterns. Python 3.12 added the `type` statement and `TypeAliasType` support for clearer alias declarations.
3. Standardize shared alias definitions for raw-vs-validated shapes. The clearer alias and generic syntax in 3.12 reduces ambiguity in boundary helper APIs and makes internal typed contracts easier to read and review.

### 10.3 When using Python 3.13, improve this process by doing these three things

1. Use `TypeIs` for custom narrowing helpers where you previously relied on weaker boolean checks or overused `cast()`. Python 3.13 added `typing.TypeIs` as a more intuitive narrowing mechanism than `TypeGuard` in many cases.
2. Use `ReadOnly` in `TypedDict` definitions for payload fields that should never be mutated after validation. Python 3.13 added `typing.ReadOnly` for `TypedDict` items.
3. Replace ad hoc mutation of structured payload dictionaries with immutable or read-only typed representations where possible. The new `ReadOnly` support gives static checkers a direct way to enforce post-validation invariants.

### 10.4 When using Python 3.14, improve this process by doing these three things

1. Stop reading `__annotations__` directly in framework, validator, or metaprogramming code. Python 3.14 changed annotation evaluation semantics and recommends using `annotationlib` APIs instead.
2. Use `annotationlib.get_annotations()` when you need runtime access to annotations in cross-version-aware infrastructure code. Python 3.14 introduced `annotationlib` specifically to inspect deferred annotations safely.
3. Audit any library glue, decorators, or code generation that depends on eager annotation evaluation. Python 3.14 adopted deferred evaluation of annotations under PEP 649 and PEP 749, so annotation-reading code needs to be explicit and future-safe.

## 11. Allowed and Disallowed Examples

### Allowed

- `Any` inside `llm_boundary.py` while receiving unknown tool output, followed immediately by Pydantic validation into `AgentResponse`
- `object` in a parser that accepts a truly unknown external value and narrows it through checks
- `cast()` after a runtime discriminator check or validated schema step
- `TypeAdapter(list[OrderEvent]).validate_python(raw)` at ingress

### Disallowed

- `cast(User, payload)` without validation
- `dict[str, Any]` passed through service layers
- `Any` in domain models, business logic, repositories, or utilities
- returning raw JSON from adapter functions
- using `object` to avoid defining a union or protocol

## 12. Review Checklist

Before merging code, reviewers should ask:

1. Is unknown data isolated to an explicit boundary?
2. Does the boundary validate immediately?
3. Does it return a concrete typed object?
4. Does any raw untyped value leak into internal code?
5. Is every `cast()` justified by a prior proof step?
6. Could Pydantic `BaseModel` or `TypeAdapter` replace custom parsing?
7. Does Hypothesis cover malformed, partial, and edge-case inputs?
8. Are Python-version-specific typing improvements being used where available?

## 13. Non-Negotiable Standard

Unknown data may enter the system only through explicit boundary adapters. Boundary adapters may use limited untyped constructs only to ingest and validate raw input. After validation, the typed core must remain fully typed. `Any`, `object`, and unchecked `cast()` are exceptions for ingress only, never a substitute for modeling.
