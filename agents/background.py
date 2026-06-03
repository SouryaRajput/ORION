"""
ORION Background Task Manager
Runs autonomous agent tasks in background threads while keeping the voice loop responsive.
Supports task submission, cancellation, status queries, and voice notifications.
"""

import threading
import time
import uuid
import os
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Optional, Callable


@dataclass
class BackgroundTask:
    id: str
    name: str
    goal: str
    status: str = "pending"       # pending | running | done | failed | cancelled
    result: Optional[str] = None
    priority: str = "normal"      # urgent | normal
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    execution_mode: str = "graph"
    _agent: Optional[object] = field(default=None, repr=False)
    _future: Optional[Future] = field(default=None, repr=False)


class BackgroundManager:
    _tasks: dict = {}
    _lock = threading.Lock()
    _pending_notifications: list = []
    _notify_fn: Optional[Callable] = None
    _executor = ThreadPoolExecutor(
        max_workers=max(1, int(os.getenv("BACKGROUND_MAX_WORKERS", "2"))),
        thread_name_prefix="bg"
    )
    _max_retained_tasks = max(10, int(os.getenv("BACKGROUND_MAX_RETAINED_TASKS", "200")))

    @classmethod
    def _prune_completed_locked(cls):
        completed = sorted(
            (
                task for task in cls._tasks.values()
                if task.status in ("done", "failed", "cancelled")
            ),
            key=lambda task: task.completed_at or task.created_at
        )
        overflow = len(cls._tasks) - cls._max_retained_tasks
        for task in completed[:max(0, overflow)]:
            cls._tasks.pop(task.id, None)

    @classmethod
    def set_notify_fn(cls, fn: Callable):
        """Set the voice notification function (speak_audio)."""
        cls._notify_fn = fn

    @classmethod
    def submit(
        cls,
        name: str,
        goal: str,
        priority: str = "normal",
        execution_mode: str = "graph"
    ) -> str:
        """Submit a goal for background execution. Returns task_id."""
        if not goal.strip():
            raise ValueError("Background task goal cannot be empty.")
        if priority not in ("urgent", "normal"):
            raise ValueError("Background task priority must be 'urgent' or 'normal'.")
        if execution_mode not in ("graph", "react"):
            raise ValueError("Execution mode must be 'graph' or 'react'.")

        task_id = str(uuid.uuid4())[:8]

        task = BackgroundTask(
            id=task_id,
            name=name,
            goal=goal,
            priority=priority,
            execution_mode=execution_mode
        )

        def _worker():
            try:
                with cls._lock:
                    if task.status == "cancelled":
                        return
                    task.status = "running"
                print(f"[BG] Task '{task.name}' ({task.id}) started.")

                if task.execution_mode == "graph":
                    from agents.task_graph import execute_goal_as_graph
                    result = execute_goal_as_graph(goal=task.goal, speak_fn=None)
                else:
                    from agents.autonomous import AgentLoop
                    agent = AgentLoop(goal=task.goal, max_steps=20, speak_fn=None)
                    with cls._lock:
                        task._agent = agent
                    result = agent.run()

                with cls._lock:
                    if task.status == "cancelled":
                        return
                    task.result = result
                    task.status = "done"
                    task.completed_at = time.time()

                elapsed = task.completed_at - task.created_at
                print(f"[BG] Task '{task.name}' ({task.id}) completed in {elapsed:.1f}s.")

            except Exception as e:
                with cls._lock:
                    if task.status == "cancelled":
                        return
                    task.status = "failed"
                    task.result = f"Task failed: {str(e)}"
                    task.completed_at = time.time()
                print(f"[BG] Task '{task.name}' ({task.id}) FAILED: {e}")

            cls._deliver_notification(task)

        with cls._lock:
            cls._prune_completed_locked()
            cls._tasks[task_id] = task

        task._future = cls._executor.submit(_worker)
        return task_id

    @classmethod
    def _deliver_notification(cls, task: BackgroundTask):
        """Handle notification delivery based on priority."""
        if task.status == "cancelled":
            return
        if task.priority == "urgent" and cls._notify_fn:
            # Urgent: interrupt and speak immediately
            summary = task.result[:200] if task.result else "Task completed."
            cls._notify_fn(f"Urgent update on {task.name}: {summary}")
        else:
            # Normal: queue for next interaction
            with cls._lock:
                cls._pending_notifications.append(task)

    @classmethod
    def check_pending(cls) -> list:
        """Check and return pending notifications. Clears the queue."""
        with cls._lock:
            pending = list(cls._pending_notifications)
            cls._pending_notifications.clear()
        return pending

    @classmethod
    def get_status(cls, task_id: str) -> Optional[dict]:
        """Get the status of a specific task."""
        with cls._lock:
            task = cls._tasks.get(task_id)
            if not task:
                return None
            return {
                "id": task.id,
                "name": task.name,
                "status": task.status,
                "result": task.result[:300] if task.result else None,
                "elapsed": (task.completed_at or time.time()) - task.created_at
            }

    @classmethod
    def list_active(cls) -> list:
        """List all active (running) background tasks."""
        with cls._lock:
            return [
                {"id": t.id, "name": t.name, "status": t.status,
                 "elapsed": time.time() - t.created_at}
                for t in cls._tasks.values()
                if t.status in ("pending", "running")
            ]

    @classmethod
    def list_all(cls) -> list:
        """List all tasks (active and completed)."""
        with cls._lock:
            return [
                {"id": t.id, "name": t.name, "status": t.status,
                 "elapsed": (t.completed_at or time.time()) - t.created_at}
                for t in cls._tasks.values()
            ]

    @classmethod
    def cancel(cls, task_id: str) -> bool:
        """Cancel a running background task."""
        with cls._lock:
            task = cls._tasks.get(task_id)
            if not task or task.status not in ("pending", "running"):
                return False
            if task._agent:
                task._agent.cancelled = True
            if task._future:
                task._future.cancel()
            task.status = "cancelled"
            task.completed_at = time.time()
        print(f"[BG] Task '{task.name}' ({task.id}) cancelled.")
        return True

    @classmethod
    def cancel_all(cls):
        """Cancel all running tasks."""
        with cls._lock:
            for task in cls._tasks.values():
                if task.status in ("pending", "running"):
                    if task._agent:
                        task._agent.cancelled = True
                    if task._future:
                        task._future.cancel()
                    task.status = "cancelled"
                    task.completed_at = time.time()
        print("[BG] All background tasks cancelled.")

    @classmethod
    def cleanup_old(cls, max_age: int = 3600):
        """Remove completed tasks older than max_age seconds."""
        cutoff = time.time() - max_age
        with cls._lock:
            to_remove = [
                tid for tid, t in cls._tasks.items()
                if t.status in ("done", "failed", "cancelled")
                and t.completed_at and t.completed_at < cutoff
            ]
            for tid in to_remove:
                del cls._tasks[tid]
