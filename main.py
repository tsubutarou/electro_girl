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
from game.assets import load_sprites, load_sounds
from game.sim import (
    step_sim,
    pick_idle_state,
    action_snack,
    action_pet,
    action_toggle_lights,
)
from game.ui import make_buttons, cycle_bg, clamp01, Button, WardrobeMenu
from game.render import draw_frame
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
    sprites = load_sprites(scale=3)
    sounds = load_sounds(mixer_ok)

    dlg = Dialogue(cfg.DLG_PATH)
    topics = Topics(cfg.TOPICS_PATH)

    g = load_or_new()
    # 表情の初期値
    g.expression = getattr(g, "expression", "normal")
    g.dock_bottom_right = getattr(g, "dock_bottom_right", True)

    now = time.time()
    if not g.first_seen:
        g.first_seen = now
        save(g)

    pick_idle_state(g, dlg, now)
    greet_on_start(g, dlg, now)

    btn_snack, btn_pet, btn_light, gear, talk = make_buttons()
    wardrobe = WardrobeMenu()

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
            btns = [btn_snack, btn_pet, btn_light, talk.btn_talk, *gear.all_buttons_for_draw()]
            draw_frame(
                screen, font, font_small, sprites, g, btns, pygame.mouse.get_pos(),
                gear=gear, talk=talk, wardrobe=wardrobe, journal_open=journal_open, journal_scroll=journal_scroll
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

        # ---- 瞬き（放置でも動く）----
        if now >= g.next_blink and g.blink_until <= now:
            g.blink_until = now + 0.12
            g.next_blink = now + random.uniform(3.0, 6.0)

        # ---- 口パク（セリフ表示中だけ）----
        if now < g.line_until:
            if now >= g.mouth_until:
                g.mouth_open = not g.mouth_open
                g.mouth_until = now + 0.18
        else:
            g.mouth_open = False

        dlg.load_if_needed()
        topics.load_if_needed()
        gear.update_labels(g)

        refresh_unlocks()

        cats, entries = build_category_view()
        talk.relayout(cats, entries)

        for e in pygame.event.get():

            # Ctrl + Left Drag: move the window (useful for NOFRAME).
            if (
                e.type == pygame.MOUSEBUTTONDOWN
                and e.button == 1
                and (pygame.key.get_mods() & pygame.KMOD_CTRL)
            ):
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

                if gear.btn_gear.hit(pos):
                    gear.toggle()
                    continue

                if gear.open:
                    if gear.item_bg.hit(pos):
                        cycle_bg(g, +1)
                        set_line(g, now, "背景チェンジ。", (1.2, 2.0))
                        play_sfx("talk")
                        save(g)
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
                        continue
                    if wardrobe.next_btn.hit(pos):
                        wardrobe.page = (wardrobe.page + 1) % max(1, wardrobe._max_pages)
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
                    continue

                if talk.btn_talk.hit(pos):
                    talk.toggle()
                    continue

                if talk.open:
                    if talk.close_btn.hit(pos):
                        talk.close()
                        continue

                    # tabs
                    for i, tab in enumerate(talk.tabs):
                        if tab.hit(pos) and i < len(cats):
                            talk.set_category(cats[i][0])
                            break

                    # paging
                    if talk.prev_btn.hit(pos):
                        talk.page_prev()
                        continue
                    if talk.next_btn.hit(pos):
                        talk.page_next()
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
                if btn_snack.hit(pos):
                    play_sfx("snack")
                    action_snack(g)
                    set_line(g, now, dlg.pick("react_snack") or "おやつ！", (1.5, 3.0))
                    play_sfx("talk")
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

                if e.key == pygame.K_b:
                    cycle_bg(g, +1)
                    set_line(g, now, "背景チェンジ。", (1.2, 2.0))
                    play_sfx("talk")
                    save(g)

        # シミュレーション
        step_sim(g, now, dt)
        if now >= g.state_until:
            pick_idle_state(g, dlg, now)
        
        # セリフが終わったら通常表情に戻す
        if now >= g.line_until:
            if g.expression == "smile":
                g.expression = "normal"


        # 自発おしゃべり（邪魔しない）
        if (not talk.open) and (not journal_open) and (not g.awaiting_choice):
            if dlg.should_chatter(now) and now >= g.line_until:
                set_line(g, now, dlg.pick(g.state) or "……", (2.0, 4.0))
                play_sfx("talk")
                dlg.schedule_next_chatter(now)

        if now - last_save > 5:
            save(g)
            last_save = now


        # wardrobe outfits list (auto from loaded sprites)
        outfits = sorted({k[len("clothes_"):] for k in sprites.keys() if k.startswith("clothes_")})
        wardrobe.relayout(outfits, sprites)

        btns = [btn_snack, btn_pet, btn_light, talk.btn_talk, *gear.all_buttons_for_draw()]
            # wardrobe buttons are drawn inside draw_frame, but keep hover calc independent
        draw_frame(
            screen, font, font_small, sprites, g, btns, pygame.mouse.get_pos(),
            gear=gear, talk=talk, wardrobe=wardrobe, journal_open=journal_open, journal_scroll=journal_scroll
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
