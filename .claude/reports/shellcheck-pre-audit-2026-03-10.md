# ShellCheck Pre-Audit Report
**Script:** `scripts/fetch-platform-docs.sh` (defined in Task 2.1 of `.planning/todos/pending/2026-03-10-platform-doc-fetch.md`)
**Audit date:** 2026-03-10
**Auditor:** Manual static analysis (ShellCheck not executed; issues identified by rule reference)
**Target:** Bash 5.1+, `set -euo pipefail`

---

## Summary

**Total issues found: 12**

| Severity | Count |
|----------|-------|
| High     | 4     |
| Medium   | 5     |
| Low      | 3     |

---

## Issues

### ISSUE-01 — `local` used in `main()` (top-level function)
**Severity:** High
**Rule:** SC2168
**Location:** `main()` function — the three `local name=...` / `local url=...` declarations inside the three `for entry in` loops within `main()`

`local` is only valid inside a function. `main()` is a function here, so `local` itself is syntactically legal, but the issue is subtler: **`local` silently swallows the exit code** of any command substitution on the right-hand side. All three loop bodies in `main()` use:

```bash
local name="${entry%%|*}"
local url="${entry##*|}"
```

These are pure parameter expansions (no subshell), so exit code masking does not apply here. However, the pattern is still flagged as a style issue because `local` inside loop bodies suggests incorrect scoping intent (the variable is re-declared on every iteration). More critically, the same pattern appears in `write_manifest()` (see ISSUE-02 and ISSUE-03), where it does mask failures.

**Fix:** Declare loop variables once before the loop with `local`, then assign inside the loop without `local`:

```bash
# Before (inside loop body):
for entry in "${GIT_PLATFORMS[@]}"; do
    local name="${entry%%|*}"
    local url="${entry##*|}"
    clone_or_update_repo "${name}" "${url}"
done

# After:
local name url
for entry in "${GIT_PLATFORMS[@]}"; do
    name="${entry%%|*}"
    url="${entry##*|}"
    clone_or_update_repo "${name}" "${url}"
done
```

This applies to all three `for entry in` loops in `main()`.

---

### ISSUE-02 — `local var=$(...)` masks command substitution exit code
**Severity:** High
**Rule:** SC2155
**Location:** `clone_or_update_repo()` — line:
```bash
default_branch="$(git -C "${dest}" symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's|refs/remotes/origin/||' || echo "main")"
```
This specific line is fine because `default_branch` is already declared `local` separately. But in `write_manifest()`, the following pattern appears twice (once for git platforms, once for doc-site platforms):

```bash
local sha="$(git -C "${vendor_path}" rev-parse HEAD 2>/dev/null || echo "unknown")"
```
and:
```bash
local files_json="$(cd "${snapshot_path}" && find . -type f ... | sort | sed ... | awk ...)"
```

When `local` and command substitution are combined in a single statement, Bash assigns the exit code of `local` (always 0) to `$?`, not the exit code of the command substitution. Under `set -e`, a failing subshell command would normally abort the script, but `local var=$(failing_cmd)` suppresses this — the failure is silently hidden.

**Fix:** Declare and assign separately:

```bash
# Before:
local sha="$(git -C "${vendor_path}" rev-parse HEAD 2>/dev/null || echo "unknown")"

# After:
local sha
sha="$(git -C "${vendor_path}" rev-parse HEAD 2>/dev/null || echo "unknown")"
```

Apply to every `local varname="$(..."` pattern in `write_manifest()`, `clone_or_update_repo()`, and anywhere else in the script.

**All affected locations in the script:**
- `clone_or_update_repo()`: `local default_branch` — already split correctly, no issue here
- `write_manifest()` git-platforms loop: `local sha="$(...)"`  — **SC2155 violation**
- `write_manifest()` git-platforms loop: `local files_json="$(cd ... | awk ...)"` — **SC2155 violation**
- `write_manifest()` doc-site loop: `local files_json="$(cd ... | awk ...)"` — **SC2155 violation**
- Top-level (not in a function): `SNAPSHOT_DATE="$(date -u +%Y-%m-%d)"` — no `local`, fine
- Top-level: `timestamp="$(date -u ...)"` in `write_manifest()` — `local timestamp` declared on prior line, `timestamp="$(..."` on its own line — **correctly split**, no issue

