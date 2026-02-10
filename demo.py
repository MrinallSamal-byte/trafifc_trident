#!/usr/bin/env python3
"""
🏆 Traffic-Mind — Hackathon Demo Script
════════════════════════════════════════
One-click presentation that tells a story in 3 acts.

    python demo.py

Act 1 → "The Problem"   : Timer mode struggles under heavy traffic
Act 2 → "The Solution"  : AI takes over and clears the queues
Act 3 → "The Results"   : Side-by-side comparison stats
"""

import sys
import time
import pygame

from config.settings import (
    Direction,
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS,
    SPAWN_RATE_HIGH,
)
from simulation.road_network import Intersection
from simulation.vehicle import VehicleSpawner, VehicleState
from simulation.traffic_light import TrafficLightState
from controllers.timer_controller import TimerController
from controllers.dqn_controller import DQNController
from controllers.rule_based_controller import RuleBasedController
from visualization.renderer import Renderer
from visualization.dashboard import Dashboard


def run_demo():
    # ── Init ─────────────────────────────────
    renderer = Renderer(SCREEN_WIDTH, SCREEN_HEIGHT)
    intersection = Intersection()
    vehicles: list = []
    spawner = VehicleSpawner(intersection, spawn_rate=SPAWN_RATE_HIGH)
    dashboard = Dashboard()
    clock = pygame.time.Clock()

    timer_ctrl = TimerController()

    # Try AI, fall back to Smart
    ai_ctrl = None
    ai_label = "AI (DQN)"
    try:
        ai_ctrl = DQNController(vehicles, model_path="models/best_model.pth")
        print("✅ Loaded trained DQN model for demo")
    except Exception:
        print("⚠️  No trained model — using Smart (Rule-Based) as 'AI'")
        ai_ctrl = RuleBasedController(vehicles)
        ai_label = "Smart (Rule-Based)"

    screen = renderer.screen
    font_big = pygame.font.SysFont("Arial", 40, bold=True)
    font_sub = pygame.font.SysFont("Arial", 22)
    font_stat = pygame.font.SysFont("Arial", 28, bold=True)
    font_label = pygame.font.SysFont("Arial", 20)

    # ── Helper: title card ────────────────
    def show_title_card(title: str, subtitle: str, seconds: float):
        start = time.time()
        while time.time() - start < seconds:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
            # Dark overlay
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 200))
            screen.blit(overlay, (0, 0))
            # Title
            t_surf = font_big.render(title, True, (52, 152, 219))
            screen.blit(t_surf, (SCREEN_WIDTH // 2 - t_surf.get_width() // 2,
                                 SCREEN_HEIGHT // 2 - 40))
            if subtitle:
                s_surf = font_sub.render(subtitle, True, (200, 200, 200))
                screen.blit(s_surf, (SCREEN_WIDTH // 2 - s_surf.get_width() // 2,
                                     SCREEN_HEIGHT // 2 + 15))
            pygame.display.flip()
            clock.tick(30)

    # ── Helper: run simulation for N seconds ──
    def run_phase(controller, mode_name, seconds):
        dashboard.set_controller_name(mode_name)
        frames = int(seconds * FPS)
        total_passed = 0
        wait_sum = 0
        wait_count = 0
        max_wait = 0

        for _ in range(frames):
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()

            spawner.try_spawn_all_directions(vehicles)
            light_states = controller.get_state()

            for v in vehicles[:]:
                is_green = light_states[v.direction] == TrafficLightState.GREEN
                is_yellow = light_states[v.direction] == TrafficLightState.YELLOW
                v.update(is_green, is_yellow)

                if v.has_crossed():
                    total_passed += 1
                    wait_sum += v.wait_time
                    wait_count += 1
                    if v.wait_time > max_wait:
                        max_wait = v.wait_time
                    dashboard.record_passed(v)
                    if v in v.lane.vehicles:
                        v.lane.vehicles.remove(v)
                    vehicles.remove(v)

            controller.step()
            dashboard.update(vehicles, fps=clock.get_fps())
            metrics = dashboard.get_metrics()
            metrics["total_vehicles"] = len(vehicles)

            renderer.render_frame(intersection, vehicles, controller, metrics, mode_name)
            clock.tick(FPS)

        avg_wait = wait_sum / wait_count if wait_count else 0
        return {
            "passed": total_passed,
            "avg_wait": avg_wait,
            "max_wait": max_wait,
        }

    # ═══════════════════════════════════════
    # ACT 1: THE PROBLEM
    # ═══════════════════════════════════════
    show_title_card("Act 1: The Problem", "Fixed-timer traffic lights cause jams", 3)
    timer_stats = run_phase(timer_ctrl, "Timer (Dumb)", 30)

    # ═══════════════════════════════════════
    # TRANSITION
    # ═══════════════════════════════════════
    show_title_card("Now watch what happens when we turn on AI...", "", 3)

    # ═══════════════════════════════════════
    # ACT 2: THE SOLUTION
    # ═══════════════════════════════════════
    show_title_card("Act 2: AI Takes Control 🤖", "Deep Q-Network Reinforcement Learning", 3)
    ai_stats = run_phase(ai_ctrl, ai_label, 30)

    # ═══════════════════════════════════════
    # ACT 3: THE RESULTS
    # ═══════════════════════════════════════
    def pct_change(old, new):
        if old == 0:
            return 0
        return ((new - old) / abs(old)) * 100

    tp_pct = pct_change(timer_stats["passed"], ai_stats["passed"])
    aw_pct = pct_change(timer_stats["avg_wait"], ai_stats["avg_wait"])
    mw_pct = pct_change(timer_stats["max_wait"], ai_stats["max_wait"])

    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                waiting = False
            if event.type == pygame.KEYDOWN:
                waiting = False

        screen.fill((20, 20, 35))

        # Title
        t = font_big.render("🏆 Results", True, (52, 152, 219))
        screen.blit(t, (SCREEN_WIDTH // 2 - t.get_width() // 2, 40))

        col1_x = SCREEN_WIDTH // 2 - 250
        col2_x = SCREEN_WIDTH // 2 + 50
        y = 130

        # Headers
        h1 = font_stat.render("TIMER MODE", True, (231, 76, 60))
        h2 = font_stat.render(ai_label.upper(), True, (46, 204, 113))
        screen.blit(h1, (col1_x, y))
        screen.blit(h2, (col2_x, y))
        y += 50

        rows = [
            ("Throughput", f"{timer_stats['passed']}", f"{ai_stats['passed']}", f"{tp_pct:+.0f}%"),
            ("Avg Wait", f"{timer_stats['avg_wait']:.0f} fr", f"{ai_stats['avg_wait']:.0f} fr", f"{aw_pct:+.0f}%"),
            ("Max Wait", f"{timer_stats['max_wait']:.0f} fr", f"{ai_stats['max_wait']:.0f} fr", f"{mw_pct:+.0f}%"),
        ]

        for label, v1, v2, pct_str in rows:
            lbl = font_label.render(label + ":", True, (200, 200, 200))
            s1 = font_stat.render(v1, True, (231, 76, 60))
            arrow = font_label.render("→→→", True, (150, 150, 150))
            s2 = font_stat.render(v2, True, (46, 204, 113))
            p = font_label.render(pct_str, True, (241, 196, 15))

            screen.blit(lbl, (col1_x - 120, y + 5))
            screen.blit(s1, (col1_x, y))
            screen.blit(arrow, (col1_x + 180, y + 8))
            screen.blit(s2, (col2_x, y))
            screen.blit(p, (col2_x + 200, y + 5))
            y += 60

        # Big result line
        y += 30
        congestion_reduction = max(0, -aw_pct)
        big = font_big.render(f"🏆 AI Reduced Congestion by {congestion_reduction:.0f}% 🏆", True, (46, 204, 113))
        screen.blit(big, (SCREEN_WIDTH // 2 - big.get_width() // 2, y))

        hint = font_label.render("Press any key to exit", True, (120, 120, 120))
        screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 50))

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()
    print("\n🏁 Demo complete!")


if __name__ == "__main__":
    run_demo()
