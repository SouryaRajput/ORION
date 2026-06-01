"""
ORION Background Task Manager
Runs autonomous agent tasks in background threads while keeping the voice loop responsive.
Supports task submission, cancellation, status queries, and voice notifications.
"""

import threading
import time
import uuid
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
    _agent: Optional[object] = field(default=None, repr=False)
    _thread: Optional[threading.Thread] = field(default=None, repr=False)


class BackgroundManager:
    _tasks: dict = {}
    _lock = threading.Lock()
    _pending_notifications: list = []
    _notify_fn: Optional[Callable] = None

    @classmethod
    def set_notify_fn(cls, fn: Callable):
        """Set the voice notification function (speak_audio)."""
        cls._notify_fn = fn

    @classmethod
    def submit(cls, name: str, goal: str, priority: str = "normal") -> str:
        """Submit a goal for background execution. Returns task_id."""
        task_id = str(uuid.uuid4())[:8]

        task = BackgroundTask(
            id=task_id,
            name=name,
            goal=goal,
            priority=priority
        )

        def _worker():
            try:
                task.status = "running"
                print(f"[BG] Task '{task.name}' ({task.id}) started.")

                from agents.autonomous import AgentLoop
                agent = AgentLoop(goal=task.goal, max_steps=20, speak_fn=None)
                task._agent = agent

                task.result = agent.run()
                task.status = "done"
                task.completed_at = time.time()

                elapsed = task.completed_at - task.created_at
                print(f"[BG] Task '{task.name}' ({task.id}) completed in {elapsed:.1f}s.")

            except Exception as e:
                task.status = "failed"
                task.result = f"Task failed: {str(e)}"
                task.completed_at = time.time()
                print(f"[BG] Task '{task.name}' ({task.id}) FAILED: {e}")

            cls._deliver_notification(task)

        thread = threading.Thread(target=_worker, daemon=True, name=f"bg-{task_id}")
        task._thread = thread

        with cls._lock:
            cls._tasks[task_id] = task

        thread.start()
        return task_id

    @classmethod
    def _deliver_notification(cls, task: BackgroundTask):
        """Handle notification delivery based on priority."""
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
        task = cls._tasks.get(task_id)
        if not task or task.status not in ("pending", "running"):
            return False
        if task._agent:
            task._agent.cancelled = True
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