---

### ISSUE-03 — Unquoted `$1` in function argument check
**Severity:** Medium
**Rule:** SC2086
**Location:** Top-level argument parsing:

```bash
if [[ "${1:-}" == "--dry-run" ]]; then
```

This is actually correctly quoted with `${1:-}`. No issue here. Moving on — this was a false lead on inspection.

---

### ISSUE-03 — `git reset --hard` with `--quiet` flag order (flag after operand)
**Severity:** High
**Rule:** Not a ShellCheck rule — correctness bug
**Location:** `clone_or_update_repo()`:

```bash
git -C "${dest}" reset --hard "origin/${default_branch}" --quiet
```

`git reset` does not accept `--quiet` after the commit-ish argument. The `--quiet` / `-q` flag for `git reset --hard` must appear before the commit reference. Placing it after `"origin/${default_branch}"` will cause git to interpret `--quiet` as an additional pathspec or fail with an error on some git versions.

**Fix:**

```bash
# Before:
git -C "${dest}" reset --hard "origin/${default_branch}" --quiet

# After:
git -C "${dest}" reset --hard --quiet "origin/${default_branch}"
```

---

### ISSUE-04 — `find . -not -name '.'` is a no-op filter
**Severity:** High
**Rule:** Correctness bug (not a ShellCheck rule)
**Location:** `write_manifest()` — appears twice (git platforms loop and doc-site platforms loop):

```bash
find . -type f -not -name '.' | sort | sed 's|^\./||' | awk '...'
```

`-not -name '.'` is intended to exclude the `.` entry, but `find . -type f` already excludes `.` because `.` is a directory, not a regular file (`-type f` filters it out). The `-not -name '.'` predicate is therefore dead code — it never matches and never excludes anything.

This is harmless in practice but indicates a misunderstanding of `find` behavior and constitutes dead/misleading code.

**Fix:** Remove the `-not -name '.'` predicate:

```bash
# Before:
find . -type f -not -name '.' | sort | sed 's|^\./||' | awk '...'

# After:
find . -type f | sort | sed 's|^\./||' | awk '...'
```

---

### ISSUE-05 — Unquoted glob expansion in `extract_doc_platform()`
**Severity:** Medium
**Rule:** SC2035 / SC2086
**Location:** `extract_doc_platform()`:

```bash
cp "${vendor_path}"/*.md "${snapshot_path}/" 2>/dev/null || true
```

If `${vendor_path}` contains no `.md` files, the glob `*.md` is unexpanded (literal `*.md`) and `cp` will fail with "No such file or directory". The `2>/dev/null || true` suppresses the error, which is intentional, but the pattern also risks issues if `vendor_path` itself contains spaces or special characters — though it is double-quoted here so path traversal is not a concern.

The suppression pattern `2>/dev/null || true` also silences legitimate copy failures (e.g., permission errors on destination). A cleaner approach uses a conditional check or `shopt -s nullglob`.

**Fix:**

```bash
# Before:
cp "${vendor_path}"/*.md "${snapshot_path}/" 2>/dev/null || true

# After (nullglob approach — Bash 5.1+):
shopt -s nullglob
local mdfiles=("${vendor_path}"/*.md)
shopt -u nullglob
if [[ ${#mdfiles[@]} -gt 0 ]]; then
    cp "${mdfiles[@]}" "${snapshot_path}/"
fi
```

Or the minimal fix preserving original intent but making failure explicit:

```bash
# Minimal fix: check before copying
if compgen -G "${vendor_path}/*.md" > /dev/null 2>&1; then
    cp "${vendor_path}"/*.md "${snapshot_path}/"
fi
```

---

### ISSUE-06 — `log ""` outputs a timestamp with no message (minor cosmetic issue)
**Severity:** Low
**Rule:** Style / correctness
**Location:** `main()` — two calls: `log ""` for blank-line separators

