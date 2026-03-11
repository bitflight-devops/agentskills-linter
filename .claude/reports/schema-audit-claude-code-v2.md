# Claude Code Schema Audit v2

**Audit date**: 2026-03-10
**Schema under audit**: `packages/skilllint/schemas/claude_code/v1.json`

## Evidence sources

- `plugins/plugin-dev/skills/plugin-structure/references/manifest-reference.md` — authoritative plugin.json field reference
- `plugins/plugin-dev/skills/plugin-structure/SKILL.md` — plugin structure and SKILL.md format docs
- `plugins/plugin-dev/skills/plugin-structure/examples/minimal-plugin.md` — minimal plugin example
- `plugins/plugin-dev/skills/plugin-structure/examples/advanced-plugin.md` — advanced plugin example
- `plugins/plugin-dev/skills/agent-development/SKILL.md` — authoritative agent frontmatter reference
- `plugins/plugin-dev/skills/command-development/SKILL.md` — authoritative command frontmatter reference
- Real `plugin.json` files: `code-review`, `feature-dev`, `commit-commands`
- Real agent `.md` files: `feature-dev/agents/code-reviewer.md`, `pr-review-toolkit/agents/comment-analyzer.md`, `plugin-dev/agents/plugin-validator.md`, `feature-dev/agents/code-explorer.md`
- Real command `.md` files: `commit-commands/commands/commit.md`, `commit-commands/commands/commit-push-pr.md`, `code-review/commands/code-review.md`, `feature-dev/commands/feature-dev.md`, `ralph-wiggum/commands/ralph-loop.md`
- Real `SKILL.md` files: `claude-opus-4-5-migration`, `frontend-design`, `hookify/writing-rules`

---

## plugin section

Schema `required_fields`: `["name", "version", "description"]`
Schema `optional_fields`: `["author", "skills", "agents", "commands", "hooks"]`

### Required fields

**name** — DOCUMENTED REQUIRED
> manifest-reference.md: "#### name (required)" — "The unique identifier for the plugin."
> Confirmed: all 3 real plugin.json files have `name`.

**version** — WRONG-REQUIRED (has default, not required)
> manifest-reference.md: "#### version ... **Default**: `"0.1.0"` if not specified"
> minimal-plugin.md: `{"name": "hello-world"}` — explicitly labelled "Only the required `name` field". No `version`.
> Fix: move `version` from `required_fields` to `optional_fields`.

**description** — WRONG-REQUIRED (recommended, not required)
> manifest-reference.md: description appears under "### Recommended Metadata", not under required fields.
> plugin-structure SKILL.md required block: `{"name": "plugin-name"}` — description absent.
> minimal-plugin.md: `{"name": "hello-world"}` — no description.
> Fix: move `description` from `required_fields` to `optional_fields`.

### Optional fields

**author** — DOCUMENTED
> manifest-reference.md: "#### author ... **Type**: Object"
> Correctly in `optional_fields`.

**skills** — PHANTOM (no such plugin.json field)
> manifest-reference.md component path fields: `commands`, `agents`, `hooks`, `mcpServers`. No `skills`.
> plugin-structure SKILL.md "### Component Path Configuration": lists `commands`, `agents`, `hooks`, `mcpServers`. No `skills`.
> Zero real plugin.json files contain a `skills` key. Skills are auto-discovered from the `skills/` directory.
> Fix: remove `skills` from `optional_fields`.

**agents** — DOCUMENTED
> manifest-reference.md: "#### agents ... **Type**: String or Array of strings ... **Default**: `["./agents"]`"
> Correctly in `optional_fields`.

**commands** — DOCUMENTED
> manifest-reference.md: "#### commands ... **Type**: String or Array of strings ... **Default**: `["./commands"]`"
> Correctly in `optional_fields`.

**hooks** — DOCUMENTED
> manifest-reference.md: "#### hooks ... **Type**: String (path to JSON file) or Object (inline configuration)"
> Correctly in `optional_fields`.

### Missing documented optional fields

**mcpServers** — DOCUMENTED, MISSING FROM SCHEMA
> manifest-reference.md: "#### mcpServers ... **Type**: String (path to JSON file) or Object ... **Default**: `./.mcp.json`"
> advanced-plugin.md: `"mcpServers": "./.mcp.json"` — confirmed in example.
> Fix: add `mcpServers` to `optional_fields`.

**homepage** — DOCUMENTED, MISSING FROM SCHEMA
> manifest-reference.md: "#### homepage ... **Type**: String (URL)"
> advanced-plugin.md: `"homepage": "https://docs.company.com/plugins/devops"` — confirmed in example.
> Fix: add `homepage` to `optional_fields`.

