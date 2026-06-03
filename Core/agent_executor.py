"""
Dynamic Agent Executor — Gives ORION the ability to perform actions 
that are NOT hardcoded, by generating and executing shell commands or 
Python snippets via LLM reasoning.

Safety: All commands require spoken confirmation before execution unless
they are read-only (e.g., `curl`, `cat`, `echo`, `ls`, `which`, `ifconfig`).
"""

import os
import re
import json
import subprocess
import requests
from typing import Optional

from study.utils.logger import get_logger

log = get_logger("agent_executor")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
MODEL_NAME = "google/gemini-2.5-flash"

# Commands that are safe to run without user confirmation
SAFE_PREFIXES = (
    "echo ", "cat ", "ls ", "pwd", "whoami", "which ", "where ",
    "ifconfig", "curl -s", "curl --silent", "dig ", "nslookup ",
    "date", "uname", "python3 -c \"import", "python3 -c 'import",
    "hostname", "printenv", "defaults read",
)
SHELL_CONTROL_TOKENS = (";", "&&", "||", "|", "`", "$(", "\n", "\r", ">", "<")

AGENT_SYSTEM_PROMPT = """You are ORION's action planner. The user has asked you to perform a real-world task on their macOS computer.

Your job is to:
1. Break the task into concrete executable steps.
2. For each step, provide the EXACT shell command to run.
3. Explain what each step does in plain English.

RULES:
- You are running on macOS (zsh shell).
- You have access to: curl, python3, pip3, osascript, defaults, networksetup, security, etc.
- For API interactions (like MongoDB Atlas), use curl with their REST API.
- To search the web, read news, or fetch information, DO NOT just open a browser window. Instead, write a short `python3 -c` script to fetch an RSS feed (e.g. Google News RSS), use an API, or scrape the content using requests/BeautifulSoup, and print the results so you can summarize them for the user.
- Only use `open "https://url"` if the user EXPLICITLY asks you to "open the browser" or "open Chrome".
- If a task genuinely requires credentials you don't have, say so clearly.
- Prefer single-line commands. Use python3 -c for complex logic.
- NEVER delete files, format disks, or do anything destructive without extreme caution.
- If the task is impossible from a terminal, explain why and suggest alternatives.

ENVIRONMENT VARIABLES AVAILABLE:
- OPENROUTER_API_KEY (for AI APIs)
- Any .env vars the user has configured

OUTPUT FORMAT — return ONLY this JSON:
{
  "feasible": true,
  "explanation": "One sentence explaining the approach",
  "steps": [
    {
      "description": "What this step does",
      "command": "the exact shell command",
      "safe": true
    }
  ],
  "needs_info": null
}

If you need information from the user first (e.g., an API key, a project name), set:
{
  "feasible": false,
  "explanation": "What I need from you",
  "steps": [],
  "needs_info": "What specific info is needed"
}
"""


def plan_action(user_request: str) -> Optional[dict]:
    """
    Ask the LLM to generate an action plan for a user request.
    Returns a dict with steps, or None on failure.
    """
    if not OPENROUTER_API_KEY:
        log.error("No OPENROUTER_API_KEY set.")
        return None

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL_NAME,
                "messages": [
                    {"role": "system", "content": AGENT_SYSTEM_PROMPT},
                    {"role": "user", "content": user_request},
                ],
                "temperature": 0.1,
                "max_tokens": 1500,
                "response_format": {"type": "json_object"},
            },
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()
        plan = json.loads(content)
        log.info(f"Action plan generated: {plan.get('explanation', '')}")
        return plan
    except Exception as e:
        log.error(f"Action planning failed: {e}")
        return None


def is_command_safe(command: str) -> bool:
    """Check if a command is read-only and safe to auto-execute."""
    cmd_stripped = command.strip()
    if not cmd_stripped or any(token in cmd_stripped for token in SHELL_CONTROL_TOKENS):
        return False
    return any(cmd_stripped.startswith(prefix) for prefix in SAFE_PREFIXES)


