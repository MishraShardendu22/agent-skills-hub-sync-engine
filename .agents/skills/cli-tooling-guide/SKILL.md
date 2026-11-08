---
name: cli-tooling-guide
scope: generic
description: >-
  Standard operating guide for first-class authenticated CLI tools in the repository:
  GitHub CLI (gh), Docker CLI (docker), uv, and pnpm.
---

# Authenticated CLI Tooling & Operations Guide

This repository treats specialized developer CLI tools as first-class automation interfaces. AI agents and developers should prefer these authenticated CLIs over manual workflows.

---

## 1. Tooling Matrix & Authentication Overview

| Tool | CLI Binary | Auth Check Command | Primary Usage in System |
|---|---|---|---|
| **GitHub CLI** | `gh` | `gh auth status` | Pull requests, issues, repo management, label sync, Actions monitoring |
| **Docker CLI** | `docker` | `docker info` | Image builds, multi-stage validation, local test containers |
| **Python Package Manager** | `uv` | `uv --version` | Virtualenv management, dependency syncing, type checking |
| **Node.js Package Manager** | `pnpm` | `pnpm --version` | Frontend dependencies, Next.js build, Biome formatting/linting |
| **Go Toolchain** | `go` | `go version` | Backend API compilation, worker CLI execution, test suites |

---

## 2. Command Reference by Tool

### A. GitHub CLI (`gh`)
* **Create Pull Request**:
  ```bash
  gh pr create --base main --head <branch-name> --assignee "@me" --label "type/<type>,area/<area>,status/ready-for-review" --body "<body-markdown>"
  ```
* **View PR Status & Checks**:
  ```bash
  gh pr status
  gh pr checks <pr-number>
  ```
* **Check Actions Runs**:
  ```bash
  gh run list --limit 10
  ```

### B. Python Package Manager (`uv`)
* **Strict Rule**: Always use `uv`. Never invoke bare `pip install` or `python -m venv`.
* **Environment & Run**:
  ```bash
  uv venv
  uv sync
  uv run pytest
  uv add <pkg>
  ```

### C. Node.js Package Manager (`pnpm`)
* **Strict Rule**: Always use `pnpm`. Never invoke `npm` or `yarn`. Only commit `pnpm-lock.yaml`.
* **Dependencies & Build**:
  ```bash
  pnpm install
  pnpm add <pkg>
  pnpm up
  pnpm run build
  pnpm run test
  ```

---

## 3. Recovery & Re-Authentication Runbook

If any CLI tool reports authentication expiration or failure, alert the human developer with the exact command:

1. **GitHub CLI**: `gh auth login`
2. **Docker Hub**: `docker login`
3. **Project CLIs with stored logins** (OS keychain or a private credentials file): when one reports an expired, revoked or unreadable login, give the human the project's documented login command (for example a `make login-<service>` target). Never work around it by pasting tokens into `.env` files, and never run interactive browser logins on the human's behalf.
