"""
Traffic-Mind – Vehicle Simulation
Vehicle class with two-phase update and collision-aware movement.
"""

import random
from enum import Enum
import pygame

from config.settings import (
    Direction,
    CAR_LENGTH,
    CAR_WIDTH,
    CAR_SPEED_MIN,
    CAR_SPEED_MAX,
    CAR_COLORS,
    SAFE_DISTANCE,
    KICKSTART_SPEED,
    ACCELERATION_RATE,
    RESUME_THRESHOLD,
    RESUME_SPEED_FACTOR,
    EMERGENCY_COLOR,
    EMERGENCY_STRIPE_COLOR,
    EMERGENCY_SPEED,
    INTERSECTION_LEFT,
    INTERSECTION_RIGHT,
    INTERSECTION_TOP,
    INTERSECTION_BOTTOM,
)


# ═══════════════════════════════════════════════
# Vehicle State Enum
# ═══════════════════════════════════════════════

class VehicleState(Enum):
    """Tracks vehicle's current behavior."""
    WAITING = "WAITING"      # Stopped at red light or behind another car
    MOVING = "MOVING"        # Driving normally
    CROSSING = "CROSSING"    # Currently inside intersection


# ═══════════════════════════════════════════════
# Vehicle Class
# ═══════════════════════════════════════════════

# Global vehicle ID counter
_vehicle_id_counter = 0


