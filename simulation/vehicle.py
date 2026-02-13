"""
Traffic-Mind – Vehicle & Spawner
Handles individual car physics, rendering, and spawn logic.
"""

import random
import pygame
from config.settings import (
    Direction,
    CAR_LENGTH, CAR_WIDTH,
    CAR_SPEED_MIN, CAR_SPEED_MAX,
    CAR_COLORS, SAFE_DISTANCE,
    MAX_VEHICLES,
    SCREEN_WIDTH, SCREEN_HEIGHT,
    INTERSECTION_LEFT, INTERSECTION_RIGHT,
    INTERSECTION_TOP, INTERSECTION_BOTTOM,
    EMERGENCY_SPAWN_RATE, EMERGENCY_COLOR,
    EMERGENCY_STRIPE_COLOR, EMERGENCY_SPEED,
)


class VehicleState:
    MOVING = "MOVING"
    WAITING = "WAITING"
    CROSSING = "CROSSING"
    DESPAWNED = "DESPAWNED"


_next_id = 0


def _make_id():
    global _next_id
    _next_id += 1
    return _next_id


class Vehicle:
    """A single car in the simulation."""

    def __init__(self, direction: Direction, lane, x: float, y: float,
                 is_emergency: bool = False):
        self.id = _make_id()
        self.direction = direction
        self.lane = lane
        self.is_emergency = is_emergency

        self.x = float(x)
        self.y = float(y)

        if is_emergency:
            self.max_speed = EMERGENCY_SPEED
            self.color = EMERGENCY_COLOR
        else:
            self.max_speed = random.uniform(CAR_SPEED_MIN, CAR_SPEED_MAX)
            self.color = random.choice(CAR_COLORS)

        self.speed = self.max_speed
        self.state = VehicleState.MOVING

        self.wait_time = 0
        self.total_time = 0

        # Orient size based on travel direction
        if direction in (Direction.NORTH, Direction.SOUTH):
            self.width = CAR_WIDTH
            self.height = CAR_LENGTH
        else:
            self.width = CAR_LENGTH
            self.height = CAR_WIDTH

        self.rect = pygame.Rect(
            int(self.x - self.width / 2),
            int(self.y - self.height / 2),
            self.width,
            self.height,
        )

    # ─── helpers ────────────────────────────
    def _distance_to_stop_line(self) -> float:
        sx, sy = self.lane.stop_line_pos
        if self.direction == Direction.NORTH:
            return self.y - sy
        elif self.direction == Direction.SOUTH:
            return sy - self.y
        elif self.direction == Direction.EAST:
            return sx - self.x
        elif self.direction == Direction.WEST:
            return self.x - sx
        return 0

    def _past_stop_line(self) -> bool:
        return self._distance_to_stop_line() < -5

    def _in_intersection_zone(self) -> bool:
        return (
            INTERSECTION_LEFT - 5 <= self.x <= INTERSECTION_RIGHT + 5
            and INTERSECTION_TOP - 5 <= self.y <= INTERSECTION_BOTTOM + 5
        )

    # ─── front-vehicle check ───────────────
    def check_front_vehicle(self, vehicles_in_lane) -> float | None:
        """Return the distance to the vehicle directly ahead, or None."""
        best_dist = None
        for other in vehicles_in_lane:
            if other.id == self.id:
                continue
            if self.direction == Direction.NORTH:
                if other.y < self.y:
                    d = self.y - other.y - other.height / 2 - self.height / 2
                    if best_dist is None or d < best_dist:
                        best_dist = d
            elif self.direction == Direction.SOUTH:
                if other.y > self.y:
                    d = other.y - self.y - other.height / 2 - self.height / 2
                    if best_dist is None or d < best_dist:
                        best_dist = d
            elif self.direction == Direction.EAST:
                if other.x > self.x:
                    d = other.x - self.x - other.width / 2 - self.width / 2
                    if best_dist is None or d < best_dist:
                        best_dist = d
            elif self.direction == Direction.WEST:
                if other.x < self.x:
                    d = self.x - other.x - other.width / 2 - self.width / 2
                    if best_dist is None or d < best_dist:
                        best_dist = d
        return best_dist

    # ─── update ────────────────────────────
    def update(self, light_is_green: bool, light_is_yellow: bool):
        """
        Move this vehicle for one frame.

        Args:
            light_is_green: True if this vehicle's direction has green.
            light_is_yellow: True if yellow.
        """
        self.total_time += 1

        dist_stop = self._distance_to_stop_line()
        front_dist = self.check_front_vehicle(self.lane.vehicles)

        # ── Follow car ahead ──
        if front_dist is not None and front_dist < SAFE_DISTANCE + 5:
            self.speed = max(0, self.speed - 0.3)
            if front_dist <= SAFE_DISTANCE:
                self.speed = 0
                self.state = VehicleState.WAITING
                self.wait_time += 1
                self._update_rect()
                return

        # ── Red / yellow light behaviour ──
        if not self._past_stop_line() and not self._in_intersection_zone():
            if not light_is_green:
                if light_is_yellow and dist_stop < 40:
                    # Close to stop line on yellow → keep going
                    pass
                elif dist_stop < 60:
                    # Decelerate as we approach
                    decel = max(0.1, dist_stop / 60) * self.max_speed
                    self.speed = max(0, min(self.speed, decel))
                    if dist_stop < 5:
                        self.speed = 0
                        self.state = VehicleState.WAITING
                        self.wait_time += 1
                        self._update_rect()
                        return

        # ── Accelerate toward max speed ──
        if self.speed < self.max_speed:
            self.speed = min(self.max_speed, self.speed + 0.15)

        if self._in_intersection_zone():
            self.state = VehicleState.CROSSING
        elif self.speed > 0:
            self.state = VehicleState.MOVING
        else:
            self.state = VehicleState.WAITING
            self.wait_time += 1
            self._update_rect()
            return

        # ── Move ──
        if self.direction == Direction.NORTH:
            self.y -= self.speed
        elif self.direction == Direction.SOUTH:
            self.y += self.speed
        elif self.direction == Direction.EAST:
            self.x += self.speed
        elif self.direction == Direction.WEST:
            self.x -= self.speed

        self._update_rect()

    def _update_rect(self):
        self.rect.x = int(self.x - self.width / 2)
        self.rect.y = int(self.y - self.height / 2)

    # ─── despawn check ─────────────────────
    def has_crossed(self) -> bool:
        margin = 30
        if self.direction == Direction.NORTH and self.y < -margin:
            return True
        if self.direction == Direction.SOUTH and self.y > SCREEN_HEIGHT + margin:
            return True
        if self.direction == Direction.EAST and self.x > SCREEN_WIDTH + margin:
            return True
        if self.direction == Direction.WEST and self.x < -margin:
            return True
        return False

    # ─── draw ──────────────────────────────
    def draw(self, screen: pygame.Surface):
        # Body
        body_rect = pygame.Rect(self.rect)
        pygame.draw.rect(screen, self.color, body_rect, border_radius=4)
        # Darker border
        darker = tuple(max(0, c - 40) for c in self.color)
        pygame.draw.rect(screen, darker, body_rect, width=2, border_radius=4)

        cx, cy = self.rect.centerx, self.rect.centery
        hw, hh = self.rect.width // 2, self.rect.height // 2

        # Emergency vehicle special rendering
        if self.is_emergency:
            # White stripe across centre
            if self.direction in (Direction.NORTH, Direction.SOUTH):
                stripe_rect = pygame.Rect(body_rect.x, cy - 3, body_rect.width, 6)
            else:
                stripe_rect = pygame.Rect(cx - 3, body_rect.y, 6, body_rect.height)
            pygame.draw.rect(screen, EMERGENCY_STRIPE_COLOR, stripe_rect)

            # Flashing siren light (alternates red/blue every 8 frames)
            flash = (self.total_time // 8) % 2 == 0
            siren_color = (0, 100, 255) if flash else (255, 0, 0)
            siren_r = 4
            if self.direction in (Direction.NORTH, Direction.SOUTH):
                pygame.draw.circle(screen, siren_color, (cx, cy - hh + 5), siren_r)
            else:
                pygame.draw.circle(screen, siren_color, (cx - hw + 5, cy), siren_r)

            # Glow effect around the vehicle
            glow_surf = pygame.Surface((body_rect.width + 12, body_rect.height + 12), pygame.SRCALPHA)
            glow_color = (*siren_color[:3], 40)
            pygame.draw.rect(glow_surf, glow_color,
                             (0, 0, body_rect.width + 12, body_rect.height + 12),
                             border_radius=8)
            screen.blit(glow_surf, (body_rect.x - 6, body_rect.y - 6))
            return  # skip normal headlights/taillights

        # Headlights & taillights
        hl_color = (255, 255, 180)
        tl_color = (255, 40, 40)
        r = 2

        if self.direction == Direction.NORTH:
            pygame.draw.circle(screen, hl_color, (cx - 4, cy - hh + 3), r)
            pygame.draw.circle(screen, hl_color, (cx + 4, cy - hh + 3), r)
            pygame.draw.circle(screen, tl_color, (cx - 4, cy + hh - 3), r)
            pygame.draw.circle(screen, tl_color, (cx + 4, cy + hh - 3), r)
        elif self.direction == Direction.SOUTH:
            pygame.draw.circle(screen, hl_color, (cx - 4, cy + hh - 3), r)
            pygame.draw.circle(screen, hl_color, (cx + 4, cy + hh - 3), r)
            pygame.draw.circle(screen, tl_color, (cx - 4, cy - hh + 3), r)
            pygame.draw.circle(screen, tl_color, (cx + 4, cy - hh + 3), r)
        elif self.direction == Direction.EAST:
            pygame.draw.circle(screen, hl_color, (cx + hw - 3, cy - 4), r)
            pygame.draw.circle(screen, hl_color, (cx + hw - 3, cy + 4), r)
            pygame.draw.circle(screen, tl_color, (cx - hw + 3, cy - 4), r)
            pygame.draw.circle(screen, tl_color, (cx - hw + 3, cy + 4), r)
        elif self.direction == Direction.WEST:
            pygame.draw.circle(screen, hl_color, (cx - hw + 3, cy - 4), r)
            pygame.draw.circle(screen, hl_color, (cx - hw + 3, cy + 4), r)
            pygame.draw.circle(screen, tl_color, (cx + hw - 3, cy - 4), r)
            pygame.draw.circle(screen, tl_color, (cx + hw - 3, cy + 4), r)

        # Brake lights brighter when waiting
        if self.state == VehicleState.WAITING:
            bright_tl = (255, 0, 0)
            if self.direction == Direction.NORTH:
                pygame.draw.circle(screen, bright_tl, (cx - 4, cy + hh - 3), r + 1)
                pygame.draw.circle(screen, bright_tl, (cx + 4, cy + hh - 3), r + 1)
            elif self.direction == Direction.SOUTH:
                pygame.draw.circle(screen, bright_tl, (cx - 4, cy - hh + 3), r + 1)
                pygame.draw.circle(screen, bright_tl, (cx + 4, cy - hh + 3), r + 1)
            elif self.direction == Direction.EAST:
                pygame.draw.circle(screen, bright_tl, (cx - hw + 3, cy - 4), r + 1)
                pygame.draw.circle(screen, bright_tl, (cx - hw + 3, cy + 4), r + 1)
            elif self.direction == Direction.WEST:
                pygame.draw.circle(screen, bright_tl, (cx + hw - 3, cy - 4), r + 1)
                pygame.draw.circle(screen, bright_tl, (cx + hw - 3, cy + 4), r + 1)


class VehicleSpawner:
    """Spawns vehicles at road entry points."""

    def __init__(self, intersection, spawn_rate: float = 0.05):
        self.intersection = intersection
        self.spawn_rate = spawn_rate

    def set_rate(self, rate: float):
        self.spawn_rate = rate

    def _spawn_clear(self, lane) -> bool:
        """Check that the spawn zone is not blocked."""
        sx, sy = lane.start_pos
        for v in lane.vehicles:
            dist = abs(v.x - sx) + abs(v.y - sy)
            if dist < CAR_LENGTH + SAFE_DISTANCE + 10:
                return False
        return True

    def try_spawn_all_directions(self, all_vehicles: list):
        """Attempt to spawn one vehicle per direction per frame."""
        if len(all_vehicles) >= MAX_VEHICLES:
            return

        for direction in Direction:
            # Check for emergency vehicle spawn
            is_emergency = random.random() < EMERGENCY_SPAWN_RATE

            if not is_emergency and random.random() > self.spawn_rate:
                continue
            lanes = self.intersection.get_incoming_lanes_for(direction)
            lane = random.choice(lanes)
            if not self._spawn_clear(lane):
                continue
            sx, sy = lane.start_pos
            v = Vehicle(direction, lane, sx, sy, is_emergency=is_emergency)
            lane.vehicles.append(v)
            all_vehicles.append(v)
            if is_emergency:
                print(f"🚨 Emergency vehicle spawned heading {direction.name}!")
