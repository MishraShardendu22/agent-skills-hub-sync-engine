---
name: ci-cd-workflow
scope: generic
description: >-
  Rules, architectures, and guidelines for maintaining GitHub Actions CI/CD workflows,
  Docker Hub image publishing, and automated deployments.
---

# CI/CD & Deployment Architecture Skill

This skill guides AI agents and contributors in maintaining GitHub Actions CI/CD pipelines, container image publishing, and automated deployments.

---

## 1. Local Branch-First Development & Commit Cadence

> [!IMPORTANT]
> **CREATE A LOCAL BRANCH FIRST & COMMIT FREQUENTLY**:
> Always start by creating a dedicated local branch from `main`:
> ```bash
> git switch -c <developer-or-agent>/main/<feature-name>
> ```
> Commit at each logical milestone (`more commits = more explanatory work`). Never commit directly on `main`.

---

## 2. Multi-Environment CI/CD Pipeline

```yaml
jobs:
  backend-test:
    name: Backend Test & Build
    steps:
      - uses: actions/setup-go@v5
      - run: go test -v -race ./...
      - run: go build -v ./...

  service-test:
    name: Python Service Test & Lint
    steps:
      - uses: astral-sh/setup-uv@v5
      - run: uv sync
      - run: uv run pytest

  frontend-test:
    name: Frontend Lint & Build
    steps:
      - uses: pnpm/action-setup@v4
      - uses: actions/setup-node@v4
      - run: pnpm install --frozen-lockfile
      - run: pnpm run lint
      - run: pnpm run build
```

---

## 3. Local CI Mirroring Runbook

To guarantee that your changes pass CI before committing:

```bash
# 1. Run the pre-commit gate (exact mirror of CI checks)
make pre-commit

# 2. Alternatively, run individual CI jobs locally:
# Go Backend:
go test -v -race ./... && go build -v ./...

# Python Service:
uv run pytest

# Frontend:
pnpm run lint && pnpm run build
```

---

## 4. Secrets vs Centralized Configuration

- **Secrets**: Strictly defined in `.env` / CI Secrets and runtime dashboards (`DATABASE_URL`, `API_KEY`, `JWT_SECRET`).
- **Operational Defaults**: Centralized in code modules.
- Never hardcode secrets in CI workflow YAML or Git commits.

---

## 4. DSA Confidence Engine — CI Reference

> [!IMPORTANT]
> **MANDATORY**: Every repository MUST have a CI workflow file at `.github/workflows/ci.yml`. Without it, there is no automated quality gate on Pull Requests.

For the `dsa-confidence-engine` (Go 1.25 monorepo), the CI pipeline runs three jobs sequenced as:

```
go-lint (gofmt check)
    └── go-test (go test -v -race ./...)
    └── go-build (go build ./... + go mod tidy check)
```

**Local mirrors of CI jobs** (run these before pushing):

```bash
# Mirror go-lint:
gofmt -l .                            # Must return empty output

# Mirror go-test:
go test -v -race -count=1 ./...

# Mirror go-build:
go build -v ./...
go mod tidy && git diff --exit-code go.mod go.sum
```

**CI triggers:**
- Every `git push` to **any branch** — fast feedback loop
- Every `pull_request` targeting **`main`** — enforced quality gate before merge

**Required workflow file:** `.github/workflows/ci.yml`
See `.agents/skills/github-pr-issue-automation/SKILL.md` Section 5 for the full list of required workflows.

