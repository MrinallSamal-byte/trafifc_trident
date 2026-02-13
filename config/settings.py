"""
Traffic-Mind: Configuration & Hyperparameters
All constants, colors, and tunable parameters in one place.
"""

from enum import IntEnum

# ─────────────────────────────────────────────
# DIRECTIONS
# ─────────────────────────────────────────────
class Direction(IntEnum):
    NORTH = 0
    SOUTH = 1
    EAST = 2
    WEST = 3


# ─────────────────────────────────────────────
# WINDOW / DISPLAY
# ─────────────────────────────────────────────
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
FPS = 60
BACKGROUND_COLOR = (30, 30, 30)  # Dark theme

# ─────────────────────────────────────────────
# ROAD GEOMETRY
# ─────────────────────────────────────────────
ROAD_WIDTH = 80          # pixels per direction (incoming or outgoing)
LANE_WIDTH = 40          # pixels per lane
NUM_LANES = 2            # per direction
INTERSECTION_SIZE = ROAD_WIDTH * 2   # width & height of centre box

# Intersection centre is the screen centre
INTERSECTION_CENTER_X = SCREEN_WIDTH // 2
INTERSECTION_CENTER_Y = SCREEN_HEIGHT // 2

# Bounding box of the intersection
INTERSECTION_LEFT   = INTERSECTION_CENTER_X - ROAD_WIDTH
INTERSECTION_RIGHT  = INTERSECTION_CENTER_X + ROAD_WIDTH
INTERSECTION_TOP    = INTERSECTION_CENTER_Y - ROAD_WIDTH
INTERSECTION_BOTTOM = INTERSECTION_CENTER_Y + ROAD_WIDTH

# ─────────────────────────────────────────────
# VEHICLE
# ─────────────────────────────────────────────
CAR_LENGTH = 30
CAR_WIDTH = 18
CAR_SPEED_MIN = 2.0
CAR_SPEED_MAX = 4.0
CAR_COLORS = [
    (41, 128, 185),   # Blue
    (231, 76, 60),    # Red
    (46, 204, 113),   # Green
    (241, 196, 15),   # Yellow
    (155, 89, 182),   # Purple
    (230, 126, 34),   # Orange
    (26, 188, 156),   # Teal
    (236, 240, 241),  # White-ish
    (243, 156, 18),   # Amber
    (192, 57, 43),    # Dark red
]
SPAWN_RATE_LOW = 0.02
SPAWN_RATE_MEDIUM = 0.05
SPAWN_RATE_HIGH = 0.08
MAX_VEHICLES = 200
SAFE_DISTANCE = 10  # minimum gap between cars (pixels)

# ─────────────────────────────────────────────
# TRAFFIC LIGHTS
# ─────────────────────────────────────────────
GREEN_DURATION_TIMER = 90      # frames – fixed-timer controller
YELLOW_DURATION = 30           # frames
MIN_GREEN_DURATION = 30        # frames – AI / rule-based
MAX_GREEN_DURATION = 180       # frames
LIGHT_RADIUS = 12

# Colours
LIGHT_RED    = (255, 0, 0)
LIGHT_YELLOW = (255, 255, 0)
LIGHT_GREEN  = (0, 255, 0)

LIGHT_RED_DIM    = (80, 0, 0)
LIGHT_YELLOW_DIM = (80, 80, 0)
LIGHT_GREEN_DIM  = (0, 80, 0)

# ─────────────────────────────────────────────
# DQN HYPERPARAMETERS
# ─────────────────────────────────────────────
STATE_SIZE = 12            # 4 dirs × 3 features
ACTION_SIZE = 2            # 0 = NS green, 1 = EW green
LEARNING_RATE = 0.001
GAMMA = 0.95               # discount factor
EPSILON_START = 1.0
EPSILON_END = 0.01
EPSILON_DECAY = 0.995
BATCH_SIZE = 64
MEMORY_SIZE = 10000
TARGET_UPDATE_FREQ = 100   # steps
HIDDEN_LAYERS = [128, 128]
DECISION_INTERVAL = 30     # frames between AI decisions
MAX_EPISODE_STEPS = 3000

# ─────────────────────────────────────────────
# REWARD SHAPING
# ─────────────────────────────────────────────
REWARD_CAR_PASSED = 1.0
PENALTY_CAR_WAITING = -0.1
PENALTY_LONG_WAIT = -0.5
LONG_WAIT_THRESHOLD = 200   # frames
PENALTY_SWITCH = -0.2
REWARD_THROUGHPUT_BONUS = 2.0
THROUGHPUT_BONUS_THRESHOLD = 5  # cars per decision interval

# ─────────────────────────────────────────────
# HARDWARE (Arduino)
# ─────────────────────────────────────────────
SERIAL_PORT = "/dev/ttyUSB0"   # Linux default; change for Windows
BAUD_RATE = 9600
HARDWARE_ENABLED = False

# ─────────────────────────────────────────────
# UI COLOURS / THEME
# ─────────────────────────────────────────────
UI_PANEL_BG = (20, 20, 20, 180)          # semi-transparent
UI_PANEL_BORDER = (60, 60, 60)
UI_TEXT_PRIMARY = (240, 240, 240)
UI_TEXT_SECONDARY = (180, 180, 180)
UI_ACCENT_BLUE = (52, 152, 219)
UI_ACCENT_GREEN = (46, 204, 113)
UI_ACCENT_RED = (231, 76, 60)
UI_ACCENT_YELLOW = (241, 196, 15)

ROAD_COLOR = (50, 50, 50)
ROAD_MARKING_COLOR = (200, 200, 200)
STOP_LINE_COLOR = (255, 255, 255)
GRASS_COLOR = (20, 60, 20)
INTERSECTION_COLOR = (55, 55, 55)

# ─────────────────────────────────────────────
# EMERGENCY VEHICLES (Green Corridor)
# ─────────────────────────────────────────────
EMERGENCY_SPAWN_RATE = 0.002        # probability per direction per frame
EMERGENCY_COLOR = (220, 20, 20)     # red body
EMERGENCY_STRIPE_COLOR = (255, 255, 255)  # white stripe
EMERGENCY_SPEED = 5.0               # faster than normal cars
EMERGENCY_PRIORITY_FRAMES = 90      # frames to hold green for emergency

# ─────────────────────────────────────────────
# CO2 EMISSIONS (Eco Impact)
# ─────────────────────────────────────────────
CO2_IDLE_RATE = 0.0041    # kg CO2 per frame per idling vehicle (~2.3 kg/hr)
CO2_MOVING_RATE = 0.0023  # kg CO2 per frame per moving vehicle
