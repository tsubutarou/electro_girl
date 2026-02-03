from __future__ import annotations
import random
import time

from .model import Girl, clamp
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


def action_snack(g: Girl):
    g.hunger = clamp(g.hunger + cfg.SNACK_HUNGER_RECOVER)
    g.mood = clamp(g.mood + 3)
    g.affection += 1


def action_pet(g: Girl):
    g.mood = clamp(g.mood + cfg.PET_MOOD_RECOVER)
    g.affection += 2


def action_toggle_lights(g: Girl):
    g.lights_off = not g.lights_off
    if g.lights_off:
        g.state = "sleep"
        g.state_until = time.time() + random.uniform(8, 14)
