from __future__ import annotations
import json
import os
from dataclasses import dataclass, asdict, field

from . import config as cfg


def clamp(x, a=0, b=100):
    return max(a, min(b, x))


@dataclass
class Girl:
    hunger: float = 80.0
    mood: float = 70.0
    sleepiness: float = 20.0
    affection: int = 0
    lights_off: bool = False

    state: str = "idle"
    state_until: float = 0.0

    line: str = "……"
    line_until: float = 0.0

    last_seen: float = 0.0
    first_seen: float = 0.0

    bg_index: int = 0

    sfx_muted: bool = False
    sfx_scale: float = 1.0

    borderless: bool = False
    dock_bottom_right: bool = True

    unlocked_topics: list[str] = field(default_factory=list)
    flags: dict[str, bool] = field(default_factory=dict)
    journal: list[dict] = field(default_factory=list)

    # NEW: 解放直後マーク（topic id のリスト）
    new_topics: list[str] = field(default_factory=list)

    active_topic: str = ""
    seq_index: int = 0
    pending_yes: str = ""
    pending_no: str = ""
    pending_flag: str = ""
    awaiting_choice: bool = False
    
    last_auto_day: str = ""
    
    # face animation
    blink_until: float = 0.0
    next_blink: float = 0.0
    mouth_open: bool = False
    mouth_until: float = 0.0
    
    expression: str = "normal"

    # clothes
    outfit: str = "normal"


def load_or_new() -> Girl:
    if os.path.exists(cfg.SAVE_PATH):
        try:
            with open(cfg.SAVE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            base = asdict(Girl())
            base.update(data)
            return Girl(**base)
        except Exception:
            pass
    return Girl()


def save(g: Girl):
    with open(cfg.SAVE_PATH, "w", encoding="utf-8") as f:
        json.dump(asdict(g), f, ensure_ascii=False, indent=2)
