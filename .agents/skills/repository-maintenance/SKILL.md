---
name: repository-maintenance
scope: generic
description: >-
  Procedures for database schema integrity, idempotent migrations, backup/restore execution,
  and dependency maintenance.
---

# Repository Maintenance Skill

This skill provides procedures for maintaining database integrity, executing database backups, applying schema migrations, and managing dependencies across repositories.

---

## 1. Local Branch-First Development

> [!IMPORTANT]
> **CREATE A LOCAL BRANCH FIRST**: Always start by creating a dedicated local branch from `main`:
> ```bash
> git switch -c <developer-or-agent>/main/<feature-name>
> ```
> Never apply maintenance or schema changes directly on `main`.

---

## 2. Database Schema Integrity & Migrations

> [!CAUTION]
> **CRITICAL RULE**: Never execute destructive SQL statements (`DROP TABLE`, `TRUNCATE`) in production environments.

### Migration Rules
- All migrations MUST be located in a versioned migrations directory (e.g. `db/migrations/` or `migrations/`) using timestamped or numbered files (`NNNNNN_<name>.up.sql` and `NNNNNN_<name>.down.sql`).
- All SQL statements MUST be idempotent:
  - `CREATE TABLE IF NOT EXISTS ...`
  - `CREATE INDEX IF NOT EXISTS ...`
  - `ALTER TABLE ... ADD COLUMN IF NOT EXISTS ...`
- A catalog check (`information_schema`) names the schema it inspects. Without that filter, a table or view of the same name in another schema answers instead.

---

## 3. Backup & Disaster Recovery Runbook

On the self-hosted machine the database is dumped by `ghb` (`deploy/selfhost/README.md#backups`): a nightly systemd timer, and a dump before every migration.

```bash
sudo ghb backup                 # dump now (to /var/backups/ghb, 14 kept)
sudo ghb restore latest         # or: sudo ghb restore <file>
```

Encrypted copies in S3-compatible storage (`BACKUP_S3_*`) are restored with `deploy/shared/db-backup/restore.sh` ([`deploy/shared/README.md`](../../../deploy/shared/README.md#restore-a-dump)).

---

## 4. Dependency Management

- **Go Dependencies**: Managed via `go.mod`. Update with `go get -u` and clean with `go mod tidy`.
- **Python Dependencies**: Managed via `uv`. Update with `uv lock --upgrade` and sync with `uv sync`.
- **Frontend Dependencies**: Managed via `pnpm`. Update with `pnpm update`. Ensure lockfiles remain frozen in CI.
