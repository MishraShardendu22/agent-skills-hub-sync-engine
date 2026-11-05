---
name: dependency-maintenance
scope: codebase-github-backup-automation-system
description: >-
  Weekly dependency maintenance for the monorepo: the ledger of every direct dependency across Go, the three
  pnpm apps and tests/e2e, the Observatory's uv project, Docker base images and GitHub Actions (docs/dependencies/ledger.json,
  scripts/deps-ledger.py), when the check runs (Monday, caught up on the next run), how an update is judged safe,
  how a breaking update is deferred for two weeks and then migrated, including the code changes it needs.
---

# Dependency Maintenance

> [!IMPORTANT]
> **CODEBASE-SPECIFIC SCOPE**: This skill is strictly specific to the **GitHub Backup Automation System** (`github-backup-automation-system`): its ledger, script, Makefile targets, Security Audit workflow and the five services' toolchains.

---

## 1. Why

New advisories arrive for unchanged code (the Security Audit workflow goes red on every open pull request), per-package update pull requests have no view of the whole stack, and a major version that needs code changes waits for someone to notice. This skill gives the repository one record of what it depends on and one weekly routine that an agent runs, with the judgement spelled out.

## 2. The ledger

`docs/dependencies/ledger.json`, maintained by `scripts/deps-ledger.py` (standard library only; `python3 >= 3.9`). It holds:

| Field | Meaning |
| :--- | :--- |
| `last_check`, `last_check_note` | When the weekly check last ran and what it did. |
| `ecosystems.<key>.dependencies` | Every **direct** dependency with its resolved version and the date it last changed. Keys: `go` (`go.mod`), `pnpm:src/apps/github-backup-dashboard`, `pnpm:src/apps/github-backup-design`, `pnpm:src/apps/github-backup-docs`, `uv:src/services/github-backup-observatory`, `docker` (base images of every Dockerfile, with `ARG` defaults filled in), `compose` (third-party images the compose files pin, as `tag@sha256:<12 hex>`), `github-actions` (`uses:` pins). pnpm ecosystems also record `pnpm.overrides`. |
| `deferred` | Updates that must wait: dependency, versions, the reason, `deferred_on` and `revisit_on`. |
| `history` | Every applied update, newest last. |

The ledger never guesses: `scan` reads the manifests and lockfiles, `record`/`defer`/`resolve`/`checked` are written by the agent that did the work. `tests/test_deps_ledger.py` fails when the committed ledger and the committed manifests disagree, so a dependency change without `make deps-scan` does not pass the hook.

## 3. When the check runs

The check is weekly and belongs to **Monday**. It is done by the **first agent run of the week**, whatever day that is:

1. At the start of a session in this repository, run `make deps-due`.
2. `dependency check DUE` means: it is Monday and no check ran yet, **or** Monday was missed and this is the first run since (any later day of the same week, weekends included). Do the check now, in this session, before other work; never wait for the next Monday.
3. `not due` means this week's check already ran; `deps-due` also lists deferred updates whose `revisit_on` date has arrived, which are due now regardless of the weekday. (`scripts/deps-ledger.py due --strict` exits `2` when not due, for scripts.)
4. A failed Security Audit run or a Dependabot alert on a pull request is handled at once, on any day, with the same routine narrowed to that dependency.

`make deps-due` costs one file read and prints one line, so it is cheap to run on every session start (AGENTS.md section 10 asks for exactly that).

## 4. The routine (`make deps-check` runs steps 1 to 3)

