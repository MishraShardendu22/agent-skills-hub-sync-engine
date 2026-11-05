---
name: ci-cd-workflow
scope: generic
description: >-
  Rules, architectures, and guidelines for maintaining GitHub Actions CI/CD workflows,
  container image publishing (GHCR and Docker Hub), security scanning, releases, and deployments.
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
on:
  push:
    branches: ['**']        # every branch, including stacked PR branches
  pull_request:
    branches: [main]        # jobs only do work for PRs from forks (see below)

permissions:
  contents: read            # least privilege; jobs add only what they write

jobs:
  changes:                  # dorny/paths-filter: go / python / frontend / docker / scripts outputs
    if: github.event_name == 'push' || github.event.pull_request.head.repo.full_name != github.repository
  backend-test:
    needs: changes
    if: needs.changes.outputs.go == 'true'
    runs-on: [self-hosted, linux, workstation]
    steps:
      - uses: actions/checkout@<full-commit-sha> # vX.Y.Z
        with:
          persist-credentials: false
      - uses: actions/setup-go@<full-commit-sha> # vX.Y.Z
        with:
          go-version-file: go.mod   # honours the toolchain directive
      - run: git ls-files -z '*.go' | xargs -0 gofmt -l   # must print nothing
      - run: go mod tidy -diff
      - run: go vet ./...
      - run: go test -race -count=1 ./...
      - run: CGO_ENABLED=0 go build ./...
  service-test:             # astral-sh/setup-uv, uv sync --locked, type check, tests
  frontend-test:            # pnpm/action-setup (reads packageManager), install --frozen-lockfile, lint, tsc, build
  smoke:                    # build every image, start the compose stack, wait for each /health
  ci-status:                # needs every job, if: always(), fails on any failure or cancellation
