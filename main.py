#!/usr/bin/env python3
"""
Traffic-Mind: AI-Powered Traffic Light Controller
══════════════════════════════════════════════════
Main application — run this to start the real-time simulation.

Usage:
    python main.py                # Normal mode (GUI simulation)
    python main.py --hardware     # Enable Arduino connection
"""

import argparse
import sys
import pygame

from config.settings import (
    Direction,
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS,
    SPAWN_RATE_MEDIUM, SERIAL_PORT, BAUD_RATE,
)
from simulation.road_network import Intersection
from simulation.vehicle import VehicleSpawner, VehicleState
from simulation.traffic_light import TrafficLightState
from controllers.timer_controller import TimerController
from controllers.rule_based_controller import RuleBasedController
from controllers.dqn_controller import DQNController
from visualization.renderer import Renderer
from visualization.dashboard import Dashboard
from hardware.arduino_bridge import ArduinoBridge


def main():
    parser = argparse.ArgumentParser(description="Traffic-Mind Simulation")
    parser.add_argument("--hardware", action="store_true", help="Enable Arduino hardware")
    args = parser.parse_args()

    # ── Initialise ───────────────────────────
    renderer = Renderer(SCREEN_WIDTH, SCREEN_HEIGHT)
    intersection = Intersection()
    vehicles: list = []
    spawner = VehicleSpawner(intersection, spawn_rate=SPAWN_RATE_MEDIUM)
    dashboard = Dashboard()

    # ── Controllers ──────────────────────────
    timer_ctrl = TimerController()
    smart_ctrl = RuleBasedController(vehicles)

    dqn_ctrl = None
    dqn_model_available = False
    try:
        dqn_ctrl = DQNController(vehicles, model_path="models/best_model.pth")
        dqn_model_available = True
        print("✅ Trained DQN model loaded!")
    except FileNotFoundError:
        # No trained model yet — initialise with random weights
        try:
            dqn_ctrl = DQNController(vehicles, model_path=None)
            print("⚠️  No trained model found. AI mode uses random weights. Train with: python train.py")
        except Exception:
            print("⚠️  DQN controller could not be initialised.")

    active_controller = timer_ctrl
    mode_name = "Timer (Dumb)"
    dashboard.set_controller_name(mode_name)

    # ── Arduino ──────────────────────────────
    arduino = None
    if args.hardware:
        arduino = ArduinoBridge(SERIAL_PORT, BAUD_RATE)
        if arduino.is_connected():
            print("✅ Arduino connected!")
        else:
            print("⚠️  Arduino not found. Running software-only.")

    # ── Main loop ────────────────────────────
    clock = pygame.time.Clock()
    running = True
    spawn_rate = SPAWN_RATE_MEDIUM

    print("👋 Hello! Welcome to Traffic-Mind!")
    print("🚦 Traffic-Mind is running!")
    print("   [1] Timer  [2] Smart  [3] AI  [R] Reset  [+/-] Density  [H] Hardware\n")

    while running:
        # ── Events ──
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    active_controller = timer_ctrl
                    mode_name = "Timer (Dumb)"
                    dashboard.set_controller_name(mode_name)
                    print("Switched to TIMER mode")

                elif event.key == pygame.K_2:
                    active_controller = smart_ctrl
                    mode_name = "Smart (Rule-Based)"
                    dashboard.set_controller_name(mode_name)
                    print("Switched to SMART mode")

                elif event.key == pygame.K_3:
                    if dqn_ctrl:
                        active_controller = dqn_ctrl
                        mode_name = "AI (DQN)"
                        if not dqn_model_available:
                            mode_name = "AI (DQN - untrained)"
                        dashboard.set_controller_name(mode_name)
                        print("🤖 Switched to AI mode!")
                    else:
                        print("⚠️  AI controller not available. Train first with: python train.py")

                elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                    spawn_rate = min(spawn_rate + 0.01, 0.10)
                    print(f"Traffic density: {spawn_rate:.2f}")

                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    spawn_rate = max(spawn_rate - 0.01, 0.01)
                    print(f"Traffic density: {spawn_rate:.2f}")

                elif event.key == pygame.K_r:
                    for lane in intersection.get_all_incoming_lanes():
                        lane.vehicles.clear()
                    vehicles.clear()
                    dashboard.reset()
                    print("↻ Reset!")

                elif event.key == pygame.K_h and arduino:
                    arduino.hardware_enabled = not arduino.hardware_enabled
                    status = "ON" if arduino.hardware_enabled else "OFF"
                    print(f"Hardware: {status}")

                elif event.key == pygame.K_ESCAPE:
                    running = False

        # ── Simulation tick ──
        spawner.set_rate(spawn_rate)
        spawner.try_spawn_all_directions(vehicles)

        light_states = active_controller.get_state()

        for v in vehicles[:]:
            is_green = light_states[v.direction] == TrafficLightState.GREEN
            is_yellow = light_states[v.direction] == TrafficLightState.YELLOW
            v.update(is_green, is_yellow)

            if v.has_crossed():
                dashboard.record_passed(v)
                if v in v.lane.vehicles:
                    v.lane.vehicles.remove(v)
                vehicles.remove(v)

        active_controller.step()

        # ── Dashboard ──
        actual_fps = clock.get_fps()
        dashboard.update(vehicles, fps=actual_fps)
        metrics = dashboard.get_metrics()
        metrics["total_vehicles"] = len(vehicles)

        # ── Hardware sync ──
        if arduino and arduino.is_connected() and arduino.hardware_enabled:
            arduino.sync_with_simulation(active_controller.lights)

        # ── Render ──
        renderer.render_frame(
            roads=intersection,
            vehicles=vehicles,
            controller=active_controller,
            metrics=metrics,
            mode=mode_name,
        )

        clock.tick(FPS)

    # ── Cleanup ──
    if arduino:
        arduino.close()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
