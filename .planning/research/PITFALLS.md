# Pitfalls Research

**Domain:** Python linter with LSP server, MCP server, VS Code extension, pluggable platform adapters, multi-format distribution
**Researched:** 2026-03-02
**Confidence:** MEDIUM — LSP/MCP server pitfalls verified via official docs and multiple community sources; VS Code bundling and distribution pitfalls verified via official VS Code docs and GitHub issues; adapter architecture pitfalls are MEDIUM (community sources, no single authoritative reference)

---

## Critical Pitfalls

### Pitfall 1: stdout Corruption in MCP STDIO Server

**What goes wrong:**
The MCP STDIO transport reserves stdout exclusively for JSON-RPC messages. Any Python code — including the linter itself, a dependency, or a logging call — that writes to stdout corrupts the protocol stream. The client receives a parse error and drops the connection silently or with a cryptic -32000 error. This includes `print()` calls, `logging` configured to stdout, ANSI terminal escape codes, and tiktoken's first-run download messages.

**Why it happens:**
Python's `print()` defaults to stdout. The linter's existing CLI uses stdout for diagnostic output. When the MCP server wraps the linter, developers copy CLI invocation patterns without redirecting output, contaminating the JSON-RPC channel.

**How to avoid:**
- Redirect ALL logging to stderr before the MCP server starts: `logging.basicConfig(stream=sys.stderr)`
- Never call `print()` in any code path reachable from an MCP tool handler
- Capture linter output programmatically (StringIO or a custom reporter) rather than letting it write to stdout
- Suppress tiktoken's download progress output when running as MCP server (it writes to stdout on first use)
- Test with MCP Inspector before integrating into a client

**Warning signs:**
- MCP client disconnects immediately on first tool call
- Error -32000 "Server disconnected" in client logs
- Tool calls succeed in isolation but fail when linter diagnostic output is non-empty
- `python -m skilllint.mcp` produces visible text before JSON output

**Phase to address:**
MCP Server phase — enforce stderr-only logging as a hard constraint from day one; do not backport a fix after the server is integrated.

---

### Pitfall 2: pygls v2 Breaking Import Path (LSP Server)

**What goes wrong:**
pygls v2 moved `LanguageServer` from `pygls.server` to `pygls.lsp.server`. Code using the v1 import path fails with `AttributeError: module 'pygls.server' has no attribute 'LanguageServer'`. This is a silent runtime failure — the import resolves, the attribute lookup fails when the server starts.

Simultaneously, `LanguageServer.progress` changed semantics in v2: it now sends a `$/progress` notification directly, not the Progress helper. Code using `server.progress` to create work-done progress bars must switch to `server.work_done_progress`.

**Why it happens:**
pygls v2 is a major release with coordinated breaking changes. Documentation examples online mix v1 and v2 syntax. The error message names `pygls.server` which does exist (as a shim) but doesn't export `LanguageServer`, making it confusing.

**How to avoid:**
- Pin pygls to `>=2.0` explicitly in pyproject.toml and use v2 import paths from the start
- Use `from pygls.lsp.server import LanguageServer`
- Use `server.work_done_progress` not `server.progress` for progress notifications
- Read the official migration guide before writing any LSP server code: https://pygls.readthedocs.io/en/latest/pygls/howto/migrate-to-v2.html

**Warning signs:**
- `AttributeError: module 'pygls.server' has no attribute 'LanguageServer'` at server startup
- Work-done progress bars send raw `$/progress` instead of structured begin/report/end notifications
- CI passes but server fails at runtime in editor integration tests

**Phase to address:**
LSP Server phase — pin version and use v2 APIs exclusively; no v1 compatibility shim.

---

### Pitfall 3: Full Document Sync Causes Stale Diagnostics in LSP

**What goes wrong:**
Choosing `TextDocumentSyncKind.Full` instead of `TextDocumentSyncKind.Incremental` means diagnostic updates are debounced by the editor client and not sent on every keypress. The linter appears to work but shows stale errors: a fixed violation stays highlighted for seconds after the fix, and new violations don't appear until the user stops typing. This is not a bug — it is the designed behavior of Full sync — but it feels broken to users.