1. **Scan**: `make deps-scan` (`deps-ledger.py scan`) shows direct dependencies that changed since the ledger was written and new or removed ones.
2. **Outdated**: `make deps-outdated` lists newer versions of direct dependencies (Go: `go list -m -u`; pnpm apps: `pnpm outdated`; Observatory: `uv pip list --outdated` in its `.venv`). Docker base images and GitHub Actions are listed with their pins only; check their upstream releases and update the pins by hand.
3. **Audit**: `make deps-audit` runs what the Security Audit workflow runs: `pnpm audit --audit-level high` per app (the docs site's job is advisory, like `blocking: false` in the workflow), `pip-audit` on the Observatory lock with the workflow's `--ignore-vuln` list, `govulncheck ./...`, and Trivy when it is installed.
4. **Decide**, for every newer version and every advisory, with the rules in section 5.
5. **Apply** the updates (section 6), run the affected test suites (`make test-go`, `make test-py`, `make test-dashboard`, the design and docs site builds), and record each one: `scripts/deps-ledger.py record --ecosystem <key> --name <pkg> --from <old> --to <new> --note "<why>"`; add `--transitive` for a package forced through `pnpm.overrides`.
6. **Defer** what cannot be done safely now (section 5): `scripts/deps-ledger.py defer --ecosystem <key> --name <pkg> --from <old> --to <new> --reason "<what breaks>"` (revisit in 14 days by default, `--days` to change).
7. **Close** the check: `make deps-scan-record` (writes the scanned state into the ledger) and `scripts/deps-ledger.py checked --note "<one line>"`. Commit as `chore(deps): <what changed>` with the ledger, the manifests and the lockfiles in the same commit, and put `make deps-report` into the pull request body.

## 5. Judging an update

| Situation | Decision |
| :--- | :--- |
| A **security advisory** at `high` or `critical` on a blocking audit (dashboard, design, Observatory, Go) | Update now, on any day. When the vulnerable package is transitive and its dependents still pin the vulnerable range, force it with `pnpm.overrides` (`">=<fixed version>"`) and verify with the app's build and tests. |
| An advisory **without a fixed release** | `defer` it with the reason "no fixed release" and the upstream it depends on; revisit in 14 days. The docs site's audit is advisory, so it never blocks. |
| **Patch or minor** of a direct dependency, tests and builds green | Update. |
| **Major** of a direct dependency, or any update whose changelog lists breaking changes that touch our code (SDK signatures, config keys, runtime requirements) | Read the changelog. If the code changes are clear and bounded, make them in the same change, with tests, and update. If not, `defer` for 14 days: upstream often publishes a fix or a migration note in that time, and the team may already know the error. When the revisit date arrives, do the migration, including the code or SDK changes it needs; do not defer the same update twice without a new reason recorded. |
| Docker base images, compose images, GitHub Actions | Update the pin by hand (new tag; for Actions the new commit SHA and its `# vX.Y.Z` comment); merge when CI is green (for `deploy/selfhost` and `deploy/shared`, also their `check.sh`) and `make deps-scan-record` afterwards. |
| `@mishrashardendu22/observatory-tokens` and `observatory-ui` | Never by hand: the `design-system-update.yml` pull request does it (`docs/DESIGN_SYSTEM_RELEASES.md`). |

Safe means: the affected suites pass (`go test ./...` with `TEST_DATABASE_URL`, `pytest`, `pyright`, Vitest, `tsc`, Biome, the Next.js and Docusaurus builds), the Security Audit checks pass, and no behaviour the documentation promises changed.

## 6. Applying an update per ecosystem

- **Go**: `go get <module>@<version> && go mod tidy` at the repository root (one module for the API, the MCP server and the worker). `go.mod`'s `go`/`toolchain` lines and the Dockerfiles' `golang` tag move together.
- **pnpm apps** (`src/apps/*`): prefer `pnpm update <pkg>` when the lockfile diff touches only that package. When the dependents pin a vulnerable range, or a plain update drags unrelated packages along, add `"pnpm": {"overrides": {"<pkg>": ">=<version>"}}` to `package.json` and run `pnpm install --lockfile-only`. Then `scripts/check-lockfile-integrity.sh --fix <lockfile>` (regenerating a lockfile drops the integrity hashes of the design-system tarball entries) and `pnpm install --frozen-lockfile`. Never commit an npm or yarn lockfile.
- **pnpm itself**: `corepack use pnpm@<version>` in each of `src/apps/*` and `tests/e2e` (it writes `packageManager` as `pnpm@<version>+sha512.<hex>` after checking npm's signature), then `node scripts/verify-pnpm-signature.mjs`; CI installs only the bytes with that sha512 (`.github/actions/setup-pnpm`), and the Security Audit checks the signature again on every `package.json` change and weekly.
- **Observatory** (`uv`): `uv lock --upgrade-package <pkg>` (or edit the bound in `pyproject.toml` and `uv lock`), then `uv sync`, `uv run pytest`, `uv run --with pyright pyright`.
- **Docker, GitHub Actions**: edit the `FROM` tag or the `uses:` SHA and `# vX.Y.Z` comment (`gh api repos/<owner>/<action>/commits/<tag> --jq .sha`); see section 5.

Before committing, delete local build output that is not ignored by `go vet` (`src/apps/github-backup-docs/build`, which carries copies of linked `.go` files).

## 7. Dependabot

Dependabot opens no pull requests: every entry in `.github/dependabot.yml` sets `open-pull-requests-limit: 0`, and security-update pull requests are off in the repository settings. This routine applies every update itself. Dependabot alerts stay on; an alert is handled at once (section 3, item 4). To turn the pull requests back on, remove `open-pull-requests-limit: 0` from an entry.

## 8. Commands

```bash
make deps-due            # is the weekly check due? also lists deferred updates to revisit (--strict: exit 2 when not)
make deps-check          # scan + outdated + audit, in one run
make deps-scan           # manifests vs ledger
make deps-scan-record    # write the manifests' state into the ledger
make deps-outdated       # newer versions (network)
make deps-audit          # the Security Audit workflow's checks, locally
make deps-report         # Markdown summary for a pull request body
scripts/deps-ledger.py record|defer|resolve|checked ...   # see --help
```

`--today YYYY-MM-DD` on any command records or evaluates another day (used by the tests).
