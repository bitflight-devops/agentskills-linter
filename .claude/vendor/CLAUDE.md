# Platform Vendor Documentation

Local clones of official platform repositories for schema auditing and validation research.

## Refreshing

```bash
uv run scripts/fetch_platform_docs.py        # update all platforms
uv run scripts/fetch_platform_docs.py --dry-run  # preview without changes
```

Clones are gitignored — they are local caches only. Re-run the script to pull updates.

## Platform Documentation Index

| Platform | Vendor Directory | Key Docs for Schema / Rules / Validation |
|---|---|---|
| Claude Code | `claude_code/` | `plugins/README.md`, `plugins/plugin-dev/skills/plugin-structure/`, `CHANGELOG.md` |
| OpenAI Codex | `codex/` | `AGENTS.md`, `codex-rs/config.md`, `codex-rs/docs/`, `CHANGELOG.md` |
| Gemini CLI | `gemini_cli/` | `docs/` (full directory), `GEMINI.md`, `CONTRIBUTING.md` |
| Kilocode | `kilocode/` | `AGENTS.md`, `README.md` |
| Kimi | `kimi/` | `AGENTS.md`, `docs/`, `CHANGELOG.md` |
| Opencode | `opencode/` | `AGENTS.md`, `README.md` |
| Cursor | `cursor/` | `rules.md` (fetched from cursor.com/docs/context/rules) |
| GitHub Copilot CLI | `copilot_cli/` | `about-copilot-cli.md`, `using-copilot-cli.md` |
