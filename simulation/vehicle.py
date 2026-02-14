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
            # FIX: If currently stopped (speed=0), give a minimum kick-start
            if self.speed == 0 and ratio > 0.3:
                next_speed = self.max_speed * ratio * 0.3
            else:
                next_speed = max(0, next_speed * ratio * 0.5)
            if next_speed < 0.1:
                next_speed = 0
                next_state = VehicleState.WAITING
                should_stop = True
        else:
            # Approaching safe distance — gentle deceleration
            ratio = (front_dist - SAFE_DISTANCE) / SAFE_DISTANCE
            target_speed = self.max_speed * min(1.0, ratio)
            next_speed = max(0, next_speed - max(0.2, next_speed - target_speed))

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
    # FIX: If stopped and no obstacles, give a stronger initial acceleration
    if not should_stop and next_speed < self.max_speed:
        if self.speed == 0 and next_speed == 0:
            # Vehicle was stopped and no immediate obstacles — resume with stronger kick
            next_speed = min(self.max_speed, 0.5)
        else:
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

    # Determine priority (emergency vehicles always win)
    priority = 100 if self.is_emergency else 1

    return MoveProposal(
        vehicle=self,
        next_x=next_x,
        next_y=next_y,
        next_speed=next_speed,
        next_state=next_state,
        next_rect=next_rect,
        approved=True,
        priority=priority,
    )
