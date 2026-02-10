"""
Traffic-Mind – Dashboard (metrics tracker for the HUD)
"""

import time
from config.settings import Direction
from simulation.vehicle import VehicleState


class Dashboard:
    """Tracks live and historical performance metrics for the UI overlay."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.total_cars_passed = 0
        self.total_cars_spawned = 0
        self.throughput_history = []      # per-interval throughput
        self.wait_time_history = []
        self._interval_passed = 0
        self._frame_counter = 0
        self._interval_frames = 60       # compute stats every second

        self.current_avg_wait = 0.0
        self.current_max_wait = 0.0
        self.queue_lengths = {d: 0 for d in Direction}

        self.start_time = time.time()
        self.fps = 0.0

        # Per-controller totals for final comparison
        self.controller_totals = {
            "Timer (Dumb)": {"passed": 0, "wait_sum": 0, "wait_count": 0},
            "Smart (Rule-Based)": {"passed": 0, "wait_sum": 0, "wait_count": 0},
            "AI (DQN)": {"passed": 0, "wait_sum": 0, "wait_count": 0},
        }
        self._active_ctrl_name = "Timer (Dumb)"

    def set_controller_name(self, name: str):
        self._active_ctrl_name = name

    def record_passed(self, vehicle):
        """Called when a vehicle crosses the intersection."""
        self.total_cars_passed += 1
        self._interval_passed += 1

        ct = self.controller_totals.get(self._active_ctrl_name)
        if ct is not None:
            ct["passed"] += 1
            ct["wait_sum"] += vehicle.wait_time
            ct["wait_count"] += 1

    def update(self, vehicles: list, fps: float = 60.0):
        """Called every frame."""
        self._frame_counter += 1
        self.fps = fps

        # Queue lengths
        for d in Direction:
            self.queue_lengths[d] = sum(
                1 for v in vehicles if v.direction == d and v.state == VehicleState.WAITING
            )

        # Wait times
        waits = [v.wait_time for v in vehicles if v.state == VehicleState.WAITING]
        self.current_avg_wait = (sum(waits) / len(waits)) if waits else 0.0
        self.current_max_wait = max(waits) if waits else 0.0

        # Interval stats (once per second)
        if self._frame_counter >= self._interval_frames:
            self.throughput_history.append(self._interval_passed)
            self.wait_time_history.append(self.current_avg_wait)
            self._interval_passed = 0
            self._frame_counter = 0

    def get_metrics(self) -> dict:
        return {
            "fps": self.fps,
            "elapsed": time.time() - self.start_time,
            "throughput": self.throughput_history[-1] if self.throughput_history else 0,
            "avg_wait": self.current_avg_wait,
            "max_wait": self.current_max_wait,
            "queues": dict(self.queue_lengths),
            "total_passed": self.total_cars_passed,
            "total_waiting": sum(self.queue_lengths.values()),
            "total_vehicles": sum(self.queue_lengths.values()) + 0,  # filled by caller
            "throughput_history": list(self.throughput_history),
        }

    def get_comparison_data(self) -> dict:
        """Return per-controller averages for the comparison screen."""
        out = {}
        for name, ct in self.controller_totals.items():
            avg_w = ct["wait_sum"] / ct["wait_count"] if ct["wait_count"] else 0
            out[name] = {"total_passed": ct["passed"], "avg_wait": avg_w}
        return out
