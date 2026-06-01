"""
ORION Scheduled Intelligence
Persistent cron-like scheduler with condition monitoring, powered by the Agent Loop.
Supports one-time jobs, recurring cron schedules, and conditional monitoring.
"""

import json
import time
import threading
import os
import re
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Optional
from pathlib import Path


SCHEDULES_FILE = Path("memory/schedules.json")


@dataclass
class ScheduledJob:
    id: str
    name: str
    goal: str
    schedule_type: str           # "once" | "cron" | "monitor"
    config: dict = field(default_factory=dict)
    active: bool = True
    last_run: Optional[float] = None
    created_at: float = field(default_factory=time.time)
    run_count: int = 0


def _match_cron_field(field_expr: str, value: int) -> bool:
    """Check if a value matches a cron field expression."""
    if field_expr == "*":
        return True
    
    for part in field_expr.split(","):
        part = part.strip()
        # Handle */N (every N)
        if part.startswith("*/"):
            divisor = int(part[2:])
            if value % divisor == 0:
                return True
        # Handle N-M (range)
        elif "-" in part:
            lo, hi = part.split("-", 1)
            if int(lo) <= value <= int(hi):
                return True
        # Handle exact match
        else:
            if value == int(part):
                return True
    return False


def _cron_matches(cron_expr: str, dt: datetime) -> bool:
    """Check if a datetime matches a 5-field cron expression."""
    fields = cron_expr.strip().split()
    if len(fields) != 5:
        return False
    minute, hour, dom, month, dow = fields
    return (
        _match_cron_field(minute, dt.minute) and
        _match_cron_field(hour, dt.hour) and
        _match_cron_field(dom, dt.day) and
        _match_cron_field(month, dt.month) and
        _match_cron_field(dow, dt.weekday())  # 0=Monday in Python
    )