**Why it happens:**
Full sync is simpler to implement (no need to apply incremental text changes to an in-memory document state). Developers choose it to avoid complexity and discover the UX problem only after editor integration.

**How to avoid:**
- Use `TextDocumentSyncKind.Incremental` from the start
- Maintain in-memory document state using pygls's built-in workspace document management (`server.workspace.get_text_document(uri)`)
- Run the linter asynchronously on each incremental change notification, not just on save

**Warning signs:**
- Diagnostics update only when the file is saved, not while typing
- Highlighted errors persist for 1-3 seconds after the line is corrected
- `textDocumentSync: 1` (Full) in server capabilities JSON

**Phase to address:**
LSP Server phase — set incremental sync in the server capability declaration; treat it as a hard requirement, not an optimization.

---

### Pitfall 4: LSP Diagnostic Positions Use 0-Based Line/Character, Not 1-Based

**What goes wrong:**
The LSP protocol uses 0-based line and character offsets for `Range` positions. The existing linter reports errors with 1-based line numbers (as printed by the CLI). Mapping CLI line numbers directly to LSP `Range` objects shifts every diagnostic one line down. Users see the error underline on the wrong line.

Multi-byte characters (Unicode in YAML values, emoji in descriptions) add a second trap: LSP character offsets are UTF-16 code units by default, not byte offsets or UTF-8 code points. A YAML value containing an emoji (`🚀`) occupies 2 UTF-16 code units, so character offsets after the emoji are wrong if calculated in Python's `len()` (which uses UTF-32).

**Why it happens:**
Python's line counting is 1-based in most contexts (`enumerate(lines, 1)`). The LSP spec is 0-based. Developers forget to subtract 1 when building `Position` objects.

**How to avoid:**
- Subtract 1 from all line numbers when building LSP `Position` objects
- Use `positionEncoding` negotiation — prefer `utf-16` (LSP default) or `utf-8` (supported since LSP 3.17) and compute character offsets accordingly
- Add a test with a YAML value containing a multi-byte Unicode character and verify the underline appears on the correct character

**Warning signs:**
- All diagnostics appear one line below the actual violation
- Squiggles in the editor are offset to the right after any Unicode character in a YAML value
- Editor shows `[1, 0]` as the start of the first line, but underlines appear at `[2, 0]`

**Phase to address:**
LSP Server phase — implement a helper function that converts linter `ValidationIssue` positions to LSP `Position` objects with an explicit offset-conversion test suite.

---

### Pitfall 5: VS Code Extension Activation on Wrong File Type

**What goes wrong:**
The extension registers `onLanguage:yaml` or `onLanguage:markdown` activation events. VS Code activates the extension for every YAML or Markdown file in the workspace — including files that are not plugin/skill/agent files. The LSP server starts for irrelevant files, wastes memory, and produces false-positive diagnostics on non-linter YAML files.

Conversely, registering `workspaceContains:**/SKILL.md` activates too eagerly — the extension starts at workspace open for any workspace containing a SKILL.md anywhere, even before the user opens a relevant file.

**Why it happens:**
`onLanguage:yaml` seems natural for a YAML-heavy linter. The `workspaceContains` pattern is copy-pasted from examples without understanding its "always active" semantics.

**How to avoid:**
- Register `onLanguage:yaml` only if the extension should activate for arbitrary YAML files (it should not — skilllint only validates specific schemas)
- Use `onLanguage:markdown` restricted via document selectors that check file name patterns (`SKILL.md`, `AGENT.md`, `COMMAND.md`)
- For the LSP client, configure `documentSelector` with `{ pattern: '**/{SKILL,AGENT,COMMAND,plugin}.{md,yaml,json}' }` to restrict which files the server receives
- Never use `"*"` as an activation event

**Warning signs:**
- Extension activates when opening a plain `README.md` or `docker-compose.yml`
- LSP diagnostics appear on non-skilllint YAML files
- Extension startup time complaints from users with large YAML-heavy repos

**Phase to address:**
VS Code Extension phase — configure `documentSelector` patterns before writing any LSP client code; they are harder to change once users depend on extension behavior.