```bash
log ""
```

The `log` function is:
```bash
log() {
    printf "[%s] %s\n" "$(date -u +%H:%M:%S)" "$*"
}
```

When called with an empty string, this prints `[HH:MM:SS] ` (timestamp plus trailing space plus newline). The intent is a visual blank-line separator. This produces noisy output with a timestamp prefix on every blank line.

**Fix:** Use `printf '\n'` directly for blank line separators instead of `log ""`:

```bash
# Before:
log ""

# After:
printf '\n'
```

---

### ISSUE-07 — `echo` used instead of `printf` (portability/consistency)
**Severity:** Low
**Rule:** SC2059 / style
**Location:** Top-level argument handling:

```bash
echo "[dry-run] No files will be written or repos cloned."
```

The rest of the script consistently uses `printf` via the `log()` helper. This one `echo` call is inconsistent and bypasses the timestamp prefix.

**Fix:** Replace with the `log` function call (which uses `printf` internally):

```bash
# Before:
echo "[dry-run] No files will be written or repos cloned."

# After:
log "dry-run: No files will be written or repos cloned."
```

---

### ISSUE-08 — `cd` in command substitution without `|| exit` (SC2164 variant)
**Severity:** Medium
**Rule:** SC2164
**Location:** `write_manifest()` — appears twice in the `files_json` command substitution:

```bash
files_json="$(cd "${snapshot_path}" && find . -type f -not -name '.' | sort | sed 's|^\./||' | awk 'BEGIN{printf "["} NR>1{printf ","} {printf "\"%s\"", $0} END{printf "]"}')"
```

The `cd "${snapshot_path}" &&` pattern is correct inside the subshell (the `&&` propagates failure to skip the `find`). However, if `cd` fails (directory does not exist), the entire subshell exits non-zero, causing `files_json` to be set to an empty string — not `[]`. This produces malformed JSON in the manifest.

The guard `if [[ -d "${snapshot_path}" ]]; then` wraps this in the doc-site loop but **not** in the git-platforms loop. In the git-platforms loop, `files_json` starts as `"[]"` but the conditional `if [[ -d "${snapshot_path}" ]]; then` only guards the assignment to `files_json` — if the guard is true but `cd` then fails for any other reason, the JSON output breaks.

This is not a `set -e` issue because the subshell is inside `$(...)` which does not propagate failure to the outer script under `set -e` — the outer variable just gets an empty value.

**Fix:** Handle the empty result case after the substitution, or use `pushd`/`popd` with error handling:

```bash
# Before (in git platforms loop):
local files_json="[]"
if [[ -d "${snapshot_path}" ]]; then
    files_json="$(cd "${snapshot_path}" && find . -type f -not -name '.' | sort | sed 's|^\./||' | awk 'BEGIN{printf "["} NR>1{printf ","} {printf "\"%s\"", $0} END{printf "]"}')"
fi

# After:
local files_json="[]"
if [[ -d "${snapshot_path}" ]]; then
    local raw_json
    raw_json="$(cd "${snapshot_path}" && find . -type f | sort | sed 's|^\./||' | awk 'BEGIN{printf "["} NR>1{printf ","} {printf "\"%s\"", $0} END{printf "]"}')"
    [[ -n "${raw_json}" ]] && files_json="${raw_json}"
fi
```

Note: SC2155 (ISSUE-02) also applies here — `local files_json="$(...)` masks the subshell exit code.

---

### ISSUE-09 — JSON values not escaped (correctness / security)
**Severity:** Medium
**Rule:** Not a ShellCheck rule — correctness / data integrity bug
**Location:** `write_manifest()` — `printf` calls that embed shell variables directly into JSON:

```bash
printf '    {\n      "name": "%s",\n      "source": "git",\n      "url": "%s",\n      "sha": "%s",\n      "timestamp": "%s",\n      "files": %s\n    }' \
    "${name}" "${url}" "${sha}" "${timestamp}" "${files_json}"
```

