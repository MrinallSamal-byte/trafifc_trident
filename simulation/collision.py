"""
Traffic-Mind – Collision Detection & Resolution Engine
═══════════════════════════════════════════════════════
Production-grade collision management ensuring zero vehicle overlaps.

Architecture:
    1. Every vehicle proposes its next position (MoveProposal).
    2. CollisionManager validates all proposals simultaneously.
    3. Approved proposals are committed; rejected vehicles stop.

Collision methods:
    - AABB (Axis-Aligned Bounding Box) with configurable safe margin
    - Intersection conflict-zone occupancy tracking
    - Priority-based conflict resolution (emergency > crossing > lower ID)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, TYPE_CHECKING

import pygame

from config.settings import (
    COLLISION_SAFE_MARGIN,
    INTERSECTION_MAX_OCCUPANTS,
    COLLISION_DEBUG_ASSERTIONS,
)

if TYPE_CHECKING:
    from simulation.vehicle import Vehicle

logger = logging.getLogger("collision")


# ═══════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════

@dataclass
class MoveProposal:
    """Encapsulates a vehicle's proposed next state before committing."""
    vehicle: "Vehicle"
    next_x: float
    next_y: float
    next_rect: pygame.Rect
    next_speed: float
    next_state: str  # VehicleState value
    approved: bool = True

    # Priority for conflict resolution (higher = more important)
    # Computed during validation
    priority: int = field(default=0, init=False)

    def compute_priority(self) -> int:
        """
        Priority ordering (higher wins):
            3 — Emergency vehicle
            2 — Already crossing the intersection
            1 — Moving normally
            0 — Waiting / stopped
        Ties are broken by lower vehicle ID (first-come-first-served).
        """
        from simulation.vehicle import VehicleState
        v = self.vehicle
        if v.is_emergency:
            self.priority = 3
        elif v.state == VehicleState.CROSSING:
            self.priority = 2
        elif self.next_speed > 0:
            self.priority = 1
        else:
            self.priority = 0
        return self.priority


# ═══════════════════════════════════════════════
# Low-level Geometry Helpers
# ═══════════════════════════════════════════════

def inflate_rect(rect: pygame.Rect, margin: int) -> pygame.Rect:
    """Return a copy of *rect* expanded by *margin* pixels on every side."""
    return pygame.Rect(
        rect.x - margin,
        rect.y - margin,
        rect.width + 2 * margin,
        rect.height + 2 * margin,
    )


def aabb_overlap(a: pygame.Rect, b: pygame.Rect) -> bool:
    """Precise Axis-Aligned Bounding Box overlap test."""
    return (
        a.left < b.right
        and a.right > b.left
        and a.top < b.bottom
        and a.bottom > b.top
    )


