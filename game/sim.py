from __future__ import annotations
import random
import time

from .model import Girl, clamp
from .snacks import Snack
from .dialogue import Dialogue, set_line
from . import config as cfg


def pick_idle_state(g: Girl, dlg: Dialogue, now: float):
    if g.lights_off or g.sleepiness >= 85:
        g.state = "sleep"
    elif g.hunger <= 20 or g.mood <= 20:
        g.state = "grumpy"
    else:
        g.state = "music" if random.random() < 0.35 else "idle"

    g.state_until = now + random.uniform(cfg.IDLE_MIN_SEC, cfg.IDLE_MAX_SEC)
    set_line(g, now, dlg.pick(g.state) or "……", (2.5, 5.0))


def step_sim(g: Girl, now: float, dt: float):
    g.hunger = clamp(g.hunger - cfg.HUNGER_DECAY * dt)
    g.mood = clamp(g.mood - cfg.MOOD_DECAY * dt)
    g.sleepiness = clamp(g.sleepiness + cfg.SLEEP_INC * dt)

    if g.state == "sleep":
        g.sleepiness = clamp(g.sleepiness - 0.10 * dt * (cfg.LIGHTS_OFF_SLEEP_RECOVER if g.lights_off else 1.0))
        g.mood = clamp(g.mood + 0.02 * dt)
        g.hunger = clamp(g.hunger - 0.01 * dt)
    elif g.state == "music":
        g.mood = clamp(g.mood + 0.03 * dt)
        g.sleepiness = clamp(g.sleepiness + 0.01 * dt)
    elif g.state == "grumpy":
        g.mood = clamp(g.mood - 0.02 * dt)

    step_move(g, now, dt)


def step_move(g: Girl, now: float, dt: float):
    """Simple x-axis wandering inside the right panel.

    We store x_offset as a pixel offset from the right panel center.
    """
    # Don't wander while sleeping / lights off
    if getattr(g, "lights_off", False) or getattr(g, "state", "") == "sleep":
        g.vx_px_per_sec = 0.0
        return

    # limits
    half = cfg.RIGHT_PANEL_W / 2.0
    lim = max(0.0, half - float(getattr(cfg, "WALK_MARGIN_PX", 18)))

    # walking window
    if now < getattr(g, "walk_until", 0.0):
        g.x_offset = float(getattr(g, "x_offset", 0.0)) + float(getattr(g, "vx_px_per_sec", 0.0)) * dt
        if g.x_offset > lim:
            g.x_offset = lim
            g.vx_px_per_sec = -abs(float(getattr(g, "vx_px_per_sec", 0.0)) or cfg.WALK_SPEED_PX_PER_SEC)
        elif g.x_offset < -lim:
            g.x_offset = -lim
            g.vx_px_per_sec = abs(float(getattr(g, "vx_px_per_sec", 0.0)) or cfg.WALK_SPEED_PX_PER_SEC)
        return

    # resting
    if now < getattr(g, "next_walk_at", 0.0):
        g.vx_px_per_sec = 0.0
        return

    # start a new walk
    dur = random.uniform(cfg.WALK_MIN_SEC, cfg.WALK_MAX_SEC)
    rest = random.uniform(cfg.WALK_REST_MIN_SEC, cfg.WALK_REST_MAX_SEC)
    g.walk_until = now + dur
    g.next_walk_at = g.walk_until + rest
    sign = -1.0 if random.random() < 0.5 else 1.0
    g.vx_px_per_sec = sign * float(cfg.WALK_SPEED_PX_PER_SEC)


def action_snack(g: Girl, snack: Snack | None = None, now: float | None = None):
    """Apply a snack.

    snack is optional for backward compatibility; if None, use legacy constants.
    """
    if snack is None:
        g.hunger = clamp(g.hunger + cfg.SNACK_HUNGER_RECOVER)
        g.mood = clamp(g.mood + 3)
        g.affection += 1
        return

    g.hunger = clamp(g.hunger + float(snack.hunger))
    g.mood = clamp(g.mood + float(snack.mood))
    g.affection += int(snack.affection)

    if now is None:
        now = time.time()
    g.last_snack_id = snack.id
    g.last_snack_at = float(now)
    g.snack_count = int(getattr(g, "snack_count", 0)) + 1


def action_pet(g: Girl):
    g.mood = clamp(g.mood + cfg.PET_MOOD_RECOVER)
    g.affection += 2


def action_toggle_lights(g: Girl):
    g.lights_off = not g.lights_off
    if g.lights_off:
        g.state = "sleep"
        g.state_until = time.time() + random.uniform(8, 14)