**repository** — DOCUMENTED, MISSING FROM SCHEMA
> manifest-reference.md: "#### repository ... **Type**: String (URL) or Object"
> advanced-plugin.md: `"repository": {"type": "git", "url": "..."}` — confirmed in example.
> Fix: add `repository` to `optional_fields`.

**license** — DOCUMENTED, MISSING FROM SCHEMA
> manifest-reference.md: "#### license ... **Type**: String ... **Format**: SPDX identifier"
> advanced-plugin.md: `"license": "Apache-2.0"` — confirmed in example.
> Fix: add `license` to `optional_fields`.

**keywords** — DOCUMENTED, MISSING FROM SCHEMA
> manifest-reference.md: "#### keywords ... **Type**: Array of strings"
> advanced-plugin.md: `"keywords": ["devops", "ci-cd", ...]` — confirmed in example.
> Fix: add `keywords` to `optional_fields`.

---

## skill section

Schema `required_fields`: `["name", "version", "description"]`
Schema `optional_fields`: `["author", "triggers", "tools", "permissions", "dependencies"]`

### Required fields

**name** — DOCUMENTED REQUIRED
> plugin-structure SKILL.md: "SKILL.md format: `name: Skill Name`"
> All 3 real SKILL.md files have `name`. Correctly required.

**version** — WRONG-REQUIRED (optional in practice)
> plugin-structure SKILL.md does not state version is required.
> `frontend-design/SKILL.md`: no `version` field — only `name`, `description`, `license`.
> `claude-opus-4-5-migration/SKILL.md`: no `version` field — only `name`, `description`.
> `hookify/writing-rules/SKILL.md`: has `version: 0.1.0`.
> Version is present in 1 of 3 sampled real SKILL.md files. Not consistently required.
> Fix: move `version` from `required_fields` to `optional_fields`.

**description** — DOCUMENTED REQUIRED
> plugin-structure SKILL.md: "SKILL.md format: `description: When to use this skill`"
> All 3 real SKILL.md files have `description`. Correctly required.

### Optional fields

**author** — PHANTOM
> Neither plugin-structure SKILL.md nor any real SKILL.md files have an `author` frontmatter key.
> `author` is a `plugin.json` metadata field only.
> Fix: remove `author` from skill `optional_fields`.

**triggers** — PHANTOM
> No SKILL.md frontmatter reference in any vendor doc. Absent from all real SKILL.md files.
> Fix: remove `triggers` from skill `optional_fields`.

**tools** — PHANTOM for skills
> `tools` is an agent frontmatter field (agent-development SKILL.md: "### tools (optional)"). Not a SKILL.md field.
> Zero real SKILL.md files have a `tools` frontmatter key.
> Fix: remove `tools` from skill `optional_fields`.

**permissions** — PHANTOM
> No SKILL.md frontmatter reference in any vendor doc. Absent from all real SKILL.md files.
> Fix: remove `permissions` from skill `optional_fields`.

**dependencies** — PHANTOM
> No SKILL.md frontmatter reference in any vendor doc. Absent from all real SKILL.md files.
> Fix: remove `dependencies` from skill `optional_fields`.

### Missing documented optional fields

**license** — OBSERVED IN REAL FILE, MISSING FROM SCHEMA
> `frontend-design/SKILL.md` frontmatter: `license: Complete terms in LICENSE.txt` — official Anthropic-authored plugin.
> Fix: add `license` to skill `optional_fields`.

---

## agent section

Schema `required_fields`: `["name", "version", "description"]`
Schema `optional_fields`: `["author", "tools", "permissions", "model"]`

### Required fields

**name** — DOCUMENTED REQUIRED
> agent-development SKILL.md: "### name (required) — Agent identifier used for namespacing and invocation."
> All real agent files have `name`. Correctly required.

**version** — PHANTOM (no agent has version in frontmatter)
> agent-development SKILL.md format block does not include `version`.
> Zero real agent `.md` files have a `version` frontmatter key.
> Fix: remove `version` from agent `required_fields`.

**description** — DOCUMENTED REQUIRED
> agent-development SKILL.md: "### description (required) — Defines when Claude should trigger this agent."
> All real agent files have `description`. Correctly required.

### Optional fields

**author** — PHANTOM
> agent-development SKILL.md field list: `name`, `description`, `model`, `color`, `tools`. No `author`.
> Zero real agent `.md` files have an `author` frontmatter key.
> Fix: remove `author` from agent `optional_fields`.

**tools** — DOCUMENTED OPTIONAL
> agent-development SKILL.md: "### tools (optional) — Restrict agent to specific tools."
> `feature-dev/agents/code-reviewer.md`: `tools: Glob, Grep, LS, Read, ...` — confirmed.
> `plugin-dev/agents/plugin-validator.md`: `tools: ["Read", "Grep", "Glob", "Bash"]` — confirmed.
> Correctly in `optional_fields`.

