"""
Traffic-Mind – Collision Detection Tests
═════════════════════════════════════════
Verifies that the collision engine and two-phase update pipeline
guarantee zero vehicle overlaps under all conditions.

Run: python -m pytest tests/test_collision.py -v
  or: python tests/test_collision.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame
pygame.init()  # needed for Rect

from config.settings import Direction, SAFE_DISTANCE
from simulation.collision import (
    aabb_overlap,
    inflate_rect,
    safe_distance_overlap,
    CollisionManager,
    MoveProposal,
)
from simulation.vehicle import Vehicle, VehicleState, VehicleSpawner
from simulation.road_network import Intersection


# ─── helpers ────────────────────────────
def _make_vehicle(direction, lane, x, y, is_emergency=False):
    """Create a vehicle at specific position."""
    return Vehicle(direction, lane, x, y, is_emergency=is_emergency)


def _get_lane(intersection, direction, index=0):
    """Get a lane by direction and index."""
    return intersection.get_incoming_lanes_for(direction)[index]


# ═══════════════════════════════════════════
# AABB geometry tests
# ═══════════════════════════════════════════

def test_aabb_overlap_true():
    a = pygame.Rect(0, 0, 10, 10)
    b = pygame.Rect(5, 5, 10, 10)
    assert aabb_overlap(a, b), "Overlapping rects should be detected"


def test_aabb_overlap_false():
    a = pygame.Rect(0, 0, 10, 10)
    b = pygame.Rect(20, 20, 10, 10)
    assert not aabb_overlap(a, b), "Non-overlapping rects should not be detected"


def test_aabb_adjacent_no_overlap():
    """Touching but not overlapping (edge-to-edge)."""
    a = pygame.Rect(0, 0, 10, 10)
    b = pygame.Rect(10, 0, 10, 10)
    assert not aabb_overlap(a, b), "Adjacent rects should not overlap"


def test_inflate_rect():
    r = pygame.Rect(10, 10, 20, 20)
    inflated = inflate_rect(r, 5)
    assert inflated.x == 5
    assert inflated.y == 5
    assert inflated.width == 30
    assert inflated.height == 30


def test_safe_distance_overlap():
    a = pygame.Rect(0, 0, 10, 10)
    b = pygame.Rect(12, 0, 10, 10)  # 2px gap
    assert not aabb_overlap(a, b), "Base rects don't overlap"
    assert safe_distance_overlap(a, b, 5), "Should overlap with margin"


# ═══════════════════════════════════════════
# CollisionManager tests
# ═══════════════════════════════════════════

def test_no_collision_when_apart():
    """Two vehicles far apart should both be approved."""
    intersection = Intersection()
    lane_n = _get_lane(intersection, Direction.NORTH, 0)
    lane_s = _get_lane(intersection, Direction.SOUTH, 0)

    v1 = _make_vehicle(Direction.NORTH, lane_n, 300, 700)
    v2 = _make_vehicle(Direction.SOUTH, lane_s, 300, 100)

    p1 = MoveProposal(vehicle=v1, next_x=300, next_y=698,
                       next_rect=pygame.Rect(291, 683, 18, 30),
                       next_speed=2.0, next_state=VehicleState.MOVING)
    p2 = MoveProposal(vehicle=v2, next_x=300, next_y=102,
                       next_rect=pygame.Rect(291, 87, 18, 30),
                       next_speed=2.0, next_state=VehicleState.MOVING)

    mgr = CollisionManager()
    approved, rejected = mgr.validate_all([p1, p2], intersection.conflict_zone)
    assert len(approved) == 2
    assert len(rejected) == 0


def test_collision_blocks_lower_priority():
    """When two vehicles collide, at least one is rejected."""
    intersection = Intersection()
    lane = _get_lane(intersection, Direction.NORTH, 0)

    v1 = _make_vehicle(Direction.NORTH, lane, 300, 400)
    v2 = _make_vehicle(Direction.NORTH, lane, 300, 402)  # very close!

    # Both propose nearly identical positions
    p1 = MoveProposal(vehicle=v1, next_x=300, next_y=398,
                       next_rect=pygame.Rect(291, 383, 18, 30),
                       next_speed=2.0, next_state=VehicleState.MOVING)
    p2 = MoveProposal(vehicle=v2, next_x=300, next_y=400,
                       next_rect=pygame.Rect(291, 385, 18, 30),
                       next_speed=2.0, next_state=VehicleState.MOVING)

    mgr = CollisionManager()
    approved, rejected = mgr.validate_all([p1, p2], intersection.conflict_zone)
    assert len(rejected) >= 1, "At least one vehicle must be rejected"
    assert mgr.collision_count > 0


def test_emergency_vehicle_gets_priority():
    """Emergency vehicle should win conflict resolution."""
    intersection = Intersection()
    lane = _get_lane(intersection, Direction.NORTH, 0)

    # Place vehicles far enough that the winner's proposed rect doesn't
    # overlap the loser's current rect (which would trigger cascading rejection)
    v_normal = _make_vehicle(Direction.NORTH, lane, 300, 500)
    v_emerg = _make_vehicle(Direction.NORTH, lane, 300, 460, is_emergency=True)

    # Propose positions that overlap each other
    p_normal = MoveProposal(vehicle=v_normal, next_x=300, next_y=470,
                             next_rect=pygame.Rect(291, 455, 18, 30),
                             next_speed=2.0, next_state=VehicleState.MOVING)
    p_emerg = MoveProposal(vehicle=v_emerg, next_x=300, next_y=458,
                            next_rect=pygame.Rect(291, 443, 18, 30),
                            next_speed=5.0, next_state=VehicleState.MOVING)

    mgr = CollisionManager()
    approved, rejected = mgr.validate_all([p_normal, p_emerg], intersection.conflict_zone)

    # Emergency should be approved, normal rejected
    approved_ids = {p.vehicle.id for p in approved}
    rejected_ids = {p.vehicle.id for p in rejected}
    assert v_emerg.id in approved_ids, "Emergency vehicle should be approved"
    assert v_normal.id in rejected_ids, "Normal vehicle should be rejected"


def test_intersection_cap():
    """Intersection should not have more than INTERSECTION_MAX_OCCUPANTS."""
    from config.settings import INTERSECTION_MAX_OCCUPANTS
    intersection = Intersection()
    lane = _get_lane(intersection, Direction.NORTH, 0)

    iz = intersection.conflict_zone
    cx, cy = iz.centerx, iz.centery

    proposals = []
    vehicles = []
    for i in range(INTERSECTION_MAX_OCCUPANTS + 4):
        v = _make_vehicle(Direction.NORTH, lane, cx + i * 2, cy)
        vehicles.append(v)
        # Place the proposed rect inside the intersection
        p = MoveProposal(
            vehicle=v,
            next_x=cx + i * 2,
            next_y=cy,
            next_rect=pygame.Rect(cx + i * 2 - 9, cy - 15, 18, 30),
            next_speed=2.0,
            next_state=VehicleState.CROSSING,
        )
        proposals.append(p)

    mgr = CollisionManager()
    approved, rejected = mgr.validate_all(proposals, intersection.conflict_zone)

    # Some should be in the intersection (up to cap), others rejected
    in_zone_approved = [p for p in approved if aabb_overlap(p.next_rect, iz)]
    assert len(in_zone_approved) <= INTERSECTION_MAX_OCCUPANTS


def test_propose_commit_pipeline():
    """Propose → commit should update vehicle position correctly."""
    intersection = Intersection()
    lane = _get_lane(intersection, Direction.NORTH, 0)
    v = _make_vehicle(Direction.NORTH, lane, 300, 700)

    old_y = v.y
    proposal = v.propose_move(light_is_green=True, light_is_yellow=False)
    v.commit_move(proposal)

    assert v.y < old_y, "Northbound vehicle should have moved up"
    assert v.speed > 0, "Vehicle should have non-zero speed"


def test_propose_reject_pipeline():
    """Reject should keep vehicle at original position."""
    intersection = Intersection()
    lane = _get_lane(intersection, Direction.NORTH, 0)
    v = _make_vehicle(Direction.NORTH, lane, 300, 700)

    old_x, old_y = v.x, v.y
    _ = v.propose_move(light_is_green=True, light_is_yellow=False)
    v.reject_move()

    assert v.x == old_x and v.y == old_y, "Rejected vehicle should not move"
    assert v.speed == 0, "Rejected vehicle should have zero speed"
    assert v.state == VehicleState.WAITING


def test_vehicle_resumes_after_rejection():
    """Vehicle should resume moving after its proposal is rejected and the
    blocking vehicle moves away (i.e. speed must recover from zero)."""
    intersection = Intersection()
    lane = _get_lane(intersection, Direction.NORTH, 0)
    v = _make_vehicle(Direction.NORTH, lane, 300, 700)

    # 1. Normal propose → reject (simulates stopping for cross-traffic)
    _ = v.propose_move(light_is_green=True, light_is_yellow=False)
    v.reject_move()
    assert v.speed == 0, "Vehicle should be stopped after rejection"

    # 2. On the next frame, with no obstacles, the vehicle should propose
    #    a move with positive speed (i.e. it resumes)
    proposal = v.propose_move(light_is_green=True, light_is_yellow=False)
    assert proposal.next_speed > 0, (
        "Vehicle with speed=0 should propose positive speed when unblocked"
    )
    v.commit_move(proposal)
    assert v.speed > 0, "Vehicle should have resumed moving"
    assert v.state != VehicleState.WAITING, "Vehicle should no longer be WAITING"


def test_vehicle_resumes_after_front_vehicle_leaves():
    """Vehicle stopped behind another should resume when the front car moves
    far enough away."""
    intersection = Intersection()
    lane = _get_lane(intersection, Direction.NORTH, 0)

    # Front vehicle far ahead; back vehicle was previously rejected (speed=0)
    v_front = _make_vehicle(Direction.NORTH, lane, 300, 600)
    v_back = _make_vehicle(Direction.NORTH, lane, 300, 700)
    lane.vehicles.extend([v_front, v_back])

    # Simulate previous rejection
    v_back.speed = 0
    v_back.state = VehicleState.WAITING

    # Front vehicle is 100px ahead (> 2*SAFE_DISTANCE=80), should not impede
    proposal = v_back.propose_move(light_is_green=True, light_is_yellow=False)
    assert proposal.next_speed > 0, (
        "Back vehicle should propose positive speed when front is far away"
    )

    # Now test with front vehicle within SAFE_DISTANCE but not too close
    lane.vehicles.clear()
    v_front2 = _make_vehicle(Direction.NORTH, lane, 300, 670)
    v_back2 = _make_vehicle(Direction.NORTH, lane, 300, 700)
    lane.vehicles.extend([v_front2, v_back2])
    v_back2.speed = 0
    v_back2.state = VehicleState.WAITING

    # front_dist = 700 - 655 - 15 - 15 = 15, within SAFE_DISTANCE but above hard-stop threshold
    v_front2.y = 655
    v_front2._update_rect()

    proposal2 = v_back2.propose_move(light_is_green=True, light_is_yellow=False)
    # front_dist = 15, ratio = 15/40 = 0.375
    # next_speed = max_speed * 0.375 * 0.5 > 0
    assert proposal2.next_speed > 0, (
        "Back vehicle should propose positive speed even when starting from 0, "
        "if front vehicle is within SAFE_DISTANCE but not too close"
    )


def test_assert_no_overlaps_clean():
    """assert_no_overlaps should pass for well-separated vehicles."""
    intersection = Intersection()
    lane_n = _get_lane(intersection, Direction.NORTH, 0)
    lane_s = _get_lane(intersection, Direction.SOUTH, 0)

    v1 = _make_vehicle(Direction.NORTH, lane_n, 300, 700)
    v2 = _make_vehicle(Direction.SOUTH, lane_s, 300, 100)

    # Should not raise
    CollisionManager.assert_no_overlaps([v1, v2])


def test_count_overlaps():
    """count_current_overlaps should correctly count overlapping pairs."""
    intersection = Intersection()
    lane = _get_lane(intersection, Direction.NORTH, 0)

    v1 = _make_vehicle(Direction.NORTH, lane, 300, 400)
    v2 = _make_vehicle(Direction.NORTH, lane, 300, 400)  # exact same spot

    count = CollisionManager.count_current_overlaps([v1, v2])
    assert count == 1, f"Expected 1 overlap, got {count}"


def test_perpendicular_collision():
    """N/S and E/W vehicles at intersection should trigger collision detection."""
    intersection = Intersection()
    lane_n = _get_lane(intersection, Direction.NORTH, 0)
    lane_e = _get_lane(intersection, Direction.EAST, 0)

    iz = intersection.conflict_zone
    cx, cy = iz.centerx, iz.centery

    v_n = _make_vehicle(Direction.NORTH, lane_n, cx, cy)
    v_e = _make_vehicle(Direction.EAST, lane_e, cx, cy)

    p_n = MoveProposal(vehicle=v_n, next_x=cx, next_y=cy - 2,
                        next_rect=pygame.Rect(cx - 9, cy - 17, 18, 30),
                        next_speed=2.0, next_state=VehicleState.CROSSING)
    p_e = MoveProposal(vehicle=v_e, next_x=cx + 2, next_y=cy,
                        next_rect=pygame.Rect(cx - 13, cy - 9, 30, 18),
                        next_speed=2.0, next_state=VehicleState.CROSSING)

    mgr = CollisionManager()
    approved, rejected = mgr.validate_all([p_n, p_e], intersection.conflict_zone)
    assert len(rejected) >= 1, "Perpendicular overlap must be detected"


# ═══════════════════════════════════════════
# Integration: Full environment step
# ═══════════════════════════════════════════

def test_environment_step_no_crash():
    """Environment should complete a full step without errors."""
    from simulation.environment import TrafficEnvironment

    env = TrafficEnvironment(render_mode=False)
    state = env.reset()
    assert state.shape == (12,)

    next_state, reward, done, info = env.step(0)
    assert next_state.shape == (12,)
    assert "collisions" in info
    env.close()


def test_vehicle_spawner_set_rate_updates_spawn_rate():
    intersection = Intersection()
    spawner = VehicleSpawner(intersection, spawn_rate=0.05)
    spawner.set_rate(0.08)
    assert spawner.spawn_rate == 0.08


def test_environment_100_steps_zero_overlaps():
    """Run 100 steps and verify zero overlaps at the end of each step."""
    from simulation.environment import TrafficEnvironment

    env = TrafficEnvironment(render_mode=False)
    env.reset()

    for i in range(100):
        action = i % 2  # alternate actions
        _, _, done, info = env.step(action)
        # After each step, check for overlaps
        overlap_count = CollisionManager.count_current_overlaps(env.vehicles)
        assert overlap_count == 0, (
            f"Step {i}: found {overlap_count} overlapping vehicle pairs"
        )
        if done:
            break

    env.close()


# ═══════════════════════════════════════════
# Run all tests
# ═══════════════════════════════════════════

if __name__ == "__main__":
    tests = [
        test_aabb_overlap_true,
        test_aabb_overlap_false,
        test_aabb_adjacent_no_overlap,
        test_inflate_rect,
        test_safe_distance_overlap,
        test_no_collision_when_apart,
        test_collision_blocks_lower_priority,
        test_emergency_vehicle_gets_priority,
        test_intersection_cap,
        test_propose_commit_pipeline,
        test_propose_reject_pipeline,
        test_vehicle_resumes_after_rejection,
        test_vehicle_resumes_after_front_vehicle_leaves,
        test_assert_no_overlaps_clean,
        test_count_overlaps,
        test_perpendicular_collision,
        test_environment_step_no_crash,
        test_environment_100_steps_zero_overlaps,
    ]

    passed = 0
    failed = 0
    for test_fn in tests:
        try:
            test_fn()
            print(f"  ✅ {test_fn.__name__}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {test_fn.__name__}: {e}")
            failed += 1

    print(f"\n{'═' * 50}")
    print(f"  Results: {passed} passed, {failed} failed")
    print(f"{'═' * 50}")
    sys.exit(1 if failed > 0 else 0)
