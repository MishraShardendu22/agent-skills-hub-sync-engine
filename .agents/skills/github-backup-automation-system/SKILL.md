---
name: github-backup-automation-system
scope: codebase-github-backup-automation-system
description: >-
  System architecture, inter-service topology, database schemas, and AI observatory development runbooks for the GitHub Backup Automation System monorepo.
---

# GitHub Backup Automation System — AI Agent Skills Suite

> [!IMPORTANT]
> **CODEBASE-SPECIFIC SCOPE**: These skills are strictly specific to the **GitHub Backup Automation System** (`github-backup-automation-system`). They provide concrete architecture topologies, service boundaries, and AI agent observatory runbooks for this codebase.

---

## Skills Catalog

This directory contains the following dedicated skills:

| Skill File | Scope | Domain | Description |
| :--- | :--- | :--- | :--- |
| [`github-backup-architecture.md`](github-backup-architecture.md) | `codebase-github-backup-automation-system` | System Architecture | End-to-end system topology, service responsibilities (`src/apps/github-backup-dashboard`, `src/services/github-backup-observatory`, `src/backend/github-backup-api`, `src/services/github-backup-worker`, `src/backend/github-backup-mcp`), PostgreSQL database schema, and the CI/CD workflows, images, compose smoke test and env files. |
| [`agentic-observatory-workflow.md`](agentic-observatory-workflow.md) | `codebase-github-backup-automation-system` | AI Observatory | Adding tools to `src/services/github-backup-observatory/data/tools/`, Tool-Calling RAG workflows, HITL email alerts, and OpenRouter multi-key pool failover. |
| [`service-naming-standard.md`](service-naming-standard.md) | `codebase-github-backup-automation-system` | Naming & Layout | Canonical product names, source directories, commands, containers, and migration rules. |
| [`dependency-maintenance.md`](dependency-maintenance.md) | `codebase-github-backup-automation-system` | Dependency Maintenance | The dependency ledger (`docs/dependencies/ledger.json`, `scripts/deps-ledger.py`), the weekly Monday check caught up on the next run, how updates are judged safe, the two-week deferral of breaking updates and their migration. |
| [`worker-setup-and-logins.md`](worker-setup-and-logins.md) | `codebase-github-backup-automation-system` | Worker Setup & Logins | `make setup` scheduling per OS, the GitHub App and device-flow logins, the keychain credential store, and their invariants and tests. |
