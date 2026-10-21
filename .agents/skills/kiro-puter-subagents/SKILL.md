---
name: kiro-puter-subagents
description: >-
  Use this skill to delegate subtasks, code refactoring, file analysis, or live web search
  to external CLI subagents (kiro-pool with multi-account rotation and puter-ai-cli/mycli).
  Contains model-selection strategies to minimize token/credit burn and handles quota limits.
scope: generic
---

# Kiro & Puter Multi-Account Subagent Delegation Guide

This skill guides the primary agent on delegating secondary tasks (code generation, file reviews, boilerplate writing, syntax checks, or live web search) to local CLI sub-agents powered by **`kiro-pool`** and **`mycli` (Puter AI CLI)**.

Both tools feature **multi-account token pools** to multiply free credits and avoid single-account rate limits.

---

## Subagent Routing Matrix: Which Engine to Choose?

| Task Requirement | Recommended Engine | Command Pattern | Why? |
|---|---|---|---|
| **Autonomous Workspace File Edits** | `kiro-pool` | `kiro-pool chat --v3 -m <model> --no-interactive --trust-all-tools "..."` | Has direct tool permissions to inspect and edit files in the workspace. |
| **Real-time Live Web Search** | `puter` (`mycli`) | `mycli ask -m gpt-4o -w "..."` | Puter has native serverless web search (`-w` / `--web-search`) with live citations. |
| **Ultra-cheap Bulk Code Generation** | `kiro-pool` | `kiro-pool chat --v3 -m qwen3-coder-next ...` | Consumes only **0.05x credits** (20x cheaper than standard models). |
| **Everyday Quick Q&A / Text Lookups** | `puter` (`mycli`) | `mycli ask -m gpt-5-nano "..."` | Near-zero token latency (< 1s), uses Puter's serverless pool. |
| **Precision Refactoring / Bug Finding** | `kiro-pool` | `kiro-pool chat --v3 -m claude-haiku-4.5 ...` | Claude Haiku 4.5 is extremely accurate on code at only **0.40x credits**. |
| **Deep Architecture / System Design** | `puter` (`mycli`) | `mycli ask -m gpt-5.4 "..."` | Full frontier GPT-5.4 reasoning capacity. |

---

## Model Selection & Credit Optimization

To avoid exhausting credits rapidly, match your subtask to the lowest-cost model that can accomplish it:

### 1. Kiro Account Pool Models (`kiro-pool`)

Kiro charges credits per request based on a model multiplier:

| Model ID | Multiplier | Credit Burn | Optimal Use Case |
|---|---|---|---|
| **`qwen3-coder-next`** | **0.05x** | Extremely low | Scaffolding repetitive boilerplate, bulk file scanning, regex generation. |
| **`minimax-m2.1`** | **0.15x** | Very low | Quick summarization, syntax formatting. |
| **`deepseek-3.2`** | **0.25x** | Low | Algorithmic logic, Python/Go/TS script generation, unit test cases. |
| **`claude-haiku-4.5`** | **0.40x** | Moderate | **Default Workhorse**: High-precision code refactoring, targeted bug hunting, diff analysis. |
| **`glm-5`** | **0.50x** | Moderate | Broad technical explanations. |
| **`claude-sonnet-4.5`** | **1.30x** | High | *Reserve for critical tasks*: Complex multi-file architectural reasoning or subtle concurrency bugs. |

> [!IMPORTANT]
> **Always use `kiro-pool` instead of `kiro-cli` directly.**  
> Running `kiro-cli` exhausts your single default account. `kiro-pool` multiplexes requests across **10 enrolled Google accounts** with auto-failover and 60-minute cooldown recovery.

### 2. Puter AI CLI Models (`mycli`)

Puter provides 1,000 monthly credits per account (currently pooled across 3 accounts = 3,000 credits):

| Model ID | Speed | Web Search? | Optimal Use Case |
|---|---|---|---|
| **`gpt-5-nano`** *(Default)* | Ultra-fast (< 1s) | No | Fast code snippets, error explanation, formatting, small helper functions. |
| **`gpt-4o`** | Fast (~2s) | **Yes (`-w`)** | Live web research, package documentation verification, balanced coding. |
| **`gpt-5.3-codex`** | High accuracy | No | Backend systems, API design, data pipeline implementations. |
| **`gpt-5.4`** | Frontier reasoning | No | Complex system architecture, performance optimization strategy. |
| **`claude-3-5-sonnet`** | High quality | No | Elegant code structure, technical documentation writing. |

---

## Execution Methods

### Option A: Using the Unified Delegation Runner (Recommended)

A helper script is provided at `scripts/delegate.py` inside this skill directory. It automatically filters out internal daemon/node logs and formats clean responses:

```bash
# 1. Quick refactor with Claude Haiku 4.5 via Kiro Pool
python3 ~/.gemini/config/skills/kiro-puter-subagents/scripts/delegate.py \
  --engine kiro \
  -m claude-haiku-4.5 \
  "Refactor the following function for readability: <code snippet>"

# 2. Ultra-cheap bulk generation with Qwen3 Coder
python3 ~/.gemini/config/skills/kiro-puter-subagents/scripts/delegate.py \
  --engine kiro \
  -m qwen3-coder-next \
  "Write mock test fixtures for the user auth endpoints."

# 3. Live Web Search with Puter AI CLI
python3 ~/.gemini/config/skills/kiro-puter-subagents/scripts/delegate.py \
  --engine puter \
  -m gpt-4o \
  -w \
  "What is the latest release version and breaking changes of Next.js?"
```

---

### Option B: Direct Shell Invocation

If calling the CLI binaries directly via `run_command`:

#### Kiro Pool Invocation
```bash
kiro-pool chat --v3 --model claude-haiku-4.5 --no-interactive --trust-all-tools "<prompt>"
```
* Note: Output may contain server progress lines (`[INFO] kas.server...`); inspect the final lines for the assistant answer.

#### Puter CLI Invocation
```bash
# Standard query
mycli ask -m gpt-5-nano "<prompt>"

# With live web search
mycli ask -m gpt-4o -w "<prompt>"

# Pipe files into Puter
cat src/config.go | mycli ask "Check this configuration for potential race conditions."
```

---

## Quota Exhaustion & Error Handling Protocol

When delegating tasks, monitor exit codes and stderr for quota exhaustion:

### 1. Kiro Account Pool Limit Exhaustion
If all accounts in `kiro-pool` are throttled or in cooldown, the command returns code 1 or 429 with:
```
[kiro-pool ERROR] All pooled accounts are currently throttled or no accounts exist.
```
**Required Action:**  
Immediately halt further Kiro calls and inform the user:
> *"The Kiro CLI multi-account pool limit is exhausted. All 10 accounts are currently in cooldown or out of credits. Please wait for the cooldown window to reset or add additional accounts via `kiro-pool add`."*  
Then seamlessly fall back to `mycli` (`gpt-5-nano` or `gpt-4o`) or Antigravity's direct tools.

### 2. Puter CLI Token Pool Exhaustion
If all tokens in Puter's rotation pool hit rate limits:
```
Error: Puter rate limit exceeded. Please wait a moment and try again.
```
**Required Action:**  
Alert the user:
> *"Puter AI CLI token pool limit is exhausted across all configured accounts."*  
Fall back to `kiro-pool` or Antigravity's built-in reasoning.
