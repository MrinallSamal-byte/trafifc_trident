"""
Traffic-Mind – Performance Metrics Collector
Throughput, wait-time analysis, and cross-controller comparison.
"""

import numpy as np
from config.settings import Direction, MAX_VEHICLES


class MetricsCollector:
    """Collects, computes, and compares traffic performance metrics."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.vehicles_waiting = {d: 0 for d in Direction}
        self.vehicles_passed = {d: 0 for d in Direction}
        self.wait_times: list[float] = []
        self._interval_passed = 0
        self._frame = 0

    # ─── per-frame update ─────────────────
    def record_waiting(self, direction: Direction, count: int):
        self.vehicles_waiting[direction] = count

    def record_passed(self, direction: Direction, wait_time: float):
        self.vehicles_passed[direction] = self.vehicles_passed.get(direction, 0) + 1
        self.wait_times.append(wait_time)
        self._interval_passed += 1

    # ─── computed stats ───────────────────
    @property
    def throughput(self) -> float:
        """Cars per 100 frames (approximate)."""
        if self._frame == 0:
            return 0.0
        return (sum(self.vehicles_passed.values()) / self._frame) * 100

    @property
    def average_wait_time(self) -> float:
        return float(np.mean(self.wait_times)) if self.wait_times else 0.0

    @property
    def max_wait_time(self) -> float:
        return float(max(self.wait_times)) if self.wait_times else 0.0

    @property
    def congestion_index(self) -> float:
        """0..1 — total waiting / capacity."""
        total_waiting = sum(self.vehicles_waiting.values())
        return min(1.0, total_waiting / MAX_VEHICLES)

    @property
    def efficiency_score(self) -> float:
        """Throughput as a fraction of theoretical max (approximation)."""
        theoretical = 4 * 4.0  # 4 directions × ~4 cars per second
        return min(1.0, self.throughput / (theoretical * 100)) if theoretical else 0.0

    # ─── comparison ───────────────────────
    @staticmethod
    def compare_controllers(timer_metrics: dict, smart_metrics: dict, ai_metrics: dict) -> dict:
        """
        Each dict should have keys: 'throughput', 'avg_wait', 'max_wait'.
        Returns improvement percentages.
        """
        def pct(old, new):
            if old == 0:
                return 0
            return ((new - old) / abs(old)) * 100

        result = {}
        if timer_metrics and ai_metrics:
            result["throughput_improvement"] = f"+{pct(timer_metrics['throughput'], ai_metrics['throughput']):.0f}% vs Timer"
            result["wait_time_reduction"] = f"{pct(timer_metrics['avg_wait'], ai_metrics['avg_wait']):.0f}% vs Timer"
            result["max_wait_reduction"] = f"{pct(timer_metrics['max_wait'], ai_metrics['max_wait']):.0f}% vs Timer"
        return result

    def generate_report(self) -> str:
        lines = [
            "═" * 50,
            " Traffic-Mind — Performance Report",
            "═" * 50,
            f"  Total cars passed  : {sum(self.vehicles_passed.values())}",
            f"  Throughput         : {self.throughput:.1f} cars / 100fr",
            f"  Avg wait time      : {self.average_wait_time:.1f} frames",
            f"  Max wait time      : {self.max_wait_time:.0f} frames",
            f"  Congestion index   : {self.congestion_index:.2f}",
            f"  Efficiency score   : {self.efficiency_score:.1%}",
            "═" * 50,
        ]
        return "\n".join(lines)
