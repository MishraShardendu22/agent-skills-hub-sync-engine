---
name: service-naming-standard
scope: codebase-github-backup-automation-system
description: >-
  Strict naming and directory conventions for the GitHub Backup Automation System
  applications, services, commands, containers, and deployment references.
---

# GitHub Backup Automation System Naming Standard

> [!IMPORTANT]
> **CODEBASE-SPECIFIC SCOPE**: This skill is strictly specific to the **GitHub Backup Automation System** repository.

## Canonical Product Units

Every deployable unit has a stable, product-prefixed name. Generic names such as `frontend`, `backend`, `server`, and `service` are not canonical product names.

| Responsibility | Canonical name | Canonical directory |
|---|---|---|
| Next.js dashboard | `github-backup-dashboard` | `src/apps/github-backup-dashboard/` |
| Go REST and WebSocket API | `github-backup-api` | `src/backend/github-backup-api/` |
| Python AI and RAG service | `github-backup-observatory` | `src/services/github-backup-observatory/` |
| Go scheduled backup engine | `github-backup-worker` | `src/services/github-backup-worker/` |
| Go MCP integration server | `github-backup-mcp` | `src/backend/github-backup-mcp/` |

The repository uses `src/apps/` for user-facing applications, `src/services/` for runtime workers and AI services, and `src/backend/` for the REST API and MCP integration server.

## Naming Rules

1. Deployable directories use lowercase kebab-case and begin with `github-backup-`.
2. Go command directories use the exact executable name under `cmd/`:
   - `cmd/github-backup-api/`
   - `cmd/github-backup-worker/`
   - `cmd/github-backup-mcp/`
3. Built binaries use the same canonical executable names: `github-backup-api`, `github-backup-worker`, and `github-backup-mcp`.
4. Docker Compose service keys, container names, Render service names, and CI build labels use the canonical product name.
5. Existing environment variable names remain unchanged unless a separate configuration migration explicitly requires a rename.
6. Internal Go packages use responsibility names such as `transport`, `repository`, `application`, and `domain`; avoid catch-all packages named `util`, `common`, or `misc` for new code.
7. Compatibility aliases may remain temporarily, but they must be labeled as legacy wrappers and must delegate to the canonical unit. New code must never introduce another alias.

## Forbidden New Names

Do not introduce these as names for deployable units, source roots, Docker services, or commands:

```text
frontend
backend
service
server
app
worker-service
mcp-server
agent
observatory-service
```

The existing names remain valid only as migration aliases until the repository migration is complete.

## Migration Requirements

When moving a unit to its canonical directory:

1. Update Makefile targets, Dockerfiles, Compose, Render, CI, systemd documentation, and README references in the same change.
2. Preserve stable public commands such as `make backup`.
3. Keep a legacy wrapper only when an external command or deployment depends on the old path.
4. Run `go test ./...`, `go vet ./...`, `go build ./...`, and the relevant frontend or Python validation commands.
5. Search for old names before finishing:

```bash
grep -RInE 'frontend|backend|mcp-server|agentic-observatory' \
  --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=.next .
```

Every remaining match must be either an intentional legacy compatibility reference or historical documentation.
