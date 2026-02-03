from __future__ import annotations
import pygame
import time

from .model import Girl
from . import config as cfg


def status_text(g: Girl) -> str:
    return f"H{int(g.hunger):02d} M{int(g.mood):02d} S{int(g.sleepiness):02d} ❤{g.affection}"


def _fmt_time(ts: float) -> str:
    try:
        lt = time.localtime(ts)
        return f"{lt.tm_mon:02d}/{lt.tm_mday:02d} {lt.tm_hour:02d}:{lt.tm_min:02d}"
    except Exception:
        return ""


def draw_frame(
    screen,
    font,
    font_small,
    sprites,
    g: Girl,
    btns,
    mouse_pos,
    gear=None,
    talk=None,
    snack=None,
    wardrobe=None,
    snack_icons: dict[str, pygame.Surface] | None = None,
    journal_open: bool = False,
    journal_scroll: int = 0,
):
    # ---- background ----
    bg = cfg.BG_THEMES[g.bg_index % len(cfg.BG_THEMES)]["bg"] if cfg.BG_THEMES else (25, 25, 32)
    screen.fill(bg)

    # ---- header ----
    screen.blit(font.render("ELECTRO GIRL", True, (220, 220, 235)), (cfg.LEFT_X, 10))
    st = f"state:{g.state}  lights:{'OFF' if g.lights_off else 'ON'}"
    screen.blit(font_small.render(st, True, (180, 180, 200)), (cfg.LEFT_X, 32))
    screen.blit(font_small.render(status_text(g), True, (210, 210, 225)), (cfg.LEFT_X, 52))

    theme_name = cfg.BG_THEMES[g.bg_index % len(cfg.BG_THEMES)]["name"] if cfg.BG_THEMES else "bg"
    screen.blit(font_small.render(f"bg:{theme_name}", True, (170, 170, 190)), (cfg.LEFT_X, 70))

    # ---- character frame ----
    # x-axis movement (offset from right panel center)
    base_cx = cfg.RIGHT_X + cfg.RIGHT_PANEL_W // 2
    cx = int(base_cx + float(getattr(g, "x_offset", 0.0)))
    cy = 92
    frame_rect = pygame.Rect(cfg.RIGHT_X, cy - 44, cfg.RIGHT_PANEL_W, 88)
    pygame.draw.rect(screen, (45, 45, 58), frame_rect, 0, 10)
    pygame.draw.rect(screen, (110, 110, 135), frame_rect, 2, 10)

    # =========================
    # キャラ描画（body + face合成）
    # =========================
    now = time.time()

    # body（なければ従来の立ち絵）
    body = sprites.get("body_idle") or sprites.get(g.state, sprites["idle"])
    screen.blit(body, body.get_rect(center=(cx, cy)))

    # clothes overlay (optional)
    outfit = getattr(g, "outfit", "normal")
    clothes = sprites.get(f"clothes_{outfit}")
    if clothes:
        screen.blit(clothes, clothes.get_rect(center=(cx, cy)))

    # face合成：ベース顔は常に描き、瞬き・口を上に重ねる
    expr = getattr(g, "expression", "normal")
    face_base = sprites.get(f"face_{expr}") or sprites.get("face_normal")

    if face_base:
        screen.blit(face_base, face_base.get_rect(center=(cx, cy)))

        # 瞬き（目だけ透過の画像）
        blink = sprites.get("face_blink")
        if blink:
            # sleep中 / lights_off中は常に閉じ目
            if getattr(g, "state", "") == "sleep" or getattr(g, "lights_off", False):
                screen.blit(blink, blink.get_rect(center=(cx, cy)))
            elif now < getattr(g, "blink_until", 0.0):
                screen.blit(blink, blink.get_rect(center=(cx, cy)))

        # 口パク（口だけ透過の画像）
        if getattr(g, "mouth_open", False):
            mouth = sprites.get("face_mouth")
            if mouth:
                screen.blit(mouth, mouth.get_rect(center=(cx, cy)))

    # ---- lights overlay ----
    if g.lights_off:
        overlay = pygame.Surface((cfg.W, cfg.H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 90))
        screen.blit(overlay, (0, 0))

    # ---- gear panel bg ----
    if gear is not None and getattr(gear, "open", False):
        pygame.draw.rect(screen, (35, 35, 46), gear.panel, 0, 10)
        pygame.draw.rect(screen, (120, 120, 140), gear.panel, 2, 10)

    # ---- talk panel bg ----
    if talk is not None and getattr(talk, "open", False):
        pygame.draw.rect(screen, (35, 35, 46), talk.panel, 0, 10)
        pygame.draw.rect(screen, (120, 120, 140), talk.panel, 2, 10)

        # tabs
        for tab in getattr(talk, "tabs", []):
            tab.draw(screen, font_small, tab.hit(mouse_pos))

        # topics（lockedはdisabled描画）
        for b, locked in zip(getattr(talk, "topic_buttons", []), getattr(talk, "topic_locked", [])):
            if locked:
                b.draw_disabled(screen, font_small)
            else:
                b.draw(screen, font_small, b.hit(mouse_pos))

    # ---- snack panel bg ----
    if snack is not None and getattr(snack, "open", False):
        pygame.draw.rect(screen, (35, 35, 46), snack.panel, 0, 10)
        pygame.draw.rect(screen, (120, 120, 140), snack.panel, 2, 10)

        # items
        icons = snack_icons or {}
        for b, sid in zip(getattr(snack, "snack_buttons", []), getattr(snack, "snack_ids", [])):
            b.draw(screen, font_small, b.hit(mouse_pos))
            ic = icons.get(sid)
            if ic:
                # icon at left inside button
                r = b.rect
                screen.blit(ic, ic.get_rect(midleft=(r.left + 10, r.centery)))

        # paging + close
        if hasattr(snack, "prev_btn"):
            snack.prev_btn.draw(screen, font_small, snack.prev_btn.hit(mouse_pos))
        if hasattr(snack, "next_btn"):
            snack.next_btn.draw(screen, font_small, snack.next_btn.hit(mouse_pos))
        if hasattr(snack, "close_btn"):
            snack.close_btn.draw(screen, font_small, snack.close_btn.hit(mouse_pos))

    # ---- journal ----
    if journal_open:
        panel = pygame.Rect(8, 24, cfg.W - 16, cfg.H - 32)
        pygame.draw.rect(screen, (28, 28, 36), panel, 0, 12)
        pygame.draw.rect(screen, (120, 120, 140), panel, 2, 12)
        screen.blit(font.render("JOURNAL", True, (230, 230, 240)), (panel.x + 10, panel.y + 8))

        lines = list(getattr(g, "journal", []) or [])
        start = max(0, len(lines) - 12 - journal_scroll)
        view = lines[start : start + 12]
        y = panel.y + 32
        for ent in view:
            ts = _fmt_time(float(ent.get("t", 0)))
            txt = str(ent.get("text", ""))
            head = ts + " "
            surf = font_small.render((head + txt)[:52], True, (225, 225, 235))
            screen.blit(surf, (panel.x + 10, y))
            y += 14


    # ---- wardrobe panel bg ----
    if wardrobe is not None and getattr(wardrobe, "open", False):
        pygame.draw.rect(screen, (35, 35, 46), wardrobe.panel, 0, 10)
        pygame.draw.rect(screen, (120, 120, 140), wardrobe.panel, 2, 10)

        # controls
        if hasattr(wardrobe, "prev_btn") and getattr(wardrobe, "_max_pages", 1) > 1:
            wardrobe.prev_btn.draw(screen, font_small, wardrobe.prev_btn.hit(mouse_pos))
        if hasattr(wardrobe, "next_btn") and getattr(wardrobe, "_max_pages", 1) > 1:
            wardrobe.next_btn.draw(screen, font_small, wardrobe.next_btn.hit(mouse_pos))
        if hasattr(wardrobe, "close_btn"):
            wardrobe.close_btn.draw(screen, font_small, wardrobe.close_btn.hit(mouse_pos))

        # thumbnails
        for it in getattr(wardrobe, "items", []):
            hover = it.hit(mouse_pos)
            selected = (getattr(g, "outfit", "normal") == getattr(it, "outfit_id", ""))
            it.draw(screen, font_small, hover=hover, selected=selected)

    # ---- speech bubble（会話は常に見える場所）----
    bubble = pygame.Rect(cfg.LEFT_X, cfg.H - 44 - 36, (cfg.W - cfg.RIGHT_PANEL_W - 16) - cfg.LEFT_X, 28)
    pygame.draw.rect(screen, (35, 35, 46), bubble, 0, 8)
    pygame.draw.rect(screen, (90, 90, 110), bubble, 2, 8)
    screen.blit(font_small.render(g.line, True, (235, 235, 245)), (bubble.x + 8, bubble.y + 6))

    # ---- base buttons ----
    mx, my = mouse_pos
    for b in btns:
        b.draw(screen, font_small, b.hit((mx, my)))
