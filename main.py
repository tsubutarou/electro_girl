"""ElectroGirl entry point.

This file wires together:
  - save/load (model.py)
  - simulation ticks (sim.py)
  - UI interactions (ui.py)
  - rendering (render.py)

Tip for future-you:
  - Keep "environment" toggles (lights/background/window) separate from the
    girl's internal state. The project works because nothing hard-locks.
"""

import os
import time
import random
import json

import sys
import ctypes

import pygame

from game import config as cfg
from game.model import load_or_new, save
from game.dialogue import Dialogue, greet_on_start, set_line
from game.assets import load_sprites, load_sounds, load_clothes_offsets, load_background_images, make_theme_thumbs
from game.sim import (
    step_sim,
    pick_idle_state,
    step_sleep_system,
    maybe_start_pre_sleep,
    maybe_start_wake_up,
    maybe_start_sleep_talk,
    action_snack,
    action_pet,
    action_toggle_lights,
)
from game.ui import make_buttons, cycle_bg, clamp01, Button
from game.render import draw_frame
from game.snacks import Snacks
from game.topics import Topics, unlock_ok, describe_unlock
from game.journal import add_log



def _load_borderless_pref() -> bool:
    """Read borderless preference from save file without constructing full Girl.
    This allows creating the window with the right flags on startup."""
    try:
        if os.path.exists(cfg.SAVE_PATH):
            with open(cfg.SAVE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return bool(data.get("borderless", False))
    except Exception:
        pass
    return False




def _load_dock_pref() -> bool:
    """Read borderless preference from save file without constructing full Girl.
    This allows creating the window with the right flags on startup."""
    try:
        if os.path.exists(cfg.SAVE_PATH):
            with open(cfg.SAVE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return bool(data.get("dock_bottom_right", True))
    except Exception:
        pass
    return False




def _move_window_bottom_right(margin: int = 8) -> None:
    """Windows: move window to bottom-right corner of the primary monitor.

    Note: If the window has a frame/titlebar, the *outer* window size is larger than cfg.W/cfg.H.
    We therefore compute the current window rect and use its size to avoid clipping off-screen.
    """
    if sys.platform != "win32":
        return
    try:
        info = pygame.display.get_wm_info()
        hwnd = info.get("window")
        if not hwnd:
            return

        user32 = ctypes.windll.user32
        sw = int(user32.GetSystemMetrics(0))  # SM_CXSCREEN
        sh = int(user32.GetSystemMetrics(1))  # SM_CYSCREEN

        # Get outer window size (includes frame), so we can keep the whole window visible.
        from ctypes import wintypes
        rect = wintypes.RECT()
        if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            win_w = int(rect.right - rect.left)
            win_h = int(rect.bottom - rect.top)
        else:
            # Fallback: assume client size
            win_w = int(cfg.W)
            win_h = int(cfg.H)

        x = max(0, sw - win_w - margin)
        y = max(0, sh - win_h - margin)

        SWP_NOSIZE = 0x0001
        SWP_NOZORDER = 0x0004
        SWP_SHOWWINDOW = 0x0040
        user32.SetWindowPos(hwnd, 0, x, y, 0, 0, SWP_NOSIZE | SWP_NOZORDER | SWP_SHOWWINDOW)
    except Exception:
        return



def _get_cursor_pos():
    """Windows: get cursor position in screen coordinates. Returns (x,y) or None."""
    if sys.platform != "win32":
        return None
    try:
        from ctypes import wintypes
        pt = wintypes.POINT()
        if ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)):
            return int(pt.x), int(pt.y)
    except Exception:
        pass
    return None


def _set_window_pos_screen(x: int, y: int) -> bool:
    """Windows: move window top-left to (x,y) in screen coordinates."""
    if sys.platform != "win32":
        return False
    try:
        info = pygame.display.get_wm_info()
        hwnd = info.get("window")
        if not hwnd:
            return False
        user32 = ctypes.windll.user32

        SWP_NOSIZE = 0x0001
        SWP_NOZORDER = 0x0004
        SWP_SHOWWINDOW = 0x0040

        user32.SetWindowPos(hwnd, 0, int(x), int(y), 0, 0, SWP_NOSIZE | SWP_NOZORDER | SWP_SHOWWINDOW)
        return True
    except Exception:
        return False




