---
name: dependency-maintenance
scope: codebase-github-backup-automation-system
description: >-
  Weekly dependency maintenance for the monorepo: the ledger of every direct dependency across Go, the three
  pnpm apps and tests/e2e, the Observatory's uv project, Docker base images and GitHub Actions (docs/dependencies/ledger.json,
  scripts/deps-ledger.py), the Weekly Dependency Update workflow that runs the check every Monday with Claude
  (deps-weekly.yml) and the merge gate that merges patch and minor updates (deps-merge.yml), the impact map of
  the checks each change must pass (scripts/deps-impact.py), how an update is judged safe, and how a breaking
  update is deferred for two weeks and then migrated, including the code changes it needs.
---

# Dependency Maintenance

> [!IMPORTANT]
> **CODEBASE-SPECIFIC SCOPE**: This skill is strictly specific to the **GitHub Backup Automation System** (`github-backup-automation-system`): its ledger, scripts, Makefile targets, the weekly update, merge gate and Security Audit workflows, and the five services' toolchains.

---

## 1. Why

New advisories arrive for unchanged code (the Security Audit workflow goes red on every open pull request), per-package update pull requests have no view of the whole stack, and a major version that needs code changes waits for someone to notice. This skill gives the repository one record of what it depends on and one weekly routine, with the judgement spelled out. The routine is run every Monday by a workflow (section 3) whose agent reads this skill, and by hand when that run did not happen. An update can break something that depends on it, so every change passes the checks of the impact map (section 6) before it is pushed.

## 2. The ledger

`docs/dependencies/ledger.json`, maintained by `scripts/deps-ledger.py` (standard library only; `python3 >= 3.9`). It holds:

| Field | Meaning |
| :--- | :--- |
| `last_check`, `last_check_note` | When the weekly check last ran and what it did. |
| `ecosystems.<key>.dependencies` | Every **direct** dependency with its resolved version and the date it last changed. Keys: `go` (`go.mod`), `pnpm:src/apps/github-backup-dashboard`, `pnpm:src/apps/github-backup-design`, `pnpm:src/apps/github-backup-docs`, `uv:src/services/github-backup-observatory`, `docker` (base images of every Dockerfile, with `ARG` defaults filled in), `compose` (third-party images the compose files pin, as `tag@sha256:<12 hex>`), `ci-services` (the images `scripts/ci-services.sh` starts for the CI integration jobs, same form), `github-actions` (`uses:` pins), `workflow-images` (images the workflows run themselves: `env` values named `*_IMAGE` and `image:` keys in `.github/workflows/*.yml`, this project's own images left out, as `tag@sha256:<12 hex>`). pnpm ecosystems also record `pnpm.overrides`. |
| `deferred` | Updates that must wait: dependency, versions, the reason, `deferred_on` and `revisit_on`. |
| `history` | Every applied update, newest last. |

The ledger never guesses: `scan` reads the manifests and lockfiles, `record`/`defer`/`resolve`/`checked` are written by the agent that did the work. `tests/test_deps_ledger.py` fails when the committed ledger and the committed manifests disagree (direct dependencies and `pnpm.overrides`), so a dependency or override change without `make deps-scan` does not pass the hook.

## 3. When the check runs

The check is weekly and belongs to **Monday**. The **Weekly Dependency Update** workflow (`.github/workflows/deps-weekly.yml`) runs it at 03:23 UTC on the self-hosted runners: Claude follows section 4 in a sandbox, a second job without an agent tests the change again, and only a change that passes becomes a pull request `deps/weekly-YYYY-MM-DD` (details and the merge policy: `docs/DEPENDENCIES.md`). The workflow's own agent starts at section 4; any other agent session does this:

1. At the start of a session in this repository, run `make deps-due`.
2. `dependency check DUE` means: it is Monday and no check is on `main` yet, **or** Monday was missed and this is the first run since (any later day of the same week, weekends included). The workflow's pull request carries the `checked` entry, so the check stays due on `main` until that pull request is merged. Look first: `gh pr list --state open --search 'head:deps/weekly-'` and the latest comment on the issue "Weekly dependency report" (`gh issue list --label dependencies`).
   - A `deps/weekly-*` pull request is open, or this week's comment says the run proposed nothing: the check is done. Tell the owner what waits for them (a pull request without `deps/auto-merge`, a failed merge gate, a refusal); never redo the check, and never merge the pull request yourself.
   - This week's run did not happen or failed: say so, and run the routine (section 4) by hand in this session, before other work; never wait for the next Monday. Starting the workflow (`gh workflow run deps-weekly.yml`) is the owner's call.
3. `not due` means this week's check is on `main`; `deps-due` also lists deferred updates whose `revisit_on` date has arrived, which are due now regardless of the weekday. (`scripts/deps-ledger.py due --strict` exits `2` when not due, for scripts; the workflow's `due` job uses it.)
4. A failed Security Audit run or a Dependabot alert on a pull request is handled at once, on any day, with the same routine narrowed to that dependency.

