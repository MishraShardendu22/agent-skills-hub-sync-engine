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
    # Fast runners: go test -race of the worker engine took 338-553 s on the Dell (dell-ci-N), 22-35 s on the laptop.
    runs-on: [self-hosted, linux, workstation, fast]
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
  frontend-test:            # setup-node, ./.github/actions/setup-pnpm (packageManager's sha512), install --frozen-lockfile, lint, tsc, build
  smoke:                    # build every image, start the compose stack, wait for each /health
  ci-status:                # needs every job, if: always(), fails on any failure or cancellation
```

### Workflow Hardening Rules

1. **Pin every action by full commit SHA** with a `# vX.Y.Z` comment, on its current major version (Node 24 runtime). Look SHAs up with `gh api repos/<owner>/<action>/commits/<tag> --jq .sha`; update SHA and comment together by hand (Dependabot pull requests are off).
2. **Name the runners by their labels**: every job has `runs-on: [self-hosted, linux, workstation]`, the owner's runners on every machine, except a job that runs untrusted code with an AI agent (CI autofix's fix job), which gets a label only an isolated runner carries (`autofix-sandbox`), so it cannot land on the pool that runs privileged jobs. No job runs on runners GitHub hosts, on another CI provider or on a fallback; declare custom labels in `.github/actionlint.yaml`. **Heavy jobs ask for the fast machine**: when the runners span machines of different speed, only the fast machine's runners carry `fast`, and a CPU-heavy job adds it (`[self-hosted, linux, workstation, fast]`) with a one-line comment above `runs-on` that says why, a measurement when there is one. Heavy means compiling or testing much code (Go race tests and builds, integration tests with their database, `tsc`, Vitest, Next.js builds), driving a browser against a local build (Frontend E2E, Lighthouse), building images or emulating another architecture; on the owner's dual-core second machine `go test -race` for the worker engine took 338-553 s against 22-35 s on the laptop. Light jobs (change detection, docs and contract checks, deployment configuration, the Python suite, scripts, lockfile audits, govulncheck, gitleaks, Trivy, a browser check of the deployed sites, triage, review, status aggregates) keep the three labels so every machine shares them. A matrix whose entries differ picks the labels with an expression (`${{ matrix.app == '<heavy>' && fromJSON('[..., "fast"]') || fromJSON('[...]') }}`), so the job's name and its check names stay the same. A scaler that starts runners on one machine counts as demand only the queued jobs that ask for its runners' own label (here `workstation`) and whose labels are all among those its runners carry.
3. **Least privilege**: top-level `permissions: contents: read`; grant `packages: write`, `pull-requests: write` and similar only to the job that needs them. Check out with `persist-credentials: false` unless a later step must push.
4. **Path filtering with an aggregate check**: skip jobs whose files did not change, and add one always-running status job that fails when any job failed or was cancelled; require only that job in branch protection.
5. **One run per change**: CI runs on `push` to every branch, so the `pull_request` run does work only for PRs from forks (`github.event.pull_request.head.repo.full_name != github.repository`). Add `concurrency` so superseded runs are cancelled, except on the default branch, which gets one group per commit (`github.ref == 'refs/heads/main' && github.sha || ...`): a group holds one running and one pending run, and a new run cancels the pending one, so a shared default-branch group can drop a commit's CI run and, with it, the images it should publish.
6. **Never report work that did not happen**: a step whose secret is missing must skip with a `::warning::` or `::notice::`, and summaries must state what actually ran. Secrets cannot appear in `if:`; test them in a step (`[ -n "$VAR" ]`) and use its output.
7. **No real credentials in tests**: test jobs use mock values, never repository secrets.
8. **Private repositories on free plans**: artifacts and caches count against quota; disable build-record uploads (`DOCKER_BUILD_RECORD_UPLOAD: "false"`) and keep one cache scope per image.
9. Lint workflows with `actionlint` and `zizmor` (`--config .github/zizmor.yml`, which turns off `self-repository`: actionlint 1.7.12 rejects the `uses: $/...` form it asks for); justify any `zizmor: ignore[...]` inline.
10. **Jobs independent, runners several**: every job depends on the change detection alone, so the jobs of a run execute side by side; a self-hosted machine runs as many runners as its cores and memory allow, decided by demand and the machine's state rather than a fixed count (the owner's laptop registers six and `deploy/workstation-runners/ghb_scaler.py` runs one to six of them), and only jobs that share one resource (the smoke test's Docker daemon) wait for each other, and they take turns through a lock file (rule 11), not a `concurrency` group. Never run a test twice: the integration job tests only the packages that use its service containers (`scripts/go-db-packages.sh`), and the unit job the rest. When one service container is the bottleneck, split the job into shards that each get their own (the integration job's `migrations` and `services` shards, `go-db-packages.sh --shard`), and measure the package parallelism (`go test -p`) against that service: too little leaves it idle, too much makes it the bottleneck. Integration tests that each get their own database run with `t.Parallel()`, except those that time a lock or change cluster-wide state such as roles. Jobs that need a database run it in a container on a port Docker picks, never install one on the runner. On the self-hosted runners a step starts it (`scripts/ci-services.sh up`, and `down` under `if: always()`), not `services:`: rootless Docker picks a published port from the range the host's connections and the tests' listeners use, RootlessKit then fails to bind it ("address already in use"), and the runner never retries a service container; the script publishes on 127.0.0.1, tries another port up to three times and removes what a lost job left. A database container that tests fill with throwaway data keeps its data directory on a RAM disk (`--tmpfs <data dir>:rw`): it outlives nothing, and it is the job's main disk load. The same goes for the Security Audit: a `changes` job gates govulncheck on Go changes, pip-audit on the Observatory lockfile, each pnpm audit on its app's lockfile (a JSON matrix of the apps that changed), Trivy on any lockfile or Dockerfile, the pinned pnpm release's registry signature on a `package.json` and the workflow lint on `.github/`; gitleaks always runs, and the schedule audits everything. Image publishing is scoped the same way: an image is rebuilt only when an input changed since its last publish (`scripts/image-inputs.sh`), and otherwise the previous image gets the commit's tags, so every commit keeps a full tag set.
11. **Runners that share one machine**: the runners on one machine keep one home, one Docker daemon and their caches between jobs, so no step may assume a fresh machine. Keep caches on the runner's disk (`setup-go` with `cache: false`, `setup-node` without `cache`), put state that parallel jobs would mix (the pnpm directory, a Docker config with registry logins, free ports) under `runner.temp` per job, make jobs that share one resource on the machine take turns through a lock file (`flock` on a file in `$XDG_RUNTIME_DIR`, held for one step), not a `concurrency` group shared across branches: a group keeps one running and one pending job, and each newly queued job cancels the pending one, so with several branches pushing, jobs are cancelled before they start; and pick binaries and emulation by `runner.arch`. The Docker daemon is rootless: `docker run -u "$(id -u)"` maps the user to a subordinate id, so a mounted checkout looks owned by someone else inside the container, and git in there refuses it as "dubious ownership". A tool that reads git history in a container gets `safe.directory` through `GIT_CONFIG_COUNT`/`GIT_CONFIG_KEY_0`/`GIT_CONFIG_VALUE_0`, and its step fails when the tool's log shows a git error (gitleaks logs the error, scans 0 commits and exits 0). A count of 0 alone is not proof: gitleaks also reports 0 for commits that only delete files or change binaries. A tool that writes a mounted directory (Trivy's database cache) runs without `-u` under rootless Docker, because the container's root is the runner's user and a subordinate id cannot write that directory; choose `-u` only when `docker info --format '{{.SecurityOptions}}'` does not say `rootless`, and fail the step when the tool itself fails rather than letting a later step use what it left behind.
12. **Browser tests run production builds and stay hermetic**: a job that drives a site in a browser (Playwright) builds and serves it as it is deployed (a static export with the host's headers, `next build` then `next start`), answers every request to a third-party host it does not test inside the browser (`context.route`): analytics and tracking services, never with a real key, and the web fonts and other assets a site loads from another host, which the browser is also told not to resolve, so a missed host fails every run instead of only when the runner's network drops, and points server-side backends at a closed port. On self-hosted runners that share a machine it takes free ports (`E2E_*_PORT`) instead of fixed ones, keeps the browser in the shared `~/.cache/ms-playwright`, and installs system libraries (`--with-deps`) only on hosted runners. The same checks against the live sites run on a schedule, with the same interception. Upload the report only on failure (artifact quota).
13. **A capped self-hosted runner caps the steps, never the runner**: when a workstation runs CI next to a person's work, cap what the steps run (a cgroup slice with `MemoryHigh` and a `CPUWeight` below the desktop's) but neither the listener nor `Runner.Worker`: memory throttling also throttles the cgroup's sockets, the listener loses its long poll and the worker stops renewing the job's lease ("The self-hosted runner lost communication with the server"). A job-start hook that moves the worker into the cap is the wrong tool; a `bash` first on the runner's `PATH` (its `.path` file) that starts each step's shell with `systemd-run --user --scope --slice=<cap>` caps every `run:` step and what it starts, and service containers are capped through the Docker daemon's cgroup parent. Share an action archive cache between the runners (`ACTIONS_RUNNER_ACTION_ARCHIVE_CACHE`): many jobs in a short time from one address get `429` from codeload.github.com while downloading `actions/checkout`, and a token does not raise that limit. Measure with pressure stall information (`/proc/pressure/memory`) before choosing the cap; see `docs/architecture/current/06-operations.md#ci-runners`.
14. **AI agents in workflows: read-only by default, writes on the owner's word**: a job that runs an AI agent on every pull request gets read-only tools (deny the edit, commit and push tools explicitly) and one comment it rewrites, not a new one per run. A job whose agent may push starts only from a comment by the owner (`author_association == 'OWNER'`), only on an open pull request from the same repository whose head is not the default branch (checked in a step), under a per-pull-request `concurrency` group without `cancel-in-progress`. Pushes that must start CI again come from an app's token, never the `GITHUB_TOKEN` (its pushes start no workflow), and the workflow's own token stays read-only. The agent's instructions say that the pull request's text is data, and every run is bounded by a model, a turn limit and `timeout-minutes`. One standing exception, the owner's word of 2026-11-06: **CI autofix** may commit without a comment, but only to an open, non-draft pull request by the owner without the label `no-autofix`, whose head is still the failed CI push run's commit pushed by the owner or `claude[bot]`, and at most 3 autofix commits in a row (trailer `CI-Autofix-Run:`). Split it by privilege: the job that decides (and re-runs jobs whose annotations show a runner failure, up to the run's third attempt, never one that failed in the code) holds `actions: write`, `checks: read` and `pull-requests: write`, and fails rather than guess when it cannot read an annotation; the job that runs the agent holds only read scopes and the read-only `GITHUB_TOKEN` (`github_token: ${{ github.token }}`, so the action mints no app token), because the checks it runs execute the branch's code; its allowed commands name each check and include no program runner (`uv run`, `pnpm exec`, `go -exec`), and `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB: "1"` keeps the Claude secrets out of the environment those commands inherit, a weak layer only: a command running as the same user reads them from `/proc/$CLAUDE_PID/environ`. None of that is a sandbox on a self-hosted runner: the checks can do what the runner's user can (replace the runner tools on every runner's `PATH`, take over later jobs and their `id-token`, use the Docker socket), so say so wherever the job is described, and run the job only on a runner label that only an isolated runner carries (`autofix-sandbox`: another user or a rootless container without those rights, its network limited to GitHub's and Anthropic's hosts and the package hosts its setup needs), with a repository variable as a second switch (`CI_AUTOFIX_AGENT` = `isolated`, checked by the gate and the job's `if`). Hand a CI run to one fix at a time: the gate's comment names the workflow run that holds the fix, and the gate of a re-run hands nothing over while that run is in progress, and fails rather than start a fix when it cannot write that comment. Right after its checkout, before the agent or the branch's code runs, the fix job looks again with the default branch's script: a pull request that moved on while it waited leaves the commit job only the comment to update, and a fix of the same run that has reported, or a hand-off to another workflow run, skips both. Give it Go caches of its own under `RUNNER_TEMP`, never the runner user's. Agent mode refuses a `github.actor` that is a bot not in `allowed_bots`, so list each bot that can start the triggering run (`claude[bot]`, and `github-actions[bot]` after the gate's re-run). A deterministic script from the default branch reads the pull request again, then commits the change through `createCommitOnBranch` with an app token it mints and revokes itself, against `expectedHeadOid`, and refuses `.github/`, `.githooks/`, `.husky/`, `.claude/`, `.mcp.json`, `.claude.json`, `AGENTS.md`, `CLAUDE.md` and `CLAUDE.local.md` in any directory, `.agents/` and `agents/` (the skills), `docs/architecture/doc-map.toml`, `.gitmodules`, `.ripgreprc`, compared in lower case for a case-insensitive checkout (the action's `SENSITIVE_PATHS`, which it does not restore on `workflow_run`, plus the instructions the next attempt and the owner's sessions read, and the hooks; the agent lists what should change there in its summary), file modes and changes to executable files (the mutation has no mode field), secrets (every added line scanned with `--text`, so binary files count), lockfiles the summary does not name by their whole path, and a message with `[skip ci]` or a `skip-checks:` trailer. Tokens go to `curl` on standard input, never as arguments, and every text the scripts did not write (the agent's summary, the paths a refusal names, the failed jobs' names from the branch's `ci.yml`) is quoted into the comment with `<!--`, `-->` and `@` defused. When the branch has moved, it commits nothing and leaves the comment alone if a newer run's gate has rewritten it (each comment records its run). The agent never edits `.github/`, never weakens a test or check, and runs with `--setting-sources user` (on `workflow_run` the action does not restore the branch's `.claude/` from the base). Comments go out as `github-actions[bot]`, one per pull request found by a marker, never as `claude[bot]`, whose oldest comment the review rewrites. See `.github/workflows/pr-review.yml`.
15. **On a self-hosted machine, emulation and registry logins belong to the host and the job**: register QEMU on the host (a binfmt handler with the `F` flag, from the distribution's package) and skip `docker/setup-qemu-action` where that handler exists. Under rootless Docker the action's `binfmt_misc` mount gives the daemon's user namespace a table of its own that stays empty after the container exits and hides the host's handlers (`exec format error` on every foreign-platform `RUN`). Give each job its own `DOCKER_CONFIG` and write an entry into it before `docker login` (`{"auths": {"ghcr.io": {}}}`): from an empty config the Docker CLI stores the login in a credential helper (`pass`, `secretservice`) that every runner shares, and one job's logout removes the login another job is pushing with. Test emulation in the daemon the build uses (`docker run --platform` with a small image pinned by digest, or a static foreign-architecture binary) and fail with a message that names the fix. A `docker-container` builder passes such tests on its own, because the `moby/buildkit` image ships its own emulators; Docker's default builder does not. A builder that `setup-buildx-action` creates is used only when the build step sees the same `DOCKER_CONFIG` or gets its name, so check which builder the build log names.
16. **A package manager comes from bytes the repository pins, not from a second resolution at run time**: every pnpm job runs `actions/setup-node`, then `./.github/actions/setup-pnpm` with the project's `package.json`. `packageManager` names the release with the sha512 of its npm tarball (`pnpm@9.15.9+sha512.<hex>`, written by `corepack use pnpm@<version>`), and `scripts/install-pnpm.sh` downloads the tarball once into a cache the runners share (`~/.cache/ghb-pnpm`, curl with retries), checks the hash before caching it and on every use, and unpacks it into the job's `runner.temp`; a tarball whose hash differs is never cached or run. Never use `pnpm/action-setup`: v6 installs pnpm 11 and runs `pnpm self-update` to the pinned release in every job, and pnpm 11 then downloads the release's registry signature (the packument) with no retry; a cut-off download failed the job (`ERR_PNPM_PNPM_ENGINE_IDENTITY_UNVERIFIABLE`, CI run 42028433266, 1 of 67 installs over 40 runs; the step took 10 s median, 33 s p90, 172 s at worst, against 0.6 s from the cache). Its `version` input changes nothing: the switch runs whenever the release differs from the action's own. The jobs skip the registry signature on purpose, and that is safe because they run only the bytes whose sha512 is committed: the signature proves which bytes npm published, so it is checked where the pin is chosen. `corepack use` verifies it when it writes the pin, and the Security Audit's `pnpm-signature` job (`node scripts/verify-pnpm-signature.mjs`) checks that every pnpm project pins the same release, that the registry's `dist.integrity` is the pinned sha512 and that npm's ECDSA signature over it verifies, on every change to a `package.json` and weekly; `tests/verify_pnpm_signature_test.mjs` covers each way it must fail, against a local fake registry. To move to another pnpm release, run `corepack use pnpm@<version>` in `src/apps/*` and `tests/e2e`, then the script.
17. **Performance budgets are measured, not guessed**: a job builds the web app as it is deployed, serves it on a free port with its backends on a closed one, and runs Lighthouse CI (`@lhci/cli` from the browser tests' lockfile, never `pnpm dlx`, mobile lab settings, the browser the browser tests already install) against the public pages with a budgets file kept next to the app; a make target does the same against a running server. Budgets start as warnings while a redesign lands and become errors once the pages meet them; scores that are already met (SEO) fail at once.

---

## 2b. Image Publishing, Security Audit & Releases

- **Images**: build `linux/amd64,linux/arm64` with `docker/build-push-action` (`sbom: true`, `provenance: mode=max`), push to `ghcr.io/<owner lowercase>/<image>` with the built-in `GITHUB_TOKEN` (`packages: write`), and to Docker Hub only when its secrets exist. Tag `sha-<short>`, `latest` on the default branch and semver on `v*` tags (`flavor: latest=false`). Publish only commits that passed CI: trigger on `workflow_run` of CI (`branches: [main]`), accept only `event == 'push'` runs from this repository that succeeded, check out `workflow_run.head_sha`, and take the `sha-` tag and revision label from that SHA (not `github.sha`). Skip publishing when CI skipped the Docker smoke test, so bot data commits and documentation-only pushes do not publish. Add `latest` only when no file in the CI `docker` path filter changed on the default branch after the commit (compare API with the job's `GITHUB_TOKEN`; 300 or more listed files counts as changed), so a re-run of an old CI run or runs finishing out of order cannot move `latest` backwards; keep that glob list identical to the CI filter (a test checks it). Use one concurrency group per commit for the publish workflow too. Tag and manual runs must find a successful CI push run for the commit.
- **Deployments** that happen outside Actions (for example an operator running a deploy command on the server) need no deploy step; do not add steps that silently skip.
- **Rollbacks and migrations**: a deploy script that rolls back by starting the previous release must know whether that release accepts the current schema. When services refuse a database migrated past what they know, a deploy that applied migrations cannot roll back by a restart: record that it migrated, keep the backup it made before migrating, and log how to restore it instead of starting a release that exits.
- **Smoke tests**: CI must run the images it builds. Start the compose stack as an isolated project (no published ports, generated secrets, fresh volumes), wait with `docker compose up --wait`, probe each health endpoint, and print `docker compose logs` on failure.
- **Security audit workflow** (PRs, default-branch pushes, weekly schedule): language audits (`govulncheck`, `pip-audit` on the exported lockfile, `pnpm audit --audit-level high`), `gitleaks` over git history with a value-based allowlist for test fixtures, a Trivy filesystem scan failing only on fixable CRITICAL findings, and workflow linting. Without GitHub code scanning (private repositories on free plans), report in job logs and step summaries.
- **Dependency updates**: `.github/dependabot.yml` lists every ecosystem (language packages, Dockerfile base images, GitHub Actions) with `open-pull-requests-limit: 0`, so Dependabot opens no pull requests; updates go through the weekly dependency check.
- **Releases**: a `v*` tag first runs a gate job (the tagged commit must be an ancestor of `origin/main` and `go test` must pass), then GoReleaser (static `CGO_ENABLED=0` binaries, archives, `checksums.txt`, GitHub release) with `contents: write` on that job only and no build cache; GoReleaser writes the release notes from the commits since the previous tag (`changelog: use: git`). Validate locally with `goreleaser check` and `goreleaser release --snapshot --clean --skip=publish`.

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

