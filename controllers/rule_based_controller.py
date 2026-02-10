"""
Traffic-Mind – Rule-Based Controller (the "smart" baseline)
Adapts signal timing based on vehicle density per direction.
"""

from simulation.traffic_light import TrafficLightController
from simulation.vehicle import VehicleState
from config.settings import (
    Direction,
    MIN_GREEN_DURATION, MAX_GREEN_DURATION,
    YELLOW_DURATION,
)


class RuleBasedController(TrafficLightController):
    """
    Switches lights dynamically based on queue pressure.

    Logic:
    - Count waiting vehicles per direction
    - Compute "pressure" = vehicle_count + avg_wait * 0.5
    - Switch to the heavier direction if its pressure is
      1.5× greater than the current green direction's pressure
    """

    NAME = "Smart (Rule-Based)"

    def __init__(self, vehicles_ref: list):
        super().__init__()
        self.vehicles_ref = vehicles_ref  # mutable list shared with main
        self.phase_timer = MIN_GREEN_DURATION
        self.green_elapsed = 0

    # ── helpers ───────────────────────────
    def _count_waiting(self, direction: Direction) -> int:
        return sum(
            1 for v in self.vehicles_ref
            if v.direction == direction and v.state == VehicleState.WAITING
        )

    def _avg_wait(self, direction: Direction) -> float:
        waits = [
            v.wait_time for v in self.vehicles_ref
            if v.direction == direction and v.state == VehicleState.WAITING
        ]
        return (sum(waits) / len(waits)) if waits else 0.0

    def _pressure(self, direction: Direction) -> float:
        return self._count_waiting(direction) * 1.0 + self._avg_wait(direction) * 0.5

    def _ns_pressure(self) -> float:
        return self._pressure(Direction.NORTH) + self._pressure(Direction.SOUTH)

    def _ew_pressure(self) -> float:
        return self._pressure(Direction.EAST) + self._pressure(Direction.WEST)

    # ── step ─────────────────────────────
    def step(self):
        self.phase_timer -= 1
        self.green_elapsed += 1

        # In a yellow phase → just count down
        if self.current_phase in (self.PHASE_YELLOW_1, self.PHASE_YELLOW_2):
            if self.phase_timer <= 0:
                if self.current_phase == self.PHASE_YELLOW_1:
                    self._apply_phase(self.PHASE_EW_GREEN)
                else:
                    self._apply_phase(self.PHASE_NS_GREEN)
                self.phase_timer = MIN_GREEN_DURATION
                self.green_elapsed = 0
            for light in self.lights.values():
                light.update()
            return

        # In a green phase → evaluate pressure
        ns_p = self._ns_pressure()
        ew_p = self._ew_pressure()

        should_switch = False

        if self.current_phase == self.PHASE_NS_GREEN:
            if (
                self.green_elapsed >= MIN_GREEN_DURATION
                and ew_p > ns_p * 1.5
            ):
                should_switch = True
            if self.green_elapsed >= MAX_GREEN_DURATION:
                should_switch = True
        elif self.current_phase == self.PHASE_EW_GREEN:
            if (
                self.green_elapsed >= MIN_GREEN_DURATION
                and ns_p > ew_p * 1.5
            ):
                should_switch = True
            if self.green_elapsed >= MAX_GREEN_DURATION:
                should_switch = True

        if should_switch:
            if self.current_phase == self.PHASE_NS_GREEN:
                self._apply_phase(self.PHASE_YELLOW_1)
            else:
                self._apply_phase(self.PHASE_YELLOW_2)
            self.phase_timer = YELLOW_DURATION
            self.green_elapsed = 0

        for light in self.lights.values():
            light.update()
