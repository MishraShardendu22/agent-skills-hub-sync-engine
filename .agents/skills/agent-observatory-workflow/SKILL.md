---
name: agent-observatory-workflow
scope: generic
description: >-
  Step-by-step instructions for building and extending Python AI agent services: adding LangChain/LiteLLM tools,
  Tool-Calling RAG workflows, enforcing Human-in-the-Loop approvals, multi-key model failover, and pgvector embeddings.
---

# Agent Observatory & Tool-Calling RAG Workflow Guide

This skill guides agents and engineers on how to build, extend, test, and enhance AI agent services utilizing Tool-Calling RAG, LangChain/LiteLLM architectures, and pgvector embeddings.

---

## 1. Local Branch-First Development

> [!IMPORTANT]
> **CREATE A LOCAL BRANCH FIRST**: Always start by creating a dedicated local branch from `main`:
> ```bash
> git switch -c <developer-or-agent>/main/<feature-name>
> ```
> Never develop or modify agent code directly on `main`.

---

## 2. Adding a New Agent Tool

1. Create or update a tool file under your agent tools directory (e.g. `agent/tools/` or `data/tools/`):
   ```python
   from typing import Annotated, Any
   from langchain_core.tools import tool

   @tool
   async def inspect_custom_metric(
       metric_name: Annotated[str, "The name of the metric to query"],
       days: Annotated[int, "Number of lookback days"] = 7,
   ) -> dict[str, Any]:
       """Query operational metrics from the database or external API."""
       # Perform database query or API call
       return {"metric": metric_name, "value": 42}
   ```
2. Export the tool in the tools package `__init__.py`.
3. Register the tool in your central agent runner's `TOOLS` list.

---

## 3. Tool-Calling RAG & Vector Knowledge Base

The AI service operates as a **Tool-Calling RAG Agent**:
1. **Pre-turn Retrieval**: Injects top relevance chunks into system context before iteration 1.
2. **Dynamic Tool Calling**: The agent calls `hybrid_search_knowledge_base` during reasoning loops for deep evidence gathering:
   ```python
   from agent.tools import hybrid_search_knowledge_base
   ```
   * Supported source filters: `['run_failure', 'backup_result', 'backup_fix', 'investigation']` (older chunks may also be `execution_log` or `chat_message`); search reads only the index (ADR 0008).
   * Combines Full-Text Search (tsvector), pgvector cosine similarity, and Reciprocal Rank Fusion (RRF).

---

## 4. Implementing Human-In-The-Loop (HITL) Actions

For sensitive or destructive actions (e.g., dispatching external emails, modifying records, triggering external deployments):
1. Keep pending confirmations in a shared store (a database table), not in process memory: the approval request can reach a different instance or worker than the stream that waits for it.
2. In the agent loop, before running the tool, store a pending row (id, owner, tool, arguments) and emit an event that also carries the model's tool call id, so the UI can pair it with the tool's start and end events:
   ```python
   if tool_name in CONFIRMATION_REQUIRED_TOOLS:
       confirm_id = str(uuid.uuid4())
       await confirmations.create(confirm_id, username=username, tool_name=tool_name, args=tool_args)
       yield json.dumps({
           "type": "confirm_required",
           "confirm_id": confirm_id,
           "name": tool_name,
           "args": tool_args,
           "tool_call_id": tool_call_id,
       })
       # Poll this confirmation's own row; on timeout or cancellation mark it expired.
       decision = await confirmations.wait_for_decision(confirm_id, timeout=120.0, poll_interval=0.5)
   ```
3. Let only the owner decide (a decision from another user looks like an unknown id), and refuse a second decision.
4. Treat a timeout as a rejection. Feed the approval or rejection back to the LLM context to continue safely.
5. Code paths that cannot ask (non-streaming chat, direct tool execution endpoints) must refuse these tools instead of running them.

---

## 5. Multi-Key API Failover

When interacting with external LLM APIs (e.g. OpenRouter, OpenAI, Anthropic):
- Resolve the keys for each request (the user's own key, or the server pool) and pass them explicitly; never keep a process-wide "current key" that concurrent requests change.
- Rotate to the next key only on HTTP `401`, `402` or `429`. Other errors, such as `400` for a bad request, are the caller's problem and must be returned, not retried on every key.
- A user's own key is never replaced by another user's key or, unless configured, by the server pool.
- Give every call a timeout, disable hidden SDK retries, and put a deadline on the whole agent turn.

---

## 6. Comprehensive Agent Test Suites

Use pytest with the network blocked, so a test that would call a real LLM, email server or backend fails instead:
```bash
# Unit tests (HTTP mocked with respx, LLMs replaced by fakes)
uv run pytest

# Integration tests against a disposable local database
TEST_DATABASE_URL=postgres://postgres:postgres@127.0.0.1:5432/postgres uv run pytest -m integration
```
