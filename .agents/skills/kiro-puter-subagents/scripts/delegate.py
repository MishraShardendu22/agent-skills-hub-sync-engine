#!/usr/bin/env python3
"""
Unified Subagent Delegator for kiro-pool and puter-ai-cli (mycli).
Handles clean execution, multi-account routing, web search, and quota exhaustion detection.
"""

import sys
import subprocess
import argparse
import re

def clean_kiro_output(raw: str) -> str:
    """Filter internal node warnings and KAS JSON logging from stdout."""
    clean_lines = []
    for line in raw.splitlines():
        trimmed = line.strip()
        if (
            trimmed.startswith("[INFO]") or
            trimmed.startswith("[ERROR]") or
            trimmed.startswith("(node:") or
            trimmed.startswith("[kiro-pool]") or
            "GenerateAssistantResponseCommand" in trimmed or
            "acp." in trimmed or
            "KRS" in trimmed
        ):
            continue
        clean_lines.append(line)
    return "\n".join(clean_lines).strip()

def run_kiro(prompt: str, model: str = "claude-haiku-4.5") -> int:
    cmd = [
        "kiro-pool", "chat",
        "--v3",
        "--model", model,
        "--no-interactive",
        "--trust-all-tools",
        prompt
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = proc.communicate()

    # Check for pool exhaustion
    combined = (stdout + "\n" + stderr).lower()
    if "all pooled accounts are currently throttled" in combined or "no accounts exist" in combined:
        sys.stderr.write("\n[ALERT] Kiro CLI multi-account pool limit is exhausted! All accounts are in cooldown or out of credits.\n")
        return 429

    cleaned = clean_kiro_output(stdout)
    if cleaned:
        sys.stdout.write(cleaned + "\n")
    elif proc.returncode != 0:
        sys.stderr.write(stderr)

    return proc.returncode

def run_puter(prompt: str, model: str = "gpt-5-nano", web_search: bool = False) -> int:
    cmd = ["mycli", "ask", "-m", model]
    if web_search:
        cmd.append("-w")
    cmd.append(prompt)

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = proc.communicate()

    combined = (stdout + "\n" + stderr).lower()
    if "rate limit exceeded" in combined or "all tokens in pool failed" in combined or "429" in combined:
        sys.stderr.write("\n[ALERT] Puter AI CLI token pool limit is exhausted!\n")
        return 429

    if stdout:
        sys.stdout.write(stdout)
    if stderr:
        sys.stderr.write(stderr)

    return proc.returncode

def main():
    parser = argparse.ArgumentParser(description="Unified Delegator for kiro-pool and puter-ai-cli")
    parser.add_argument("--engine", choices=["kiro", "puter"], required=True, help="Engine to use: 'kiro' (kiro-pool) or 'puter' (mycli)")
    parser.add_argument("--model", "-m", default=None, help="Model name (e.g., claude-haiku-4.5, qwen3-coder-next, gpt-5-nano, gpt-4o)")
    parser.add_argument("--web", "-w", action="store_true", help="Enable real-time web search (Puter engine)")
    parser.add_argument("prompt", help="Prompt or task instructions to delegate")

    args = parser.parse_args()

    if args.engine == "kiro":
        model = args.model or "claude-haiku-4.5"
        code = run_kiro(args.prompt, model=model)
    else:
        model = args.model or "gpt-5-nano"
        code = run_puter(args.prompt, model=model, web_search=args.web)

    sys.exit(code)

if __name__ == "__main__":
    main()
