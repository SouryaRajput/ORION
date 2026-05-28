"""
Async utility helpers for the study mode system.
"""

import asyncio
from typing import TypeVar, Callable, Any
from concurrent.futures import ThreadPoolExecutor

T = TypeVar("T")

# Shared thread pool for CPU-bound tasks (Manim rendering, etc.)
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="study-worker")


async def run_in_thread(func: Callable[..., T], *args: Any) -> T:
    """Run a blocking/CPU-bound function in a background thread."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, func, *args)


async def timeout_wrapper(coro, seconds: float, default: Any = None) -> Any:
    """Run an async coroutine with a timeout. Returns default on timeout."""
    try:
        return await asyncio.wait_for(coro, timeout=seconds)
    except asyncio.TimeoutError:
        return default


class AsyncEventChannel:
    """Simple pub/sub event channel for async components."""

    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = {}

    def subscribe(self, event: str, handler: Callable):
        self._subscribers.setdefault(event, []).append(handler)

    async def emit(self, event: str, data: Any = None):
        for handler in self._subscribers.get(event, []):
            if asyncio.iscoroutinefunction(handler):
                await handler(data)
            else:
                handler(data)
