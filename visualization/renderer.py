"""
Traffic-Mind – PyGame Renderer (beautiful dark-theme visualisation)
"""

import pygame
import math
from config.settings import (
    Direction,
    SCREEN_WIDTH, SCREEN_HEIGHT,
    ROAD_WIDTH, LANE_WIDTH,
    INTERSECTION_CENTER_X, INTERSECTION_CENTER_Y,
    INTERSECTION_LEFT, INTERSECTION_RIGHT,
    INTERSECTION_TOP, INTERSECTION_BOTTOM,
    INTERSECTION_SIZE,
    ROAD_COLOR, ROAD_MARKING_COLOR, STOP_LINE_COLOR,
    GRASS_COLOR, INTERSECTION_COLOR,
    BACKGROUND_COLOR,
    UI_PANEL_BG, UI_PANEL_BORDER,
    UI_TEXT_PRIMARY, UI_TEXT_SECONDARY,
    UI_ACCENT_BLUE, UI_ACCENT_GREEN, UI_ACCENT_RED, UI_ACCENT_YELLOW,
)


class Renderer:
    """High-quality PyGame rendering engine."""

    def __init__(self, width: int = SCREEN_WIDTH, height: int = SCREEN_HEIGHT):
        pygame.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("🚦 Traffic-Mind — AI Traffic Controller")

        self.font_large = pygame.font.SysFont("Arial", 24, bold=True)
        self.font_med = pygame.font.SysFont("Arial", 18)
        self.font_small = pygame.font.SysFont("Arial", 14)
        self.font_tiny = pygame.font.SysFont("Arial", 12)

        self.frame_count = 0

    # ─── background & grass ───────────────
    def draw_background(self):
        self.screen.fill(BACKGROUND_COLOR)

        # Four grass quadrants (corners between roads)
        patches = [
            (0, 0, INTERSECTION_LEFT, INTERSECTION_TOP),
            (INTERSECTION_RIGHT, 0, self.width - INTERSECTION_RIGHT, INTERSECTION_TOP),
            (0, INTERSECTION_BOTTOM, INTERSECTION_LEFT, self.height - INTERSECTION_BOTTOM),
            (INTERSECTION_RIGHT, INTERSECTION_BOTTOM,
             self.width - INTERSECTION_RIGHT, self.height - INTERSECTION_BOTTOM),
        ]
        for x, y, w, h in patches:
            pygame.draw.rect(self.screen, GRASS_COLOR, (x, y, w, h))

    # ─── roads ────────────────────────────
    def draw_roads(self):
        cx, cy = INTERSECTION_CENTER_X, INTERSECTION_CENTER_Y

        # Horizontal road
        pygame.draw.rect(self.screen, ROAD_COLOR,
                         (0, cy - ROAD_WIDTH, self.width, ROAD_WIDTH * 2))
        # Vertical road
        pygame.draw.rect(self.screen, ROAD_COLOR,
                         (cx - ROAD_WIDTH, 0, ROAD_WIDTH * 2, self.height))

        # Intersection centre
        pygame.draw.rect(self.screen, INTERSECTION_COLOR,
                         (INTERSECTION_LEFT, INTERSECTION_TOP,
                          INTERSECTION_SIZE, INTERSECTION_SIZE))

        # ── lane markings (dashed centre lines) ──
        dash_len = 20
        gap = 15

        # Vertical centre line
        y = 0
        while y < self.height:
            if not (INTERSECTION_TOP - 2 <= y <= INTERSECTION_BOTTOM + 2):
                pygame.draw.line(self.screen, ROAD_MARKING_COLOR,
                                 (cx, y), (cx, min(y + dash_len, self.height)), 2)
            y += dash_len + gap

        # Horizontal centre line
        x = 0
        while x < self.width:
            if not (INTERSECTION_LEFT - 2 <= x <= INTERSECTION_RIGHT + 2):
                pygame.draw.line(self.screen, ROAD_MARKING_COLOR,
                                 (x, cy), (min(x + dash_len, self.width), cy), 2)
            x += dash_len + gap

        # ── edge lines (solid) ──
        for offset in (-ROAD_WIDTH, ROAD_WIDTH):
            # Vertical edges
            pygame.draw.line(self.screen, (100, 100, 100),
                             (cx + offset, 0), (cx + offset, INTERSECTION_TOP), 1)
            pygame.draw.line(self.screen, (100, 100, 100),
                             (cx + offset, INTERSECTION_BOTTOM), (cx + offset, self.height), 1)
            # Horizontal edges
            pygame.draw.line(self.screen, (100, 100, 100),
                             (0, cy + offset), (INTERSECTION_LEFT, cy + offset), 1)
            pygame.draw.line(self.screen, (100, 100, 100),
                             (INTERSECTION_RIGHT, cy + offset), (self.width, cy + offset), 1)

        # ── stop lines ──
        lw = 3
        # North stop line (bottom of intersection, right half)
        pygame.draw.line(self.screen, STOP_LINE_COLOR,
                         (cx, INTERSECTION_BOTTOM), (cx + ROAD_WIDTH, INTERSECTION_BOTTOM), lw)
        # South stop line (top of intersection, left half)
        pygame.draw.line(self.screen, STOP_LINE_COLOR,
                         (cx - ROAD_WIDTH, INTERSECTION_TOP), (cx, INTERSECTION_TOP), lw)
        # East stop line (left of intersection, bottom half)
        pygame.draw.line(self.screen, STOP_LINE_COLOR,
                         (INTERSECTION_LEFT, cy), (INTERSECTION_LEFT, cy + ROAD_WIDTH), lw)
        # West stop line (right of intersection, top half)
        pygame.draw.line(self.screen, STOP_LINE_COLOR,
                         (INTERSECTION_RIGHT, cy - ROAD_WIDTH), (INTERSECTION_RIGHT, cy), lw)

    # ─── vehicles ─────────────────────────
    def draw_vehicles(self, vehicles):
        for v in vehicles:
            v.draw(self.screen)

    # ─── traffic lights ───────────────────
    def draw_traffic_lights(self, controller):
        controller.draw(self.screen)

    # ─── UI overlay ───────────────────────
    def draw_ui_overlay(self, metrics: dict, mode: str):
        # ── Top bar ──
        top_bar = pygame.Surface((self.width, 60), pygame.SRCALPHA)
        top_bar.fill((20, 20, 20, 200))
        self.screen.blit(top_bar, (0, 0))

        title = self.font_large.render("🚦 Traffic-Mind", True, UI_ACCENT_BLUE)
        self.screen.blit(title, (15, 5))

        mode_surf = self.font_med.render(f"Mode: {mode}", True, UI_ACCENT_GREEN)
        self.screen.blit(mode_surf, (250, 8))

        fps_surf = self.font_small.render(
            f"FPS: {metrics.get('fps', 0):.0f}  |  "
            f"Time: {metrics.get('elapsed', 0):.0f}s  |  "
            f"Cars: {metrics.get('total_vehicles', 0)}",
            True, UI_TEXT_SECONDARY,
        )
        self.screen.blit(fps_surf, (250, 32))

        # ── Left panel ──
        panel_w = 220
        panel_h = 310
        panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel_surf.fill((20, 20, 20, 200))
        px, py = 10, 75
        self.screen.blit(panel_surf, (px, py))
        pygame.draw.rect(self.screen, UI_PANEL_BORDER, (px, py, panel_w, panel_h), 1, border_radius=4)

        y = py + 10
        header = self.font_med.render("📊 Live Stats", True, UI_ACCENT_BLUE)
        self.screen.blit(header, (px + 15, y)); y += 30

        stats = [
            ("Throughput", f"{metrics.get('throughput', 0)}/int"),
            ("Avg Wait", f"{metrics.get('avg_wait', 0):.1f} fr"),
            ("Max Wait", f"{metrics.get('max_wait', 0):.0f} fr"),
            ("CO\u2082 Emitted", f"{metrics.get('co2_total', 0):.2f} kg"),
        ]
        for label, val in stats:
            s = self.font_small.render(f"{label}: {val}", True, UI_TEXT_PRIMARY)
            self.screen.blit(s, (px + 15, y)); y += 22

        y += 5
        # Queue bars per direction
        for d_name, d_enum in [("N", Direction.NORTH), ("S", Direction.SOUTH),
                                ("E", Direction.EAST), ("W", Direction.WEST)]:
            q = metrics.get("queues", {}).get(d_enum, 0)
            label = self.font_small.render(f"Queue {d_name}:", True, UI_TEXT_SECONDARY)
            self.screen.blit(label, (px + 15, y))

            bar_x = px + 95
            bar_w = max(0, min(q * 10, 100))
            bar_color = UI_ACCENT_GREEN if q < 5 else (UI_ACCENT_YELLOW if q <= 10 else UI_ACCENT_RED)
            pygame.draw.rect(self.screen, bar_color, (bar_x, y + 2, bar_w, 14), border_radius=2)
            pygame.draw.rect(self.screen, (60, 60, 60), (bar_x, y + 2, 100, 14), 1, border_radius=2)

            num = self.font_tiny.render(str(q), True, UI_TEXT_PRIMARY)
            self.screen.blit(num, (bar_x + 105, y + 1))
            y += 22

        y += 8
        passed_s = self.font_small.render(f"Total Passed: {metrics.get('total_passed', 0)}", True, UI_ACCENT_GREEN)
        self.screen.blit(passed_s, (px + 15, y)); y += 20
        waiting_s = self.font_small.render(f"Total Waiting: {metrics.get('total_waiting', 0)}", True, UI_ACCENT_RED)
        self.screen.blit(waiting_s, (px + 15, y))

        # ── Bottom bar ──
        bot_h = 40
        bot_surf = pygame.Surface((self.width, bot_h), pygame.SRCALPHA)
        bot_surf.fill((20, 20, 20, 200))
        by = self.height - bot_h
        self.screen.blit(bot_surf, (0, by))

        controls = [
            ("[1] Timer", mode == "Timer (Dumb)"),
            ("[2] Smart", mode == "Smart (Rule-Based)"),
            ("[3] AI", mode == "AI (DQN)"),
            ("[R] Reset", False),
            ("[+/-] Density", False),
            ("[H] Hardware", False),
        ]
        cx = 30
        for text, active in controls:
            color = UI_ACCENT_GREEN if active else UI_TEXT_SECONDARY
            s = self.font_small.render(text, True, color)
            if active:
                rect = s.get_rect(topleft=(cx - 4, by + 10))
                rect.inflate_ip(8, 4)
                pygame.draw.rect(self.screen, (*UI_ACCENT_GREEN[:3], 40), rect, border_radius=3)
            self.screen.blit(s, (cx, by + 12))
            cx += s.get_width() + 25

    # ─── throughput sparkline ─────────────
    def draw_throughput_graph(self, history: list, mode: str):
        if len(history) < 2:
            return
        gw, gh = 180, 80
        gx = self.width - gw - 15
        gy = self.height - 55 - gh

        surf = pygame.Surface((gw, gh), pygame.SRCALPHA)
        surf.fill((20, 20, 20, 160))
        self.screen.blit(surf, (gx, gy))
        pygame.draw.rect(self.screen, UI_PANEL_BORDER, (gx, gy, gw, gh), 1, border_radius=3)

        data = history[-gw:]
        if not data:
            return
        max_val = max(max(data), 1)
        color_map = {"Timer (Dumb)": UI_ACCENT_RED, "Smart (Rule-Based)": UI_ACCENT_YELLOW, "AI (DQN)": UI_ACCENT_GREEN}
        line_color = color_map.get(mode, UI_ACCENT_BLUE)

        points = []
        for i, val in enumerate(data):
            px = gx + int(i * gw / len(data))
            py_val = gy + gh - 5 - int((val / max_val) * (gh - 10))
            points.append((px, py_val))

        if len(points) >= 2:
            pygame.draw.lines(self.screen, line_color, False, points, 2)

        label = self.font_tiny.render("Throughput", True, UI_TEXT_SECONDARY)
        self.screen.blit(label, (gx + 5, gy + 3))

    # ─── full frame ───────────────────────
    def render_frame(self, roads, vehicles, controller, metrics, mode):
        self.frame_count += 1
        self.draw_background()
        self.draw_roads()
        self.draw_vehicles(vehicles)
        self.draw_traffic_lights(controller)
        self.draw_ui_overlay(metrics, mode)
        self.draw_throughput_graph(metrics.get("throughput_history", []), mode)
        pygame.display.flip()
