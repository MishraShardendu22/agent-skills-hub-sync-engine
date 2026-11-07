---
name: agentic-observatory-workflow
scope: codebase-github-backup-automation-system
description: >-
  Specific procedures for developing, extending, and testing the Python AI Observatory service in github-backup-automation-system (tools, pgvector, HITL, OpenRouter pool).
---

# Agentic Observatory Service Workflow

> [!IMPORTANT]
> **CODEBASE-SPECIFIC SCOPE**: This skill is strictly specific to the **GitHub Backup Automation System** (`github-backup-automation-system`). It guides agents on modifying and extending `src/services/github-backup-observatory/`.

---

## 1. Adding a Tool to the Observatory Agent

1. Implement the tool in `src/services/github-backup-observatory/data/tools/`:
   ```python
   from typing import Annotated, Any
   from langchain_core.tools import tool

   @tool
   async def inspect_backup_metric(
       metric_name: Annotated[str, "Name of the operational metric"],
       limit: Annotated[int, "Number of data points"] = 10,
   ) -> dict[str, Any]:
       """Query operational metrics from the PostgreSQL database."""
       return {"metric": metric_name, "count": limit}
   ```
2. Export the tool in `src/services/github-backup-observatory/data/tools/__init__.py`.
3. Register the tool in `TOOLS` within `src/services/github-backup-observatory/agent/openrouter.py`.

Never add a tool that sends e-mail or any other message out of the product (ADR 0020). A report is the agent's answer: the system prompt (`agent/prompts.py`) tells the model to write it in the chat and point to the message's Download button. `POST /reports` only stores a report, which `GET /reports/{id}/download` returns to clients that call the Observatory directly (the dashboard's proxy does not forward `/reports`).

---

## 2. Tool-Calling RAG & Knowledge Base Search

The Observatory agent calls `hybrid_search_knowledge_base` during reasoning loops:
- **Source Filters**: `['run_failure', 'backup_result', 'backup_fix', 'investigation']` (older chunks may also be `execution_log` or `chat_message`). Since B7a (ADR 0008) only failures, failed results, fixes and completed investigations are indexed, and search reads only the index.
- **Indexing**: background jobs on `public.platform_jobs` (ADR 0013, `services/job_runner.py`, `services/indexing_jobs.py`): handlers return the jobs to queue, act for the account their payload names, and read runs only through the insights API; jobs carry their text (`000029`). A new source is a builder in `data/index_sources.py` plus the write that queues it.
- **LLM caps**: every OpenRouter call goes through `call_with_failover`, which holds a slot of its purpose (`utils/llm_limits.py`); background work runs inside `llm_limits.background()`.
- **Hybrid Algorithm**: PostgreSQL Full-Text Search (`tsvector`) + pgvector cosine similarity + Reciprocal Rank Fusion (RRF).

---

## 3. Human-In-The-Loop (HITL) Confirmations

Sensitive actions (tools in `CONFIRMATION_REQUIRED_TOOLS` in `agent/openrouter.py`; the set is empty today, and the tests register the test-only tool `publish_test_note` through the `gated_tool` fixture) require user confirmation:
1. `stream_agent()` stores a pending row with `data.confirmations.create_confirmation()` (table `ai_tool_confirmations`: `confirm_id`, `session_id`, `username`, `tool_name`, `args`, `status`, `created_at`, `decided_at`) and yields:
   ```json
   {"type": "confirm_required", "confirm_id": "<uuid>", "name": "<tool name>", "args": {}, "tool_call_id": "<id>"}
   ```
2. The dashboard answers with `POST /chat/confirm` and `{"confirm_id": "<uuid>", "approve": true}` (`approved` is an accepted alias; keep `approve`, the deployed dashboard sends it). `data.confirmations.decide()` only lets the user who started the turn decide.
3. The stream waits with `wait_for_decision(confirm_id, timeout=HITL_CONFIRMATION_TIMEOUT_SECONDS, poll_interval=HITL_POLL_INTERVAL_SECONDS)`. A timeout or a disconnect marks the row `expired`, which counts as rejected; the tool then ends with `tool_end` and `success: false`.
4. `POST /chat` and `POST /api/tools/execute` refuse these tools.

Every event of one tool call carries the same `tool_call_id` (`ensure_tool_call_ids()` fills in a UUID when the model sent none). Keep the SSE shapes additive; the dashboard depends on them (`docs/STREAMING_ARCHITECTURE.md`).

---

## 4. Multi-Key OpenRouter Failover

Centralized in `src/services/github-backup-observatory/utils/openrouter_keys.py`:
- `OpenRouterCredentials`: the keys one request may use, resolved per request by `services.openrouter_accounts.resolve_credentials(username)` (the user's own key, else `server_credentials()`).
- `call_with_failover(credentials, operation, purpose=...)`: runs `operation(key)`; moves to the next server key only on `401`, `402` or `429`. A `400` raises `OpenRouterRequestRejected`; a user key is never rotated (`UserKeyRejected` 403, `UserKeyOutOfCredits` 402, `UserKeyRateLimited` 429).
- `use_credentials(credentials)`: sets the credentials for code that cannot take them as an argument (LangChain tools); pass them explicitly everywhere else.
- HTTP goes through `utils/openrouter_http.py` (shared clients, attribution headers, `api_url()` on `OPENROUTER_API_BASE`).

---

## 5. Database Changes

The observatory runs no DDL. New tables and indexes go into a new idempotent migration in `src/platform/dbmigrate/migrations/` (`NNNNNN_name.up.sql` plus a `.down.sql` that drops only what it created); the Go API applies it at startup. Add the table to `data/db.py` metadata only if the ORM needs it.

---

## 6. Verification & Test Suite

```bash
cd src/services/github-backup-observatory

# Unit tests (network blocked; OpenRouter and the Go backend are mocked)
uv run pytest

# Integration tests: disposable database built from the migration files
TEST_DATABASE_URL=postgres://postgres:postgres@127.0.0.1:55432/postgres uv run pytest

# Type check
uv run --with pyright pyright
```
