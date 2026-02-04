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
    bg_image=None,
    bg_label: str | None = None,
    gear=None,
    talk=None,
    wardrobe=None,
    bg_menu=None,
    snack_menu=None,
    journal_open: bool = False,
    journal_scroll: int = 0,
    clothes_offsets=None,
    debug_lines=None,
):
    # ---- background ----
    bg = cfg.BG_THEMES[g.bg_index % len(cfg.BG_THEMES)]["bg"] if cfg.BG_THEMES else (25, 25, 32)
    screen.fill(bg)

    # image background (cover)
    if bg_image is not None:
        try:
            iw, ih = bg_image.get_size()
            if iw > 0 and ih > 0:
                sw, sh = cfg.W, cfg.H
                s = max(sw / iw, sh / ih)
                nw = max(1, int(iw * s))
                nh = max(1, int(ih * s))
                scaled = pygame.transform.smoothscale(bg_image, (nw, nh))
                x = (sw - nw) // 2
                y = (sh - nh) // 2
                screen.blit(scaled, (x, y))
        except Exception:
            pass

    # ---- header ----
    screen.blit(font.render("ELECTRO GIRL", True, (220, 220, 235)), (cfg.LEFT_X, 10))
    st = f"state:{g.state}  lights:{'OFF' if g.lights_off else 'ON'}"
    screen.blit(font_small.render(st, True, (180, 180, 200)), (cfg.LEFT_X, 32))
    screen.blit(font_small.render(status_text(g), True, (210, 210, 225)), (cfg.LEFT_X, 52))

    if bg_label is None:
        theme_name = cfg.BG_THEMES[g.bg_index % len(cfg.BG_THEMES)]["name"] if cfg.BG_THEMES else "bg"
        bg_label = theme_name
    screen.blit(font_small.render(f"bg:{bg_label}", True, (170, 170, 190)), (cfg.LEFT_X, 70))

    # ---- character frame ----
    cx = cfg.RIGHT_X + cfg.RIGHT_PANEL_W // 2
    cx += int(getattr(g, 'x_offset', 0))
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

    # clothes overlay（衣装ごとのオフセット対応）
    oid = getattr(g, "outfit", "normal")
    clothes = sprites.get(f"clothes_{oid}") or sprites.get("clothes_normal")
    if clothes:
        off = (0, 0)
        if isinstance(clothes_offsets, dict):
            off = clothes_offsets.get(oid) or clothes_offsets.get("normal") or (0, 0)
        ox, oy = off
        screen.blit(clothes, clothes.get_rect(center=(cx + int(ox), cy + int(oy))))

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

        # paging + close
        if hasattr(talk, "prev_btn"):
            talk.prev_btn.draw(screen, font_small, talk.prev_btn.hit(mouse_pos))
        if hasattr(talk, "next_btn"):
            talk.next_btn.draw(screen, font_small, talk.next_btn.hit(mouse_pos))
        if hasattr(talk, "close_btn"):
            talk.close_btn.draw(screen, font_small, talk.close_btn.hit(mouse_pos))

        # YES/NO
        if getattr(g, "awaiting_choice", False):
            talk.btn_yes.draw(screen, font_small, talk.btn_yes.hit(mouse_pos))
            talk.btn_no.draw(screen, font_small, talk.btn_no.hit(mouse_pos))

    # ---- wardrobe panel bg ----
    if wardrobe is not None and getattr(wardrobe, "open", False):
        pygame.draw.rect(screen, (35, 35, 46), wardrobe.panel, 0, 12)
        pygame.draw.rect(screen, (120, 120, 140), wardrobe.panel, 2, 12)

        # buttons
        wardrobe.close_btn.draw(screen, font_small, wardrobe.close_btn.hit(mouse_pos))
        wardrobe.prev_btn.draw(screen, font_small, wardrobe.prev_btn.hit(mouse_pos))
        wardrobe.next_btn.draw(screen, font_small, wardrobe.next_btn.hit(mouse_pos))

        # thumbs
        for it in getattr(wardrobe, "items", []):
            it.draw(
                screen,
                font_small,
                hover=it.hit(mouse_pos),
                selected=(getattr(g, "outfit", "normal") == getattr(it, "value", "")),
            )

    # ---- background menu panel bg ----
    if bg_menu is not None and getattr(bg_menu, "open", False):
        pygame.draw.rect(screen, (35, 35, 46), bg_menu.panel, 0, 12)
        pygame.draw.rect(screen, (120, 120, 140), bg_menu.panel, 2, 12)

        bg_menu.close_btn.draw(screen, font_small, bg_menu.close_btn.hit(mouse_pos))
        bg_menu.prev_btn.draw(screen, font_small, bg_menu.prev_btn.hit(mouse_pos))
        bg_menu.next_btn.draw(screen, font_small, bg_menu.next_btn.hit(mouse_pos))

        sel_mode = getattr(g, "bg_mode", "theme")
        sel_val = ""
        if sel_mode == "image":
            sel_val = "img:" + (getattr(g, "bg_image_id", "") or "")
        else:
            # theme selection by index
            try:
                name = cfg.BG_THEMES[getattr(g, "bg_index", 0) % len(cfg.BG_THEMES)].get("name", "")
                sel_val = "theme:" + str(name)
            except Exception:
                sel_val = ""
        for it in getattr(bg_menu, "items", []):
            it.draw(screen, font_small, hover=it.hit(mouse_pos), selected=(it.value == sel_val))

    # ---- snack panel bg ----
    if snack_menu is not None and getattr(snack_menu, "open", False):
        pygame.draw.rect(screen, (35, 35, 46), snack_menu.panel, 0, 12)
        pygame.draw.rect(screen, (120, 120, 140), snack_menu.panel, 2, 12)

        snack_menu.close_btn.draw(screen, font_small, snack_menu.close_btn.hit(mouse_pos))
        snack_menu.prev_btn.draw(screen, font_small, snack_menu.prev_btn.hit(mouse_pos))
        snack_menu.next_btn.draw(screen, font_small, snack_menu.next_btn.hit(mouse_pos))

        for it in getattr(snack_menu, "items", []):
            it.draw(screen, font_small, hover=it.hit(mouse_pos), selected=False)

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

    # ---- UI panels (gear / talk / wardrobe) ----
    mx, my = mouse_pos

    # gear menu panel background (buttons are in btns list)
    if gear is not None and getattr(gear, "open", False):
        pygame.draw.rect(screen, (40, 40, 52), gear.panel, 0, 10)
        pygame.draw.rect(screen, (120, 120, 145), gear.panel, 2, 10)

    # talk menu panel
    if talk is not None and getattr(talk, "open", False):
        pygame.draw.rect(screen, (40, 40, 52), talk.panel, 0, 10)
        pygame.draw.rect(screen, (120, 120, 145), talk.panel, 2, 10)

        # close / paging
        talk.close_btn.draw(screen, font_small, talk.close_btn.hit((mx, my)))
        talk.prev_btn.draw(screen, font_small, talk.prev_btn.hit((mx, my)))
        talk.next_btn.draw(screen, font_small, talk.next_btn.hit((mx, my)))

        # tabs
        for tab in getattr(talk, "tabs", []):
            tab.draw(screen, font_small, tab.hit((mx, my)))

        # topic buttons
        for b in getattr(talk, "topic_buttons", []):
            b.draw(screen, font_small, b.hit((mx, my)))

        # YES/NO if awaiting
        if getattr(g, "awaiting_choice", False):
            talk.btn_yes.draw(screen, font_small, talk.btn_yes.hit((mx, my)))
            talk.btn_no.draw(screen, font_small, talk.btn_no.hit((mx, my)))

    # wardrobe menu panel
    if wardrobe is not None and getattr(wardrobe, "open", False):
        pygame.draw.rect(screen, (40, 40, 52), wardrobe.panel, 0, 10)
        pygame.draw.rect(screen, (120, 120, 145), wardrobe.panel, 2, 10)

        wardrobe.close_btn.draw(screen, font_small, wardrobe.close_btn.hit((mx, my)))
        wardrobe.prev_btn.draw(screen, font_small, wardrobe.prev_btn.hit((mx, my)))
        wardrobe.next_btn.draw(screen, font_small, wardrobe.next_btn.hit((mx, my)))

        sel = getattr(g, "outfit", "normal")
        for it in getattr(wardrobe, "items", []):
            it.draw(screen, font_small, it.hit((mx, my)), selected=(it.value == sel))

    # ---- base buttons ----
    mx, my = mouse_pos
    for b in btns:
        b.draw(screen, font_small, b.hit((mx, my)))


    # ---- speech bubble（UIより前面に表示）----
    line_txt = getattr(g, "line", "") or ""
    walking = abs(float(getattr(g, "vx_px_per_sec", 0.0))) > 0.01
    if walking or getattr(g, "state", "") == "sleep" or getattr(g, "lights_off", False):
        line_txt = ""

    if line_txt:
        bubble_w = (cfg.W - cfg.RIGHT_PANEL_W - 16) - cfg.LEFT_X
        bubble = pygame.Rect(cfg.LEFT_X, cfg.H - 44 - 36, bubble_w, 28)

        # If bubble would overlap the *bottom action buttons* (SNACK/PET/TALK),
        # lift it just above them. Ignore gear menu items that may be near the top.
        min_btn_top = None
        try:
            bottom_btns = [b for b in (btns or []) if hasattr(b, "rect") and b.rect.top >= (cfg.H - 80)]
            if bottom_btns:
                min_btn_top = min(b.rect.top for b in bottom_btns)
        except Exception:
            min_btn_top = None

        if min_btn_top is not None and bubble.bottom > (min_btn_top - 6):
            bubble.bottom = max(32, min_btn_top - 6)

        pygame.draw.rect(screen, (35, 35, 46), bubble, 0, 8)
        pygame.draw.rect(screen, (90, 90, 110), bubble, 2, 8)
        screen.blit(font_small.render(line_txt, True, (235, 235, 245)), (bubble.x + 8, bubble.y + 6))

    # ---- debug HUD (F1) ----
    if debug_lines:
        pad = 6
        lines = [str(x) for x in debug_lines if x is not None]
        if lines:
            w = max(font_small.size(s)[0] for s in lines) + pad * 2
            h = (font_small.get_height() + 2) * len(lines) + pad * 2
            w = min(w, cfg.W - 16)
            h = min(h, cfg.H - 16)
            panel = pygame.Rect(8, 8, w, h)
            surf = pygame.Surface((panel.w, panel.h), pygame.SRCALPHA)
            surf.fill((0, 0, 0, 140))
            screen.blit(surf, panel.topleft)
            pygame.draw.rect(screen, (200, 200, 220), panel, 1, 8)

            y = panel.y + pad
            for s in lines:
                screen.blit(font_small.render(s, True, (240, 240, 250)), (panel.x + pad, y))
                y += font_small.get_height() + 2