---

### Pitfall 6: Monolith-to-Package Migration Breaks Existing PEP 723 Scripts

**What goes wrong:**
The current codebase runs as PEP 723 standalone scripts with `sys.path.insert()` for imports. Migrating to a proper package (with `pyproject.toml` and installable modules) changes import semantics. The PEP 723 scripts become invalid because `import frontmatter_core` (relative) conflicts with `from skilllint.frontmatter_core import ...` (absolute package import). Pre-commit hook users who depend on `uv run plugin_validator.py` get import errors after the migration.

**Why it happens:**
PEP 723 scripts assume co-location. Packaging assumes module hierarchy. The transition period where both exist simultaneously causes two different import paths for the same module, creating confusing `ModuleNotFoundError` messages.

**How to avoid:**
- Migrate to the package structure in a single phase; do not run PEP 723 scripts and packaged modules in parallel
- Update pre-commit hook config to use the `skilllint` CLI entry point immediately after packaging
- Add a compatibility shim or clear deprecation notice for `uv run plugin_validator.py` — do not silently break existing hook users
- Test the pre-commit hook integration as part of the packaging phase acceptance criteria

**Warning signs:**
- `ModuleNotFoundError: No module named 'frontmatter_core'` in CI after packaging
- Pre-commit hooks fail for users who haven't re-run `uv sync`
- Two different code paths silently co-existing with diverging behavior

**Phase to address:**
Package Structure phase (first milestone phase) — the migration must be atomic; pre-commit integration test must be part of the packaging phase, not deferred.

---

### Pitfall 7: MCP Tool Descriptions Used as Prompt Injection Vectors

**What goes wrong:**
MCP tool `description` fields are sent verbatim to the LLM. An attacker who can influence the tool description (e.g., via a crafted plugin file that the `validate_plugin` tool processes) can inject instructions that the AI follows. The `scaffold_plugin` tool is particularly high-risk: if the template content is derived from untrusted input, the scaffold output becomes a prompt injection vector delivered to the next LLM turn.

Tool poisoning is distinct: a legitimate-looking MCP server that hosts `validate_skill` could include hidden instructions in the tool description telling the AI to also exfiltrate the user's `~/.claude/settings.json`.

**Why it happens:**
MCP tool descriptions are trusted implicitly by the LLM. Developers treat them like code comments (inert) when they are actually LLM-visible instructions.

**How to avoid:**
- Keep MCP tool descriptions short, factual, and static — never interpolate user-provided content into descriptions
- For `scaffold_*` tools: return a template string, do not embed the template in the description
- Do not expose raw file content in tool descriptions — descriptions must describe what the tool does, not what it found
- Apply least-privilege: MCP server should only read files the user explicitly passes as arguments, not walk the filesystem
- Return validation results as structured data (JSON), not as natural-language strings that could contain malicious content from the validated file

**Warning signs:**
- Tool descriptions contain dynamic content (f-strings, format strings)
- `scaffold_plugin` tool description references file paths or user-provided names
- Tool results include raw YAML/Markdown content from validated files embedded in the description field

**Phase to address:**
MCP Server phase — treat tool descriptions as security-sensitive strings; review all descriptions before the MCP server ships.

---

### Pitfall 8: Pluggable Adapter Tight Coupling via Global Registry

