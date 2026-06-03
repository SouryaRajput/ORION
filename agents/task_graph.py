"""
ORION Task Graph Engine
DAG-based task decomposition and parallel execution.
Breaks complex goals into a graph of subtasks with dependencies,
then executes them in topological order with parallel independent nodes.
"""

import os
import re
import json
import time
import threading
import requests
from dataclasses import dataclass, field
from typing import Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv
load_dotenv()


@dataclass
class TaskNode:
    id: str
    description: str
    tool: str
    tool_input: dict = field(default_factory=dict)
    depends_on: list = field(default_factory=list)
    status: str = "pending"  # pending | running | done | failed
    output: Any = None
    error: Optional[str] = None


class TaskGraph:
    """
    A directed acyclic graph of tasks. Executes nodes respecting dependencies,
    running independent nodes in parallel via a thread pool.
    """

    def __init__(self, goal: str, nodes: list):
        self.goal = goal
        self._validate_nodes(nodes)
        self.nodes = {n.id: n for n in nodes}
        self.output_registry = {}  # node_id → output
        self._lock = threading.Lock()
        self.cancelled = False

    @staticmethod
    def _validate_nodes(nodes: list):
        """Reject malformed graphs before any tool can run."""
        from agents.tool_registry import ToolRegistry

        if not nodes:
            raise ValueError("Task graph must contain at least one node.")
        if len(nodes) > 12:
            raise ValueError("Task graph exceeds the 12-node execution limit.")

        node_ids = [node.id for node in nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("Task graph contains duplicate node IDs.")

        known_ids = set(node_ids)
        for node in nodes:
            if not node.id or not node.tool:
                raise ValueError("Every task node needs an ID and tool.")
            if ToolRegistry.get(node.tool) is None:
                raise ValueError(f"Node '{node.id}' references unknown tool '{node.tool}'.")
            unknown = set(node.depends_on) - known_ids
            if unknown:
                raise ValueError(
                    f"Node '{node.id}' references unknown dependencies: {sorted(unknown)}"
                )
            if node.id in node.depends_on:
                raise ValueError(f"Node '{node.id}' cannot depend on itself.")

        visiting = set()
        visited = set()
        dependencies = {node.id: node.depends_on for node in nodes}

        def visit(node_id):
            if node_id in visiting:
                raise ValueError("Task graph contains a dependency cycle.")
            if node_id in visited:
                return
            visiting.add(node_id)
            for dependency_id in dependencies[node_id]:
                visit(dependency_id)
            visiting.remove(node_id)
            visited.add(node_id)

        for node_id in node_ids:
            visit(node_id)

    def _skip_blocked_nodes(self):
        """Mark nodes blocked by failed dependencies as skipped."""
        for node in self.nodes.values():
            if node.status != "pending":
                continue
            failed_dependencies = [
                dependency_id
                for dependency_id in node.depends_on
                if self.nodes[dependency_id].status in ("failed", "skipped")
            ]
            if failed_dependencies:
                node.status = "skipped"
                node.error = (
                    "Blocked by failed dependencies: "
                    + ", ".join(failed_dependencies)
                )

    def get_ready_nodes(self) -> list:
        """Return nodes whose dependencies are all 'done'."""
        self._skip_blocked_nodes()
        ready = []
        for node in self.nodes.values():
            if node.status != "pending":
                continue
            deps_met = all(
                self.nodes[dep_id].status == "done"
                for dep_id in node.depends_on
            )
            if deps_met:
                ready.append(node)
        return ready

    def _all_done(self) -> bool:
        """Check if all nodes are in a terminal state."""
        return all(
            n.status in ("done", "failed", "skipped")
            for n in self.nodes.values()
        )

    def _resolve_refs(self, tool_input: dict) -> dict:
        """Replace {ref:node_id} placeholders with actual outputs."""
        resolved = {}
        for key, value in tool_input.items():
            if isinstance(value, str) and value.startswith("{ref:") and value.endswith("}"):
                ref_id = value[5:-1]
                resolved[key] = str(self.output_registry.get(ref_id, f"[No output from {ref_id}]"))[:3000]
            else:
                resolved[key] = value
        return resolved

    def _run_node(self, node: TaskNode) -> Any:
        """Execute a single task node."""
        from agents.tool_registry import ToolRegistry

        node.status = "running"
        print(f"[GRAPH] Running: {node.id} — {node.description}")

        try:
            resolved_input = self._resolve_refs(node.tool_input)
            result = ToolRegistry.execute(node.tool, **resolved_input)
            if isinstance(result, str) and result.startswith("Error"):
                raise RuntimeError(result)
            node.output = result
            node.status = "done"

            with self._lock:
                self.output_registry[node.id] = result

            print(f"[GRAPH] Done: {node.id} ({str(result)[:80]}...)")
            return result

        except Exception as e:
            node.status = "failed"
            node.error = str(e)
            print(f"[GRAPH] Failed: {node.id} — {e}")
            return f"Error: {e}"

    def execute(self, on_progress=None, max_workers=4) -> dict:
        """
        Execute the full DAG with parallel independent nodes.
        Returns the output_registry mapping node_id → result.
        """
        start = time.time()
        print(f"[GRAPH] Executing task graph for: {self.goal}")
        print(f"[GRAPH] {len(self.nodes)} nodes, max {max_workers} parallel workers")

        max_workers = max(1, min(max_workers, 4, len(self.nodes)))
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            iteration = 0
            while not self._all_done() and not self.cancelled:
                ready = self.get_ready_nodes()

                if not ready:
                    # Check for deadlock (no ready nodes but not all done)
                    pending = [n for n in self.nodes.values() if n.status == "pending"]
                    if pending:
                        print(f"[GRAPH] WARNING: {len(pending)} nodes stuck (dependency deadlock?).")
                        for n in pending:
                            n.status = "failed"
                            n.error = "Dependency deadlock"
                    break

                # Submit ready nodes for parallel execution
                futures = {}
                for node in ready:
                    node.status = "running"
                    futures[pool.submit(self._run_node, node)] = node

                # Wait for this batch to complete
                for future in as_completed(futures):
                    node = futures[future]
                    try:
                        future.result()
                    except Exception as e:
                        node.status = "failed"
                        node.error = str(e)

                iteration += 1
                if on_progress:
                    done_count = sum(1 for n in self.nodes.values() if n.status == "done")
                    on_progress(done_count, len(self.nodes))

        elapsed = time.time() - start
        done_count = sum(1 for n in self.nodes.values() if n.status == "done")
        print(f"[GRAPH] Complete: {done_count}/{len(self.nodes)} nodes in {elapsed:.1f}s")

        return self.output_registry

    def get_summary(self) -> str:
        """Get a human-readable summary of the graph execution."""
        lines = [f"Task Graph: {self.goal}"]
        for node in self.nodes.values():
            status_icon = {"done": "✅", "failed": "❌", "skipped": "⏭", "running": "🔄", "pending": "⏳"}.get(node.status, "?")
            output_preview = str(node.output)[:80] if node.output else (node.error or "—")
            lines.append(f"  {status_icon} {node.id}: {node.description} → {output_preview}")
        return "\n".join(lines)


def decompose_goal(goal: str) -> Optional[TaskGraph]:
    """
    Use the LLM to decompose a complex goal into a TaskGraph DAG.
    Returns None if decomposition fails.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("[GRAPH] No OPENROUTER_API_KEY.")
        return None

    from agents.tool_registry import ToolRegistry
    from agents.prompts import get_decompose_prompt

    tool_descriptions = ToolRegistry.get_tool_descriptions()
    system_prompt = get_decompose_prompt(tool_descriptions)

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "google/gemini-2.5-flash",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Goal: {goal}"}
                ],
                "temperature": 0.2,
                "max_tokens": 2000,
            },
            timeout=20
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"].strip()

        # Parse JSON
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*', '', content)
        match = re.search(r'\{[\s\S]*\}', content)
        if not match:
            print(f"[GRAPH] Could not parse decomposition: {content[:200]}")
            return None

        data = json.loads(match.group())
        nodes = []
        for node_data in data.get("nodes", []):
            nodes.append(TaskNode(
                id=node_data["id"],
                description=node_data.get("description", ""),
                tool=node_data.get("tool", "llm_analyze"),
                tool_input=node_data.get("tool_input", {}),
                depends_on=node_data.get("depends_on", [])
            ))

        if not nodes:
            return None

        graph = TaskGraph(goal=goal, nodes=nodes)
        print(f"[GRAPH] Decomposed into {len(nodes)} nodes")
        return graph

    except Exception as e:
        print(f"[GRAPH] Decomposition error: {e}")
        return None


def execute_goal_as_graph(goal: str, speak_fn=None) -> str:
    """
    High-level function: decompose a goal into a task graph and execute it.
    Falls back to the AgentLoop if decomposition fails.
    """
    graph = decompose_goal(goal)

    if graph is None:
        # Fallback to sequential agent loop
        from agents.autonomous import AgentLoop
        agent = AgentLoop(goal=goal, speak_fn=speak_fn)
        return agent.run()

    # Execute the graph
    def _progress(done, total):
        if speak_fn and done > 0 and done % 2 == 0:
            speak_fn(f"Making progress... {done} of {total} steps done.")

    results = graph.execute(on_progress=_progress)

    # Synthesize results using the final node or LLM
    if results:
        # Combine all outputs for final synthesis
        from agents.tool_registry import ToolRegistry
        all_data = "\n\n".join(
            f"[{node_id}]: {str(output)[:1000]}"
            for node_id, output in results.items()
        )

        final_answer = ToolRegistry.execute(
            "llm_analyze",
            prompt=f"Synthesize the following research data into a comprehensive, polished answer for: {goal}. "
                   f"Be thorough but concise. Use natural language suitable for voice.",
            data=all_data[:6000]
        )
        return final_answer

    return "I completed the task graph but could not produce results."
