---
name: worker-setup-and-logins
scope: codebase-github-backup-automation-system
description: >-
  Runbook for installing and scheduling the backup worker (make setup, scripts/setup.sh) and for its logins
  (GitHub App manifest, device flow, destination and OpenRouter logins, the keychain-backed credential store).
---

# Backup Worker Setup & Logins

> [!IMPORTANT]
> **CODEBASE-SPECIFIC SCOPE**: This skill is strictly specific to the **GitHub Backup Automation System** (`github-backup-automation-system`) backup worker in `src/services/github-backup-worker/`.

---

## 1. Commands

| Task | Command |
| :--- | :--- |
| Install on a machine (build, login offer, schedule) | `make setup` (`scripts/setup.sh install`; `ARGS=--dry-run`, `ARGS="--generate-only DIR"`, `ARGS="--scheduler systemd\|launchd\|cron"`) |
| Update, status, uninstall | `make update`, `make status`, `make uninstall` (`ARGS=--purge-credentials`) |
| Register the GitHub App (once per owner) | `make github-app` (`ORG=<org>`), then enable Device Flow and install the app as printed |
| GitHub login | `make login-github` (`ARGS=--from-gh`, `ARGS="--profile destination --from-gh"`, `ARGS="--store file"`) |
| OpenRouter login | `make login-openrouter` (`ARGS=--no-browser`); `github-backup-worker auth token openrouter` prints the key |
| Inspect | `github-backup-worker auth status` (never prints secrets), `github-backup-worker version` |
| Windows | `scripts/setup.ps1` (untested) |

The human runs these. Agents must not start browser logins, write the owner's keychain, install timers or disable the legacy system timer (`/etc/systemd/system/github-backup.timer`) on their own; the scripts never run `sudo`.

## 2. Architecture

- `credentials/`: the store. Secrets go to the OS keychain through `github.com/zalando/go-keyring` (service `github-backup`, keys `github:source`, `github:destination`, `openrouter:default`); without a keychain, or with `--store file`, to `credentials.json` (0600, directory 0700) in `config.Dir()` (`os.UserConfigDir()/github-backup`). `credentials.json` also indexes every login without keychain secrets. Keychain calls time out (`config.KeychainTimeout`).
- `githubauth/`: device flow and refresh (`github.com/login/...`, `GITHUB_SERVER_URL`), `gh auth token` import, and `StoredTokens`, the run's `config.TokenProvider` (stored login first, `EnvTokens` only when nothing is stored, refresh before `config.TokenRefreshMargin`, rotated refresh tokens stored again, a bad_refresh_token re-reads the store).
- `githubapp/`: `manifest.json` (public, contents and metadata read, no webhook) and the manifest flow; `github-app.json` holds the app's client id and secret (the private key and webhook secret are dropped).
- `openrouter/`: PKCE login; `internal/loopback` serves the local callback pages (Host-checked), `internal/browser` opens pages.
- `internal/app/githubaccess.go`: how a run uses the logins: installation discovery (`discovery.Lister.Installations`) for GitHub App tokens with `GITHUB_DISCOVERY=auto`, the private-destination check tokens, and the destination login as a scoped `gitexec.BasicAuthHeader` for an `https://` `BACKUP_REPO_PATH`.

## 3. Invariants

1. A stored login that cannot be read fails the run; never fall back to environment tokens (it would list less and mark repositories missing).
2. No installation is an error, never an empty listing.
3. Tokens never appear in argv, URLs, `.git/config`, logs or `auth status`.
4. Scheduled units call `%h/.local/bin/github-backup-worker` in the worker directory. A coordinated machine (`DATABASE_URL` in the repository's root `.env`, or linked) whose worker has schedule slots (its `run --help` names "schedule slot") gets one hourly `run --scheduled` at a minute fixed per machine, which backs up at the account's slot and serves requested runs; otherwise the weekly `run --scheduled` plus the hourly `run --pending-only`, and a plain `run` with no hourly job when the built worker lacks those flags. Re-running setup moves a machine between the two (after linking, unlinking or adding a database: `make update`).
5. `scripts/setup.sh` stays bash 3.2 portable (no associative arrays, `mapfile`, `${var,,}`, `sed -i`, `readlink -f`, `date -d`), prints every change under `--dry-run` and writes nothing.

## 4. Testing

```bash
go test -race ./src/services/github-backup-worker/...   # keyring.MockInit, httptest fakes, fake HOME
bash tests/setup_script_test.sh                          # also re-runs itself in the bash:3.2 image when present
```

Tests must never reach the real keychain (call `keyring.MockInit()` in `TestMain` of any package that opens the store), GitHub or OpenRouter (use `internal/fakegithub`, which also serves the GitHub App OAuth flow and installations), or real schedulers (stand-in `systemctl`, `loginctl`, `launchctl`, `crontab` on `PATH`).