**permissions** — PHANTOM
> Not in agent-development SKILL.md field list. Zero real agent `.md` files have `permissions`.
> Fix: remove `permissions` from agent `optional_fields`.

**model** — WRONG-OPTIONAL (documented as required)
> agent-development SKILL.md: "### model (required) — Which model the agent should use."
> `code-reviewer.md`: `model: sonnet`; `comment-analyzer.md`: `model: inherit`; `code-explorer.md`: `model: sonnet` — confirmed in all samples.
> Fix: move `model` from `optional_fields` to `required_fields`.

### Missing documented required fields

**color** — DOCUMENTED REQUIRED, MISSING FROM SCHEMA
> agent-development SKILL.md: "### color (required) — Visual identifier for agent in UI. **Options:** `blue`, `cyan`, `green`, `yellow`, `magenta`, `red`"
> `code-reviewer.md`: `color: red`; `comment-analyzer.md`: `color: green`; `code-explorer.md`: `color: yellow`; `plugin-validator.md`: `color: yellow` — confirmed in all samples.
> Fix: add `color` to agent `required_fields`.

---

## command section

Schema `required_fields`: `["name", "version"]`
Schema `optional_fields`: `["description", "author"]`

### Required fields

**name** — PHANTOM (derived from filename, not a frontmatter field)
> command-development SKILL.md frontmatter fields: `description`, `allowed-tools`, `model`, `argument-hint`, `disable-model-invocation`. No `name`.
> `commit.md`, `commit-push-pr.md`, `code-review.md`, `feature-dev.md`, `ralph-loop.md` — zero real command files have `name` in frontmatter.
> Fix: remove `name` from command `required_fields`.

**version** — PHANTOM
> command-development SKILL.md has no `version` entry.
> Zero real command `.md` files have `version`.
> Fix: remove `version` from command `required_fields`.

### Optional fields

**description** — DOCUMENTED OPTIONAL
> command-development SKILL.md: "### description ... **Default:** First line of command prompt"
> Present in all 5 real command files sampled. Correctly in `optional_fields`.

**author** — PHANTOM
> command-development SKILL.md field list has no `author` entry.
> Zero real command `.md` files have `author`.
> Fix: remove `author` from command `optional_fields`.

### Missing documented optional fields

**allowed-tools** — DOCUMENTED, MISSING FROM SCHEMA
> command-development SKILL.md: "### allowed-tools ... **Type:** String or Array"
> `commit.md`: `allowed-tools: Bash(git add:*), ...`; `ralph-loop.md`: `allowed-tools: ["Bash(...)"]` — confirmed.
> Fix: add `allowed-tools` to command `optional_fields`.

**model** — DOCUMENTED, MISSING FROM SCHEMA
> command-development SKILL.md: "### model ... **Type:** String (sonnet, opus, haiku)"
> Fix: add `model` to command `optional_fields`.

**argument-hint** — DOCUMENTED, MISSING FROM SCHEMA
> command-development SKILL.md: "### argument-hint ... **Type:** String"
> `feature-dev.md`: `argument-hint: Optional feature description`; `ralph-loop.md`: `argument-hint: "PROMPT [--max-iterations N]..."` — confirmed.
> Fix: add `argument-hint` to command `optional_fields`.

**disable-model-invocation** — DOCUMENTED, MISSING FROM SCHEMA
> command-development SKILL.md: "### disable-model-invocation ... **Type:** Boolean"
> Fix: add `disable-model-invocation` to command `optional_fields`.

---

## Recommended changes

**plugin:**
- Move `version` required → optional (has documented default `"0.1.0"`)
- Move `description` required → optional (under "Recommended Metadata" in docs; absent from minimal example)
- Remove `skills` from optional (phantom; not a plugin.json field)
- Add `mcpServers`, `homepage`, `repository`, `license`, `keywords` to optional (all documented in manifest-reference.md)

**skill:**
- Move `version` required → optional (absent from 2/3 real SKILL.md files)
- Remove `author`, `triggers`, `tools`, `permissions`, `dependencies` from optional (all phantom)
- Add `license` to optional (observed in `frontend-design/SKILL.md`)

**agent:**
- Remove `version` from required (phantom; not in agent-development SKILL.md field list)
- Move `model` optional → required (agent-development SKILL.md: "### model (required)")
- Add `color` to required (agent-development SKILL.md: "### color (required)"; confirmed in all real agent files)
- Remove `author`, `permissions` from optional (both phantom)

**command:**
- Remove `name`, `version` from required (both phantom as frontmatter fields)
- Remove `author` from optional (phantom)
- Add `allowed-tools`, `model`, `argument-hint`, `disable-model-invocation` to optional (all documented)
