
import sys
import os
import unittest
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from simulation.vehicle import Vehicle, VehicleState
from config.settings import Direction, KICKSTART_SPEED, SAFE_DISTANCE

class MockLane:
    def __init__(self):
        self.vehicles = []
        # Moving North: Start > End.
        # Stop line at 480.
        self.stop_line_pos = (600, 480) 
        self.start_pos = (600, 800)
        self.end_pos = (600, 0)

class TestVehicleResume(unittest.TestCase):
    def setUp(self):
        self.lane = MockLane()
        # Create a vehicle BEHIND the stop line
        # Moving North (y decreases).
        # Stop line y=480.
        # Vehicle Center y=510. Height=30. Half=15.
        # Front y = 510-15 = 495.
        # Dist to line = 495 - 480 = 15.
        self.vehicle = Vehicle(Direction.NORTH, self.lane, 600, 510)
        self.vehicle.speed = 0
        self.vehicle.state = VehicleState.WAITING
        self.lane.vehicles.append(self.vehicle)

    def test_resume_on_green(self):
        # 1. Simulate Red Light
        # light_is_green=False
        proposal = self.vehicle.propose_move(light_is_green=False, light_is_yellow=False)
        self.assertEqual(proposal.next_speed, 0, "Vehicle should stay stopped at red light")
        
        # 2. Simulate Green Light
        print("\n--- Switching to GREEN ---")
        proposal = self.vehicle.propose_move(light_is_green=True, light_is_yellow=False)
        
        print(f"Speed: {self.vehicle.speed} -> Proposal: {proposal.next_speed}")
        
        # It should kickstart
        self.assertGreater(proposal.next_speed, 0, "Vehicle should resume moving on green")
        self.assertAlmostEqual(proposal.next_speed, KICKSTART_SPEED, msg="Vehicle should use kickstart speed")

    def test_resume_following_too_close(self):
        # Create a lead vehicle
        lead_vehicle = Vehicle(Direction.NORTH, self.lane, 600, 480) # Center at stop line
        lead_vehicle.speed = 0
        self.lane.vehicles.append(lead_vehicle)

        # Our vehicle is behind
        # Lead Back = 480 + 15 = 495.
        # We want Dist = 2.0 (Less than 2.8 threshold).
        # Our Front = 495 + 2.0 = 497.
        # Our Center = 497 + 15 = 512.
        self.vehicle.y = 512 
        
        # Verify distance calculation
        # (512 - 15) - (480 + 15) = 497 - 495 = 2.0.
        dist = self.vehicle.check_front_vehicle(self.lane.vehicles)
        print(f"Distance: {dist}")
        self.assertAlmostEqual(dist, 2.0)
        
        # 1. Lead stopped. We should be stopped.
        proposal = self.vehicle.propose_move(light_is_green=True, light_is_yellow=False)
        self.assertEqual(proposal.next_speed, 0, "Should wait for lead vehicle")

        # 2. Lead vehicle moves JUST A TINY BIT
        # Lead moves to 479 (1 pixel).
        lead_vehicle.y = 479
        # New Back = 479 + 15 = 494.
        # Our Front = 497.
        # Dist = 3.0.
        # 3.0 > 2.8 (SAFE_DISTANCE * 0.1).
        # So `should_stop` should be False.
        # Ratio = 3.0 / 28 = 0.107.
        # Speed = max * 0.107 * 0.8.
        
        proposal = self.vehicle.propose_move(light_is_green=True, light_is_yellow=False)
        print(f"Follower Speed (Dist=3.0): {self.vehicle.speed} -> {proposal.next_speed}")
        
        self.assertGreater(proposal.next_speed, 0, "Should resume when lead vehicle moves slightly")

if __name__ == '__main__':
    unittest.main()