def execute_command(command: str, timeout: int = 30) -> dict:
    """
    Execute a single shell command and return the result.
    Returns: {"success": bool, "output": str, "error": str}
    """
    log.info(f"Executing: {command}")
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.path.expanduser("~"),
        )
        output = result.stdout.strip()
        error = result.stderr.strip()

        if result.returncode == 0:
            log.info(f"Success: {output[:200]}")
            return {"success": True, "output": output, "error": ""}
        else:
            log.warning(f"Command failed (code {result.returncode}): {error}")
            return {"success": False, "output": output, "error": error}

    except subprocess.TimeoutExpired:
        log.error(f"Command timed out after {timeout}s")
        return {"success": False, "output": "", "error": "Command timed out."}
    except Exception as e:
        log.error(f"Execution error: {e}")
        return {"success": False, "output": "", "error": str(e)}


def summarize_results(user_request: str, steps_results: list[dict]) -> str:
    """
    Ask the LLM to summarize execution results into a short spoken response.
    """
    results_text = "\n".join(
        f"Step {i+1}: {r['description']}\n"
        f"  Command: {r['command']}\n"
        f"  Result: {'✅ ' + r['output'][:300] if r['success'] else '❌ ' + r['error'][:300]}"
        for i, r in enumerate(steps_results)
    )

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL_NAME,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are ORION. Summarize what happened in 1-2 natural spoken sentences. "
                            "Be conversational. If something failed, explain what went wrong briefly."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"User asked: {user_request}\n\nResults:\n{results_text}",
                    },
                ],
                "temperature": 0.3,
                "max_tokens": 100,
            },
            timeout=10,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        # Fallback: just report success/failure
        successes = sum(1 for r in steps_results if r["success"])
        total = len(steps_results)
        if successes == total:
            return "Done. All steps completed successfully."
        else:
            return f"Partially done. {successes} out of {total} steps succeeded."


def execute_action(user_request: str, confirm_fn=None, speak_fn=None) -> str:
    """
    Full pipeline: plan → confirm → execute → summarize.

    Args:
        user_request: What the user asked ORION to do.
        confirm_fn: Optional callable that returns True/False for user confirmation.
                    If None, only safe commands are auto-executed.
        speak_fn: Optional callable to speak intermediate status updates.

    Returns:
        A spoken summary of what happened.
    """
    def _speak(text):
        if speak_fn:
            speak_fn(text)

    # Step 1: Plan
    plan = plan_action(user_request)

    if not plan:
        return "Sorry, I couldn't figure out how to do that."

    if not plan.get("feasible", False):
        needs = plan.get("needs_info", "")
        explanation = plan.get("explanation", "I need more information.")
        return f"{explanation} {needs}".strip()

    steps = plan.get("steps", [])
    if not steps:
        return plan.get("explanation", "I'm not sure how to do that.")

    # Step 2: Announce
    _speak(plan.get("explanation", "Let me work on that."))

    # Step 3: Execute each step
    results = []
    for i, step in enumerate(steps):
        cmd = step.get("command", "")
        desc = step.get("description", f"Step {i+1}")
        if not cmd:
            continue

        # Safety check
        # The planner cannot grant itself permission by setting safe=true.
        auto_safe = is_command_safe(cmd)

        if not auto_safe:
            if confirm_fn:
                _speak(f"I need to run: {desc}. Should I go ahead?")
                if not confirm_fn():
                    results.append({
                        "description": desc,
                        "command": cmd,
                        "success": False,
                        "output": "",
                        "error": "Skipped by user.",
                    })
                    continue
            else:
                # No confirmation function — skip unsafe commands
                log.warning(f"Skipping unsafe command (no confirm_fn): {cmd}")
                results.append({
                    "description": desc,
                    "command": cmd,
                    "success": False,
                    "output": "",
                    "error": "Skipped: requires confirmation.",
                })
                continue

        # Execute
        result = execute_command(cmd)
        result["description"] = desc
        result["command"] = cmd
        results.append(result)

        # If a step fails, stop and report
        if not result["success"]:
            break

    # Step 4: Summarize
    return summarize_results(user_request, results)