None of the values (`name`, `url`, `sha`, `timestamp`) are JSON-escaped. If any value contains a double-quote, backslash, or newline, the output JSON is malformed. Platform names and URLs in the script's data do not currently contain these characters, but this is a fragile assumption — it will break if the data ever changes or if SHA values somehow contain special characters (they won't, but the pattern is unsafe by design).

File paths collected by `find` and embedded into `files_json` by `awk` also have no JSON escaping applied. Filenames containing backslashes or double-quotes would produce invalid JSON.

**Fix for platform-controlled static strings:** Low risk for `sha` and `timestamp` (controlled by git and `date`). Moderate risk for `url` and `name`. If the file list may ever include unusual filenames, add escaping in the `awk` script:

```awk
# Before:
awk 'BEGIN{printf "["} NR>1{printf ","} {printf "\"%s\"", $0} END{printf "]"}'

# After (escape backslash and double-quote):
awk 'BEGIN{printf "["} NR>1{printf ","} {gsub(/\\/, "\\\\"); gsub(/"/, "\\\""); printf "\"%s\"", $0} END{printf "]"}'
```

For a production script, use `python3 -c 'import json,sys; ...'` or `jq` to build the JSON rather than string concatenation.

---

### ISSUE-10 — `DRY_RUN` variable compared with string "false" instead of boolean pattern
**Severity:** Low
**Rule:** Style / robustness
**Location:** Multiple places, e.g. `main()`:

```bash
if [[ "${DRY_RUN}" == false ]]; then
```

And `ensure_dir()`:
```bash
if [[ "${DRY_RUN}" == true ]]; then
```

Using string comparisons against `"true"` / `"false"` is a valid pattern in Bash, but unquoted `false` and `true` on the right side of `[[ == ]]` are treated as literal strings (not glob patterns), so this is technically correct. However, it is inconsistent with idiomatic Bash where boolean state is typically tracked as `0`/`1` integers and tested with `(( DRY_RUN ))`, or the variable is compared against a consistent `"true"` string pattern throughout.

The script already handles this consistently — both sides are always quoted or are literals without glob characters — so this is a **Low** priority style note rather than a correctness issue.

**Recommended idiom for future scripts:**

```bash
# Declare as integer
DRY_RUN=0
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

# Test with arithmetic
if (( DRY_RUN )); then ...
```

---

### ISSUE-11 — `git pull --ff-only` failure recovery uses `git reset --hard`
**Severity:** Medium
**Rule:** Operational correctness / safety
**Location:** `clone_or_update_repo()`:

```bash
git -C "${dest}" pull --ff-only --quiet 2>/dev/null || {
    log "WARNING: git pull failed for ${name}, trying fetch+reset..."
    git -C "${dest}" fetch origin --quiet
    local default_branch
    default_branch="$(git -C "${dest}" symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's|refs/remotes/origin/||' || echo "main")"
    git -C "${dest}" reset --hard "origin/${default_branch}" --quiet
}
```

`git pull 2>/dev/null` silences all stderr. If `git pull --ff-only` fails for a reason other than a non-fast-forward (e.g., network failure, corrupted repo), the `2>/dev/null` discards the diagnostic. The fallback then proceeds with `git fetch` + `git reset --hard`, which will also fail silently because the fetch errors are not suppressed — but the reset will run against a potentially stale `origin/${default_branch}` reference, corrupting the vendor clone.

Additionally, `git -C "${dest}" symbolic-ref refs/remotes/origin/HEAD` fails (exit code 128) when `origin/HEAD` has not been set (common for shallow clones with `--depth 1`). The `|| echo "main"` fallback handles this, but always defaulting to `"main"` is incorrect for repos whose default branch is `master`, `trunk`, or anything else.

**Fix:** Remove the `2>/dev/null` from `git pull` so failures are visible. For the default branch, use `git remote show origin` or store the branch at clone time:

