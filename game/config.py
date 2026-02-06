from __future__ import annotations
import os

# Window size
# A slightly vertical "toy" aspect ratio (tamagotchi-ish).
W, H = 360, 320
FPS = 60

SAVE_PATH = "save.json"

ASSETS = "assets"
IMG_DIR = os.path.join(ASSETS, "img")
SFX_DIR = os.path.join(ASSETS, "sfx")
DLG_PATH = os.path.join(ASSETS, "dialogue", "lines.json")
TOPICS_PATH = os.path.join(ASSETS, "dialogue", "topics.json")

# Snacks
SNACKS_DIR = os.path.join(ASSETS, "snacks")
SNACKS_PATH = os.path.join(SNACKS_DIR, "snacks.json")
SNACKS_ICON_DIR = os.path.join(SNACKS_DIR, "icons")

# Snack UI
SNACK_MENU_COLS = 4
SNACK_MENU_ROWS = 1
SNACK_ICON_SCALE = 1  # icons are already small; bump if needed

LEFT_X = 12
RIGHT_PANEL_W = 128
RIGHT_X = W - RIGHT_PANEL_W - 20

HUNGER_DECAY = 0.020
MOOD_DECAY   = 0.010
SLEEP_INC    = 0.015

SNACK_HUNGER_RECOVER = 18
PET_MOOD_RECOVER     = 12
LIGHTS_OFF_SLEEP_RECOVER = 0.8

IDLE_MIN_SEC = 4
IDLE_MAX_SEC = 9

BG_THEMES = [
    {"name": "midnight", "bg": (25, 25, 32)},
    {"name": "ink",      "bg": (18, 20, 28)},
    {"name": "plum",     "bg": (32, 22, 36)},
    {"name": "forest",   "bg": (18, 28, 24)},
    {"name": "cocoa",    "bg": (30, 24, 22)},
    {"name": "sky",      "bg": (22, 28, 36)},
]

SFX_BASE_VOLUME = {
    "snack": 0.35,
    "pet":   0.30,
    "off":   0.35,
    "on":    0.35,
    "talk":  0.30,
}

# X movement (right panel wandering)
WALK_SPEED_PX_PER_SEC = 22.0

WALK_MIN_SEC = 1.5
WALK_MAX_SEC = 2.5
WALK_REST_MIN_SEC = 15.0
WALK_REST_MAX_SEC = 30.0

WALK_MARGIN_PX = 10  # keep within right panel

# Walk animation
WALK_ANIM_FPS = 10.0
WALK_BOB_PX = 2
WALK_BOB_HZ = 2.0


# ---- idle beat scheduler (after each line) ----
IDLE_DECIDE_WALK_CHANCE = 0.35
IDLE_SILENT_AFTER_LINE_MIN_SEC = 1.5
IDLE_SILENT_AFTER_LINE_MAX_SEC = 4.0
IDLE_LINE_MIN_SEC = 2.2
IDLE_LINE_MAX_SEC = 6.0
IDLE_SEC_PER_CHAR = 0.07


# ---- lights-off sleep system ----
SLEEP_READY_MIN_SEC = 25.0
SLEEP_READY_MAX_SEC = 120.0

SLEEP_CHANCE_DARK_PRE_READY = 0.02
SLEEP_CHANCE_DARK_READY = 0.80

WAKE_CHANCE_BRIGHT_WHILE_SLEEPING = 0.85

# --- Sleep talk (phase2) ---
SLEEP_TALK_CHANCE_DARK = 0.22
SLEEP_TALK_CHANCE_BRIGHT = 0.12
WAKE_CHANCE_DARK_WHILE_SLEEPING = 0.03

SLEEP_TALK_MIN_SEC = 1.2
SLEEP_TALK_MAX_SEC = 2.6
SLEEP_SILENT_BEAT_MIN_SEC = 2.0
SLEEP_SILENT_BEAT_MAX_SEC = 4.0

# Pre-sleep / wake transition durations
DROWSY_MIN_SEC = 1.5
DROWSY_MAX_SEC = 2.8
WAKE_DROWSY_MIN_SEC = 0.9
WAKE_DROWSY_MAX_SEC = 1.4



# Atlas/animation rules
FACE_DURING_WALK = False  # v0.1: walk中は表情パーツを重ねない
CLOTHES_WALK_ANIM = True  # clothes_walk_* があれば歩行に合わせて切替


# --- Dialogue bubble (multiline) ---
BUBBLE_MAX_LINES = 3          # 1ページに表示する最大行数
BUBBLE_PADDING_X = 8
BUBBLE_PADDING_Y = 6
BUBBLE_LINE_GAP = 2           # 行間の追加ピクセル


# --- Custom unified menu (v0.2) ---
# NOTE: values below may be overridden again in the placement section.
CUSTOM_MENU_PANEL_Y = 90
"""Custom menu thumbnail sizing.

These thumbnails are used by the unified custom menu (衣装/背景).
The window can be relatively small, so we keep them compact to show
multiple items without requiring scrolling.
"""

THUMB_W = 88
THUMB_H = 56
THUMB_FRAME = 2
THUMB_RADIUS = 10
THUMB_NAME_HEIGHT = 16
THUMB_GAP = 10

# --- Custom menu placement ---
# Top-right, to the left of the gear button.
CUSTOM_MENU_REPLACE_CHAR = True
CUSTOM_MENU_BTN_SIZE = 28
CUSTOM_MENU_BTN_GAP = 6
CUSTOM_MENU_BTN_Y = 8
# Reserve space for the gear button at the far right.
CUSTOM_MENU_BTN_MARGIN_R = 40