```

### Workflow Hardening Rules

1. **Pin every action by full commit SHA** with a `# vX.Y.Z` comment, on its current major version (Node 24 runtime). Look SHAs up with `gh api repos/<owner>/<action>/commits/<tag> --jq .sha`; update SHA and comment together by hand (Dependabot pull requests are off).
2. **Name the runners by their labels**: every job has `runs-on: [self-hosted, linux, workstation]`, the owner's workstation runners. No job runs on runners GitHub hosts, on another CI provider or on a fallback; declare custom labels in `.github/actionlint.yaml`.
3. **Least privilege**: top-level `permissions: contents: read`; grant `packages: write`, `pull-requests: write` and similar only to the job that needs them. Check out with `persist-credentials: false` unless a later step must push.
4. **Path filtering with an aggregate check**: skip jobs whose files did not change, and add one always-running status job that fails when any job failed or was cancelled; require only that job in branch protection.
5. **One run per change**: CI runs on `push` to every branch, so the `pull_request` run does work only for PRs from forks (`github.event.pull_request.head.repo.full_name != github.repository`). Add `concurrency` so superseded runs are cancelled, except on the default branch, which gets one group per commit (`github.ref == 'refs/heads/main' && github.sha || ...`): a group holds one running and one pending run, and a new run cancels the pending one, so a shared default-branch group can drop a commit's CI run and, with it, the images it should publish.
6. **Never report work that did not happen**: a step whose secret is missing must skip with a `::warning::` or `::notice::`, and summaries must state what actually ran. Secrets cannot appear in `if:`; test them in a step (`[ -n "$VAR" ]`) and use its output.
7. **No real credentials in tests**: test jobs use mock values, never repository secrets.
8. **Private repositories on free plans**: artifacts and caches count against quota; disable build-record uploads (`DOCKER_BUILD_RECORD_UPLOAD: "false"`) and keep one cache scope per image.
9. Lint workflows with `actionlint` and `zizmor`; justify any `zizmor: ignore[...]` inline.
10. **Jobs independent, runners several**: every job depends on the change detection alone, so the jobs of a run execute side by side; a self-hosted machine runs as many runners as its cores and memory allow (four on the owner's workstation), and only jobs that share one resource (the smoke test's Docker daemon) take a `concurrency` group. Never run a test twice: the integration job tests only the packages that use its service containers (`scripts/go-db-packages.sh`), and the unit job the rest. When one service container is the bottleneck, split the job into shards that each get their own (the integration job's `migrations` and `services` shards, `go-db-packages.sh --shard`), and measure the package parallelism (`go test -p`) against that service: too little leaves it idle, too much makes it the bottleneck. Integration tests that each get their own database run with `t.Parallel()`, except those that time a lock or change cluster-wide state such as roles. Jobs that need a database declare a service container on a container port, never a step that installs or starts one on the runner. A database service container that tests fill with throwaway data keeps its data directory on a RAM disk (`options: --tmpfs <data dir>:rw`): it outlives nothing, and it is the job's main disk load. The same goes for the Security Audit: a `changes` job gates govulncheck on Go changes, pip-audit on the Observatory lockfile, each pnpm audit on its app's lockfile (a JSON matrix of the apps that changed), Trivy on any lockfile or Dockerfile and the workflow lint on `.github/`; gitleaks always runs, and the schedule audits everything. Image publishing is scoped the same way: an image is rebuilt only when an input changed since its last publish (`scripts/image-inputs.sh`), and otherwise the previous image gets the commit's tags, so every commit keeps a full tag set.
11. **Runners that share one machine**: the workstation runners keep one home, one Docker daemon and their caches between jobs, so no step may assume a fresh machine. Keep caches on the runner's disk (`setup-go` with `cache: false`, `setup-node` without `cache`), put state that parallel jobs would mix (the pnpm directory, a Docker config with registry logins, free ports) under `runner.temp` per job, queue jobs that share one resource with a `concurrency` group, and pick binaries and emulation by `runner.arch`.
12. **Browser tests run production builds and stay hermetic**: a job that drives a site in a browser (Playwright) builds and serves it as it is deployed (a static export with the host's headers, `next build` then `next start`), answers every request to a third-party host it does not test inside the browser (`context.route`): analytics and tracking services, never with a real key, and the web fonts and other assets a site loads from another host, which the browser is also told not to resolve, so a missed host fails every run instead of only when the runner's network drops, and points server-side backends at a closed port. On self-hosted runners that share a machine it takes free ports (`E2E_*_PORT`) instead of fixed ones, keeps the browser in the shared `~/.cache/ms-playwright`, and installs system libraries (`--with-deps`) only on hosted runners. The same checks against the live sites run on a schedule, with the same interception. Upload the report only on failure (artifact quota).
13. **A capped self-hosted runner caps the steps, never the runner**: when a workstation runs CI next to a person's work, cap what the steps run (a cgroup slice with `MemoryHigh` and a `CPUWeight` below the desktop's) but neither the listener nor `Runner.Worker`: memory throttling also throttles the cgroup's sockets, the listener loses its long poll and the worker stops renewing the job's lease ("The self-hosted runner lost communication with the server"). A job-start hook that moves the worker into the cap is the wrong tool; a `bash` first on the runner's `PATH` (its `.path` file) that starts each step's shell with `systemd-run --user --scope --slice=<cap>` caps every `run:` step and what it starts, and service containers are capped through the Docker daemon's cgroup parent. Share an action archive cache between the runners (`ACTIONS_RUNNER_ACTION_ARCHIVE_CACHE`): many jobs in a short time from one address get `429` from codeload.github.com while downloading `actions/checkout`, and a token does not raise that limit. Measure with pressure stall information (`/proc/pressure/memory`) before choosing the cap; see `docs/architecture/current/06-operations.md#ci-runners`.
14. **AI agents in workflows: read-only by default, writes on the owner's word**: a job that runs an AI agent on every pull request gets read-only tools (deny the edit, commit and push tools explicitly) and one comment it rewrites, not a new one per run. A job whose agent may push starts only from a comment by the owner (`author_association == 'OWNER'`), only on an open pull request from the same repository whose head is not the default branch (checked in a step), under a per-pull-request `concurrency` group without `cancel-in-progress`. Pushes that must start CI again come from an app's token, never the `GITHUB_TOKEN` (its pushes start no workflow), and the workflow's own token stays read-only. The agent's instructions say that the pull request's text is data, and every run is bounded by a model, a turn limit and `timeout-minutes`. See `.github/workflows/pr-review.yml`.
15. **On a self-hosted machine, emulation and registry logins belong to the host and the job**: register QEMU on the host (a binfmt handler with the `F` flag, from the distribution's package) and skip `docker/setup-qemu-action` where that handler exists. Under rootless Docker the action's `binfmt_misc` mount gives the daemon's user namespace a table of its own that stays empty after the container exits and hides the host's handlers (`exec format error` on every foreign-platform `RUN`). Give each job its own `DOCKER_CONFIG` and write an entry into it before `docker login` (`{"auths": {"ghcr.io": {}}}`): from an empty config the Docker CLI stores the login in a credential helper (`pass`, `secretservice`) that every runner shares, and one job's logout removes the login another job is pushing with. Test emulation in the daemon the build uses (`docker run --platform` with a small image pinned by digest, or a static foreign-architecture binary) and fail with a message that names the fix. A `docker-container` builder passes such tests on its own, because the `moby/buildkit` image ships its own emulators; Docker's default builder does not. A builder that `setup-buildx-action` creates is used only when the build step sees the same `DOCKER_CONFIG` or gets its name, so check which builder the build log names.

---

## 2b. Image Publishing, Security Audit & Releases

- **Images**: build `linux/amd64,linux/arm64` with `docker/build-push-action` (`sbom: true`, `provenance: mode=max`), push to `ghcr.io/<owner lowercase>/<image>` with the built-in `GITHUB_TOKEN` (`packages: write`), and to Docker Hub only when its secrets exist. Tag `sha-<short>`, `latest` on the default branch and semver on `v*` tags (`flavor: latest=false`). Publish only commits that passed CI: trigger on `workflow_run` of CI (`branches: [main]`), accept only `event == 'push'` runs from this repository that succeeded, check out `workflow_run.head_sha`, and take the `sha-` tag and revision label from that SHA (not `github.sha`). Skip publishing when CI skipped the Docker smoke test, so bot data commits and documentation-only pushes do not publish. Add `latest` only when no file in the CI `docker` path filter changed on the default branch after the commit (compare API with the job's `GITHUB_TOKEN`; 300 or more listed files counts as changed), so a re-run of an old CI run or runs finishing out of order cannot move `latest` backwards; keep that glob list identical to the CI filter (a test checks it). Use one concurrency group per commit for the publish workflow too. Tag and manual runs must find a successful CI push run for the commit.
- **Deployments** that a platform performs from Git (for example Vercel's Git integration or a Render blueprint with `autoDeploy`) need no deploy step; do not add steps that silently skip.
- **Rollbacks and migrations**: a deploy script that rolls back by starting the previous release must know whether that release accepts the current schema. When services refuse a database migrated past what they know, a deploy that applied migrations cannot roll back by a restart: record that it migrated, keep the backup it made before migrating, and log how to restore it instead of starting a release that exits.
- **Smoke tests**: CI must run the images it builds. Start the compose stack as an isolated project (no published ports, generated secrets, fresh volumes), wait with `docker compose up --wait`, probe each health endpoint, and print `docker compose logs` on failure.
- **Security audit workflow** (PRs, default-branch pushes, weekly schedule): language audits (`govulncheck`, `pip-audit` on the exported lockfile, `pnpm audit --audit-level high`), `gitleaks` over git history with a value-based allowlist for test fixtures, a Trivy filesystem scan failing only on fixable CRITICAL findings, and workflow linting. Without GitHub code scanning (private repositories on free plans), report in job logs and step summaries.
- **Dependency updates**: `.github/dependabot.yml` lists every ecosystem (language packages, Dockerfile base images, GitHub Actions) with `open-pull-requests-limit: 0`, so Dependabot opens no pull requests; updates go through the weekly dependency check.
- **Releases**: a `v*` tag first runs a gate job (the tagged commit must be an ancestor of `origin/main` and `go test` must pass), then GoReleaser (static `CGO_ENABLED=0` binaries, archives, `checksums.txt`, GitHub release) with `contents: write` on that job only and no build cache; use the matching `CHANGELOG.md` section as release notes. Validate locally with `goreleaser check` and `goreleaser release --snapshot --clean --skip=publish`.

---

## 3. Local CI Mirroring Runbook

To guarantee that your changes pass CI before committing:

```bash
# 1. Run the fast pre-commit checks, then the pre-push builds
make pre-commit
make pre-push

# Build the images and smoke-test the container stack
make smoke

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