def _set_window_topmost(enabled: bool) -> bool:
    """Windows: set the pygame window to be always-on-top or not."""
    if sys.platform != "win32":
        return False
    try:
        info = pygame.display.get_wm_info()
        hwnd = info.get("window")
        if not hwnd:
            return False
        user32 = ctypes.windll.user32
        try:
            user32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
            user32.SetWindowPos.restype = ctypes.c_bool
        except Exception:
            pass

        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_SHOWWINDOW = 0x0040

        HWND_TOPMOST = -1
        HWND_NOTOPMOST = -2

        user32.SetWindowPos(hwnd, HWND_TOPMOST if enabled else HWND_NOTOPMOST,
                            0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
        return True
    except Exception:
        return False

def _get_window_rect():
    """Windows: get outer window rect (left, top, right, bottom) or None."""
    if sys.platform != "win32":
        return None
    try:
        info = pygame.display.get_wm_info()
        hwnd = info.get("window")
        if not hwnd:
            return None
        user32 = ctypes.windll.user32
        from ctypes import wintypes
        rect = wintypes.RECT()
        if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return int(rect.left), int(rect.top), int(rect.right), int(rect.bottom)
    except Exception:
        pass
    return None
def _should_quit_on_escape(gear, talk, journal_open: bool) -> bool:
    """ESC: first close panels; if nothing open, quit."""
    if journal_open:
        return False
    if getattr(gear, "open", False) or getattr(talk, "open", False):
        return False
    return True



def _stop_walking(g, now: float):
    """Stop walking immediately and schedule the next walk later."""
    if hasattr(g, "vx_px_per_sec"):
        g.vx_px_per_sec = 0.0
    if hasattr(g, "walk_until"):
        g.walk_until = now
    if hasattr(g, "next_walk_at"):
        g.next_walk_at = now + random.uniform(cfg.WALK_REST_MIN_SEC, cfg.WALK_REST_MAX_SEC)


def _start_walking(g, now: float):
    """Request walking to start as soon as possible (sim.step_move will pick direction/speed)."""
    # If we are "silent" but line_until is still in the future, unlock movement.
    if hasattr(g, "line_until") and getattr(g, "line", "") == "":
        g.line_until = now

    if hasattr(g, "next_walk_at"):
        g.next_walk_at = now
    if hasattr(g, "walk_until"):
        g.walk_until = now


def _set_line_auto(g, now: float, text: str):
    from game import config as cfg
    # duration based on text length (keeps short lines readable, long lines not too long)
    n = len(text)
    dur = cfg.IDLE_LINE_MIN_SEC + n * cfg.IDLE_SEC_PER_CHAR
    dur = max(cfg.IDLE_LINE_MIN_SEC, min(cfg.IDLE_LINE_MAX_SEC, dur))
    g.line = text
    g.line_until = now + dur

def main():
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()

    mixer_ok = True
    try:
        pygame.mixer.init()
    except Exception:
        mixer_ok = False

    flags = pygame.NOFRAME if _load_borderless_pref() else 0
    screen = pygame.display.set_mode((cfg.W, cfg.H), flags)
    pygame.display.set_caption("Electro Girl")
    clock = pygame.time.Clock()

    # 起動時：右下に寄せる（常駐っぽさ）
    if _load_dock_pref():
        _move_window_bottom_right(margin=8)

    # 日本語フォント
    jp_font_path_candidates = [
        r"C:\Windows\Fonts\meiryo.ttc",
        r"C:\Windows\Fonts\YuGothM.ttc",
        r"C:\Windows\Fonts\msgothic.ttc",
    ]
    jp_font_path = next((p for p in jp_font_path_candidates if os.path.exists(p)), None)
    if jp_font_path:
        font = pygame.font.Font(jp_font_path, 16)
        font_small = pygame.font.Font(jp_font_path, 14)
    else:
        font = pygame.font.SysFont(None, 16)
        font_small = pygame.font.SysFont(None, 14)

    # --- assets ---
    # ※瞬き口パク用の face スプライトも load_sprites 側で読む（後述の差分を適用）
    scale = 3
    sprites = load_sprites(scale=scale)
    clothes_offsets = load_clothes_offsets(scale=scale)
    sounds = load_sounds(mixer_ok)

    dlg = Dialogue(cfg.DLG_PATH)
    snacks = Snacks()
    # Apply always-on-top setting on startup (Windows only)

    snacks.load_if_needed(force=True, icon_scale=cfg.SNACK_ICON_SCALE)
    topics = Topics(cfg.TOPICS_PATH)

    g = load_or_new()
    
    _set_window_topmost(bool(getattr(g, 'always_on_top', False)))
    # 表情の初期値
    g.expression = getattr(g, "expression", "normal")
    g.dock_bottom_right = getattr(g, "dock_bottom_right", True)

    now = time.time()
    # --- ensure new sleep-system fields exist for older saves ---
    if not hasattr(g, "sleep_stage"):
        g.sleep_stage = "awake"
    if not hasattr(g, "sleep_ready_at"):
        g.sleep_ready_at = 0.0
    if not hasattr(g, "sleep_stage_until"):
        g.sleep_stage_until = 0.0
    # If lights are already off on startup, schedule sleep readiness if missing.
    if getattr(g, "lights_off", False) and float(getattr(g, "sleep_ready_at", 0.0)) <= now:
        g.sleep_ready_at = now + random.uniform(cfg.SLEEP_READY_MIN_SEC, cfg.SLEEP_READY_MAX_SEC)

    if not g.first_seen:
        g.first_seen = now
        save(g)

    pick_idle_state(g, dlg, now)
    greet_on_start(g, dlg, now)

    btn_snack, btn_pet, btn_light, btn_char, gear, talk, wardrobe, bg_menu, snack_menu = make_buttons()

    # ---- background images (auto from assets/background) ----
    bg_images, bg_image_thumbs = load_background_images(scale=1, thumb_size=(40, 40))
    theme_thumbs = make_theme_thumbs(thumb_size=(40, 40))

    bg_thumbs: dict[str, pygame.Surface] = {}
    for name, t in theme_thumbs.items():
        bg_thumbs[f"theme:{name}"] = t
    for bid, t in bg_image_thumbs.items():
        bg_thumbs[f"img:{bid}"] = t

    bg_values = [f"theme:{t.get('name','theme')}" for t in (cfg.BG_THEMES or [])]
    bg_values += [f"img:{bid}" for bid in bg_images.keys()]

    # 右クリックメニュー（簡易）
    ctx_open = False
    ctx_buttons = []

    # ---- 瞬き/口パクの状態（保存しない動的属性として持つ）----
    g.blink_until = 0.0
    g.next_blink = now + random.uniform(2.5, 5.0)
    g.mouth_open = False
    g.mouth_until = 0.0

    journal_open = False
    journal_scroll = 0

    debug_hud = False

    # ---- window drag (Ctrl + Left Drag) ----
    dragging_window = False
    drag_offset = (0, 0)  # client coords offset from window top-left
    dock_disabled_by_drag = False

    def play_sfx(key: str):
        if getattr(g, "sfx_muted", False):
            return
        s = sounds.get(key)
        if s:
            base = cfg.SFX_BASE_VOLUME.get(key, 0.3)
            s.set_volume(base * clamp01(getattr(g, "sfx_scale", 1.0)))
            try:
                s.stop()
            except Exception:
                pass
            s.play()

    def current_background():
        """Return (bg_surface or None, label str)."""
        mode = getattr(g, "bg_mode", "theme")
        if mode == "image":
            bid = getattr(g, "bg_image_id", "") or ""
            if bid and bid in bg_images:
                return bg_images[bid], bid
        # theme fallback
        try:
            t = cfg.BG_THEMES[getattr(g, "bg_index", 0) % len(cfg.BG_THEMES)]
            return None, str(t.get("name", "theme"))
        except Exception:
            return None, "theme"
    

    def request_quit(now_ts: float):
        """Show a farewell line briefly, then quit."""
        bye = dlg.pick("bye") or "またね。"
        set_line(g, now_ts, bye, (2.0, 2.0))
        play_sfx("talk")
        g.last_seen = now_ts
        save(g)

        end_at = time.time() + 0.6
        while time.time() < end_at:
            for _e in pygame.event.get():
                pass
            btns = [btn_snack, btn_pet, btn_light, talk.btn_talk, btn_char, *gear.all_buttons_for_draw()]
            bg_img, bg_lbl = current_background()
            draw_frame(
                screen, font, font_small, sprites, g, btns, pygame.mouse.get_pos(),
                bg_image=bg_img, bg_label=bg_lbl,
                gear=gear, talk=talk, wardrobe=wardrobe, bg_menu=bg_menu, snack_menu=snack_menu, journal_open=journal_open, journal_scroll=journal_scroll,
                clothes_offsets=clothes_offsets,
                debug_lines=None
            )
            # context menu is ignored during exit animation
            pygame.display.flip()
            pygame.time.delay(10)
        return

    def say_with_expression(text: str, dur=(2.0, 4.0), expr="smile"):
        set_line(g, time.time(), text, dur)
        g.expression = expr


    def mark_new(topic_id: str):
        if topic_id not in g.new_topics:
            g.new_topics.append(topic_id)

    def clear_new(topic_id: str):
        if topic_id in g.new_topics:
            g.new_topics = [x for x in g.new_topics if x != topic_id]

    def refresh_unlocks():
        topics.load_if_needed()
        changed = False
        for t in topics.list_all():
            if t.id in g.unlocked_topics:
                continue
            if unlock_ok(g, t.unlock, time.time()):
                g.unlocked_topics.append(t.id)
                mark_new(t.id)
                changed = True
        if changed:
            save(g)

    def start_topic(topic_id: str):
        t = topics.get(topic_id)
        if not t:
            return
        clear_new(topic_id)
        g.active_topic = topic_id
        g.seq_index = 0
        g.awaiting_choice = False
        g.pending_yes = ""
        g.pending_no = ""
        g.pending_flag = ""
        advance_topic(t)

    def advance_topic(t):
        while g.seq_index < len(t.sequence):
            item = t.sequence[g.seq_index]
            g.seq_index += 1

            if "say" in item:
                text = str(item.get("say", ""))
                if text:
                    set_line(g, time.time(), text, (2.0, 4.0))
                    g.expression = "smile"   # ← 追加：喋り始めたら笑顔
                    add_log(g, text, t.id, t.title)
                    play_sfx("talk")
                    return


            if "ask" in item:
                q = str(item.get("ask", ""))
                yes = str(item.get("yes", "うん"))
                no = str(item.get("no", "ううん"))
                flag = str(item.get("set_flag", ""))

                if q:
                    set_line(g, time.time(), q, (3.0, 6.0))
                    g.expression = "smile"   # ← 追加
                    add_log(g, q, t.id, t.title)


                g.awaiting_choice = True
                g.pending_yes = yes
                g.pending_no = no
                g.pending_flag = flag
                play_sfx("talk")
                return

        g.active_topic = ""
        g.awaiting_choice = False

    def answer(choice_yes: bool):
        t = topics.get(g.active_topic)
        if not t:
            g.active_topic = ""
            g.awaiting_choice = False
            return

        text = g.pending_yes if choice_yes else g.pending_no
        if text:
            set_line(g, time.time(), text, (1.5, 3.0))
            g.expression = "smile"   # ← 追加
            add_log(g, text, t.id, t.title)
            play_sfx("talk")


        if g.pending_flag:
            g.flags[g.pending_flag] = True

        g.awaiting_choice = False
        g.pending_yes = ""
        g.pending_no = ""
        g.pending_flag = ""
        advance_topic(t)

    def build_category_view():
        cats = [(c.id, c.label) for c in topics.category_order()]
        if not cats:
            cats = [("misc", "その他")]

        if talk.active_cat not in [cid for cid, _ in cats]:
            talk.active_cat = cats[0][0]
            talk.page = 0

        entries = []
        for t in topics.list_all():
            if t.category != talk.active_cat:
                continue
            locked = (t.id not in g.unlocked_topics)
            is_new = (t.id in g.new_topics) and (not locked)
            entries.append((t.id, t.title, locked, is_new))

        # unlocked first, then NEW, then title
        entries.sort(key=lambda x: (x[2], not x[3], x[1]))
        return cats, entries

    last_save = time.time()
    running = True

    while running:
        dt = clock.tick(cfg.FPS) / 1000.0
        now = time.time()

        dlg.load_if_needed()
        topics.load_if_needed()

        refresh_unlocks()

        cats, entries = build_category_view()

        # outfits list for wardrobe (from loaded sprites)
        outfits = sorted({k[len("clothes_"):] for k in sprites.keys() if k.startswith("clothes_")})
        if not outfits:
            outfits = ["normal"]

        events = pygame.event.get()

        for e in events:

            # Ctrl + Left Drag: move the window (useful for NOFRAME).
            if (
                e.type == pygame.MOUSEBUTTONDOWN
                and e.button == 1
                and (pygame.key.get_mods() & pygame.KMOD_CTRL)
            ):

                # ---- multiline bubble: click to advance page ----
                try:
                    bub = getattr(g, "_bubble_rect", None)
                    pages = int(getattr(g, "_bubble_pages", 0))
                    if bub and pages > 1 and bub.collidepoint(e.pos):
                        pi = int(getattr(g, "line_page", 0))
                        if pi < pages - 1:
                            g.line_page = pi + 1
                            g.line_until = max(float(getattr(g, "line_until", 0.0)), now + 30.0)
                        else:
                            g.line_until = min(float(getattr(g, "line_until", now + 0.1)), now + 0.1)
                        continue
                except Exception:
                    pass
                dragging_window = True
                drag_offset = e.pos
                dock_disabled_by_drag = False
                continue

            if e.type == pygame.MOUSEBUTTONUP and e.button == 1 and dragging_window:
                dragging_window = False
                continue

            if e.type == pygame.MOUSEMOTION and dragging_window:
                cp = _get_cursor_pos()
                if cp:
                    x = cp[0] - int(drag_offset[0])
                    y = cp[1] - int(drag_offset[1])

                    # Clamp to primary screen so the window doesn't disappear.
                    try:
                        sw = int(ctypes.windll.user32.GetSystemMetrics(0))  # SM_CXSCREEN
                        sh = int(ctypes.windll.user32.GetSystemMetrics(1))  # SM_CYSCREEN
                    except Exception:
                        sw, sh = 0, 0

                    rect = _get_window_rect()
                    if rect and sw and sh:
                        w = rect[2] - rect[0]
                        h = rect[3] - rect[1]
                        x = max(0, min(int(x), int(sw - w)))
                        y = max(0, min(int(y), int(sh - h)))

                    _set_window_pos_screen(int(x), int(y))

                    # If the user manually drags, treat it as "I want to place it myself":
                    # auto-disable DOCK and persist the choice.
                    if (not dock_disabled_by_drag) and getattr(g, "dock_bottom_right", False):
                        g.dock_bottom_right = False
                        save(g)
                        set_line(g, now, "ドック解除。", (0.8, 1.6))
                        dock_disabled_by_drag = True
                continue
            if e.type == pygame.QUIT:
                request_quit(now)
                running = False

            
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 3:
                # 右クリック：簡易メニュー（終了）
                pos = e.pos
                if ctx_open:
                    ctx_open = False
                    continue
                w, h = 120, 22
                pad = 6
                x = min(pos[0], cfg.W - (w + 2*pad))
                y = min(pos[1], cfg.H - (h*2 + pad*3))
                btn_exit = Button((x+pad, y+pad, w, h), "EXIT")
                btn_cancel = Button((x+pad, y+pad + h + pad, w, h), "CANCEL")
                ctx_buttons = [btn_exit, btn_cancel]
                ctx_open = True
                continue

            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                pos = e.pos

                # 右クリックメニューが開いているなら、まずそれを処理
                if ctx_open:
                    if ctx_buttons and len(ctx_buttons) >= 2:
                        if ctx_buttons[0].hit(pos):  # EXIT
                            ctx_open = False
                            request_quit(now)
                            running = False
                            continue
                        if ctx_buttons[1].hit(pos):  # CANCEL
                            ctx_open = False
                            continue
                    # 外側クリックでも閉じる
                    ctx_open = False
                    continue

                if journal_open:
                    journal_open = False
                    continue

                if gear.open and (not gear.hit_any(pos)) and (not gear.btn_gear.hit(pos)):
                    gear.close()
                if talk.open and (not talk.hit_any(pos)) and (not talk.btn_talk.hit(pos)):
                    talk.close()
                if wardrobe.open and (not wardrobe.hit_any(pos)):
                    wardrobe.close()
                if bg_menu.open and (not bg_menu.hit_any(pos)):
                    bg_menu.close()
                if snack_menu.open and (not snack_menu.hit_any(pos)) and (not btn_snack.hit(pos)):
                    snack_menu.close()

                if btn_char.hit(pos):
                    wardrobe.toggle()
                    if wardrobe.open:
                        wardrobe.relayout(outfits, sprites)
                    play_sfx("talk")
                    continue

                if gear.btn_gear.hit(pos):
                    gear.toggle()
                    continue

                if gear.open:
                    if gear.btn_prev.hit(pos):
                        gear.page_prev()
                        continue
                    if gear.btn_next.hit(pos):
                        gear.page_next()
                        continue
                    if gear.item_bg.hit(pos):
                        bg_menu.toggle()
                        if bg_menu.open:
                            bg_menu.relayout(bg_values, bg_thumbs)
                        play_sfx("talk")
                        continue

                    if gear.item_frame.hit(pos):
                        g.borderless = not getattr(g, "borderless", False)
                        msg = "次回から枠なしにする。" if g.borderless else "次回から枠ありに戻す。"
                        set_line(g, now, msg, (1.2, 2.5))
                        play_sfx("talk")
                        save(g)
                        continue

                    if gear.item_dock.hit(pos):
                        g.dock_bottom_right = not getattr(g, "dock_bottom_right", True)
                        if g.dock_bottom_right:
                            _move_window_bottom_right(margin=8)
                        msg = "右下に固定する。" if g.dock_bottom_right else "右下固定、解除。"
                        set_line(g, now, msg, (1.0, 2.0))
                        play_sfx("talk")
                        save(g)
                        continue

                    if gear.item_top.hit(pos):
                        g.always_on_top = not getattr(g, "always_on_top", False)
                        ok = _set_window_topmost(bool(g.always_on_top))
                        msg = "最前面にする。" if g.always_on_top else "最前面、解除。"
                        if not ok and sys.platform == "win32":
                            msg = msg + "（反映できないかも）"
                        set_line(g, now, msg, (1.0, 2.0))
                        play_sfx("talk")
                        save(g)
                        gear.update_labels(g)
                        continue

                    if gear.item_mute.hit(pos):
                        g.sfx_muted = not g.sfx_muted
                        set_line(g, now, "無音モード。" if g.sfx_muted else "音、戻した。", (1.0, 2.0))
                        save(g)
                        continue
                    if gear.item_up.hit(pos):
                        g.sfx_scale = min(1.0, g.sfx_scale + 0.10)
                        set_line(g, now, "音量あげる。", (0.8, 1.5))
                        save(g)
                        continue
                    if gear.item_down.hit(pos):
                        g.sfx_scale = max(0.0, g.sfx_scale - 0.10)
                        set_line(g, now, "音量さげる。", (0.8, 1.5))
                        save(g)
                        continue
                    if gear.item_outfit.hit(pos):
                        wardrobe.toggle()
                        if wardrobe.open:
                            wardrobe.relayout(outfits, sprites)
                        play_sfx("talk")
                        continue

                    if gear.item_log.hit(pos):
                        journal_open = True
                        journal_scroll = 0
                        continue

                if wardrobe.open:
                    # paging
                    if wardrobe.close_btn.hit(pos):
                        wardrobe.close()
                        continue
                    if wardrobe.prev_btn.hit(pos):
                        wardrobe.page = (wardrobe.page - 1) % max(1, wardrobe._max_pages)
                        wardrobe.relayout(outfits, sprites)
                        continue
                    if wardrobe.next_btn.hit(pos):
                        wardrobe.page = (wardrobe.page + 1) % max(1, wardrobe._max_pages)
                        wardrobe.relayout(outfits, sprites)
                        continue

                    # pick outfit
                    for it in wardrobe.items:
                        if it.hit(pos):
                            g.outfit = it.value
                            set_line(g, now, f"{it.value} に着替えた。", (1.0, 2.0))
                            play_sfx("talk")
                            save(g)
                            wardrobe.close()
                            break

                if bg_menu.open:
                    if bg_menu.close_btn.hit(pos):
                        bg_menu.close()
                        continue
                    if bg_menu.prev_btn.hit(pos):
                        bg_menu.page = (bg_menu.page - 1) % max(1, bg_menu._max_pages)
                        bg_menu.relayout(bg_values, bg_thumbs)
                        continue
                    if bg_menu.next_btn.hit(pos):
                        bg_menu.page = (bg_menu.page + 1) % max(1, bg_menu._max_pages)
                        bg_menu.relayout(bg_values, bg_thumbs)
                        continue

                    for it in bg_menu.items:
                        if it.hit(pos):
                            v = it.value
                            if v.startswith("theme:"):
                                name = v.split(":", 1)[1]
                                # find theme index by name (fallback: 0)
                                idx = 0
                                for i, t in enumerate(cfg.BG_THEMES or []):
                                    if str(t.get("name", "")) == name:
                                        idx = i
                                        break
                                g.bg_mode = "theme"
                                g.bg_index = idx
                                set_line(g, now, f"背景：{name}", (1.0, 2.0))
                            elif v.startswith("img:"):
                                bid = v.split(":", 1)[1]
                                g.bg_mode = "image"
                                g.bg_image_id = bid
                                set_line(g, now, f"背景：{bid}", (1.0, 2.0))
                            play_sfx("talk")
                            save(g)
                            bg_menu.close()
                            break

                if snack_menu.open:
                    if snack_menu.close_btn.hit(pos):
                        snack_menu.close()
                        continue
                    if snack_menu.prev_btn.hit(pos):
                        snack_menu.page = (snack_menu.page - 1) % max(1, snack_menu._max_pages)
                        snack_menu.relayout([s.id for s in snacks.items], snacks.icons)
                        continue
                    if snack_menu.next_btn.hit(pos):
                        snack_menu.page = (snack_menu.page + 1) % max(1, snack_menu._max_pages)
                        snack_menu.relayout([s.id for s in snacks.items], snacks.icons)
                        continue

                    # pick snack
                    for it in snack_menu.items:
                        if it.hit(pos):
                            sn = snacks.get(it.value)
                            if sn:
                                action_snack(g, sn)
                                g.last_snack_id = sn.id
                                g.last_snack_at = now
                                g.snack_count = getattr(g, "snack_count", 0) + 1
                                tag = getattr(sn, "react_tag", "react_snack") or "react_snack"
                                line = dlg.pick(tag) or dlg.pick("react_snack") or "おやつ！"
                                set_line(g, now, line, (1.4, 3.0))
                                play_sfx("talk")
                                save(g)
                            snack_menu.close()
                            break
                    continue


                if talk.btn_talk.hit(pos):
                    talk.toggle()
                    if talk.open:
                        talk.relayout(cats, entries)
                    continue

                if talk.open:
                    if talk.close_btn.hit(pos):
                        talk.close()
                        continue

                    # tabs
                    for i, tab in enumerate(talk.tabs):
                        if tab.hit(pos) and i < len(cats):
                            talk.set_category(cats[i][0])
                            talk.relayout(cats, entries)
                            break

                    # paging
                    if talk.prev_btn.hit(pos):
                        talk.page_prev()
                        talk.relayout(cats, entries)
                        continue
                    if talk.next_btn.hit(pos):
                        talk.page_next()
                        talk.relayout(cats, entries)
                        continue

                    # YES/NO
                    if g.awaiting_choice:
                        if talk.btn_yes.hit(pos):
                            answer(True)
                            save(g)
                            continue
                        if talk.btn_no.hit(pos):
                            answer(False)
                            save(g)
                            continue

                    # topics
                    for i, b in enumerate(talk.topic_buttons):
                        if b.hit(pos):
                            if i < len(talk.topic_ids):
                                tid = talk.topic_ids[i]
                                locked = talk.topic_locked[i] if i < len(talk.topic_locked) else True
                                if locked:
                                    t = topics.get(tid)
                                    hint = describe_unlock(t.unlock) if t else "条件を満たしたら、話せる。"
                                    set_line(g, now, hint, (2.0, 4.0))
                                    play_sfx("talk")
                                    talk.close()  # ★ A: 押したら閉じる
                                else:
                                    start_topic(tid)
                                    play_sfx("talk")
                                    talk.close()  # ★ A: 押したら閉じる
                                    save(g)
                            continue

                # キャラをクリック
                char_rect = pygame.Rect(cfg.RIGHT_X, 92 - 44, cfg.RIGHT_PANEL_W, 88)
                if char_rect.collidepoint(pos):
                    text = dlg.pick("tap") or "なになに？"
                    say_with_expression(text, (2.0, 4.0), "smile")
                    play_sfx("talk")

                    dlg.schedule_next_chatter(now)
                    continue

                # 行動ボタン
                _stop_walking(g, now)

                if btn_snack.hit(pos):
                    play_sfx("snack")
                    snack_menu.toggle()
                    snacks.load_if_needed()
                    snack_menu.relayout([s.id for s in snacks.items], snacks.icons)
                    continue
                elif btn_pet.hit(pos):
                    play_sfx("pet")
                    action_pet(g)
                    set_line(g, now, dlg.pick("react_pet") or "……！", (1.5, 3.0))
                    play_sfx("talk")
                elif btn_light.hit(pos):
                    was = g.lights_off
                    action_toggle_lights(g)
                    play_sfx("off" if not was else "on")
                    tag = "react_lights_off" if not was else "react_lights_on"
                    set_line(g, now, dlg.pick(tag) or "……", (1.5, 3.0))
                    play_sfx("talk")

            elif e.type == pygame.MOUSEWHEEL:
                if journal_open:
                    journal_scroll = max(0, journal_scroll - e.y)

            elif e.type == pygame.KEYDOWN:

                # ---- multiline bubble: SPACE/ENTER to advance page ----
                try:
                    pages = int(getattr(g, "_bubble_pages", 0))
                    if pages > 1 and e.key in (pygame.K_SPACE, pygame.K_RETURN):
                        pi = int(getattr(g, "line_page", 0))
                        if pi < pages - 1:
                            g.line_page = pi + 1
                            g.line_until = max(float(getattr(g, "line_until", 0.0)), now + 30.0)
                        else:
                            g.line_until = min(float(getattr(g, "line_until", now + 0.1)), now + 0.1)
                        continue
                except Exception:
                    pass
                if e.key == pygame.K_ESCAPE:
                    # まずは開いているパネルを閉じる。何も開いていなければ終了。
                    if ctx_open:
                        ctx_open = False
                    elif _should_quit_on_escape(gear, talk, journal_open):
                        request_quit(now)
                        running = False
                    else:
                        gear.close()
                        talk.close()
                        journal_open = False

                if e.key == pygame.K_F1:
                    debug_hud = not debug_hud
                    set_line(g, now, "デバッグ表示 ON" if debug_hud else "デバッグ表示 OFF", (0.8, 1.4))
                    continue

                if e.key == pygame.K_b:
                    cycle_bg(g, +1)
                    set_line(g, now, "背景チェンジ。", (1.2, 2.0))
                    play_sfx("talk")
                    save(g)

        # シミュレーション
        step_sim(g, now, dt)
        # sleep state machine (yawn / sleep / wake transitions)
        step_sleep_system(g, dlg, now)
        if now >= g.state_until:
            pick_idle_state(g, dlg, now)

        # ---- debug: manual X move (F1) ----
        # While the debug HUD is on, allow manual left/right movement for quick wall/flip testing.
        manual_dir = 0
        if debug_hud:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT]:
                manual_dir = -1
            elif keys[pygame.K_RIGHT]:
                manual_dir = 1
            else:
                # click inside the character frame to push her left/right
                if pygame.mouse.get_pressed(num_buttons=3)[0]:
                    mx, my = pygame.mouse.get_pos()
                    frame_top = 60
                    frame_bottom = cfg.H - 64
                    frame_h = max(110, frame_bottom - frame_top)
                    frame_rect = pygame.Rect(cfg.RIGHT_X, frame_top, cfg.RIGHT_PANEL_W, frame_h)
                    if frame_rect.collidepoint((mx, my)):
                        manual_dir = -1 if mx < frame_rect.centerx else 1

        if manual_dir != 0:
            # Override movement AFTER the sim step so it cannot be immediately overwritten.
            if not hasattr(g, "x_offset"):
                g.x_offset = 0.0
            speed = float(getattr(cfg, "WALK_SPEED_PX_PER_SEC", 22.0))
            g.vx_px_per_sec = manual_dir * speed
            g.x_offset = float(getattr(g, "x_offset", 0.0)) + g.vx_px_per_sec * dt

            # Clamp within the right panel bounds.
            margin = int(getattr(cfg, "WALK_MARGIN_PX", 10))
            max_off = max(0, (cfg.RIGHT_PANEL_W // 2) - margin)
            if g.x_offset < -max_off:
                g.x_offset = -max_off
            if g.x_offset > max_off:
                g.x_offset = max_off
        elif debug_hud:
            # If manual input is not active, do not interfere with auto-walk.
            # But if auto-walk is not currently running, ensure vx doesn't stay non-zero.
            if hasattr(g, "walk_until") and now >= float(getattr(g, "walk_until", now)):
                if abs(float(getattr(g, "vx_px_per_sec", 0.0))) > 0.01:
                    g.vx_px_per_sec = 0.0

        # ---- blink / mouth (dialogue animation) ----


        # ---- 瞬き（放置でも動く）----
        # No blinking while actually sleeping.
        if getattr(g, "sleep_stage", "awake") != "sleep":
            if now >= g.next_blink and g.blink_until <= now:
                g.blink_until = now + 0.12
                g.next_blink = now + random.uniform(3.0, 6.0)
        else:
            g.blink_until = 0.0

        # ---- 口パク（セリフ表示中だけ）----
        if now < g.line_until:
            if now >= g.mouth_until:
                g.mouth_open = not g.mouth_open
                g.mouth_until = now + 0.18
        else:
            g.mouth_open = False

        # clear line when finished (silent means truly silent)
        if now >= g.line_until and getattr(g, "line", ""):
            g.line = ""
            g.line_until = now
            # after a line ends, schedule the next idle decision
            if not hasattr(g, "idle_next_at"):
                g.idle_next_at = now
            g.idle_next_at = now + random.uniform(cfg.IDLE_SILENT_AFTER_LINE_MIN_SEC, cfg.IDLE_SILENT_AFTER_LINE_MAX_SEC)

        # ---- UI layout (open menus are updated every frame) ----
        gear.update_labels(g)
        gear.relayout()
        if talk.open:
            talk.relayout(cats, entries)
        if wardrobe.open:
            wardrobe.relayout(outfits, sprites)
        if bg_menu.open:
            bg_menu.relayout(bg_values, bg_thumbs)
        if snack_menu.open:
            snacks.load_if_needed()
            snack_menu.relayout([s.id for s in snacks.items], snacks.icons)
        
        # セリフが終わったら通常表情に戻す
        if now >= g.line_until:
            if g.expression == "smile":
                g.expression = "normal"


        # 自発おしゃべり（邪魔しない）
                # ---- idle beat scheduler (after each line, decide next action) ----
        if (not talk.open) and (not journal_open) and (not g.awaiting_choice):
            walking = abs(float(getattr(g, "vx_px_per_sec", 0.0))) > 0.1
            if not hasattr(g, "idle_next_at"):
                g.idle_next_at = now + 2.0

            # If we're not currently showing a line, and it's time to act, decide the next behavior.
            if (not walking) and (not getattr(g, "line", "")) and now >= float(getattr(g, "idle_next_at", now)):
                sleep_stage = getattr(g, "sleep_stage", "awake")

                # --- Sleeping behavior ---
                if sleep_stage == "sleep" or getattr(g, "state", "") == "sleep":
                    # While sleeping, pick among: wake (prob depends on lights), silent (most of the time),
                    # and occasional sleep talk (mumbling).
                    lights_off = bool(getattr(g, "lights_off", False))
                    p_wake = float(cfg.WAKE_CHANCE_DARK_WHILE_SLEEPING if lights_off else cfg.WAKE_CHANCE_BRIGHT_WHILE_SLEEPING)
                    p_talk = float(cfg.SLEEP_TALK_CHANCE_DARK if lights_off else cfg.SLEEP_TALK_CHANCE_BRIGHT)

                    r = random.random()
                    started = False
                    if r < p_wake:
                        started = maybe_start_wake_up(g, dlg, now)
                        if started:
                            play_sfx("talk")
                    elif r < (p_wake + p_talk):
                        started = maybe_start_sleep_talk(g, dlg, now)
                        # (no sfx by default; sleep talk is subtle)

                    # schedule next check (sleeping is calmer, slower)
                    g.idle_next_at = now + random.uniform(float(cfg.SLEEP_SILENT_BEAT_MIN_SEC), float(cfg.SLEEP_SILENT_BEAT_MAX_SEC))
                    continue

# --- Drowsy transition ---
                if sleep_stage == "drowsy":
                    # Transitions are handled in step_sleep_system.
                    g.idle_next_at = now + random.uniform(0.8, 1.4)
                    continue

                # --- Awake behavior ---
                # In the dark, she can still talk / blink / wander, but she is likely to fall asleep.
                if getattr(g, "lights_off", False):
                    ready = now >= float(getattr(g, "sleep_ready_at", 0.0))
                    p_sleep = float(cfg.SLEEP_CHANCE_DARK_READY if ready else cfg.SLEEP_CHANCE_DARK_PRE_READY)
                    if random.random() < p_sleep:
                        if maybe_start_pre_sleep(g, dlg, now):
                            play_sfx("talk")
                        # Next decision will be scheduled when the line ends.
                        continue

                # Otherwise: choose between walking and talking.
                if random.random() < float(cfg.IDLE_DECIDE_WALK_CHANCE):
                    _start_walking(g, now)
                else:
                    txt = dlg.pick(g.state) or "……"
                    _set_line_auto(g, now, txt)
                    play_sfx("talk")
                # next decision will be scheduled when the line finishes (or by step_move rest)
        if now - last_save > 5:
            save(g)
            last_save = now


        # wardrobe outfits list (auto from loaded sprites)
        outfits = sorted({k[len("clothes_"):] for k in sprites.keys() if k.startswith("clothes_")})
        # relayout is handled above when wardrobe.open is True
        btns = [btn_snack, btn_pet, btn_light, talk.btn_talk, btn_char, *gear.all_buttons_for_draw()]
        # wardrobe buttons are drawn inside draw_frame, but keep hover calc independent
        debug_lines = None
        if debug_hud:
            debug_lines = [
                f"dt:{dt:.3f}  fps:{(1.0/dt):.1f}" if dt > 0 else "dt:0",
                f"state:{getattr(g,'state','')} expr:{getattr(g,'expression','')} lights:{'OFF' if getattr(g,'lights_off',False) else 'ON'}",
                f"outfit:{getattr(g,'outfit','')}  bg:{getattr(g,'bg_index',0)}",
                f"talk_open:{getattr(talk,'open',False)} page:{getattr(talk,'page',0)} cat:{getattr(talk,'active_cat','')}",
                f"gear_open:{getattr(gear,'open',False)}  wardrobe_open:{getattr(wardrobe,'open',False)} page:{getattr(wardrobe,'page',0)}",
                f"snack_open:{getattr(snack_menu,'open',False)} page:{getattr(snack_menu,'page',0)} items:{len(getattr(snack_menu,'items',[]))}",
                f"x_off:{getattr(g,'x_offset',0):.1f} vx:{getattr(g,'vx_px_per_sec',0):.1f}" if hasattr(g,'x_offset') or hasattr(g,'vx_px_per_sec') else None,
            ]

        # decide current background
        bg_image = None
        bg_label = None
        if getattr(g, "bg_mode", "theme") == "image":
            bid = getattr(g, "bg_image_id", "") or ""
            if bid and bid in bg_images:
                bg_image = bg_images[bid]
                bg_label = bid
        if bg_label is None:
            bg_label = (cfg.BG_THEMES[getattr(g, "bg_index", 0) % len(cfg.BG_THEMES)].get("name", "bg")
                        if cfg.BG_THEMES else "bg")

        draw_frame(
            screen, font, font_small, sprites, g, btns, pygame.mouse.get_pos(),
            bg_image=bg_image, bg_label=bg_label,
            gear=gear, talk=talk, wardrobe=wardrobe, bg_menu=bg_menu, snack_menu=snack_menu, journal_open=journal_open, journal_scroll=journal_scroll,
            clothes_offsets=clothes_offsets,
            debug_lines=debug_lines
        )

        # 右クリックメニュー描画
        if ctx_open:
            mx, my = pygame.mouse.get_pos()
            # panel
            if ctx_buttons:
                panel = ctx_buttons[0].rect.unionall([b.rect for b in ctx_buttons])
                panel = panel.inflate(12, 12)
                pygame.draw.rect(screen, (40, 40, 48), panel, border_radius=10)
                pygame.draw.rect(screen, (120, 120, 140), panel, 2, border_radius=10)
                for b in ctx_buttons:
                    b.draw(screen, font_small, hover=b.hit((mx, my)))
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()