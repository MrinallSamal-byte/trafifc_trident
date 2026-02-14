"""
Traffic-Mind – Traffic Light & Base Controller
State machine for traffic signals with phase management.
"""

from enum import Enum
import pygame
from config.settings import (
    Direction,
    GREEN_DURATION_TIMER, YELLOW_DURATION,
    LIGHT_RADIUS,
    LIGHT_RED, LIGHT_YELLOW, LIGHT_GREEN,
    LIGHT_RED_DIM, LIGHT_YELLOW_DIM, LIGHT_GREEN_DIM,
    INTERSECTION_LEFT, INTERSECTION_RIGHT,
    INTERSECTION_TOP, INTERSECTION_BOTTOM,
)


class TrafficLightState(Enum):
    RED = "RED"
    YELLOW = "YELLOW"
    GREEN = "GREEN"


class TrafficLight:
    """A single traffic light for one direction."""

    def __init__(self, direction: Direction):
        self.direction = direction
        self.state = TrafficLightState.RED
        self.timer = 0
        self.position = self._default_position()

    def _default_position(self):
        offset = 35  # pixels from intersection edge
        if self.direction == Direction.NORTH:
            return (INTERSECTION_RIGHT + offset, INTERSECTION_TOP - 15)
        elif self.direction == Direction.SOUTH:
            return (INTERSECTION_LEFT - offset, INTERSECTION_BOTTOM + 15)
        elif self.direction == Direction.EAST:
            return (INTERSECTION_RIGHT + 15, INTERSECTION_BOTTOM + offset)
        elif self.direction == Direction.WEST:
            return (INTERSECTION_LEFT - 15, INTERSECTION_TOP - offset)

    def set_state(self, new_state: TrafficLightState, duration: int = 0):
        self.state = new_state
        self.timer = duration

    def update(self):
        if self.timer > 0:
            self.timer -= 1

    def is_green(self) -> bool:
        return self.state == TrafficLightState.GREEN

    def is_red(self) -> bool:
        return self.state == TrafficLightState.RED

    def is_yellow(self) -> bool:
        return self.state == TrafficLightState.YELLOW

    def draw(self, screen: pygame.Surface):
        px, py = self.position

        # Housing
        housing_w, housing_h = 22, 60
        housing_rect = pygame.Rect(
            px - housing_w // 2, py - housing_h // 2,
            housing_w, housing_h,
        )
        pygame.draw.rect(screen, (25, 25, 25), housing_rect, border_radius=6)
        pygame.draw.rect(screen, (60, 60, 60), housing_rect, width=1, border_radius=6)

        # Three lights
        spacing = 16
        for i, (state_enum, bright, dim) in enumerate([
            (TrafficLightState.RED, LIGHT_RED, LIGHT_RED_DIM),
            (TrafficLightState.YELLOW, LIGHT_YELLOW, LIGHT_YELLOW_DIM),
            (TrafficLightState.GREEN, LIGHT_GREEN, LIGHT_GREEN_DIM),
        ]):
            cy = py - spacing + i * spacing
            is_active = (self.state == state_enum)
            color = bright if is_active else dim

            # Glow effect
            if is_active:
                glow_surf = pygame.Surface((LIGHT_RADIUS * 4, LIGHT_RADIUS * 4), pygame.SRCALPHA)
                glow_color = (*color[:3], 50)
                pygame.draw.circle(glow_surf, glow_color, (LIGHT_RADIUS * 2, LIGHT_RADIUS * 2), LIGHT_RADIUS * 2)
                screen.blit(glow_surf, (px - LIGHT_RADIUS * 2, cy - LIGHT_RADIUS * 2))

            pygame.draw.circle(screen, color, (px, cy), LIGHT_RADIUS - 2)


# ─────────────────────────────────────────────
# Base controller
# ─────────────────────────────────────────────
class TrafficLightController:
    """
    Abstract base class for all traffic light controllers.

    Phase 0: N-S GREEN, E-W RED
    Phase 1: All YELLOW
    Phase 2: E-W GREEN, N-S RED
    Phase 3: All YELLOW
    """

    PHASE_NS_GREEN = 0
    PHASE_YELLOW_1 = 1
    PHASE_EW_GREEN = 2
    PHASE_YELLOW_2 = 3

    def __init__(self):
        self.lights = {d: TrafficLight(d) for d in Direction}
        self.current_phase = self.PHASE_NS_GREEN
        self.phase_timer = 0
        self._apply_phase(self.current_phase)

    def _apply_phase(self, phase: int):
        self.current_phase = phase
        if phase == self.PHASE_NS_GREEN:
            self.lights[Direction.NORTH].set_state(TrafficLightState.GREEN)
            self.lights[Direction.SOUTH].set_state(TrafficLightState.GREEN)
            self.lights[Direction.EAST].set_state(TrafficLightState.RED)
            self.lights[Direction.WEST].set_state(TrafficLightState.RED)
        elif phase in (self.PHASE_YELLOW_1, self.PHASE_YELLOW_2):
            for d in Direction:
                self.lights[d].set_state(TrafficLightState.YELLOW)
        elif phase == self.PHASE_EW_GREEN:
            self.lights[Direction.NORTH].set_state(TrafficLightState.RED)
            self.lights[Direction.SOUTH].set_state(TrafficLightState.RED)
            self.lights[Direction.EAST].set_state(TrafficLightState.GREEN)
            self.lights[Direction.WEST].set_state(TrafficLightState.GREEN)

    def get_state(self):
        """Return dict direction → TrafficLightState."""
        return {d: self.lights[d].state for d in Direction}

    def get_phase_info(self) -> str:
        names = {
            self.PHASE_NS_GREEN: "N-S Green",
            self.PHASE_YELLOW_1: "Yellow (transition)",
            self.PHASE_EW_GREEN: "E-W Green",
            self.PHASE_YELLOW_2: "Yellow (transition)",
        }
        return names.get(self.current_phase, "Unknown")

    def step(self):
        """Override in subclasses."""
        raise NotImplementedError

    def draw(self, screen: pygame.Surface):
        for light in self.lights.values():
            light.draw(screen)
