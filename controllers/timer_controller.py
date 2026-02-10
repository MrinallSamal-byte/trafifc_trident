"""
Traffic-Mind – Fixed-Timer Controller (the "dumb" baseline)
Cycles through phases on a rigid timer with no awareness of traffic.
"""

from simulation.traffic_light import TrafficLightController
from config.settings import GREEN_DURATION_TIMER, YELLOW_DURATION


class TimerController(TrafficLightController):
    """
    Simply cycles:
        NS Green (90 frames) → Yellow (30) →
        EW Green (90 frames) → Yellow (30) → repeat
    """

    NAME = "Timer (Dumb)"

    def __init__(self):
        super().__init__()
        self.phase_timer = GREEN_DURATION_TIMER
        self._apply_phase(self.PHASE_NS_GREEN)

    def step(self):
        self.phase_timer -= 1
        if self.phase_timer <= 0:
            if self.current_phase == self.PHASE_NS_GREEN:
                self._apply_phase(self.PHASE_YELLOW_1)
                self.phase_timer = YELLOW_DURATION
            elif self.current_phase == self.PHASE_YELLOW_1:
                self._apply_phase(self.PHASE_EW_GREEN)
                self.phase_timer = GREEN_DURATION_TIMER
            elif self.current_phase == self.PHASE_EW_GREEN:
                self._apply_phase(self.PHASE_YELLOW_2)
                self.phase_timer = YELLOW_DURATION
            elif self.current_phase == self.PHASE_YELLOW_2:
                self._apply_phase(self.PHASE_NS_GREEN)
                self.phase_timer = GREEN_DURATION_TIMER

        for light in self.lights.values():
            light.update()
