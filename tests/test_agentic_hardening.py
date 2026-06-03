import threading
import time
import unittest
from datetime import datetime
from unittest.mock import patch

from Core.agent_executor import is_command_safe
from agents.background import BackgroundManager
from agents.scheduler import ScheduledJob, Scheduler, _cron_matches, _validate_job
from agents.task_graph import TaskGraph, TaskNode
from agents.tool_registry import Tool, ToolRegistry


class TaskGraphTests(unittest.TestCase):
    def setUp(self):
        ToolRegistry.register(
            Tool("test_echo", "Echo a value.", {"value": "Value"}, lambda value: value)
        )
        ToolRegistry.register(
            Tool(
                "test_fail",
                "Return an error.",
                {},
                lambda: "Error: expected failure"
            )
        )

    def test_rejects_unknown_dependency(self):
        with self.assertRaises(ValueError):
            TaskGraph("bad graph", [TaskNode("a", "Bad", "test_echo", depends_on=["missing"])])

    def test_rejects_unknown_tool(self):
        with self.assertRaises(ValueError):
            TaskGraph("bad tool", [TaskNode("a", "Bad", "missing_tool")])

    def test_rejects_dependency_cycle(self):
        with self.assertRaises(ValueError):
            TaskGraph(
                "cycle",
                [
                    TaskNode("a", "A", "test_echo", depends_on=["b"]),
                    TaskNode("b", "B", "test_echo", depends_on=["a"]),
                ],
            )

    def test_skips_children_after_parent_failure(self):
        graph = TaskGraph(
            "failure propagation",
            [
                TaskNode("a", "Fails", "test_fail"),
                TaskNode("b", "Blocked", "test_echo", {"value": "{ref:a}"}, ["a"]),
            ],
        )
        graph.execute()
        self.assertEqual(graph.nodes["a"].status, "failed")
        self.assertEqual(graph.nodes["b"].status, "skipped")


class SchedulerTests(unittest.TestCase):
    def test_standard_cron_weekday_uses_sunday_zero(self):
        sunday = datetime(2026, 6, 7, 9, 0)
        monday = datetime(2026, 6, 8, 9, 0)
        self.assertTrue(_cron_matches("0 9 * * 0", sunday))
        self.assertFalse(_cron_matches("0 9 * * 0", monday))

    def test_rejects_monitor_polling_faster_than_thirty_seconds(self):
        with self.assertRaises(ValueError):
            _validate_job(
                ScheduledJob("job", "Monitor", "Check status", "monitor", {"poll_interval": 5})
            )

    def test_prevents_overlapping_job_runs(self):
        scheduler = Scheduler()
        scheduler._save_jobs = lambda: None
        job = ScheduledJob(
            "job", "Once", "Do work", "once", {"run_at": datetime.now().isoformat()}
        )
        started = threading.Event()
        release = threading.Event()

        def slow_submit(**kwargs):
            started.set()
            release.wait(timeout=1)
            return "task"

        with patch("agents.background.BackgroundManager.submit", side_effect=slow_submit):
            scheduler._execute_job(job)
            self.assertTrue(started.wait(timeout=1))
            scheduler._execute_job(job)
            self.assertEqual(job.run_count, 1)
            release.set()


class BackgroundManagerTests(unittest.TestCase):
    def test_cancelled_task_is_not_overwritten_as_done(self):
        started = threading.Event()
        release = threading.Event()

        def slow_graph(**kwargs):
            started.set()
            release.wait(timeout=1)
            return "finished"

        with patch("agents.task_graph.execute_goal_as_graph", side_effect=slow_graph):
            task_id = BackgroundManager.submit("Slow", "Wait for release")
            self.assertTrue(started.wait(timeout=1))
            self.assertTrue(BackgroundManager.cancel(task_id))
            release.set()
            time.sleep(0.05)
            self.assertEqual(BackgroundManager.get_status(task_id)["status"], "cancelled")


class CommandSafetyTests(unittest.TestCase):
    def test_shell_operators_disable_auto_execution(self):
        self.assertTrue(is_command_safe("ls /tmp"))
        self.assertFalse(is_command_safe("ls /tmp; rm -rf /tmp/example"))
        self.assertFalse(is_command_safe("cat file | sh"))

    def test_registry_blocks_unsafe_tools_without_confirmation(self):
        result = ToolRegistry.execute("open_url", url="https://example.com")
        self.assertEqual(result, "Error: Tool 'open_url' requires explicit user confirmation.")


if __name__ == "__main__":
    unittest.main()