class Vehicle:
    """
    A single vehicle with two-phase update:
        1. propose_move() — compute next position/speed without modifying state
        2. commit_move() — apply approved proposal
        3. reject_move() — reject proposal, stop vehicle
    """

    def __init__(self, direction: Direction, lane, x: float, y: float, is_emergency: bool = False):
        """
        Create a vehicle at a specific position.
        
        Args:
            direction: Direction the vehicle is traveling
            lane: Lane object the vehicle belongs to
            x: Initial x position
            y: Initial y position
            is_emergency: Whether this is an emergency vehicle
        """
        global _vehicle_id_counter
        self.id = _vehicle_id_counter
        _vehicle_id_counter += 1

        self.direction = direction
        self.lane = lane
        self.x = float(x)
        self.y = float(y)
        self.is_emergency = is_emergency

        # Speed and state
        if is_emergency:
            self.max_speed = EMERGENCY_SPEED
            self.speed = EMERGENCY_SPEED
        else:
            self.max_speed = random.uniform(CAR_SPEED_MIN, CAR_SPEED_MAX)
            self.speed = self.max_speed
        
        self.state = VehicleState.MOVING

        # Dimensions (swap for E/W vehicles)
        if direction in (Direction.NORTH, Direction.SOUTH):
            self.width = CAR_WIDTH
            self.height = CAR_LENGTH
        else:
            self.width = CAR_LENGTH
            self.height = CAR_WIDTH

        # Visual appearance
        if is_emergency:
            self.color = EMERGENCY_COLOR
        else:
            self.color = random.choice(CAR_COLORS)

        # Collision rect
        self.rect = pygame.Rect(
            int(self.x - self.width / 2),
            int(self.y - self.height / 2),
            self.width,
            self.height,
        )

        # Metrics
        self.wait_time = 0      # frames spent waiting
        self.total_time = 0     # total frames alive

    # ────────────────────────────────────────────
    # Two-Phase Update Methods
    # ────────────────────────────────────────────

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
            if front_dist <= SAFE_DISTANCE * 0.1:
                # Extremely close — hard stop to avoid rear-end collision
                next_speed = 0
                next_state = VehicleState.WAITING
                should_stop = True
            elif front_dist <= SAFE_DISTANCE:
                # Within safe distance — match speed proportionally
                ratio = max(0.0, front_dist / SAFE_DISTANCE)
                # If currently stopped (speed=0), give a kick-start when there's room
                if self.speed == 0 and ratio > RESUME_THRESHOLD:
                    next_speed = self.max_speed * ratio * RESUME_SPEED_FACTOR
                else:
                    # Smooth linear deceleration — don't compound with current speed
                    next_speed = self.max_speed * ratio * 0.8
                if next_speed < 0.05:
                    next_speed = 0
                    next_state = VehicleState.WAITING
                    should_stop = True
            else:
                # Approaching safe distance — gentle deceleration
                ratio = (front_dist - SAFE_DISTANCE) / SAFE_DISTANCE
                target_speed = self.max_speed * min(1.0, ratio)
                next_speed = max(target_speed, next_speed * 0.9)

        # ── Red / yellow light behaviour ──
        slowing_for_light = False
        if not should_stop and not self._past_stop_line() and not self._in_intersection_zone():
            if not light_is_green:
                slowing_for_light = True
                if light_is_yellow and dist_stop < 40:
                    # Close to stop line on yellow → keep going
                    slowing_for_light = False
                    pass
                elif dist_stop < 80:
                    # Decelerate as we approach
                    decel = max(0.1, dist_stop / 80) * self.max_speed
                    next_speed = max(0, min(next_speed, decel))
                    if dist_stop < 5:
                        next_speed = 0
                        next_state = VehicleState.WAITING
                        should_stop = True
            
            # ── DON'T BLOCK THE BOX ──
            # Even if light is GREEN, don't enter if we can't clear the intersection!
            elif light_is_green and dist_stop < 20:
                # We are about to enter the intersection. Check if there is space on the other side.
                # Intersection span is typically ~160px. We want at least (Intersection + Car + Margin) clear.
                required_clearance = (INTERSECTION_BOTTOM - INTERSECTION_TOP) + self.height + SAFE_DISTANCE
                
                if front_dist is not None and front_dist < required_clearance:
                    # The car ahead is blocking the exit or is just inside the intersection.
                    # Stop here to keep the intersection clear for cross traffic.
                    next_speed = 0
                    next_state = VehicleState.WAITING
                    should_stop = True

        # ── JAM BUSTER FAILSAFE ──
        # If vehicle has been waiting too long but path seems clear (no car ahead), force resume.
        if self.state == VehicleState.WAITING and self.wait_time > 150:
            # 150 frames = 2.5 seconds (Faster recovery)
            # from config.settings import SAFE_DISTANCE, KICKSTART_SPEED  <-- REMOVED
            dist_to_front = self.check_front_vehicle(self.lane.vehicles)
            
            # If no car ahead OR car ahead is far away
            if dist_to_front is None or dist_to_front > SAFE_DISTANCE * 2:
                # But check if we are stopped at a RED light
                if not light_is_green and not self._past_stop_line() and not self._in_intersection_zone() and dist_stop < 10:
                    # Correctly stopped at red light — do nothing
                    pass
                else:
                    # We are stuck for no good reason (phantom jam) -> Force move
                    should_stop = False
                    next_state = VehicleState.MOVING
                    next_speed = KICKSTART_SPEED
                    # Reset wait time so we don't trigger this every frame if it persists
                    self.wait_time = 0

        # ── Accelerate toward max speed ──
        # FIX: If stopped and no obstacles, give a stronger initial acceleration
        # Only accelerate if we are NOT intentionally slowing for a red light
        if not should_stop and not slowing_for_light and next_speed < self.max_speed:
            if self.speed == 0 and next_speed == 0:
                # Vehicle was stopped and no immediate obstacles — resume with stronger kick
                next_speed = min(self.max_speed, KICKSTART_SPEED)
            else:
                next_speed = min(self.max_speed, next_speed + ACCELERATION_RATE)

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

        # Return proposal (priority will be computed by CollisionManager)
        return MoveProposal(
            vehicle=self,
            next_x=next_x,
            next_y=next_y,
            next_speed=next_speed,
            next_state=next_state,
            next_rect=next_rect,
            approved=True,
        )

    def commit_move(self, proposal):
        """
        Phase 2: Apply an approved move proposal.
        """
        self.x = proposal.next_x
        self.y = proposal.next_y
        self.speed = proposal.next_speed
        self.state = proposal.next_state
        self._update_rect()

        # Update metrics
        if self.state == VehicleState.WAITING:
            self.wait_time += 1
        else:
            self.wait_time = 0

    def reject_move(self):
        """
        Phase 2 (alternative): Reject the proposal, vehicle stops in place.
        """
        self.speed = 0
        self.state = VehicleState.WAITING
        self.wait_time += 1

    # ────────────────────────────────────────────
    # Helper Methods
    # ────────────────────────────────────────────

    def check_front_vehicle(self, vehicles):
        """
        Return distance to the vehicle directly in front, or None if no vehicle ahead.
        
        Distance is measured from the front of this vehicle to the back of the front vehicle.
        """
        min_dist = None
        for other in vehicles:
            if other.id == self.id:
                continue

            # Check if other is ahead in the same lane
            if self.direction == Direction.NORTH:
                if other.y < self.y:
                    # other is ahead (lower y)
                    # Distance = (my y - my half-height) - (other y + other half-height)
                    dist = (self.y - self.height / 2) - (other.y + other.height / 2)
                    if dist >= 0:
                        if min_dist is None or dist < min_dist:
                            min_dist = dist
            elif self.direction == Direction.SOUTH:
                if other.y > self.y:
                    dist = (other.y - other.height / 2) - (self.y + self.height / 2)
                    if dist >= 0:
                        if min_dist is None or dist < min_dist:
                            min_dist = dist
            elif self.direction == Direction.EAST:
                if other.x > self.x:
                    dist = (other.x - other.width / 2) - (self.x + self.width / 2)
                    if dist >= 0:
                        if min_dist is None or dist < min_dist:
                            min_dist = dist
            elif self.direction == Direction.WEST:
                if other.x < self.x:
                    dist = (self.x - self.width / 2) - (other.x + other.width / 2)
                    if dist >= 0:
                        if min_dist is None or dist < min_dist:
                            min_dist = dist

        return min_dist

    def _distance_to_stop_line(self) -> float:
        """Return distance from front of vehicle to the stop line."""
        sx, sy = self.lane.stop_line_pos

        if self.direction == Direction.NORTH:
            return (self.y - self.height / 2) - sy
        elif self.direction == Direction.SOUTH:
            return sy - (self.y + self.height / 2)
        elif self.direction == Direction.EAST:
            return sx - (self.x + self.width / 2)
        elif self.direction == Direction.WEST:
            return (self.x - self.width / 2) - sx
        return 0.0

    def _past_stop_line(self) -> bool:
        """Return True if the vehicle has crossed the stop line."""
        return self._distance_to_stop_line() < 0

    def _in_intersection_zone(self) -> bool:
        """Return True if vehicle's center is inside the intersection."""
        return self._pos_in_intersection(self.x, self.y)

    def _pos_in_intersection(self, x: float, y: float) -> bool:
        """Return True if given position is inside the intersection."""
        return (
            INTERSECTION_LEFT <= x <= INTERSECTION_RIGHT
            and INTERSECTION_TOP <= y <= INTERSECTION_BOTTOM
        )

    def _update_rect(self):
        """Update collision rect to match current position."""
        self.rect.x = int(self.x - self.width / 2)
        self.rect.y = int(self.y - self.height / 2)
        self.rect.width = self.width
        self.rect.height = self.height

    def has_crossed(self) -> bool:
        """Return True if the vehicle has left the visible area (despawned)."""
        sx, sy = self.lane.end_pos
        
        # Check if vehicle has reached the despawn position
        if self.direction == Direction.NORTH:
            return self.y < sy
        elif self.direction == Direction.SOUTH:
            return self.y > sy
        elif self.direction == Direction.EAST:
            return self.x > sx
        elif self.direction == Direction.WEST:
            return self.x < sx
        return False

    # ────────────────────────────────────────────
    # Rendering
    # ────────────────────────────────────────────

    def draw(self, screen: pygame.Surface):
        """Render the vehicle on screen."""
        # Draw main body
        pygame.draw.rect(screen, self.color, self.rect, border_radius=3)

        # Emergency vehicles get a stripe
        if self.is_emergency:
            MIN_STRIPE_WIDTH = 3
            stripe_width = max(MIN_STRIPE_WIDTH, self.width // 4)
            if self.direction in (Direction.NORTH, Direction.SOUTH):
                stripe_rect = pygame.Rect(
                    self.rect.x + (self.width - stripe_width) // 2,
                    self.rect.y,
                    stripe_width,
                    self.height,
                )
            else:
                stripe_rect = pygame.Rect(
                    self.rect.x,
                    self.rect.y + (self.height - stripe_width) // 2,
                    self.width,
                    stripe_width,
                )
            pygame.draw.rect(screen, EMERGENCY_STRIPE_COLOR, stripe_rect)

        # Border for definition
        border_color = tuple(max(0, c - 40) for c in self.color)
        pygame.draw.rect(screen, border_color, self.rect, width=1, border_radius=3)


# ═══════════════════════════════════════════════
# VehicleSpawner Class
# ═══════════════════════════════════════════════

class VehicleSpawner:
    """
    Spawns new vehicles at the edges of the screen.
    Ensures no vehicle spawns on top of another.
    """

    def __init__(self, intersection, spawn_rate: float):
        """
        Args:
            intersection: Intersection object with lane information
            spawn_rate: Probability per frame per direction to spawn a vehicle
        """
        self.intersection = intersection
        self.spawn_rate = spawn_rate

    def should_spawn(self) -> bool:
        """Random check against spawn rate."""
        return random.random() < self.spawn_rate

    def set_rate(self, spawn_rate: float) -> None:
        """Update spawn probability used for future spawn checks."""
        self.spawn_rate = spawn_rate

    def spawn_vehicle(self, direction: Direction, lane, is_emergency: bool = False) -> Vehicle:
        """
        Create a new vehicle at the lane's starting position.
        
        Args:
            direction: Direction the vehicle will travel
            lane: Lane object to spawn in
            is_emergency: Whether to spawn an emergency vehicle
            
        Returns:
            New Vehicle instance
        """
        x, y = lane.start_pos
        vehicle = Vehicle(direction, lane, x, y, is_emergency=is_emergency)
        lane.vehicles.append(vehicle)
        return vehicle

    def is_spawn_zone_clear(self, lane, spawn_radius: float = 60.0) -> bool:
        """
        Check if the spawn zone is clear of other vehicles.
        
        Args:
            lane: Lane to check
            spawn_radius: Minimum distance required from spawn point
            
        Returns:
            True if zone is clear, False otherwise
        """
        sx, sy = lane.start_pos
        for v in lane.vehicles:
            dx = v.x - sx
            dy = v.y - sy
            dist = (dx * dx + dy * dy) ** 0.5
            if dist < spawn_radius:
                return False
        return True

    def try_spawn_all_directions(self, vehicles_list: list) -> None:
        """
        Attempt to spawn vehicles in all directions.
        Respects per-direction queue caps to prevent congestion buildup.
        
        Args:
            vehicles_list: Global list to add new vehicles to
        """
        from config.settings import EMERGENCY_SPAWN_RATE, MAX_VEHICLES, MAX_QUEUE_PER_DIRECTION
        
        # Don't spawn if at vehicle limit
        if len(vehicles_list) >= MAX_VEHICLES:
            return
        
        # Count vehicles per direction for queue-aware spawning
        dir_counts = {d: 0 for d in Direction}
        for v in vehicles_list:
            dir_counts[v.direction] += 1
        
        # Try spawning in each direction
        for direction in Direction:
            # Skip if queue is already at capacity for this direction
            if dir_counts[direction] >= MAX_QUEUE_PER_DIRECTION:
                continue
            
            # Check if we should spawn
            if not self.should_spawn():
                continue
            
            # Get incoming lanes for this direction
            incoming_lanes = self.intersection.get_incoming_lanes_for(direction)
            if not incoming_lanes:
                continue
            
            # Pick a random lane
            lane = random.choice(incoming_lanes)
            
            # Check if spawn zone is clear
            if not self.is_spawn_zone_clear(lane):
                continue
            
            # Randomly spawn emergency vehicle
            is_emergency = random.random() < EMERGENCY_SPAWN_RATE
            
            # Create and add vehicle
            vehicle = self.spawn_vehicle(direction, lane, is_emergency=is_emergency)
            vehicles_list.append(vehicle)
