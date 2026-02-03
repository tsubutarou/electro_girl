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

    # movement
    step_move(g, now, dt)


def step_move(g: Girl, now: float, dt: float):
    """Wander left/right inside the right panel.

    Uses g.x_offset as an offset from the panel center in pixels.
    """
    # Stop moving while sleeping / lights off (keep her calm)
    if getattr(g, "lights_off", False) or getattr(g, "state", "") == "sleep":
        g.vx_px_per_sec = 0.0
        # schedule a walk later to avoid immediate start upon wake
        if getattr(g, "next_walk_at", 0.0) < now:
            g.next_walk_at = now + random.uniform(cfg.WALK_REST_MIN_SEC, cfg.WALK_REST_MAX_SEC)
        return

    # ensure fields exist (older saves)
    if not hasattr(g, "x_offset"):
        g.x_offset = 0.0
    if not hasattr(g, "vx_px_per_sec"):
        g.vx_px_per_sec = 0.0
    if not hasattr(g, "walk_until"):
        g.walk_until = 0.0
    if not hasattr(g, "next_walk_at"):
        g.next_walk_at = now + random.uniform(cfg.WALK_REST_MIN_SEC, cfg.WALK_REST_MAX_SEC)

    # walking phase
    if now < g.walk_until and g.vx_px_per_sec != 0.0:
        g.x_offset += g.vx_px_per_sec * dt

        bound = max(0, (cfg.RIGHT_PANEL_W // 2) - int(cfg.WALK_MARGIN_PX))
        if g.x_offset < -bound:
            g.x_offset = -bound
            g.vx_px_per_sec = abs(g.vx_px_per_sec)
        elif g.x_offset > bound:
            g.x_offset = bound
            g.vx_px_per_sec = -abs(g.vx_px_per_sec)

        # finish walk
        if now >= g.walk_until:
            g.vx_px_per_sec = 0.0
            g.next_walk_at = now + random.uniform(cfg.WALK_REST_MIN_SEC, cfg.WALK_REST_MAX_SEC)
        return

    # rest phase: decide whether to start a walk
    if now >= g.next_walk_at:
        direction = -1.0 if random.random() < 0.5 else 1.0
        g.vx_px_per_sec = direction * float(cfg.WALK_SPEED_PX_PER_SEC)
        g.walk_until = now + random.uniform(cfg.WALK_MIN_SEC, cfg.WALK_MAX_SEC)


def action_snack(g: Girl, snack: Snack | None = None):
    """Apply snack effects. If snack is None, use legacy defaults."""
    if snack is None:
        g.hunger = clamp(g.hunger + cfg.SNACK_HUNGER_RECOVER)
        g.mood = clamp(g.mood + 3)
        g.affection += 1
        return

    g.hunger = clamp(g.hunger + float(getattr(snack, 'hunger', 0.0)))
    g.mood = clamp(g.mood + float(getattr(snack, 'mood', 0.0)))
    g.affection += int(getattr(snack, 'affection', 0))



def action_pet(g: Girl):
    g.mood = clamp(g.mood + cfg.PET_MOOD_RECOVER)
    g.affection += 2


def action_toggle_lights(g: Girl):
    g.lights_off = not g.lights_off
    if g.lights_off:
        g.state = "sleep"
        g.state_until = time.time() + random.uniform(8, 14)
