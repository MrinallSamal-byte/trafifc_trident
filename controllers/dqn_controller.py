"""
Traffic-Mind – DQN Controller
Uses a trained DQN model to make traffic-light decisions in real time.
"""

import torch
import numpy as np

from simulation.traffic_light import TrafficLightController, TrafficLightState
from simulation.vehicle import VehicleState
from ai.dqn_network import DQN
from config.settings import (
    Direction,
    STATE_SIZE, ACTION_SIZE,
    DECISION_INTERVAL,
    MIN_GREEN_DURATION, YELLOW_DURATION,
    MAX_GREEN_DURATION,
    SCREEN_HEIGHT, SCREEN_WIDTH,
    INTERSECTION_TOP, INTERSECTION_BOTTOM,
    INTERSECTION_LEFT, INTERSECTION_RIGHT,
    EMERGENCY_PRIORITY_FRAMES,
    GREEN_DURATION_TIMER,
)


class DQNController(TrafficLightController):
    """RL-based controller that queries a trained DQN every DECISION_INTERVAL frames."""

    NAME = "AI (DQN)"

    def __init__(self, vehicles_ref: list, model_path: str | None = None):
        super().__init__()
        self.vehicles_ref = vehicles_ref
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.dqn = DQN(STATE_SIZE, ACTION_SIZE).to(self.device)
        if model_path:
            self.dqn.load_state_dict(
                torch.load(model_path, map_location=self.device, weights_only=True)
            )
        self.dqn.eval()

        self.frame_counter = 0
        self.green_elapsed = 0
        self.last_action = 0  # 0 = NS, 1 = EW
        self._in_yellow = False
        self._pending_phase = None
        self._yellow_timer = 0

        # Emergency green corridor
        self._emergency_override = False
        self._emergency_timer = 0
        self._emergency_phase = None

        # Fail-safe fallback
        self._fallback_active = False
        self._fallback_timer = GREEN_DURATION_TIMER

    # ─── state vector ─────────────────────
    def get_state_vector(self) -> np.ndarray:
        features = []
        for d in Direction:
            waiting = [v for v in self.vehicles_ref if v.direction == d and v.state == VehicleState.WAITING]
            count = len(waiting)
            avg_wait = (sum(v.wait_time for v in waiting) / count) / MAX_GREEN_DURATION if count else 0.0

            # Queue length normalised by road length
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

            features.extend([count / 20.0, avg_wait, queue_len])  # normalised

        return np.array(features, dtype=np.float32)

    # ─── emergency detection ───────────────
    def _check_emergency(self) -> int | None:
        """Return the Direction of an approaching emergency vehicle, or None."""
        for v in self.vehicles_ref:
            if v.is_emergency and v.state != 'DESPAWNED':
                return v.direction
        return None

    # ─── fail-safe timer step ──────────────
    def _fallback_step(self):
        """Simple timer-based cycling used when DQN fails."""
        self._fallback_timer -= 1
        if self._fallback_timer <= 0:
            if self.current_phase == self.PHASE_NS_GREEN:
                self._apply_phase(self.PHASE_YELLOW_1)
                self._fallback_timer = YELLOW_DURATION
            elif self.current_phase == self.PHASE_YELLOW_1:
                self._apply_phase(self.PHASE_EW_GREEN)
                self._fallback_timer = GREEN_DURATION_TIMER
            elif self.current_phase == self.PHASE_EW_GREEN:
                self._apply_phase(self.PHASE_YELLOW_2)
                self._fallback_timer = YELLOW_DURATION
            elif self.current_phase == self.PHASE_YELLOW_2:
                self._apply_phase(self.PHASE_NS_GREEN)
                self._fallback_timer = GREEN_DURATION_TIMER

        for light in self.lights.values():
            light.update()

    # ─── step ─────────────────────────────
    def step(self):
        # If DQN has crashed, use fail-safe timer
        if self._fallback_active:
            self._fallback_step()
            return

        try:
            self._ai_step()
        except Exception as e:
            print(f"⚠️  DQN error: {e}. Activating fail-safe timer fallback.")
            self._fallback_active = True
            self._fallback_step()

    def _ai_step(self):
        self.frame_counter += 1
        self.green_elapsed += 1

        # ── Emergency green corridor override ──
        emergency_dir = self._check_emergency()
        if emergency_dir is not None and not self._emergency_override:
            # Determine which phase gives green to the emergency direction
            if emergency_dir in (Direction.NORTH, Direction.SOUTH):
                needed_phase = self.PHASE_NS_GREEN
            else:
                needed_phase = self.PHASE_EW_GREEN

            if self.current_phase != needed_phase:
                # Force switch through yellow
                self._in_yellow = True
                self._yellow_timer = YELLOW_DURATION
                self._pending_phase = needed_phase
                if self.current_phase == self.PHASE_NS_GREEN:
                    self._apply_phase(self.PHASE_YELLOW_1)
                else:
                    self._apply_phase(self.PHASE_YELLOW_2)

            self._emergency_override = True
            self._emergency_timer = EMERGENCY_PRIORITY_FRAMES
            self._emergency_phase = needed_phase
            print(f"🚨 Green Corridor activated for {emergency_dir.name}!")

        # If emergency override is active, hold the green
        if self._emergency_override:
            self._emergency_timer -= 1
            if self._emergency_timer <= 0:
                self._emergency_override = False
                self._emergency_phase = None
                self.green_elapsed = 0
                print("✅ Green Corridor deactivated.")
            # During override, just count down yellow if needed, then hold green
            if self._in_yellow:
                self._yellow_timer -= 1
                if self._yellow_timer <= 0:
                    self._in_yellow = False
                    if self._pending_phase is not None:
                        self._apply_phase(self._pending_phase)
                        self._pending_phase = None
            for light in self.lights.values():
                light.update()
            return

        # Handle yellow transition
        if self._in_yellow:
            self._yellow_timer -= 1
            if self._yellow_timer <= 0:
                self._in_yellow = False
                if self._pending_phase is not None:
                    self._apply_phase(self._pending_phase)
                    self.green_elapsed = 0
                    self._pending_phase = None
            for light in self.lights.values():
                light.update()
            return

        # Make a decision every DECISION_INTERVAL frames
        if self.frame_counter % DECISION_INTERVAL == 0 and self.green_elapsed >= MIN_GREEN_DURATION:
            state = self.get_state_vector()
            with torch.no_grad():
                state_t = torch.FloatTensor(state).unsqueeze(0).to(self.device)
                action = self.dqn(state_t).argmax(dim=1).item()

            desired_phase = self.PHASE_NS_GREEN if action == 0 else self.PHASE_EW_GREEN

            if desired_phase != self.current_phase:
                # Transition through yellow
                self._in_yellow = True
                self._yellow_timer = YELLOW_DURATION
                self._pending_phase = desired_phase
                if self.current_phase == self.PHASE_NS_GREEN:
                    self._apply_phase(self.PHASE_YELLOW_1)
                else:
                    self._apply_phase(self.PHASE_YELLOW_2)
                self.last_action = action

        # Force-switch on max green
        if self.green_elapsed >= MAX_GREEN_DURATION and not self._in_yellow:
            self._in_yellow = True
            self._yellow_timer = YELLOW_DURATION
            if self.current_phase == self.PHASE_NS_GREEN:
                self._apply_phase(self.PHASE_YELLOW_1)
                self._pending_phase = self.PHASE_EW_GREEN
            else:
                self._apply_phase(self.PHASE_YELLOW_2)
                self._pending_phase = self.PHASE_NS_GREEN

        for light in self.lights.values():
            light.update()

