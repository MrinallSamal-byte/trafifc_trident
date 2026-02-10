"""
Traffic-Mind – Road Network
Defines Lane, Road, and Intersection for a single 4-way crossing.
"""

import pygame
from config.settings import (
    Direction,
    SCREEN_WIDTH, SCREEN_HEIGHT,
    ROAD_WIDTH, LANE_WIDTH, NUM_LANES,
    INTERSECTION_CENTER_X, INTERSECTION_CENTER_Y,
    INTERSECTION_LEFT, INTERSECTION_RIGHT,
    INTERSECTION_TOP, INTERSECTION_BOTTOM,
    INTERSECTION_SIZE,
)


class Lane:
    """A single lane of traffic heading in one direction."""

    def __init__(self, direction: Direction, lane_index: int):
        """
        Args:
            direction:  which way cars travel
            lane_index: 0 = inner lane (closest to centre line)
                        1 = outer lane
        """
        self.direction = direction
        self.lane_index = lane_index
        self.vehicles = []

        # Compute spawn, stop-line, and despawn positions
        self.start_pos = (0, 0)
        self.stop_line_pos = (0, 0)
        self.end_pos = (0, 0)

        self._compute_geometry()

    # ──────────────────────────────────────────
    def _compute_geometry(self):
        cx = INTERSECTION_CENTER_X
        cy = INTERSECTION_CENTER_Y

        if self.direction == Direction.NORTH:
            # Cars drive upward (from bottom edge toward top edge)
            # Incoming lanes are on the RIGHT side of the vertical road
            x = cx + LANE_WIDTH * self.lane_index + LANE_WIDTH // 2
            self.start_pos = (x, SCREEN_HEIGHT + 20)
            self.stop_line_pos = (x, INTERSECTION_BOTTOM)
            self.end_pos = (x, -20)

        elif self.direction == Direction.SOUTH:
            # Cars drive downward
            # Incoming lanes on the LEFT side of vertical road
            x = cx - LANE_WIDTH * self.lane_index - LANE_WIDTH // 2
            self.start_pos = (x, -20)
            self.stop_line_pos = (x, INTERSECTION_TOP)
            self.end_pos = (x, SCREEN_HEIGHT + 20)

        elif self.direction == Direction.EAST:
            # Cars drive rightward
            # Incoming lanes on the BOTTOM side of horizontal road
            y = cy + LANE_WIDTH * self.lane_index + LANE_WIDTH // 2
            self.start_pos = (-20, y)
            self.stop_line_pos = (INTERSECTION_LEFT, y)
            self.end_pos = (SCREEN_WIDTH + 20, y)

        elif self.direction == Direction.WEST:
            # Cars drive leftward
            # Incoming lanes on the TOP side of horizontal road
            y = cy - LANE_WIDTH * self.lane_index - LANE_WIDTH // 2
            self.start_pos = (SCREEN_WIDTH + 20, y)
            self.stop_line_pos = (INTERSECTION_RIGHT, y)
            self.end_pos = (-20, y)

    def __repr__(self):
        return f"Lane({self.direction.name}, idx={self.lane_index})"


class Road:
    """One of the four roads emanating from the intersection."""

    def __init__(self, direction: Direction):
        self.direction = direction
        # Incoming lanes: cars heading *toward* intersection
        self.incoming_lanes = [Lane(direction, i) for i in range(NUM_LANES)]
        # Outgoing lanes carry cars away – represented as opposite direction
        opposite = self._opposite(direction)
        self.outgoing_lanes = [Lane(opposite, i) for i in range(NUM_LANES)]

    @staticmethod
    def _opposite(d: Direction) -> Direction:
        return {
            Direction.NORTH: Direction.SOUTH,
            Direction.SOUTH: Direction.NORTH,
            Direction.EAST: Direction.WEST,
            Direction.WEST: Direction.EAST,
        }[d]

    def get_incoming_lanes(self):
        return self.incoming_lanes

    def get_outgoing_lanes(self):
        return self.outgoing_lanes


class Intersection:
    """The central 4-way intersection."""

    def __init__(self):
        self.position = (INTERSECTION_CENTER_X, INTERSECTION_CENTER_Y)
        self.roads = {d: Road(d) for d in Direction}

        # pygame rect for the conflict zone
        self.conflict_zone = pygame.Rect(
            INTERSECTION_LEFT,
            INTERSECTION_TOP,
            INTERSECTION_SIZE,
            INTERSECTION_SIZE,
        )

    def get_all_incoming_lanes(self):
        """Return a flat list of every incoming lane."""
        lanes = []
        for road in self.roads.values():
            lanes.extend(road.get_incoming_lanes())
        return lanes

    def get_incoming_lanes_for(self, direction: Direction):
        return self.roads[direction].get_incoming_lanes()

    def is_in_intersection(self, vehicle) -> bool:
        return self.conflict_zone.colliderect(vehicle.rect)
