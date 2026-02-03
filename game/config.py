from __future__ import annotations
import os

W, H = 360, 200
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