---
name: precommit-workflow-management
scope: generic
description: >-
  Rules, architecture, and runbooks for configuring, updating, and operating the intelligent Git pre-commit workflow.
---

# Pre-Commit Workflow Management Skill

This skill explains how to maintain, configure, and execute the intelligent pre-commit hook workflow across polyglot repositories.

---

## 1. Local Branch-First Development

> [!IMPORTANT]
> **CREATE A LOCAL BRANCH FIRST**: Always start by creating a dedicated local branch from `main`:
> ```bash
> git switch -c <developer-or-agent>/main/<feature-name>
> ```
> Never make changes directly on `main`.

---

## 2. Pre-Commit and Pre-Push Architecture

The hooks live in `.githooks/` and are tracked directly in version control. Commits must stay fast, so the work is split:

- **`pre-commit`**: fast checks only (secret scan, formatting, lint, static analysis, unit tests of the changed areas).
- **`pre-push`**: re-runs the pre-commit checks for the commits the push adds to the remote (not the layer below a stacked branch, not the `main` commits a branch merged in), then the slow builds (binaries, frontend production build, container images when container files change).

```text
Staged Changes Detected (git diff --cached)          [pre-commit]
  │
  ├── Only Go files changed ───────► Formatting, vet, tests of the changed packages
  ├── Only Python files changed ───► Pyright, test suites
  ├── Only Frontend files changed ─► Biome/Linter, tsc --noEmit
  ├── Only Documentation changed ──► Fast-path bypass (<0.2s)
  ├── Hooks / scripts / tests / Makefile ► bash -n and the changed script's own test
  ├── Workflows / skills ───────────► actionlint / validate-skills.py
  ├── Any other file ──────────────► Secret scan only; CI checks the rest
  └── Manual (PRECOMMIT_ALL=1) ─────► Every fast check

Pushed Commits Detected (stdin refs from git push)   [pre-push]
  │
  ├── Re-run the pre-commit checks for the commits new to the remote
  │   (PRECOMMIT_COMMITS: not a stacked branch's base, not merged-in main)
  ├── Code changed ────────────────► Compile binaries / frontend production build
  └── Container files changed ─────► Build the affected images (cache only)
      The builds run side by side; each one's output is printed when it ends.
```

---

## 3. Key Features

1. **Selective Staged-File Execution**: Avoids unnecessary work by only running checks relevant to the files staged for the commit.
2. **Fast-Path for Documentation, Own Tests for Tooling**: Commits containing only markdown (`*.md`), text (`*.txt`), or asset files run only the secret scan. Commits under `.github/` run the secret scan and actionlint; hooks, scripts, tests and the Makefile run `bash -n` and the test that covers them; skills run `validate-skills.py`; a file no area claims gets the secret scan and a note that CI checks the rest. None of these runs the Go, Python or frontend suites: what they run is CI's to run.
3. **Builds at Push Time, for New Commits Only**: Compilation and image builds run once per push instead of on every commit, side by side; the pre-push hook reads the pushed refs from stdin, checks only the commits the remote does not have yet (a stacked branch is not re-checked from `main`, a branch that merged `main` does not re-check `main`'s commits), and falls back to a full run when nothing of the remote is known.
4. **Subshell Directory Isolation**: Every check runs in a subshell `(cd "${REPO_ROOT}" && ...)` to prevent current working directory drift.
5. **Fail-Fast with Remediation**: Aborts immediately on failure and outputs exact commands needed to fix the problem.
6. **Zero External Runtime Dependencies**: Implemented in portable bash, requiring no heavy wrapper packages at the repository root. Keep it compatible with the bash 3.2 macOS ships: no associative arrays, `mapfile`/`readarray` or `${var,,}`, and no empty arrays under `set -u`.

---

## 4. Operations & Maintenance Runbook

### Activating the Hook Locally
```bash
make hooks-install
# Or: ./scripts/install-hooks.sh
```

### Manually Running the Gates
```bash
make pre-commit   # every fast check
make pre-push     # every check plus every build, without pushing
```

### Bypass Flags (Emergency Only)
```bash
# Skip tests for quick drafts
SKIP_TESTS=1 git commit -s -S -m "chore: draft"

# Skip the push-time builds (or only the container image builds)
SKIP_BUILDS=1 git push
SKIP_DOCKER=1 git push

# Run the builds one after another, with their output as it comes
PREPUSH_SERIAL=1 git push

# Force full validation across all subsystems
PRECOMMIT_ALL=1 git commit -s -S -m "feat: core change"
PREPUSH_ALL=1 git push

# Skip a hook entirely
SKIP_HOOKS=1 git commit -s -S -m "wip: draft"   # or PRECOMMIT_BYPASS=1
PREPUSH_BYPASS=1 git push
```