class Scheduler:
    def __init__(self):
        self.jobs: dict[str, ScheduledJob] = {}
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._poll_interval = 30  # seconds
        self._load_jobs()

    def _load_jobs(self):
        """Load persisted jobs from disk."""
        if not SCHEDULES_FILE.exists():
            return
        try:
            with open(SCHEDULES_FILE, "r") as f:
                data = json.load(f)
            for item in data:
                job = ScheduledJob(**item)
                self.jobs[job.id] = job
            print(f"[SCHEDULER] Loaded {len(self.jobs)} scheduled jobs.")
        except Exception as e:
            print(f"[SCHEDULER] Failed to load jobs: {e}")

    def _save_jobs(self):
        """Persist all jobs to disk."""
        try:
            SCHEDULES_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = [asdict(job) for job in self.jobs.values()]
            with open(SCHEDULES_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[SCHEDULER] Failed to save jobs: {e}")

    def add_job(self, job: ScheduledJob):
        """Register a new scheduled job."""
        with self._lock:
            self.jobs[job.id] = job
            self._save_jobs()
        print(f"[SCHEDULER] Added job: {job.name} ({job.schedule_type})")

    def remove_job(self, job_id: str) -> bool:
        """Remove a scheduled job."""
        with self._lock:
            if job_id in self.jobs:
                del self.jobs[job_id]
                self._save_jobs()
                return True
        return False

    def list_jobs(self) -> list:
        """List all scheduled jobs."""
        with self._lock:
            return [
                {"id": j.id, "name": j.name, "type": j.schedule_type,
                 "active": j.active, "run_count": j.run_count,
                 "last_run": j.last_run}
                for j in self.jobs.values()
            ]

    def start(self):
        """Start the scheduler daemon thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="scheduler")
        self._thread.start()
        print(f"[SCHEDULER] Started. Polling every {self._poll_interval}s. {len(self.jobs)} jobs loaded.")

    def stop(self):
        """Stop the scheduler."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        print("[SCHEDULER] Stopped.")

    def _loop(self):
        """Main scheduler loop. Checks jobs every poll_interval seconds."""
        while self._running:
            now = datetime.now()
            now_ts = time.time()

            with self._lock:
                jobs_snapshot = list(self.jobs.values())

            for job in jobs_snapshot:
                if not job.active:
                    continue

                should_run = False

                if job.schedule_type == "once":
                    run_at_str = job.config.get("run_at", "")
                    if run_at_str:
                        try:
                            run_at = datetime.fromisoformat(run_at_str)
                            if now >= run_at and job.run_count == 0:
                                should_run = True
                        except ValueError:
                            pass

                elif job.schedule_type == "cron":
                    cron_expr = job.config.get("cron", "")
                    if cron_expr and _cron_matches(cron_expr, now):
                        # Don't run if already ran this minute
                        if job.last_run is None or (now_ts - job.last_run) > 60:
                            should_run = True

                elif job.schedule_type == "monitor":
                    poll_interval = job.config.get("poll_interval", 300)
                    if job.last_run is None or (now_ts - job.last_run) >= poll_interval:
                        should_run = True

                if should_run:
                    self._execute_job(job)

            time.sleep(self._poll_interval)

    def _execute_job(self, job: ScheduledJob):
        """Execute a scheduled job in a background thread."""
        def _run():
            try:
                print(f"[SCHEDULER] Running job: {job.name}")
                job.last_run = time.time()
                job.run_count += 1

                from agents.background import BackgroundManager

                if job.schedule_type == "monitor":
                    # For monitors: run agent, then check condition
                    from agents.autonomous import AgentLoop
                    agent = AgentLoop(
                        goal=f"Check the following: {job.goal}. Return the current status/value.",
                        max_steps=5
                    )
                    result = agent.run()

                    # Check if condition is met
                    condition = job.config.get("condition", "")
                    if condition:
                        condition_met = self._check_condition(condition, result)
                        if condition_met:
                            # Condition met! Deliver urgent notification
                            BackgroundManager._deliver_notification(
                                type("Task", (), {
                                    "name": job.name,
                                    "result": f"ALERT: {condition}. Current data: {result[:300]}",
                                    "priority": "urgent"
                                })()
                            )
                            print(f"[SCHEDULER] Monitor condition MET for: {job.name}")
                        else:
                            print(f"[SCHEDULER] Monitor condition NOT met for: {job.name}. Will check again.")
                    else:
                        # No condition, just report
                        BackgroundManager._deliver_notification(
                            type("Task", (), {
                                "name": job.name,
                                "result": result[:300],
                                "priority": "normal"
                            })()
                        )
                else:
                    # For cron/once: submit as background task
                    priority = "normal"
                    BackgroundManager.submit(
                        name=f"[Scheduled] {job.name}",
                        goal=job.goal,
                        priority=priority
                    )

                # Deactivate one-time jobs after execution
                if job.schedule_type == "once":
                    job.active = False

                with self._lock:
                    self._save_jobs()

            except Exception as e:
                print(f"[SCHEDULER] Job '{job.name}' error: {e}")

        threading.Thread(target=_run, daemon=True, name=f"sched-{job.id}").start()

    def _check_condition(self, condition: str, data: str) -> bool:
        """Use LLM to check if a monitoring condition is met."""
        try:
            import requests
            from dotenv import load_dotenv
            load_dotenv()

            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                api_key = os.getenv("OPENROUTER_API_KEY")
                url = "https://openrouter.ai/api/v1/chat/completions"
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                model = "google/gemini-2.5-flash"
            else:
                url = f"https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                model = "gemini-2.5-flash"

            from agents.prompts import get_condition_check_prompt

            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": get_condition_check_prompt()},
                    {"role": "user", "content": f"CONDITION: {condition}\n\nDATA:\n{data[:3000]}"}
                ],
                "temperature": 0.0,
                "max_tokens": 200
            }

            response = requests.post(url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"].strip()

            result = json.loads(re.sub(r'```json|```', '', content).strip())
            return result.get("met", False)

        except Exception as e:
            print(f"[SCHEDULER] Condition check error: {e}")
            return False


def parse_schedule_from_text(text: str) -> ScheduledJob:
    """Parse natural language into a ScheduledJob using LLM."""
    import requests
    import uuid
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv("OPENROUTER_API_KEY")
    
    from agents.prompts import get_schedule_parse_prompt

    now = datetime.now()
    
    payload = {
        "model": "google/gemini-2.5-flash",
        "messages": [
            {"role": "system", "content": get_schedule_parse_prompt()},
            {"role": "user", "content": f"Current date/time: {now.isoformat()}\n\nSchedule request: {text}"}
        ],
        "temperature": 0.0,
        "max_tokens": 500
    }

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=15
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"].strip()
        content = re.sub(r'```json|```', '', content).strip()
        parsed = json.loads(content)

        return ScheduledJob(
            id=str(uuid.uuid4())[:8],
            name=parsed.get("name", "Scheduled Task"),
            goal=parsed.get("goal", text),
            schedule_type=parsed.get("schedule_type", "once"),
            config=parsed.get("config", {})
        )

    except Exception as e:
        print(f"[SCHEDULER] Failed to parse schedule: {e}")
        # Fallback: create a simple one-time job
        return ScheduledJob(
            id=str(uuid.uuid4())[:8],
            name="Scheduled Task",
            goal=text,
            schedule_type="once",
            config={"run_at": (now + timedelta(minutes=1)).isoformat()}
        )
