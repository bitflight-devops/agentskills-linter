#!/usr/bin/env node
'use strict';

/**
 * SessionStart hook — check for vendor documentation drift.
 * Runs `uv run scripts/fetch_platform_docs.py` and injects context
 * into the session when drift is detected (exit code 2 from the script).
 * Scope: project (.claude/settings.json)
 * Fires on: SessionStart (all sources)
 *
 * Test:
 *   echo '{"hook_event_name":"SessionStart","source":"startup"}' | node .claude/hooks/vendor-drift-check.cjs
 */

const { execFileSync } = require('node:child_process');
const path = require('node:path');

let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => {
  input += chunk;
});
process.stdin.on('end', () => {
  // Parse stdin — exit cleanly on bad input (hook must never crash)
  let _data = {};
  try {
    _data = JSON.parse(input);
  } catch {
    process.stdout.write(JSON.stringify({}));
    process.exit(0);
  }

  runDriftCheck();
});

function runDriftCheck() {
  const projectDir = process.env.CLAUDE_PROJECT_DIR || process.cwd();
  const scriptPath = path.join(projectDir, 'scripts', 'fetch_platform_docs.py');

  // Verify uv is available — portable check that works without `which`
  try {
    execFileSync('uv', ['--version'], {
      stdio: ['ignore', 'pipe', 'ignore'],
      timeout: 3000,
    });
  } catch (_) {
    process.stderr.write('vendor-drift-check: warning: uv not found, skipping drift check\n');
    process.stdout.write(JSON.stringify({}));
    process.exit(0);
  }

  // Run the drift-check script synchronously; capture stdout, suppress stderr
  let exitCode = 0;
  try {
    execFileSync('uv', ['run', scriptPath], {
      stdio: ['ignore', 'pipe', 'ignore'],
      timeout: 60000,
      cwd: projectDir,
    });
    // exit code 0 — no drift
  } catch (err) {
    if (err.code === 'ETIMEDOUT') {
      process.stderr.write('vendor-drift-check: timed out after 60s\n');
      process.stdout.write(JSON.stringify({}));
      process.exit(0);
    }
    exitCode = typeof err.status === 'number' ? err.status : 1;
  }

  if (exitCode === 2) {
    // Drift detected — inject context for the session
    const output = {
      hookSpecificOutput: {
        hookEventName: 'SessionStart',
        additionalContext:
          'Vendor documentation has changed. `.claude/vendor/.drift-pending.json` lists affected providers with diffs and changelogs. Run the schema-drift-auditor agent to assess whether schema fields are affected.',
      },
    };
    process.stdout.write(JSON.stringify(output));
    process.exit(0);
  }

  if (exitCode !== 0) {
    // Non-zero, non-2: log to stderr (shown in verbose mode), stay silent to Claude
    process.stderr.write(
      `vendor-drift-check: fetch_platform_docs.py exited with code ${exitCode}\n`,
    );
  }

  process.stdout.write(JSON.stringify({}));
  process.exit(0);
}