`make deps-due` costs one file read and prints one line, so it is cheap to run on every session start (AGENTS.md section 6 asks for exactly that).

## 4. The routine (`make deps-check` runs steps 1 to 3)

The workflow's agent follows `.github/deps-weekly-prompt.md`, which sends it through these steps. It cannot commit: it leaves the change in the working tree and writes a summary, and the later jobs test, commit and open the pull request. It may not change `.github/`, `.claude/`, `.agents/`, the hooks, any `AGENTS.md` or `CLAUDE.md`, `docs/architecture/doc-map.toml`, `scripts/`, the `Makefile`, `tests/test_deps_*.py` or fnox files: the change is refused when it does. Its container runs no npm or pnpm install script (the Claude token is in it); the verify job runs them. A change beyond pins (any changed line that is not a version or image reference: `python3 scripts/deps-impact.py pins-only` on the staged change says which file) must update a document `docs/architecture/doc-map.toml` maps to it, or verify refuses it; a change of pins only gets the `Docs-Not-Needed` line from the workflow.


1. **Scan**: `make deps-scan` (`deps-ledger.py scan`) shows direct dependencies that changed since the ledger was written and new or removed ones, and `pnpm.overrides` entries that were added, removed or changed (key or value).
2. **Outdated**: `make deps-outdated` lists newer versions of direct dependencies (Go: `go list -m -u`; pnpm apps: `pnpm outdated`; Observatory: `uv pip list --outdated` in its `.venv`). Docker base images, compose images, CI service images, workflow images and GitHub Actions are listed with their pins only; check their upstream releases and update the pins by hand.
3. **Audit**: `make deps-audit` runs what the Security Audit workflow runs: `pnpm audit --audit-level high` per app (the docs site's job is advisory, like `blocking: false` in the workflow), `pip-audit` on the Observatory lock with the workflow's `--ignore-vuln` list, `govulncheck ./...`, and Trivy when it is installed.
4. **Decide**, for every newer version and every advisory, with the rules in section 5.
5. **Apply** the updates (section 7), grouped by ecosystem, smallest risk first; after each group run `make deps-impact ARGS="--base <base>"` (`scripts/deps-impact.py run`, the checks the change affects, section 6) and fix what fails until it passes. Record each update: `scripts/deps-ledger.py record --ecosystem <key> --name <pkg> --from <old> --to <new> --note "<why>"`; add `--transitive` for a package forced through `pnpm.overrides`.
6. **Defer** what cannot be done safely now (section 5): `scripts/deps-ledger.py defer --ecosystem <key> --name <pkg> --from <old> --to <new> --reason "<what breaks>"` (revisit in 14 days by default, `--days` to change).
7. **Close** the check: `make deps-scan-record` (writes the scanned state into the ledger) and `scripts/deps-ledger.py checked --note "<one line>"`. The last impact run must pass on the final tree. By hand, commit as `chore(deps): <what changed>` with the ledger, the manifests and the lockfiles in the same commit, and put `make deps-report` and `make deps-classify ARGS="--markdown"` into the pull request body.

## 5. Judging an update

| Situation | Decision |
| :--- | :--- |
| A **security advisory** at `high` or `critical` on a blocking audit (dashboard, design, Observatory, Go) | Update now, on any day. When the vulnerable package is transitive and its dependents still pin the vulnerable range, force it with `pnpm.overrides` (`">=<fixed version>"`) and verify with the app's build and tests. |
| An advisory **without a fixed release** | `defer` it with the reason "no fixed release" and the upstream it depends on; revisit in 14 days. The docs site's audit is advisory, so it never blocks. |
| A **release less than 7 days old** | Do not take it unless it fixes a known advisory (`make deps-audit`, or a CVE or GHSA in its notes that affects this repository); take the newest release that is at least 7 days old. Name every release taken inside 7 days, and the advisory it fixes, in the summary. |
| **Patch or minor** of a direct dependency, tests and builds green | Update. The merge gate (`deps-merge.yml`) merges a weekly pull request that holds only these once CI is green and the Claude review is clean (in the newest review run of that pull request into `main`, the jobs "Claude review" and "Claude review verdict" passed, and the verdict job fails unless the verdict line says no blocking findings; no thread is open). |
| **Major** of a direct dependency, or any update whose changelog lists breaking changes that touch our code (SDK signatures, config keys, runtime requirements) | Read the changelog. If the code changes are clear and bounded, make them in the same change, with tests, and update. If not, `defer` for 14 days: upstream often publishes a fix or a migration note in that time, and the team may already know the error. When the revisit date arrives, do the migration, including the code or SDK changes it needs; do not defer the same update twice without a new reason recorded. A pull request with a major update always waits for the owner's merge. |
| Docker base images, compose images | Update the tag (or the digest of the same tag); the impact run checks the references and toolchain tags, and CI's smoke job builds the images (for `deploy/selfhost` and `deploy/shared`, also their `check.sh`); `make deps-scan-record` afterwards. |
| GitHub Actions, workflow images | The pins live in `.github/workflows` (Actions, and the images in `*_IMAGE` env values and `image:` keys, ledger key `workflow-images`), which the workflow's agent may not change: it lists newer releases in its summary, and the owner (or a session the owner asks) updates the pin by hand, the new commit SHA with its `# vX.Y.Z` comment or the new tag and digest. Never `defer` these from the workflow. |
| `@mishrashardendu22/observatory-tokens` and `observatory-ui` | A new observatory-ui release copied into `src/apps/github-backup-dashboard/vendor/` (`docs/DESIGN_SYSTEM_RELEASES.md`). |

Safe means: the affected suites pass (`go test ./...` with `TEST_DATABASE_URL`, `pytest`, `pyright`, Vitest, `tsc`, Biome, the Next.js and Docusaurus builds), the Security Audit checks pass, and no behaviour the documentation promises changed.

## 6. The impact map and the classes

`scripts/deps-impact.py` (standard library only) holds the map of what a change must pass, as data at the top of the file: areas, the paths that select each, the commands each runs (copied from `ci.yml` and the apps' `package.json` scripts), and the edges between them (`node`, the pnpm and Node.js pins, selects every pnpm app; the design-system tarballs select the dashboard, design and docs sites; the dashboard's contracts and lockfile select the API client check and the dashboard). `ledger`, `docs` and `contracts` run for every change. When a new check or path belongs to an area, change the map, not the callers.

- `make deps-impact ARGS="--base HEAD"` runs the areas the working tree's changes affect; `--areas all` runs every area. It keeps going after a failure, skips a command whose optional tool is missing (never counts it as passed) and exits `1` when a command failed. The database tests, image builds, browser tests and Lighthouse are left to CI, and the output says so.
- `make deps-classify ARGS="--base <ref>"` classes every ledger and toolchain change `patch`, `minor`, `major` or `unknown` (0.x minor moves count as major; a new or removed dependency, a pre-release, a downgrade, a Go pseudo-version, an image variant change or an Action tag on another commit is `unknown`). `auto_merge` is true only when every change is patch or minor; the workflow labels its pull request `deps/auto-merge` from it, and the merge gate classifies the head commit again before it merges.
- `python3 scripts/deps-impact.py pins-only` exits `0` when every staged line is a version or image reference (the workflow then writes `Docs-Not-Needed`), else `1` with the first file that is more. Names stay, so an added, removed or renamed Go module, Python package or npm alias is more than a pin, and a value counts only when it looks like one: a semver range or `npm:` alias with a range (no `github:`, `file:`, `git+`, URL or path), a PEP 440 specifier (no direct URL), a Go version on an existing `go`, `toolchain` or `require` line, a Dockerfile `ARG *_VERSION|*_TAG` of `[A-Za-z0-9._@:/+-]`, and only the tag and digest of a `FROM` reference `registry/name:tag[@sha256:hex]`, an `ARG *_IMAGE` value or a compose `image:` value (no `${...}`, no URL): another image is more than a pin, and so is a `go` or `toolchain` line added or removed. Text in a compose block scalar, a Dockerfile heredoc body and lines inside a Dockerfile continuation (comments and blank lines included) are no pins. `python3 scripts/deps-impact.py commands --json` prints every area's command names; the weekly pull request shows only those in its impact table.

The table of areas: `docs/DEPENDENCIES.md`, "The impact map".

## 7. Applying an update per ecosystem

- **Go**: `go get <module>@<version> && go mod tidy` at the repository root (one module for the API, the MCP server and the worker). `go.mod`'s `go`/`toolchain` lines and the Dockerfiles' `golang` tag move together.
- **pnpm apps** (`src/apps/*`): prefer `pnpm update <pkg>` when the lockfile diff touches only that package. When the dependents pin a vulnerable range, or a plain update drags unrelated packages along, add `"pnpm": {"overrides": {"<pkg>": ">=<version>"}}` to `package.json` and run `pnpm install --lockfile-only`. Then `scripts/check-lockfile-integrity.sh --fix <lockfile>` (regenerating a lockfile drops the integrity hashes of the design-system tarball entries) and `pnpm install --frozen-lockfile`. Never commit an npm or yarn lockfile.
- **pnpm itself**: `corepack use pnpm@<version>` in each of `src/apps/*` and `tests/e2e` (it writes `packageManager` as `pnpm@<version>+sha512.<hex>` after checking npm's signature), then `node scripts/verify-pnpm-signature.mjs`; CI installs only the bytes with that sha512 (`.github/actions/setup-pnpm`), and the Security Audit checks the signature again on every `package.json` change and weekly.
- **Observatory** (`uv`): `uv lock --upgrade-package <pkg>` (or edit the bound in `pyproject.toml` and `uv lock`), then `uv sync`, `uv run pytest`, `uv run --with pyright pyright`.
- **Docker, GitHub Actions**: edit the `FROM` tag or the `uses:` SHA and `# vX.Y.Z` comment (`gh api repos/<owner>/<action>/commits/<tag> --jq .sha`); see section 5.

Before committing, delete local build output that is not ignored by `go vet` (`src/apps/github-backup-docs/build`, which carries copies of linked `.go` files).

## 8. Dependabot

Dependabot opens no pull requests: every entry in `.github/dependabot.yml` sets `open-pull-requests-limit: 0`, and security-update pull requests are off in the repository settings. This routine applies every update itself. Dependabot alerts stay on; an alert is handled at once (section 3, item 4). To turn the pull requests back on, remove `open-pull-requests-limit: 0` from an entry.

## 9. Commands

```bash
make deps-due            # is the weekly check due? also lists deferred updates to revisit (--strict: exit 2 when not)
make deps-check          # scan + outdated + audit, in one run
make deps-scan           # manifests vs ledger
make deps-scan-record    # write the manifests' state into the ledger
make deps-outdated       # newer versions (network)
make deps-audit          # the Security Audit workflow's checks, locally
make deps-report         # Markdown summary for a pull request body
make deps-impact         # the checks the changes affect (ARGS="--base HEAD", "--areas all")
make deps-classify       # patch/minor/major/unknown per change, and whether it may merge by itself
scripts/deps-ledger.py record|defer|resolve|checked ...   # see --help
gh workflow run deps-weekly.yml [-f dry_run=true] [-f only=<ecosystem keys>]   # the weekly update, when the owner asks
```

`--today YYYY-MM-DD` on any command records or evaluates another day (used by the tests).
