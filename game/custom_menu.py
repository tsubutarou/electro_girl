"""custom_menu.py
Unified Custom Menu (衣装 + 背景) v0.1

- Top buttons: 🎨 (toggle), ✨ (bg tab), 👗 (clothes tab)
- Menu content: tabbed grid
- Thumbnail UI: frame + selected highlight + name label

This module is intentionally standalone to avoid touching legacy ui.py menus.
"""
from __future__ import annotations

import os
import pygame


def draw_top_buttons(screen: pygame.Surface, font_ui: pygame.font.Font, g, cfg) -> dict[str, pygame.Rect]:
    """Draw top buttons and store rects in g for click handling."""
    y = int(getattr(cfg, "CUSTOM_MENU_BTN_Y", 48))
    size = int(getattr(cfg, "CUSTOM_MENU_BTN_SIZE", 30))
    gap = int(getattr(cfg, "CUSTOM_MENU_BTN_GAP", 6))
    x = int(getattr(cfg, "LEFT_X", 12))

    def draw_btn(label: str) -> pygame.Rect:
        nonlocal x
        rect = pygame.Rect(x, y, size, size)
        x += size + gap
        pygame.draw.rect(screen, (35, 35, 46), rect, 0, 10)
        pygame.draw.rect(screen, (90, 90, 110), rect, 2, 10)
        surf = font_ui.render(label, True, (235, 235, 245))
        screen.blit(surf, surf.get_rect(center=rect.center))
        return rect

    btns = {
        "custom": draw_btn("🎨"),
        "bg": draw_btn("✨"),
        "clothes": draw_btn("👗"),
    }
    g._custom_btns = btns
    return btns


def _panel_rect(cfg) -> pygame.Rect:
    x0 = int(getattr(cfg, "LEFT_X", 12))
    y0 = int(getattr(cfg, "CUSTOM_MENU_PANEL_Y", 90))
    right_x = int(getattr(cfg, "RIGHT_X", getattr(cfg, "W", 800) - 280))
    w = max(200, right_x - x0 - 16)
    h = int(getattr(cfg, "H", 600)) - y0 - 16
    return pygame.Rect(x0, y0, w, h)


def draw_custom_menu(screen: pygame.Surface, g, cfg, font_small: pygame.font.Font, font_ui: pygame.font.Font,
                     bg_thumbs: dict[str, pygame.Surface], clothes_ids: list[str]) -> None:
    if getattr(g, "ui_mode", "main") != "custom":
        g._custom_item_rects = []
        return

    panel = _panel_rect(cfg)
    pygame.draw.rect(screen, (28, 28, 36), panel, 0, 14)
    pygame.draw.rect(screen, (70, 70, 90), panel, 2, 14)

    tab = getattr(g, "custom_tab", "clothes")
    title = font_ui.render("カスタム", True, (235, 235, 245))
    sub = font_small.render(("👗 衣装" if tab == "clothes" else "✨ 背景"), True, (200, 200, 215))
    screen.blit(title, (panel.x + 14, panel.y + 10))
    screen.blit(sub, (panel.x + 14, panel.y + 10 + title.get_height() + 2))

    thumb_w = int(getattr(cfg, "THUMB_W", 120))
    thumb_h = int(getattr(cfg, "THUMB_H", 80))
    frame = int(getattr(cfg, "THUMB_FRAME", 2))
    radius = int(getattr(cfg, "THUMB_RADIUS", 10))
    name_h = int(getattr(cfg, "THUMB_NAME_HEIGHT", 18))
    gap = int(getattr(cfg, "THUMB_GAP", 14))

    gx = panel.x + 14
    gy = panel.y + 54
    avail_w = panel.w - 28
    cols = max(1, avail_w // (thumb_w + gap))

    items: list[tuple[str, str]] = []
    if tab == "bg":
        # keys are like "theme:<name>" or "img:<id>"
        for key in sorted(bg_thumbs.keys()):
            items.append(("bg", key))
    else:
        for cid in clothes_ids:
            items.append(("clothes", cid))

    rects: list[tuple[tuple[str, str], pygame.Rect]] = []
    for idx, it in enumerate(items):
        col = idx % cols
        row = idx // cols
        x = gx + col * (thumb_w + gap)
        y = gy + row * (thumb_h + name_h + gap)
        r = pygame.Rect(x, y, thumb_w, thumb_h + name_h)
        if r.bottom > panel.bottom - 10:
            break

        selected = False
        if it[0] == "bg":
            key = it[1]
            mode = getattr(g, "bg_mode", "theme")
            if isinstance(key, str) and key.startswith("img:"):
                selected = (mode == "image" and getattr(g, "bg_image_id", "") == key.split(":", 1)[1])
            elif isinstance(key, str) and key.startswith("theme:"):
                # match current theme name
                tname = key.split(":", 1)[1]
                try:
                    cur = (cfg.BG_THEMES[getattr(g, "bg_index", 0) % len(cfg.BG_THEMES)].get("name", "")
                           if cfg.BG_THEMES else "")
                except Exception:
                    cur = ""
                selected = (mode != "image" and str(cur) == str(tname))
        if it[0] == "clothes" and getattr(g, "outfit", "normal") == it[1]:
            selected = True

        frame_col = (220, 220, 245) if selected else (90, 90, 110)
        pygame.draw.rect(screen, (35, 35, 46), r, 0, radius)
        pygame.draw.rect(screen, frame_col, r, frame, radius)

        img_rect = pygame.Rect(r.x, r.y, thumb_w, thumb_h)
        if it[0] == "bg":
            surf = bg_thumbs.get(it[1])
            if surf:
                # center-crop is handled elsewhere; here we just scale to fit
                try:
                    s = surf
                    if s.get_width() != thumb_w or s.get_height() != thumb_h:
                        s = pygame.transform.smoothscale(surf, (thumb_w, thumb_h))
                    screen.blit(s, s.get_rect(center=img_rect.center))
                except Exception:
                    pass
            # display nicer label
            key = it[1]
            if isinstance(key, str) and key.startswith("theme:"):
                name = key.split(":", 1)[1]
            elif isinstance(key, str) and key.startswith("img:"):
                name = key.split(":", 1)[1]
            else:
                name = str(key)
        else:
            name = it[1]
            ib = pygame.Rect(img_rect.x + 12, img_rect.y + 12, img_rect.w - 24, img_rect.h - 24)
            pygame.draw.rect(screen, (45, 45, 58), ib, 0, 10)
            pygame.draw.rect(screen, (90, 90, 110), ib, 2, 10)
            ic = font_ui.render("👗", True, (235, 235, 245))
            screen.blit(ic, ic.get_rect(center=ib.center))

        label = font_small.render(name, True, (235, 235, 245))
        screen.blit(label, label.get_rect(midleft=(r.x + 10, r.y + thumb_h + name_h // 2)))

        rects.append((it, r))

    g._custom_item_rects = rects
