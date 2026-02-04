from __future__ import annotations
import random
import time

from .model import Girl, clamp
from .snacks import Snack
from .dialogue import Dialogue, set_line
from . import config as cfg


def pick_idle_state(g: Girl, dlg: Dialogue, now: float):
    # Only show the sleeping pose when she is actually sleeping.
    if getattr(g, "sleep_stage", "awake") == "sleep" or g.sleepiness >= 85:
        g.state = "sleep"
    elif g.hunger <= 20 or g.mood <= 20:
        g.state = "grumpy"
    else:
        g.state = "music" if random.random() < 0.35 else "idle"

    g.state_until = now + random.uniform(cfg.IDLE_MIN_SEC, cfg.IDLE_MAX_SEC)
    # Do not automatically speak while sleeping. (Sleep talk, if desired, is handled elsewhere.)
    if g.state != "sleep":
        set_line(g, now, dlg.pick(g.state) or "……", (2.5, 5.0))


def step_sim(g: Girl, now: float, dt: float):
    g.hunger = clamp(g.hunger - cfg.HUNGER_DECAY * dt)
    g.mood = clamp(g.mood - cfg.MOOD_DECAY * dt)
    g.sleepiness = clamp(g.sleepiness + cfg.SLEEP_INC * dt)

    if getattr(g, "sleep_stage", "awake") == "sleep" or g.state == "sleep":
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
    # Stop moving while actually sleeping (and during short sleepy transitions).
    if getattr(g, "sleep_stage", "awake") in ("drowsy", "sleep") or getattr(g, "state", "") == "sleep":
        g.vx_px_per_sec = 0.0
        # schedule a walk later to avoid immediate start upon wake
        if getattr(g, "next_walk_at", 0.0) < now:
            g.next_walk_at = now + random.uniform(cfg.WALK_REST_MIN_SEC, cfg.WALK_REST_MAX_SEC)
        return

        # Stop moving while a line is displayed (no speaking while walking)
    if getattr(g, "line", "") and now < getattr(g, "line_until", 0.0):
        g.vx_px_per_sec = 0.0
        # push next walk a bit into the future so she doesn't instantly resume
        g.next_walk_at = max(getattr(g, "next_walk_at", 0.0), now + random.uniform(cfg.WALK_REST_MIN_SEC, cfg.WALK_REST_MAX_SEC))
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

    now = time.time()

    # Turning lights OFF does not force immediate sleep; it starts a randomized sleep-readiness timer.
    if g.lights_off:
        g.sleep_ready_at = now + random.uniform(cfg.SLEEP_READY_MIN_SEC, cfg.SLEEP_READY_MAX_SEC)
        # If she was already sleeping, keep sleeping. Otherwise stay awake.
        if getattr(g, "sleep_stage", "awake") not in ("drowsy", "sleep"):
            g.sleep_stage = "awake"
            g.sleep_stage_until = 0.0
    else:
        # Turning lights ON while drowsy cancels the pre-sleep transition.
        if getattr(g, "sleep_stage", "awake") == "drowsy":
            g.sleep_stage = "awake"
            g.sleep_stage_until = 0.0


def maybe_start_pre_sleep(g: Girl, dlg: Dialogue, now: float) -> bool:
    """Enter drowsy stage and show a short "yawn" line. Returns True if started."""
    if getattr(g, "sleep_stage", "awake") != "awake":
        return False
    g.sleep_stage = "drowsy"
    dur = random.uniform(cfg.DROWSY_MIN_SEC, cfg.DROWSY_MAX_SEC)
    g.sleep_stage_until = now + dur
    # Use dialogue tag if present; fall back to a short yawn.
    set_line(g, now, dlg.pick("pre_sleep") or "ふぁ……", (dur, dur))
    return True


def maybe_start_wake_up(g: Girl, dlg: Dialogue, now: float) -> bool:
    """Start a short wake-up groggy line before switching to awake. Returns True if started."""
    if getattr(g, "sleep_stage", "awake") != "sleep":
        return False
    g.sleep_stage = "drowsy"
    dur = random.uniform(cfg.WAKE_DROWSY_MIN_SEC, cfg.WAKE_DROWSY_MAX_SEC)
    g.sleep_stage_until = now + dur
    set_line(g, now, dlg.pick("wake") or "ん……", (dur, dur))
    return True



def maybe_start_sleep_talk(g: Girl, dlg: Dialogue, now: float) -> bool:
    """While sleeping, occasionally mumble a short line (sleep talk).

    Keeps sleep_stage as 'sleep'. Returns True if started.
    """
    if getattr(g, "sleep_stage", "awake") != "sleep":
        return False
    # Avoid overlapping lines.
    if getattr(g, "line", "") and now < float(getattr(g, "line_until", 0.0)):
        return False
    dur = random.uniform(cfg.SLEEP_TALK_MIN_SEC, cfg.SLEEP_TALK_MAX_SEC)
    # Use dialogue tag if present; fall back to cute mumbling.
    fallback = random.choice(["……むにゃ……", "すやぁ……", "んぅ……", "……zzz……"])
    set_line(g, now, dlg.pick("sleep_talk") or fallback, (dur, dur))
    return True

def step_sleep_system(g: Girl, dlg: Dialogue, now: float):
    """Advance the sleep system state machine.

    This function is intentionally time-based (no permanent locks), matching the
    project's "always ends" design.
    """
    stage = getattr(g, "sleep_stage", "awake")

    # Finish drowsy transition when its timer is over AND the line is no longer showing.
    if stage == "drowsy" and now >= float(getattr(g, "sleep_stage_until", 0.0)) and now >= float(getattr(g, "line_until", 0.0)):
        # Decide whether this drowsy was pre-sleep or wake-up based on lights and readiness.
        if getattr(g, "lights_off", False):
            g.sleep_stage = "sleep"
            g.state = "sleep"
        else:
            g.sleep_stage = "awake"
        g.sleep_stage_until = 0.0

