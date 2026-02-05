from __future__ import annotations

from .custom_menu import draw_top_buttons, draw_custom_menu
import pygame
import time
import math
import re


def _wrap_text_to_lines(text: str, font: pygame.font.Font, max_w: int) -> list[str]:
    """Wrap text into multiple lines so each rendered line fits within max_w.
    Newlines force line breaks. Japanese is wrapped per-character (safe default).
    """
    if not text:
        return [""]
    out: list[str] = []
    for para in text.split("\n"):
        if para == "":
            out.append("")
            continue
        cur = ""
        for ch in para:
            test = cur + ch
            if font.size(test)[0] <= max_w or cur == "":
                cur = test
            else:
                out.append(cur)
                cur = ch
        if cur:
            out.append(cur)
    return out

def _paginate_lines(lines: list[str], max_lines: int) -> list[list[str]]:
    if max_lines <= 0:
        return [lines]
    return [lines[i:i+max_lines] for i in range(0, len(lines), max_lines)]
from .model import Girl
from . import config as cfg

_FLIP_CACHE: dict[tuple[int, bool, bool], pygame.Surface] = {}


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
    # ---- custom unified menu top buttons ----
    draw_top_buttons(screen, font_small, g, cfg)

    # ---- character frame ----
    cx = cfg.RIGHT_X + cfg.RIGHT_PANEL_W // 2
    cx += int(getattr(g, "x_offset", 0))

    frame_top = 60
    frame_bottom = cfg.H - 64
    frame_h = max(110, frame_bottom - frame_top)
    frame_rect = pygame.Rect(cfg.RIGHT_X, frame_top, cfg.RIGHT_PANEL_W, frame_h)

    cy = frame_rect.bottom - int(frame_rect.height * 0.35)
    pygame.draw.rect(screen, (45, 45, 58), frame_rect, 0, 10)
    pygame.draw.rect(screen, (110, 110, 135), frame_rect, 2, 10)

    # =========================
    # キャラ描画（安全版：合成 → 反転）
    # =========================
    now = time.time()
    vx = float(getattr(g, "vx_px_per_sec", 0.0))
    walking = (abs(vx) > 0.01) and (getattr(g, "state", "idle") != "sleep")
    flip_x = vx < 0

    # optional walk frames (keys: body_walk_0, body_walk_1, ...)
    walk_keys = [k for k in sprites.keys() if k.startswith("body_walk_")]

    def _walk_key_sort(k: str) -> int:
        m = re.search(r"(\d+)$", k)
        return int(m.group(1)) if m else 0

    walk_keys.sort(key=_walk_key_sort)

    if walking and walk_keys:
        frame = int((now * float(getattr(cfg, "WALK_ANIM_FPS", 10.0))) % len(walk_keys))
        body_src = sprites.get(walk_keys[frame], sprites.get("body_idle"))
    else:
        body_src = sprites.get("body_idle") or sprites.get(g.state, sprites.get("idle"))

    bob = 0
    if walking:
        bob_px = int(getattr(cfg, "WALK_BOB_PX", 2))
        bob_hz = float(getattr(cfg, "WALK_BOB_HZ", 6.0))
        bob = int(math.sin(now * bob_hz * math.tau) * bob_px)

    if body_src:
        bw, bh = body_src.get_size()
        # Generous transparent canvas so offsets don't clip.
        char = pygame.Surface((bw * 2, bh * 2), pygame.SRCALPHA)
        center = (char.get_width() // 2, char.get_height() // 2)

        # body (unflipped)
        char.blit(body_src, body_src.get_rect(center=center))

        # clothes overlay（衣装ごとのオフセット対応）
        oid = getattr(g, "outfit", "normal")
        clothes = sprites.get(f"clothes_{oid}") or sprites.get("clothes_normal")

        # Optional: 歩行アニメ衣装（v0.1: normalのみアトラスに同梱しやすい）
        if walking and bool(getattr(cfg, "CLOTHES_WALK_ANIM", True)):
            if oid == "normal":
                ck = [k for k in sprites.keys() if k.startswith("clothes_walk_")]
                ck.sort(key=lambda k: int(re.search(r"(\d+)$", k).group(1)) if re.search(r"(\d+)$", k) else 0)
                if ck:
                    frame = int((now * float(getattr(cfg, "WALK_ANIM_FPS", 10.0))) % len(ck))
                    clothes = sprites.get(ck[frame], clothes)

        if clothes:
            off = (0, 0)
            if isinstance(clothes_offsets, dict):
                off = clothes_offsets.get(oid) or clothes_offsets.get("normal") or (0, 0)
            ox, oy = off
            char.blit(clothes, clothes.get_rect(center=(center[0] + int(ox), center[1] + int(oy))))

        # face（表情＋瞬き＋口パク）
        # v0.1: walk中は表情パーツを重ねない（ニュートラル顔はbodyに焼き込み）
        if (not walking) or bool(getattr(cfg, "FACE_DURING_WALK", False)):
            expr = getattr(g, "expression", "normal")
            face_base = sprites.get(f"face_{expr}") or sprites.get("face_normal")
            if face_base:
                char.blit(face_base, face_base.get_rect(center=center))

            blink = sprites.get("face_blink")
            if blink:
                # NOTE: 目閉じを強制するのは「実際に寝ている時」だけ。
                if getattr(g, "sleep_stage", "awake") == "sleep" or getattr(g, "state", "") == "sleep":
                    char.blit(blink, blink.get_rect(center=center))
                elif now < getattr(g, "blink_until", 0.0):
                    char.blit(blink, blink.get_rect(center=center))

            if getattr(g, "mouth_open", False):
                mouth = sprites.get("face_mouth")
                if mouth:
                    char.blit(mouth, mouth.get_rect(center=center))

        # Final flip applied ONCE to the composed character.

        if flip_x:
            char = pygame.transform.flip(char, True, False)

        screen.blit(char, char.get_rect(center=(cx, cy + bob)))

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

        wardrobe.close_btn.draw(screen, font_small, wardrobe.close_btn.hit(mouse_pos))
        wardrobe.prev_btn.draw(screen, font_small, wardrobe.prev_btn.hit(mouse_pos))
        wardrobe.next_btn.draw(screen, font_small, wardrobe.next_btn.hit(mouse_pos))

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

    # ---- base buttons ----
    mx, my = mouse_pos
    for b in btns:
        b.draw(screen, font_small, b.hit((mx, my)))

    # ---- speech bubble（UIより前面に表示 / 複数行＋ページ）----
    line_txt = getattr(g, "line", "") or ""
    walking2 = abs(float(getattr(g, "vx_px_per_sec", 0.0))) > 0.01
    # NOTE: 睡眠中でも「寝言」や「起床セリフ」を表示できるようにする。
    # バブルを消すのは「歩行中（喋りながら歩かない）」のときだけ。
    if walking2:
        line_txt = ""

    if line_txt:
        bubble_w = (cfg.W - cfg.RIGHT_PANEL_W - 16) - cfg.LEFT_X
        inner_w = max(40, bubble_w - (cfg.BUBBLE_PADDING_X * 2))
        max_lines = int(getattr(cfg, "BUBBLE_MAX_LINES", 3))
        page_i = int(getattr(g, "line_page", 0))

        wrapped = _wrap_text_to_lines(line_txt, font_small, inner_w)
        pages = _paginate_lines(wrapped, max_lines)
        if page_i >= len(pages):
            page_i = max(0, len(pages) - 1)
            g.line_page = page_i

        show_lines = pages[page_i] if pages else [line_txt]
        line_h = font_small.get_linesize() + int(getattr(cfg, "BUBBLE_LINE_GAP", 2))
        bubble_h = (cfg.BUBBLE_PADDING_Y * 2) + (len(show_lines) * line_h)

        bubble = pygame.Rect(cfg.LEFT_X, cfg.H - 44 - 36, bubble_w, bubble_h)

        # If bubble would overlap the *bottom action buttons*, lift it just above them.
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

        tx = bubble.x + cfg.BUBBLE_PADDING_X
        ty = bubble.y + cfg.BUBBLE_PADDING_Y
        for ln in show_lines:
            screen.blit(font_small.render(ln, True, (235, 235, 245)), (tx, ty))
            ty += line_h

        if len(pages) > 1:
            ind = "▶" if (page_i < len(pages) - 1) else "■"
            ind_s = font_small.render(ind, True, (235, 235, 245))
            screen.blit(ind_s, ind_s.get_rect(bottomright=(bubble.right - 6, bubble.bottom - 4)))

        setattr(g, "_bubble_rect", bubble)
        setattr(g, "_bubble_pages", len(pages))
    else:
        setattr(g, "_bubble_rect", None)
        setattr(g, "_bubble_pages", 0)

    # ---- debug HUD
    # ---- custom unified menu ----
    try:
        bg_thumbs = getattr(g, '_custom_bg_thumbs', {}) or {}
        clothes_ids = list(getattr(g, 'clothes_offsets', {}).keys()) if hasattr(g, 'clothes_offsets') else ['normal','alt']
    except Exception:
        bg_thumbs = {}
        clothes_ids = ['normal','alt']
    draw_custom_menu(screen, g, cfg, font_small, font_small, bg_thumbs, clothes_ids)
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