```bash
# At clone time, capture the default branch:
git clone --quiet --depth 1 "${url}" "${dest}"
git -C "${dest}" remote set-head origin --auto --quiet 2>/dev/null || true

# At pull time, do not suppress stderr:
git -C "${dest}" pull --ff-only --quiet || {
    log "WARNING: git pull failed for ${name}, trying fetch+reset..."
    git -C "${dest}" fetch origin --quiet
    local default_branch
    default_branch="$(git -C "${dest}" symbolic-ref refs/remotes/origin/HEAD 2>/dev/null \
        | sed 's|refs/remotes/origin/||')"
    if [[ -z "${default_branch}" ]]; then
        log "WARNING: Cannot determine default branch for ${name}, skipping reset"
        return 1
    fi
    git -C "${dest}" reset --hard --quiet "origin/${default_branch}"
}
```

---

### ISSUE-12 — `ensure_dir` called inside `clone_or_update_repo` when `DRY_RUN=false`, but not when `DRY_RUN=true`
**Severity:** Low
**Rule:** Logic / correctness
**Location:** `clone_or_update_repo()`:

```bash
if [[ "${DRY_RUN}" == true ]]; then
    if [[ -d "${dest}/.git" ]]; then
        log "dry-run: would git pull in ${dest}"
    else
        log "dry-run: would git clone ${url} into ${dest}"
    fi
    return 0
fi

ensure_dir "${VENDOR_DIR}"
```

`ensure_dir "${VENDOR_DIR}"` is called only in the live path. This is correct behaviour for `--dry-run`. However, the dry-run path checks `[[ -d "${dest}/.git" ]]` to decide what message to print. If `${VENDOR_DIR}` does not yet exist, `${dest}` cannot exist either, so this check will always be false on a fresh system. This means dry-run always prints "would git clone" even if a vendor clone already exists at a path that happens to be readable (unlikely on a fresh system but possible if the dir exists from a previous partial run before the script was changed).

This is a minor logical issue — the dry-run output is accurate in the common case. No code change is strictly required, but it is worth noting.

---

## Refactored Sections

### Refactor 1 — SC2155: Declare and assign separately in `write_manifest()`

```bash
# BEFORE (git platforms loop):
local sha="unknown"
if [[ -d "${vendor_path}/.git" ]]; then
    sha="$(git -C "${vendor_path}" rev-parse HEAD 2>/dev/null || echo "unknown")"
fi

local snapshot_path="${OUTPUT_DIR}/${name}"
local files_json="[]"
if [[ -d "${snapshot_path}" ]]; then
    files_json="$(cd "${snapshot_path}" && find . -type f -not -name '.' | sort | sed 's|^\./||' | awk 'BEGIN{printf "["} NR>1{printf ","} {printf "\"%s\"", $0} END{printf "]"}')"
fi

# AFTER:
local sha="unknown"
if [[ -d "${vendor_path}/.git" ]]; then
    local _sha
    _sha="$(git -C "${vendor_path}" rev-parse HEAD 2>/dev/null || echo "unknown")"
    sha="${_sha}"
fi

local snapshot_path="${OUTPUT_DIR}/${name}"
local files_json="[]"
if [[ -d "${snapshot_path}" ]]; then
    local _raw_json
    _raw_json="$(cd "${snapshot_path}" && find . -type f | sort | sed 's|^\./||' \
        | awk 'BEGIN{printf "["} NR>1{printf ","} {gsub(/\\/, "\\\\"); gsub(/"/, "\\\""); printf "\"%s\"", $0} END{printf "]"}')"
    [[ -n "${_raw_json}" ]] && files_json="${_raw_json}"
fi
```

Changes:
- Split `local` from command substitution to avoid SC2155 exit-code masking
- Removed dead `-not -name '.'` predicate (ISSUE-04)
- Added backslash and double-quote escaping in `awk` for JSON correctness (ISSUE-09)
- Added guard so empty `raw_json` does not overwrite the safe `"[]"` default

---

### Refactor 2 — `git reset --hard` flag ordering and stderr visibility