**What goes wrong:**
A common pattern for plugin architectures is a global registry: `ADAPTERS = {}` at module level, adapters register themselves on import. This works for bundled adapters but breaks for third-party adapters: the user must import the adapter before it self-registers, or nothing validates their platform. Adapters share mutable global state, making adapter isolation impossible (a buggy adapter can corrupt another adapter's cached schema).

**Why it happens:**
Global registries are the simplest pattern for plugin discovery. They feel clean until a test needs to mock one adapter in isolation or a user's custom adapter fails to register because the import path is wrong.

**How to avoid:**
- Use entry_points-based discovery (`importlib.metadata.entry_points(group="skilllint.adapters")`) for third-party adapters
- Keep bundled adapters as explicit imports in a known registry list, not self-registering
- Pass the adapter instance explicitly to the validator rather than looking it up from a global — enables dependency injection and testing in isolation
- Each adapter must be a pure function of its inputs; no shared mutable state between adapters

**Warning signs:**
- Adapter tests require a specific import order to pass
- Two adapter tests interfere with each other when run in the same process
- Third-party adapter registrations are not visible unless the user adds an explicit import to their config

**Phase to address:**
Platform Adapter Architecture phase — define the adapter interface and discovery mechanism before implementing any adapters.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Full LSP document sync instead of incremental | Simpler implementation, no in-memory state tracking | Stale diagnostics UX, users perceive the tool as broken | Never — use incremental from start |
| Keeping plugin_validator.py as a 5000-line monolith during LSP integration | No refactoring cost upfront | LSP server cannot import validators without dragging in CLI output code; untestable in isolation | Never for the LSP phase; must refactor first |
| Hardcoded platform schemas in validator classes instead of adapter injection | Faster initial implementation | Cannot add a new platform without modifying validator source; breaks open/closed principle | Only for initial prototype, not for packaged release |
| MCP tool that runs subprocess `uv run plugin_validator.py` | Reuses existing code immediately | Subprocess startup latency (~500ms) on every tool call; stdout contamination risk; no programmatic error handling | Never — tool must call Python API directly |
| Skipping uv sync requirement documentation | Less onboarding friction | Users get `ModuleNotFoundError` on first run after switching from PEP 723 scripts | Never — document the migration requirement explicitly |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| pygls + asyncio | Using `threading.Thread` inside a `@server.feature` handler that is async | Use `asyncio.get_event_loop().run_in_executor()` for CPU-bound linting work to avoid blocking the event loop |
| MCP Python SDK + Pydantic v2 | Pydantic v1-style serialization patterns cause `CallToolResult` to serialize to tuples instead of dicts (confirmed bug in SDK as of 2025) | Pin MCP SDK version; use `model_dump()` not `dict()` on Pydantic models returned from tool handlers |
| VS Code extension + Python process | Starting the Python LSP server process synchronously in `activate()` blocks extension activation and triggers VS Code's slow-activation warning | Start server process asynchronously; use `vscode-languageclient`'s lazy server start patterns |
| VS Code extension + VSIX packaging | VSIX file name collision — if a VSIX with the same name as a previously installed version is installed, VS Code may silently keep the old version | Always bump the version in `package.json` before generating a VSIX; automate VSIX versioning in CI |
| tiktoken + MCP/LSP server | tiktoken downloads encoding files (~1MB) on first use and may write progress to stdout | Pre-download encoding files during package installation; disable progress output via `TIKTOKEN_CACHE_DIR` env var |
| SSE vs STDIO transport for MCP | SSE transport was deprecated in the MCP spec (mid-2025); prefer Streamable HTTP for network transport | Use STDIO for local MCP servers (Claude Code integration); use Streamable HTTP if remote deployment is needed |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| tiktoken encoding re-initialization per skill | ~100ms overhead per skill; 50-skill batch takes 5+ extra seconds | Cache `tiktoken.get_encoding()` result as a module-level singleton | At ~20 skills validated in one LSP session |
| Recursive `rglob()` in ProgressiveDisclosureValidator that discards result | Visible slowdown validating skills with deeply nested `references/` | Delete the unused `rglob()` call at plugin_validator.py:956 (already identified in CONCERNS.md) | At ~1000 nested files in a single skill's references/ |
| In-memory glob expansion loading all matching files before validation starts | High memory usage on large repos with many Markdown files | Stream file discovery; process one file at a time | At ~10,000 Markdown files in workspace |
| Re-reading and re-parsing YAML for the same file across multiple validators | Multiplied I/O for batch validation; each validator opens the same file independently | Implement a per-validation-run file content cache keyed by resolved path | At ~50 skills in a single plugin |
| LSP server re-running full linter on every incremental change including whitespace | CPU spike on every keypress; editor feels sluggish | Debounce lint runs (200ms idle before triggering); skip re-lint for changes outside YAML frontmatter | Noticeable at file sizes > 2KB of frontmatter |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| MCP `scaffold_*` tool interpolates user-provided platform name or skill name into tool description | Prompt injection — AI follows embedded instructions in the crafted name | Keep descriptions static; use static templates; return scaffold result as a plain string in tool content, not in description |
| MCP server reads arbitrary filesystem paths passed as tool arguments | Path traversal — user (or AI) passes `../../etc/passwd` | Resolve and validate all paths against an allowed root (cwd or user-configured root); reject paths that escape the root |
| Subprocess `git` commands in auto_sync_manifests do not verify staging succeeded | Silent manifest drift — manifests updated but not staged; broken pre-commit workflow | Verify staging with `git diff --cached` after each stage operation; raise explicit error on mismatch |
| YAML parsed with unsafe loader anywhere in the validation pipeline | Arbitrary code execution via crafted `!!python/object` YAML tag | Verify all YAML parsing uses `yaml.safe_load()` or `ruamel.yaml` with safe mode — this is already correct per CONCERNS.md but must be enforced in all new LSP/MCP code paths |
| MCP tool returns raw file content (YAML/Markdown body) as unescaped text in tool result | Indirect prompt injection via malicious instructions in validated files | Return structured data (error codes, line numbers, field names); never return raw file content body in tool results |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| LSP diagnostics report error codes only (e.g. `SK001`) without human-readable message | User must look up every error code; frustrating for new users | Always include both code and message: `[SK001] description field is required (max 280 chars)` |
| MCP `validate_skill` tool returns a pass/fail boolean instead of structured violations | AI cannot explain what is wrong or suggest a fix | Return array of `{rule: "SK001", line: 3, field: "description", message: "...", fix_available: true}` |
| VS Code extension shows squiggle but no quick-fix action for auto-fixable violations | User cannot discover that auto-fix exists | Register `CodeActionProvider` for all violations with `fix_available: true`; show "Fix: [description]" in the context menu |
| CLI exits 0 on validation failure when used in CI | CI passes with linting errors silently; no one notices | Exit 1 on any violation; document exit codes; this is already the pattern for ruff-style tools |
| `skilllint` CLI name conflict with existing `skillint` (missing `l`) | Users type `skillint` expecting the typo alias and get command not found | Register `skillint` as an alias in `[project.scripts]`; this is already in PROJECT.md requirements but must be tested |

---

## "Looks Done But Isn't" Checklist

- [ ] **LSP server diagnostics:** Extension shows squiggles — verify they update while typing, not only on save (incremental sync test)
- [ ] **MCP server:** Tools return results in Claude Code — verify with MCP Inspector that no stdout corruption occurs when linting a file with violations
- [ ] **Pre-commit hook:** Hook runs locally — verify it also runs in a fresh `uv` environment with no pre-installed dependencies (tests the packaged entry point, not the PEP 723 script)
- [ ] **Multiple CLI aliases:** `skilllint --help` works — verify `skillint --help`, `agentlint --help`, and `pluginlint --help` all resolve to the same binary after `uv sync`
- [ ] **Platform adapter:** Claude Code adapter validates correctly — verify the adapter uses the bundled schema snapshot, not live-fetched schema (test in a network-isolated environment)
- [ ] **VS Code extension VSIX:** Extension installs from `.vsix` — verify it installs into a fresh VS Code profile with no other extensions; verify activation does not trigger on a plain `README.md`
- [ ] **MCP server security:** `validate_plugin` tool works — verify passing a file path outside the working directory is rejected with a clear error, not silently accepted

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| stdout corruption discovered after MCP server ships | HIGH — users already have broken integrations | Add `sys.stdout = sys.stderr` redirect at server entry point; release patch immediately; document in changelog |
| pygls v1/v2 import path confusion discovered mid-LSP-phase | MEDIUM — requires import audit | Run `grep -r "from pygls.server"` across codebase; replace all occurrences; re-run integration tests |
| Full sync chosen instead of incremental, discovered during beta | HIGH — users already have slow diagnostic UX; changing sync kind requires LSP client restart | Change `textDocumentSync` capability and test; ship as patch; require user to reload window |
| Monolith not refactored before LSP phase | HIGH — LSP server cannot import validators without CLI output side effects | Bite the refactoring cost; extract validators to `skilllint/validators/` package before writing LSP server code |
| MCP server prompt injection via tool description discovered post-ship | CRITICAL — security issue requiring immediate patch | Remove dynamic content from all tool descriptions; release security patch; notify users |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| stdout corruption in MCP server | MCP Server | Run `python -m skilllint.mcp validate_skill test_file.md` and verify no non-JSON output on stdout |
| pygls v2 breaking imports | LSP Server | Pin `pygls>=2.0` in pyproject.toml; import tests pass from the v2 path |
| Full sync instead of incremental | LSP Server | Server capabilities JSON shows `textDocumentSync: 2` (Incremental); diagnostics update on keypress |
| 0-based vs 1-based line positions | LSP Server | Unit test: ValidationIssue with line=1 produces LSP Position with line=0 |
| Wrong VS Code activation event scope | VS Code Extension | Extension does NOT activate when opening `docker-compose.yml`; DOES activate when opening `SKILL.md` |
| PEP 723 to package migration breaks pre-commit | Package Structure | CI job tests `uv run skilllint` (packaged) AND pre-commit hook in isolated environment |
| MCP prompt injection via tool descriptions | MCP Server | Code review: all `@mcp.tool` descriptions are static strings, no f-strings or format calls |
| Global adapter registry coupling | Platform Adapter Architecture | Adapter unit tests run in isolation without importing other adapters |
| tiktoken re-initialization per skill | Package Structure / LSP Server | Benchmark: 50-skill batch validation takes < 5s total; encoding initialized once per process |
| LSP diagnostics without human-readable messages | LSP Server | Test: diagnostic message for SK001 contains both code and description text |

---

## Sources

- pygls v2 migration guide: https://pygls.readthedocs.io/en/latest/pygls/howto/migrate-to-v2.html — HIGH confidence (official docs)
- pygls changelog: https://pygls.readthedocs.io/en/latest/changelog.html — HIGH confidence (official docs)
- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk — HIGH confidence (official repo)
- MCP build server guide: https://modelcontextprotocol.io/docs/develop/build-server — HIGH confidence (official docs)
- MCP STDIO stdout corruption (claude-flow issue): https://github.com/ruvnet/claude-flow/issues/835 — MEDIUM confidence (verified by multiple community sources)
- MCP tips/pitfalls (Nearform): https://nearform.com/digital-community/implementing-model-context-protocol-mcp-tips-tricks-and-pitfalls/ — MEDIUM confidence (verified community source)
- MCP security vulnerabilities: https://strobes.co/blog/mcp-model-context-protocol-and-its-critical-vulnerabilities/ — MEDIUM confidence (security research)
- MCP prompt injection (Simon Willison): https://simonwillison.net/2025/Apr/9/mcp-prompt-injection/ — MEDIUM confidence (credible single source)
- VS Code LSP extension guide: https://code.visualstudio.com/api/language-extensions/language-server-extension-guide — HIGH confidence (official docs)
- VS Code activation events: https://code.visualstudio.com/api/references/activation-events — HIGH confidence (official docs)
- VS Code bundling guide: https://code.visualstudio.com/api/working-with-extensions/bundling-extension — HIGH confidence (official docs)
- LSP incremental vs full sync: https://steve.dignam.xyz/2025/07/14/lsp-server-sync/ — MEDIUM confidence (technical blog, corroborated by LSP spec)
- LSP spec 3.17: https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/ — HIGH confidence (official spec)
- MCP Pydantic v2 compatibility bug: https://github.com/modelcontextprotocol/python-sdk/issues/1513 — HIGH confidence (official repo issue)
- Python packaging entry points: https://packaging.python.org/en/latest/specifications/entry-points/ — HIGH confidence (official docs)
- Existing codebase CONCERNS.md analysis — HIGH confidence (direct code audit)

---
*Pitfalls research for: Python linter (skilllint) — LSP + MCP + VS Code extension + multi-format distribution*
*Researched: 2026-03-02*
