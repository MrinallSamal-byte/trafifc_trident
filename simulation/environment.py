"""
Traffic-Mind – Gym-compatible Training Environment
Wraps the full simulation into reset() / step() / render() for DQN training.
"""

import numpy as np
import pygame
from config.settings import (
    Direction,
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS,
    DECISION_INTERVAL, MAX_EPISODE_STEPS,
    SPAWN_RATE_HIGH,
    REWARD_CAR_PASSED, PENALTY_CAR_WAITING,
    PENALTY_LONG_WAIT, LONG_WAIT_THRESHOLD,
    PENALTY_SWITCH,
    REWARD_THROUGHPUT_BONUS, THROUGHPUT_BONUS_THRESHOLD,
    MAX_GREEN_DURATION,
    INTERSECTION_TOP, INTERSECTION_BOTTOM,
    INTERSECTION_LEFT, INTERSECTION_RIGHT,
)
from simulation.road_network import Intersection
from simulation.vehicle import VehicleSpawner, VehicleState
from simulation.traffic_light import TrafficLightController, TrafficLightState


class TrafficEnvironment:
    """
    OpenAI-Gym style environment for DQN training.

    State  : 12-dim float vector (see DQNController.get_state_vector)
    Action : 0 = NS green, 1 = EW green
    """

    def __init__(self, render_mode: bool = False):
        self.render_mode = render_mode
        self.intersection = Intersection()
        self.spawner = VehicleSpawner(self.intersection, spawn_rate=SPAWN_RATE_HIGH)
        self.vehicles: list = []

        self.controller = TrafficLightController()
        # Override step so base class doesn't crash
        self.controller.step = lambda: None

        self.total_steps = 0
        self.total_passed = 0
        self.prev_action = -1

        # PyGame (only if rendering)
        self.screen = None
        self.clock = None
        if render_mode:
            pygame.init()
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
            pygame.display.set_caption("Traffic-Mind — Training")
            self.clock = pygame.time.Clock()

    # ─── state vector ─────────────────────
    def _build_state(self) -> np.ndarray:
        features = []
        for d in Direction:
            waiting = [v for v in self.vehicles if v.direction == d and v.state == VehicleState.WAITING]
            count = len(waiting)
            avg_wait = (sum(v.wait_time for v in waiting) / count / MAX_GREEN_DURATION) if count else 0.0

            if d in (Direction.NORTH, Direction.SOUTH):
                road_len = SCREEN_HEIGHT / 2
            else:
                road_len = SCREEN_WIDTH / 2

            if count:
                if d == Direction.NORTH:
                    positions = [v.y - INTERSECTION_BOTTOM for v in waiting if v.y > INTERSECTION_BOTTOM]
                elif d == Direction.SOUTH:
                    positions = [INTERSECTION_TOP - v.y for v in waiting if v.y < INTERSECTION_TOP]
                elif d == Direction.EAST:
                    positions = [INTERSECTION_LEFT - v.x for v in waiting if v.x < INTERSECTION_LEFT]
                else:
                    positions = [v.x - INTERSECTION_RIGHT for v in waiting if v.x > INTERSECTION_RIGHT]
                queue_len = max(positions) / road_len if positions else 0.0
            else:
                queue_len = 0.0

            features.extend([count / 20.0, avg_wait, queue_len])

        return np.array(features, dtype=np.float32)

    # ─── reset ────────────────────────────
    def reset(self) -> np.ndarray:
        # Remove all vehicles from lane lists too
        for lane in self.intersection.get_all_incoming_lanes():
            lane.vehicles.clear()
        self.vehicles.clear()

        self.controller = TrafficLightController()
        self.controller.step = lambda: None
        self.controller._apply_phase(self.controller.PHASE_NS_GREEN)

        self.total_steps = 0
        self.total_passed = 0
        self.prev_action = -1

        # Seed some initial vehicles
        for _ in range(30):
            self.spawner.try_spawn_all_directions(self.vehicles)

        return self._build_state()

    # ─── step ─────────────────────────────
    def step(self, action: int):
        """
        Apply *action* and simulate DECISION_INTERVAL frames.

        Returns (next_state, reward, done, info).
        """
        # Apply action → set phase
        desired = self.controller.PHASE_NS_GREEN if action == 0 else self.controller.PHASE_EW_GREEN
        self.controller._apply_phase(desired)

        reward = 0.0
        passed_this_step = 0

        if action != self.prev_action and self.prev_action != -1:
            reward += PENALTY_SWITCH
        self.prev_action = action

        light_states = self.controller.get_state()

        for _ in range(DECISION_INTERVAL):
            self.total_steps += 1

            # Spawn
            self.spawner.try_spawn_all_directions(self.vehicles)

            # Update vehicles
            for v in self.vehicles:
                is_green = light_states[v.direction] == TrafficLightState.GREEN
                is_yellow = light_states[v.direction] == TrafficLightState.YELLOW
                v.update(is_green, is_yellow)

            # Remove crossed vehicles
            crossed = [v for v in self.vehicles if v.has_crossed()]
            for v in crossed:
                reward += REWARD_CAR_PASSED
                passed_this_step += 1
                self.total_passed += 1
                if v in v.lane.vehicles:
                    v.lane.vehicles.remove(v)
                self.vehicles.remove(v)

            # Penalties
            for v in self.vehicles:
                if v.state == VehicleState.WAITING:
                    reward += PENALTY_CAR_WAITING
                    if v.wait_time > LONG_WAIT_THRESHOLD:
                        reward += PENALTY_LONG_WAIT

        # Throughput bonus
        if passed_this_step >= THROUGHPUT_BONUS_THRESHOLD:
            reward += REWARD_THROUGHPUT_BONUS

        done = self.total_steps >= MAX_EPISODE_STEPS

        waits = [v.wait_time for v in self.vehicles if v.state == VehicleState.WAITING]
        avg_wait = float(np.mean(waits)) if waits else 0.0

        info = {
            "throughput": passed_this_step,
            "avg_wait": avg_wait,
            "total_waiting": sum(1 for v in self.vehicles if v.state == VehicleState.WAITING),
            "total_passed": self.total_passed,
        }

        return self._build_state(), reward, done, info

    # ─── render ───────────────────────────
    def render(self):
        if not self.render_mode or self.screen is None:
            return

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return

        self.screen.fill((30, 30, 30))

        # Minimal render during training
        # Draw roads
        cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        pygame.draw.rect(self.screen, (50, 50, 50),
                         (0, cy - 80, SCREEN_WIDTH, 160))
        pygame.draw.rect(self.screen, (50, 50, 50),
                         (cx - 80, 0, 160, SCREEN_HEIGHT))

        # Draw vehicles
        for v in self.vehicles:
            v.draw(self.screen)

        # Draw lights
        self.controller.draw(self.screen)

        pygame.display.flip()
        self.clock.tick(FPS)

    def close(self):
        if self.screen:
            pygame.quit()
