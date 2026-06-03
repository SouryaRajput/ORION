"""
ORION Autonomous Agent Loop (ReAct Pattern)
Reason + Act loop: the LLM thinks step-by-step, decides which tool to use,
observes the result, and repeats until the goal is achieved.
"""

import os
import re
import json
import time
import requests
from typing import Optional, Callable

from dotenv import load_dotenv
load_dotenv()


class AgentLoop:
    """
    Core autonomous reasoning engine using the ReAct pattern.
    The LLM observes → thinks → acts → observes in a loop.
    """

    def __init__(self, goal: str, max_steps: int = 20, speak_fn: Optional[Callable] = None):
        if not goal.strip():
            raise ValueError("Agent goal cannot be empty.")
        self.goal = goal
        self.max_steps = max(1, min(max_steps, 20))
        self.speak_fn = speak_fn
        self.scratchpad = []        # List of {thought, action, input, observation}
        self.step = 0
        self.cancelled = False
        self._start_time = None
        self._recent_actions = []

    def run(self) -> str:
        """Execute the ReAct loop. Returns the final answer string."""
        self._start_time = time.time()

        # Load relevant memories for context
        memories = ""
        try:
            from memory.context import build_memory_context
            memories = build_memory_context(self.goal) or ""
        except Exception:
            pass

        # Get tool descriptions
        from agents.tool_registry import ToolRegistry
        tool_descriptions = ToolRegistry.get_tool_descriptions()

        from agents.prompts import get_react_system_prompt
        system_prompt = get_react_system_prompt(tool_descriptions)

        for self.step in range(self.max_steps):
            if self.cancelled:
                return "Task was cancelled by user."

            # Build the full prompt with scratchpad history
            user_prompt = self._build_user_prompt(memories)

            # Ask the LLM for the next action
            decision = self._think(system_prompt, user_prompt)

            if decision is None:
                return self._force_summarize()

            # Check for final answer
            if decision.get("final_answer"):
                answer = decision["final_answer"]
                elapsed = time.time() - self._start_time
                print(f"[AGENT] Goal achieved in {self.step + 1} steps ({elapsed:.1f}s)")
                return answer

            # Extract action
            action = decision.get("action", "")
            action_input = decision.get("action_input", {})
            thought = decision.get("thought", "")
            if not action or not isinstance(action_input, dict):
                print("[AGENT] Invalid action payload from planner.")
                return self._force_summarize()

            signature = json.dumps([action, action_input], sort_keys=True)
            self._recent_actions.append(signature)
            self._recent_actions = self._recent_actions[-3:]
            if len(self._recent_actions) == 3 and len(set(self._recent_actions)) == 1:
                print(f"[AGENT] Stopping repeated action loop: {action}")
                return self._force_summarize()

            print(f"[AGENT] Step {self.step + 1}: planning {action}...")
            print(f"[AGENT]   → {action}({json.dumps(action_input)[:100]})")

            # Execute the tool
            observation = ToolRegistry.execute(action, **action_input)
            observation_str = str(observation)[:3000]  # Cap observation size

            print(f"[AGENT]   ← {observation_str[:120]}...")

            # Record to scratchpad
            self.scratchpad.append({
                "step": self.step + 1,
                "thought": thought,
                "action": action,
                "action_input": action_input,
                "observation": observation_str
            })

            # Progress update to user (every 4 steps)
            if self.speak_fn and (self.step + 1) % 4 == 0:
                try:
                    self.speak_fn(f"Still working on it... step {self.step + 1}.")
                except Exception:
                    pass

        # Hit max steps — force a summary
        return self._force_summarize()

    def _build_user_prompt(self, memories: str) -> str:
        """Build the user-facing prompt with goal, memories, and scratchpad."""
        parts = [f"GOAL: {self.goal}"]

        if memories:
            parts.append(f"\nRELEVANT MEMORIES:\n{memories}")

        if self.scratchpad:
            parts.append("\nPREVIOUS STEPS:")
            for entry in self.scratchpad:
                parts.append(f"\nStep {entry['step']}:")
                parts.append(f"Thought: {entry['thought']}")
                parts.append(f"Action: {entry['action']}({json.dumps(entry['action_input'])})")
                parts.append(f"Observation: {entry['observation'][:1500]}")

            parts.append("\nNow decide your next step. If you have enough information, provide your final_answer.")
        else:
            parts.append("\nBegin working on this goal. Decide your first action.")

        return "\n".join(parts)

    def _think(self, system_prompt: str, user_prompt: str) -> Optional[dict]:
        """Call the LLM to decide the next action."""
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            print("[AGENT] No OPENROUTER_API_KEY set.")
            return None

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "google/gemini-2.5-flash",
                    "messages": messages,
                    "temperature": 0.2,
                    "max_tokens": 2000,
                },
                timeout=30
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"].strip()

            # Parse JSON from the response (handle markdown code blocks)
            content = re.sub(r'```json\s*', '', content)
            content = re.sub(r'```\s*', '', content)

            # Find the JSON object
            match = re.search(r'\{[\s\S]*\}', content)
            if match:
                return json.loads(match.group())

            print(f"[AGENT] Could not parse LLM response as JSON: {content[:200]}")
            return None

        except requests.exceptions.Timeout:
            print("[AGENT] LLM request timed out.")
            return None
        except json.JSONDecodeError as e:
            print(f"[AGENT] JSON parse error: {e}")
            return None
        except Exception as e:
            print(f"[AGENT] LLM error: {e}")
            return None

    def _force_summarize(self) -> str:
        """Force a summary when max steps are reached."""
        if not self.scratchpad:
            return "I wasn't able to complete this task."

        # Collect all observations
        all_observations = "\n\n".join(
            f"Step {e['step']} ({e['action']}): {e['observation'][:500]}"
            for e in self.scratchpad
        )

        # Use LLM to summarize
        try:
            from agents.tool_registry import ToolRegistry
            summary = ToolRegistry.execute(
                "llm_analyze",
                prompt=f"Summarize the following research into a clear, concise answer for the goal: {self.goal}",
                data=all_observations[:4000]
            )
            return summary
        except Exception:
            return f"Completed {len(self.scratchpad)} steps but could not produce a final summary. Raw findings: {all_observations[:500]}"