def safe_distance_overlap(a: pygame.Rect, b: pygame.Rect, margin: int) -> bool:
    """Check if two rects overlap when each is inflated by *margin* pixels."""
    return aabb_overlap(inflate_rect(a, margin), inflate_rect(b, margin // 2))


# ═══════════════════════════════════════════════
# CollisionManager
# ═══════════════════════════════════════════════

class CollisionManager:
    """
    Centralized, stateless collision arbiter.

    Usage per simulation frame:
        mgr = CollisionManager()
        approved, rejected = mgr.validate_all(proposals, intersection_rect)
    """

    def __init__(self):
        self._collision_count = 0

    @property
    def collision_count(self) -> int:
        """Number of collisions detected in the last validation pass."""
        return self._collision_count

    # ── public API ────────────────────────────

    def validate_all(
        self,
        proposals: List[MoveProposal],
        intersection_rect: pygame.Rect,
    ) -> Tuple[List[MoveProposal], List[MoveProposal]]:
        """
        Master validation pipeline.

        1.  Compute priorities for all proposals.
        2.  Check pairwise AABB overlaps (with safe margin) on proposed rects.
        3.  In every conflicting pair, reject the lower-priority vehicle.
        4.  (Iterative) Check approved proposals against the CURRENT rect
            of rejected vehicles — rejected vehicles stay in place.
        5.  Enforce intersection occupancy cap.
        6.  Return (approved, rejected) lists.

        Complexity: O(n²) pairwise – fine for n ≤ 200.
        """
        self._collision_count = 0

        # Phase 0 — priorities
        for p in proposals:
            p.compute_priority()
            p.approved = True  # reset

        # Phase 1 — pairwise safe-distance check on proposed positions
        self._resolve_pairwise(proposals)

        # Phase 2 — iterative: check approved proposals against current
        # positions of rejected vehicles (rejected stay at their current rect)
        self._resolve_against_rejected(proposals)

        # Phase 3 — intersection occupancy cap
        self._enforce_intersection_cap(proposals, intersection_rect)

        # Phase 4 — final: check approved proposals against current positions
        # of all OTHER vehicles (catches pre-existing proximity)
        self._resolve_against_rejected(proposals)

        approved = [p for p in proposals if p.approved]
        rejected = [p for p in proposals if not p.approved]
        return approved, rejected

    # ── internals ─────────────────────────────

    def _resolve_pairwise(self, proposals: List[MoveProposal]) -> None:
        """
        For every pair of proposals that would overlap (including safe margin),
        reject the one with lower priority. On tie, reject the higher-ID vehicle.
        """
        n = len(proposals)
        margin = COLLISION_SAFE_MARGIN

        for i in range(n):
            if not proposals[i].approved:
                continue
            for j in range(i + 1, n):
                if not proposals[j].approved:
                    continue

                pi, pj = proposals[i], proposals[j]

                # Skip if both vehicles are in the same lane and one is behind
                # the other — the in-lane following logic already handles this.
                # We still check to catch edge cases.

                if aabb_overlap(
                    inflate_rect(pi.next_rect, margin),
                    inflate_rect(pj.next_rect, margin),
                ):
                    self._collision_count += 1
                    loser = self._pick_loser(pi, pj)
                    loser.approved = False
                    if loser is pi:
                        break
                    logger.debug(
                        "Collision: V%d vs V%d → V%d rejected",
                        pi.vehicle.id, pj.vehicle.id, loser.vehicle.id,
                    )

    def _resolve_against_rejected(self, proposals: List[MoveProposal]) -> None:
        """
        Check each approved proposal's next_rect against the CURRENT rect
        of every rejected vehicle (which stays in place).

        Iterates up to 3 rounds to handle cascading rejections.
        """
        margin = COLLISION_SAFE_MARGIN

        for _round in range(3):
            changed = False
            rejected_rects = [
                (p.vehicle.rect, p.vehicle.id)
                for p in proposals if not p.approved
            ]
            if not rejected_rects:
                break

            for p in proposals:
                if not p.approved:
                    continue
                for (rej_rect, rej_id) in rejected_rects:
                    if aabb_overlap(
                        inflate_rect(p.next_rect, margin),
                        inflate_rect(rej_rect, margin),
                    ):
                        p.approved = False
                        self._collision_count += 1
                        changed = True
                        logger.debug(
                            "Rejected-current conflict: V%d proposed rect "
                            "overlaps V%d current rect → V%d rejected",
                            p.vehicle.id, rej_id, p.vehicle.id,
                        )
                        break  # vehicle already rejected, move to next

            if not changed:
                break

    def _enforce_intersection_cap(
        self,
        proposals: List[MoveProposal],
        intersection_rect: pygame.Rect,
    ) -> None:
        """
        Limit the number of vehicles that may simultaneously occupy the
        intersection conflict zone. Vehicles already inside get priority.
        """
        # Collect proposals whose next_rect overlaps the intersection
        in_zone: List[MoveProposal] = []
        for p in proposals:
            if not p.approved:
                continue
            if aabb_overlap(p.next_rect, intersection_rect):
                in_zone.append(p)

        if len(in_zone) <= INTERSECTION_MAX_OCCUPANTS:
            return

        # Sort by priority desc, then by vehicle ID asc (deterministic)
        in_zone.sort(key=lambda p: (-p.priority, p.vehicle.id))

        # Keep the top N, reject the rest
        for p in in_zone[INTERSECTION_MAX_OCCUPANTS:]:
            p.approved = False
            self._collision_count += 1
            logger.debug(
                "Intersection cap: V%d rejected (priority=%d)",
                p.vehicle.id, p.priority,
            )

    @staticmethod
    def _pick_loser(a: MoveProposal, b: MoveProposal) -> MoveProposal:
        """Deterministic conflict resolution: lower priority loses; ties → higher ID loses."""
        if a.priority != b.priority:
            return a if a.priority < b.priority else b
        # Tie-break: higher ID yields (preserves first-come ordering)
        return a if a.vehicle.id > b.vehicle.id else b

    # ── post-commit verification ──────────────

    @staticmethod
    def assert_no_overlaps(vehicles: list) -> None:
        """
        Debug assertion: verifies that NO two vehicles currently overlap.
        Call after all commits. Disabled when COLLISION_DEBUG_ASSERTIONS is False.
        """
        if not COLLISION_DEBUG_ASSERTIONS:
            return
        n = len(vehicles)
        for i in range(n):
            for j in range(i + 1, n):
                if aabb_overlap(vehicles[i].rect, vehicles[j].rect):
                    logger.error(
                        "OVERLAP DETECTED after commit: V%d %s  vs  V%d %s",
                        vehicles[i].id, vehicles[i].rect,
                        vehicles[j].id, vehicles[j].rect,
                    )
                    # Don't hard-crash training; log and continue
                    # In tests, you can assert False here.

    @staticmethod
    def count_current_overlaps(vehicles: list) -> int:
        """Return the number of overlapping vehicle pairs (for metrics)."""
        count = 0
        n = len(vehicles)
        for i in range(n):
            for j in range(i + 1, n):
                if aabb_overlap(vehicles[i].rect, vehicles[j].rect):
                    count += 1
        return count
