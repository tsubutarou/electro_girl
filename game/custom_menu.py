"""custom_menu.py
Unified Custom Menu (衣装 + 背景) v0.2

- Top buttons (right aligned): BG / CLOTH
  - Clicking a tab opens the menu.
  - Clicking the same tab again closes it.
- Menu content: tabbed grid
- Thumbnail UI: frame + selected highlight + name label

Notes:
  Emoji rendering is unreliable depending on the bundled font.
  This module uses ASCII labels by default to avoid mojibake.

This module is intentionally standalone to avoid touching legacy ui.py menus.
"""
from __future__ import annotations

import os
import pygame


def draw_top_buttons(screen: pygame.Surface, font_ui: pygame.font.Font, g, cfg) -> dict[str, pygame.Rect]:
    """Draw top buttons and store rects in g for click handling.

    We anchor to the top-right to avoid colliding with the header text.
    """
    y = int(getattr(cfg, "CUSTOM_MENU_BTN_Y", 8))
    size = int(getattr(cfg, "CUSTOM_MENU_BTN_SIZE", 30))
    gap = int(getattr(cfg, "CUSTOM_MENU_BTN_GAP", 6))
    margin_r = int(getattr(cfg, "CUSTOM_MENU_BTN_MARGIN_R", 8))

    # Right aligned two buttons.
    x = int(getattr(cfg, "W", 800)) - margin_r - (size * 2 + gap)

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
        "bg": draw_btn("BG"),
        "clothes": draw_btn("CL"),
    }
    g._custom_btns = btns
    return btns


def _current_bg_value(g, cfg) -> str:
    """Return current background selection as custom-menu key."""
    mode = getattr(g, "bg_mode", "theme")
    if mode == "image":
        bid = getattr(g, "bg_image_id", "") or ""
        return f"img:{bid}" if bid else ""
    # theme
    try:
        themes = getattr(cfg, "BG_THEMES", []) or []
        if not themes:
            return ""
        idx = int(getattr(g, "bg_index", 0)) % len(themes)
        name = str(themes[idx].get("name", "theme"))
        return f"theme:{name}"
    except Exception:
        return ""


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
    # Avoid emoji to prevent mojibake depending on the font.
    sub = font_small.render(("服" if tab == "clothes" else "背景"), True, (200, 200, 215))
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

    # ---- build items (bg: themes + images, clothes: ids) ----
    items: list[tuple[str, str]] = []
    if tab == "bg":
        for key in sorted(bg_thumbs.keys()):
            items.append(("bg", key))
    else:
        for cid in clothes_ids:
            items.append(("clothes", cid))

    # ---- paging / scrolling (row-based) ----
    cell_h = (thumb_h + name_h + gap)
    visible_rows = max(1, (panel.bottom - 10 - gy) // cell_h)
    total_rows = (len(items) + cols - 1) // cols
    max_scroll = max(0, total_rows - visible_rows)

    if tab == "bg":
        scroll = int(getattr(g, "custom_scroll_bg", 0))
    else:
        scroll = int(getattr(g, "custom_scroll_clothes", 0))
    scroll = max(0, min(scroll, max_scroll))

    if tab == "bg":
        g.custom_scroll_bg = scroll
    else:
        g.custom_scroll_clothes = scroll

    start_i = scroll * cols
    end_i = start_i + (visible_rows * cols)
    visible_items = items[start_i:end_i]

    # ---- scroll buttons (▲/▼) ----
    btn_size = 18
    btn_gap = 6
    bx = panel.right - 14 - btn_size
    by = panel.y + 12
    rect_up = pygame.Rect(bx, by, btn_size, btn_size)
    rect_dn = pygame.Rect(bx, by + btn_size + btn_gap, btn_size, btn_size)

    def _draw_scroll_btn(rect: pygame.Rect, enabled: bool, up: bool) -> None:
        fill = (35, 35, 46) if enabled else (25, 25, 32)
        edge = (90, 90, 110) if enabled else (60, 60, 76)
        tri = (235, 235, 245) if enabled else (130, 130, 150)
        pygame.draw.rect(screen, fill, rect, 0, 6)
        pygame.draw.rect(screen, edge, rect, 2, 6)
        if up:
            pts = [(rect.centerx, rect.y + 5), (rect.x + 5, rect.bottom - 5), (rect.right - 5, rect.bottom - 5)]
        else:
            pts = [(rect.centerx, rect.bottom - 5), (rect.x + 5, rect.y + 5), (rect.right - 5, rect.y + 5)]
        pygame.draw.polygon(screen, tri, pts)

    _draw_scroll_btn(rect_up, scroll > 0, True)
    _draw_scroll_btn(rect_dn, scroll < max_scroll, False)
    g._custom_scroll_btns = {"up": rect_up, "down": rect_dn, "tab": tab, "max": max_scroll}

    rects: list[tuple[tuple[str, str], pygame.Rect]] = []
    for idx, it in enumerate(visible_items):
        col = idx % cols
        row = idx // cols
        x = gx + col * (thumb_w + gap)
        y = gy + row * (thumb_h + name_h + gap)
        r = pygame.Rect(x, y, thumb_w, thumb_h + name_h)

        selected = False
        if it[0] == "bg":
            selected = (_current_bg_value(g, cfg) == it[1])
        if it[0] == "clothes" and getattr(g, "outfit", "normal") == it[1]:
            selected = True

        frame_col = (220, 220, 245) if selected else (90, 90, 110)
        pygame.draw.rect(screen, (35, 35, 46), r, 0, radius)
        pygame.draw.rect(screen, frame_col, r, frame, radius)

        img_rect = pygame.Rect(r.x, r.y, thumb_w, thumb_h)
        if it[0] == "bg":
            surf = bg_thumbs.get(it[1])
            if surf:
                try:
                    s = surf
                    if s.get_width() != thumb_w or s.get_height() != thumb_h:
                        s = pygame.transform.smoothscale(surf, (thumb_w, thumb_h))
                    screen.blit(s, s.get_rect(center=img_rect.center))
                except Exception:
                    pass
            key = str(it[1])
            # nicer label: theme:midnight -> midnight, img:a -> a
            if ":" in key:
                name = key.split(":", 1)[1]
            else:
                name = os.path.splitext(os.path.basename(key))[0]
        else:
            name = it[1]
            ib = pygame.Rect(img_rect.x + 12, img_rect.y + 12, img_rect.w - 24, img_rect.h - 24)
            pygame.draw.rect(screen, (45, 45, 58), ib, 0, 10)
            pygame.draw.rect(screen, (90, 90, 110), ib, 2, 10)
            ic = font_ui.render("CL", True, (235, 235, 245))
            screen.blit(ic, ic.get_rect(center=ib.center))

        label = font_small.render(name, True, (235, 235, 245))
        screen.blit(label, label.get_rect(midleft=(r.x + 10, r.y + thumb_h + name_h // 2)))

        rects.append((it, r))

    g._custom_item_rects = rects

