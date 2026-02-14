"""
Traffic-Mind – Vehicle & Spawner
Handles individual car physics, rendering, and spawn logic.

Two-phase update architecture:
    1. propose_move()  — compute next position WITHOUT modifying state
    2. commit_move()   — apply an approved MoveProposal
    3. reject_move()   — vehicle is blocked; stop and wait
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

    @staticmethod
    def _pos_in_intersection(x: float, y: float) -> bool:
        return (
            INTERSECTION_LEFT - 5 <= x <= INTERSECTION_RIGHT + 5
            and INTERSECTION_TOP - 5 <= y <= INTERSECTION_BOTTOM + 5
        )

    # ─── front-vehicle check ───────────────
    def check_front_vehicle(self, vehicles_list) -> float | None:
        """Return the distance to the vehicle directly ahead, or None.

        Args:
            vehicles_list: list of vehicles to check against (can be
                           lane-local or global for cross-lane checks).
        """
        best_dist = None
        for other in vehicles_list:
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

    # ═════════════════════════════════════════
    # TWO-PHASE UPDATE
    # ═════════════════════════════════════════

    def propose_move(self, light_is_green: bool, light_is_yellow: bool):
        """
        Phase 1: Calculate the next position / speed WITHOUT modifying state.

        Returns a MoveProposal (imported from simulation.collision).
        """
        from simulation.collision import MoveProposal

        # Start from current position
        next_x = self.x
        next_y = self.y
        next_speed = self.speed
        next_state = self.state

        self.total_time += 1

        dist_stop = self._distance_to_stop_line()
        front_dist = self.check_front_vehicle(self.lane.vehicles)

        # ── Follow car ahead (smooth deceleration) ──
        should_stop = False

        if front_dist is not None and front_dist < SAFE_DISTANCE * 2:
            if front_dist <= SAFE_DISTANCE * 0.25:
                # Very close — hard stop, do NOT move
                next_speed = 0
                next_state = VehicleState.WAITING
                should_stop = True
            elif front_dist <= SAFE_DISTANCE:
                # Within safe distance — scale speed toward zero
                ratio = max(0.0, front_dist / SAFE_DISTANCE)
                next_speed = max(0, self.max_speed * ratio * 0.5)
                if next_speed < 0.1:
                    next_speed = 0
                    next_state = VehicleState.WAITING
                    should_stop = True
            else:
                # Approaching safe distance — gentle deceleration
                ratio = (front_dist - SAFE_DISTANCE) / SAFE_DISTANCE
                target_speed = self.max_speed * min(1.0, ratio)
                if next_speed > target_speed:
                    next_speed = max(0, next_speed - max(0.2, next_speed - target_speed))
                else:
                    next_speed = target_speed

        # ── Red / yellow light behaviour ──
        if not should_stop and not self._past_stop_line() and not self._in_intersection_zone():
            if not light_is_green:
                if light_is_yellow and dist_stop < 40:
                    # Close to stop line on yellow → keep going
                    pass
                elif dist_stop < 80:
                    # Decelerate as we approach
                    decel = max(0.1, dist_stop / 80) * self.max_speed
                    next_speed = max(0, min(next_speed, decel))
                    if dist_stop < 5:
                        next_speed = 0
                        next_state = VehicleState.WAITING
                        should_stop = True

        # ── Accelerate toward max speed ──
        if not should_stop and next_speed < self.max_speed:
            next_speed = min(self.max_speed, next_speed + 0.15)

        # ── Determine state ──
        if should_stop or next_speed <= 0:
            next_speed = 0
            next_state = VehicleState.WAITING
        elif self._pos_in_intersection(next_x, next_y):
            next_state = VehicleState.CROSSING
        else:
            next_state = VehicleState.MOVING

        # ── Compute proposed position ──
        if next_speed > 0:
            if self.direction == Direction.NORTH:
                next_y -= next_speed
            elif self.direction == Direction.SOUTH:
                next_y += next_speed
            elif self.direction == Direction.EAST:
                next_x += next_speed
            elif self.direction == Direction.WEST:
                next_x -= next_speed

        # Build the proposed rect
        next_rect = pygame.Rect(
            int(next_x - self.width / 2),
            int(next_y - self.height / 2),
            self.width,
            self.height,
        )

        proposal = MoveProposal(
            vehicle=self,
            next_x=next_x,
            next_y=next_y,
            next_rect=next_rect,
            next_speed=next_speed,
            next_state=next_state,
        )
        return proposal

    def commit_move(self, proposal) -> None:
        """Phase 2a: Apply an approved MoveProposal to this vehicle."""
        self.x = proposal.next_x
        self.y = proposal.next_y
        self.speed = proposal.next_speed
        self.state = proposal.next_state
        self.rect = proposal.next_rect

        if self.state == VehicleState.WAITING:
            self.wait_time += 1

    def reject_move(self) -> None:
        """Phase 2b: Vehicle's proposal was rejected — stop in place."""
        self.speed = 0
        self.state = VehicleState.WAITING
        self.wait_time += 1
        # rect stays unchanged (vehicle doesn't move)

    # ─── legacy update (kept for backward compat) ──
    def update(self, light_is_green: bool, light_is_yellow: bool):
        """
        Single-call update that proposes and immediately commits.
        Used only by simple loops that don't need collision management.
        """
        proposal = self.propose_move(light_is_green, light_is_yellow)
        self.commit_move(proposal)

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

    def _spawn_clear(self, lane, all_vehicles: list | None = None) -> bool:
        """Check that the spawn zone is not blocked.

        Uses AABB overlap test against all provided vehicles (not just
        same-lane) for robustness.
        """
        sx, sy = lane.start_pos

        # Build a provisional rect for the spawn position
        if lane.direction in (Direction.NORTH, Direction.SOUTH):
            w, h = CAR_WIDTH, CAR_LENGTH
        else:
            w, h = CAR_LENGTH, CAR_WIDTH

        spawn_rect = pygame.Rect(
            int(sx - w / 2), int(sy - h / 2), w, h
        )
        # Inflate by safe distance for clearance
        safe_rect = pygame.Rect(
            spawn_rect.x - SAFE_DISTANCE,
            spawn_rect.y - SAFE_DISTANCE,
            spawn_rect.width + 2 * SAFE_DISTANCE,
            spawn_rect.height + 2 * SAFE_DISTANCE,
        )

        check_list = all_vehicles if all_vehicles is not None else lane.vehicles
        for v in check_list:
            if safe_rect.colliderect(v.rect):
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
            if not self._spawn_clear(lane, all_vehicles):
                continue
            sx, sy = lane.start_pos
            v = Vehicle(direction, lane, sx, sy, is_emergency=is_emergency)
            lane.vehicles.append(v)
            all_vehicles.append(v)
            if is_emergency:
                print(f"🚨 Emergency vehicle spawned heading {direction.name}!")