```bash
# BEFORE:
git -C "${dest}" pull --ff-only --quiet 2>/dev/null || {
    log "WARNING: git pull failed for ${name}, trying fetch+reset..."
    git -C "${dest}" fetch origin --quiet
    local default_branch
    default_branch="$(git -C "${dest}" symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's|refs/remotes/origin/||' || echo "main")"
    git -C "${dest}" reset --hard "origin/${default_branch}" --quiet
}

# AFTER:
git -C "${dest}" pull --ff-only --quiet || {
    log "WARNING: git pull failed for ${name}, trying fetch+reset..."
    git -C "${dest}" fetch origin --quiet
    local default_branch
    default_branch="$(git -C "${dest}" symbolic-ref refs/remotes/origin/HEAD 2>/dev/null \
        | sed 's|refs/remotes/origin/||')"
    if [[ -z "${default_branch}" ]]; then
        log "WARNING: Cannot determine default branch for ${name}, skipping hard reset"
        return 1
    fi
    # --quiet must precede the commit-ish argument
    git -C "${dest}" reset --hard --quiet "origin/${default_branch}"
}
```

Changes:
- Removed `2>/dev/null` from `git pull` so errors are visible (ISSUE-11)
- Fixed `--quiet` flag position in `git reset --hard` (ISSUE-03)
- Replaced `|| echo "main"` fallback with an explicit guard that refuses to reset to an assumed branch name (ISSUE-11)

---

### Refactor 3 — Loop variable scoping in `main()`

```bash
# BEFORE (repeated three times in main()):
for entry in "${GIT_PLATFORMS[@]}"; do
    local name="${entry%%|*}"
    local url="${entry##*|}"
    clone_or_update_repo "${name}" "${url}"
done

# AFTER:
local name url entry
for entry in "${GIT_PLATFORMS[@]}"; do
    name="${entry%%|*}"
    url="${entry##*|}"
    clone_or_update_repo "${name}" "${url}"
done
```

Changes:
- `local` declarations moved before the loop (correct scoping, SC2168-adjacent)
- Variables assigned without `local` inside loop body (avoids repeated re-declaration)
- Loop iteration variable `entry` also declared `local` before the loop

---

## Best Practices Checklist

| Check | Status | Notes |
|-------|--------|-------|
| `set -euo pipefail` | PASS | Present at line 1 of script body |
| All variable expansions quoted | PASS (mostly) | Exception: `$*` in `log()` is intentional (join args) |
| `trap` for cleanup | FAIL | No `trap EXIT` to clean up partial state on error |
| `readonly` for constants | FAIL | `VENDOR_DIR`, `PROJECT_ROOT`, `SNAPSHOT_DATE`, `OUTPUT_DIR` should be `readonly` |
| SC2155 — declare/assign separate | FAIL | 3 violations in `write_manifest()` |
| SC2164 — `cd || exit` | PASS (partial) | `cd` is inside `$(...)` subshells guarded by `&&`, acceptable |
| `local` in functions | PASS (style warning) | `local` inside loop bodies — see ISSUE-01 |
| `printf` over `echo` | FAIL (minor) | One bare `echo` in argument-parsing block |
| Input validation | PASS | `--dry-run` is the only accepted argument; others are ignored |
| Shellcheck directives documented | N/A | No suppressions used |
| JSON output correctness | FAIL | No escaping of values embedded in JSON strings |
| Error visibility | FAIL | `git pull 2>/dev/null` silences diagnostic output |

---

## Priority Order for Fixes

1. **Critical / apply before implementing:** ISSUE-02 (SC2155 — exit code masking), ISSUE-03 (git reset flag order)
2. **High — correctness bugs:** ISSUE-04 (dead `find` predicate), ISSUE-09 (JSON escaping), ISSUE-11 (silent git errors + wrong default branch fallback)
3. **Medium — robustness:** ISSUE-05 (glob expansion), ISSUE-08 (cd failure in subshell)
4. **Low — style / maintainability:** ISSUE-01 (local in loop), ISSUE-06 (log ""), ISSUE-07 (echo), ISSUE-10 (boolean pattern), ISSUE-12 (dry-run logic)
