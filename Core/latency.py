import time
from typing import Dict, Optional

class LatencyTracker:
    def __init__(self):
        self._checkpoints: Dict[str, float] = {}
        self._start_time: Optional[float] = None
        self._is_active = False

    def mark_end_of_speech(self):
        """Called the exact millisecond silence threshold is reached."""
        self._start_time = time.perf_counter()
        self._checkpoints.clear()
        self._is_active = True

    def mark_checkpoint(self, name: str):
        """Mark a component completion."""
        if self._is_active and self._start_time is not None:
            self._checkpoints[name] = time.perf_counter()

    def mark_checkpoint_once(self, name: str):
        """Mark the first occurrence of an event during the active request."""
        if (
            self._is_active
            and self._start_time is not None
            and name not in self._checkpoints
        ):
            self._checkpoints[name] = time.perf_counter()

    def end_tracking_and_report(self):
        """Called when audio begins playing."""
        if not self._is_active or self._start_time is None:
            return

        now = time.perf_counter()
        self._checkpoints["Total (Audio Start)"] = now
        
        print("\n" + "="*40)
        print("⏱️  LATENCY METRICS (from end of speech)")
        print("="*40)
        
        prev_time = self._start_time
        for name, timestamp in self._checkpoints.items():
            delta_total = (timestamp - self._start_time) * 1000
            delta_step = (timestamp - prev_time) * 1000
            print(f"[{delta_total:6.1f} ms] {name:<20} (+{delta_step:5.1f} ms)")
            prev_time = timestamp
            
        print("="*40 + "\n")
        
        self._is_active = False
        self._start_time = None

tracker = LatencyTracker()
