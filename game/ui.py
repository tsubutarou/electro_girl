from __future__ import annotations
import pygame

from .model import Girl
from . import config as cfg


class Button:
    def __init__(self, rect, label):
        self.rect = pygame.Rect(rect)
        self.label = label

    def draw(self, screen, font, hover: bool = False):
        bg = (75, 75, 90) if hover else (60, 60, 70)
        pygame.draw.rect(screen, bg, self.rect, border_radius=8)
        pygame.draw.rect(screen, (120, 120, 140), self.rect, 2, border_radius=8)
        t = font.render(self.label, True, (235, 235, 245))
        screen.blit(t, t.get_rect(center=self.rect.center))

    def draw_disabled(self, screen, font):
        pygame.draw.rect(screen, (48, 48, 58), self.rect, border_radius=8)
        pygame.draw.rect(screen, (90, 90, 105), self.rect, 2, border_radius=8)
        t = font.render(self.label, True, (175, 175, 190))
        screen.blit(t, t.get_rect(center=self.rect.center))

    def hit(self, pos):
        return self.rect.collidepoint(pos)



class ThumbButton(Button):
    def __init__(self, rect, label, value, thumb: pygame.Surface | None):
        super().__init__(rect, label)
        self.value = value
        self.thumb = thumb

    def draw(self, screen, font, hover: bool = False, selected: bool = False):
        bg = (85, 85, 105) if selected else ((75, 75, 90) if hover else (60, 60, 70))
        pygame.draw.rect(screen, bg, self.rect, border_radius=10)
        pygame.draw.rect(screen, (130, 130, 155), self.rect, 2, border_radius=10)

        # thumb
        if self.thumb:
            tr = self.thumb.get_rect(center=(self.rect.centerx, self.rect.centery - 6))
            screen.blit(self.thumb, tr)

        # label
        t = font.render(self.label, True, (235, 235, 245))
        screen.blit(t, t.get_rect(center=(self.rect.centerx, self.rect.bottom - 12)))


class WardrobeMenu:
    def __init__(self):
        self.open = False
        self.panel = pygame.Rect(0, 0, 0, 0)
        self.close_btn = Button((0, 0, 0, 0), "X")
        self.prev_btn = Button((0, 0, 0, 0), "<")
        self.next_btn = Button((0, 0, 0, 0), ">")
        self.page = 0
        self.cols = 4
        self.rows = 1
        self.items: list[ThumbButton] = []
        self.outfit_ids: list[str] = []
        self._max_pages = 1
        self.relayout([], {})

    def toggle(self):
        self.open = not self.open

    def close(self):
        self.open = False

    def relayout(self, outfit_ids: list[str], sprites: dict):
        w = cfg.W - 16
        h = 120
        x = 8
        y = 52
        self.panel = pygame.Rect(x, y, w, h)
        self.close_btn.rect = pygame.Rect(self.panel.right - 26, self.panel.top + 8, 20, 18)
        self.prev_btn.rect = pygame.Rect(self.panel.right - 56, self.panel.top + 32, 22, 18)
        self.next_btn.rect = pygame.Rect(self.panel.right - 30, self.panel.top + 32, 22, 18)

        ids = list(outfit_ids) if outfit_ids else ["normal"]
        ids = [i for i in ids if isinstance(i, str) and i]
        if "normal" not in ids:
            ids.insert(0, "normal")
        self.outfit_ids = ids

        page_size = self.cols * self.rows
        self._max_pages = max(1, (len(ids) + page_size - 1) // page_size)
        self.page = max(0, min(self.page, self._max_pages - 1))

        start = self.page * page_size
        page_ids = ids[start:start + page_size]

        pad_x = 12
        pad_y = 46
        cell_w = 64
        cell_h = 64
        gap_x = 8

        self.items = []
        for idx, oid in enumerate(page_ids):
            col = idx % self.cols
            rx = self.panel.left + pad_x + col * (cell_w + gap_x)
            ry = self.panel.top + pad_y
            rect = pygame.Rect(rx, ry, cell_w, cell_h)

            thumb = None
            surf = sprites.get(f"clothes_{oid}")
            if surf:
                tw, th = 40, 40
                w0, h0 = surf.get_size()
                if w0 > 0 and h0 > 0:
                    s = min(tw / w0, th / h0)
                    nw = max(1, int(w0 * s))
                    nh = max(1, int(h0 * s))
                    thumb = pygame.transform.smoothscale(surf, (nw, nh))

            self.items.append(ThumbButton(rect, oid, oid, thumb))

    def hit_any(self, pos) -> bool:
        if not self.open:
            return False
        if self.panel.collidepoint(pos):
            return True
        return False


class BackgroundMenu:
    """背景選択（画像 + 単色テーマ）"""
    def __init__(self):
        self.open = False
        self.panel = pygame.Rect(0, 0, 0, 0)
        self.close_btn = Button((0, 0, 0, 0), "X")
        self.prev_btn = Button((0, 0, 0, 0), "<")
        self.next_btn = Button((0, 0, 0, 0), ">")
        self.page = 0
        self.cols = 4
        self.rows = 1
        self.items: list[ThumbButton] = []
        self.values: list[str] = []  # "theme:<name>" or "img:<id>"
        self._max_pages = 1
        self.relayout([], {})

    def toggle(self):
        self.open = not self.open

    def close(self):
        self.open = False

    def relayout(self, values: list[str], thumbs: dict[str, pygame.Surface]):
        # left side panel (avoid right panel)
        w = cfg.RIGHT_X - 16
        h = 120
        x = 8
        y = 52
        self.panel = pygame.Rect(x, y, max(160, w), h)

        self.close_btn.rect = pygame.Rect(self.panel.right - 26, self.panel.top + 8, 20, 18)
        self.prev_btn.rect = pygame.Rect(self.panel.right - 56, self.panel.top + 32, 22, 18)
        self.next_btn.rect = pygame.Rect(self.panel.right - 30, self.panel.top + 32, 22, 18)

        vals = list(values) if values else []
        vals = [v for v in vals if isinstance(v, str) and v]
        self.values = vals

        page_size = self.cols * self.rows
        self._max_pages = max(1, (len(vals) + page_size - 1) // page_size)
        self.page = max(0, min(self.page, self._max_pages - 1))

        start = self.page * page_size
        page_vals = vals[start:start + page_size]

        pad_x = 12
        pad_y = 46
        cell_w = 64
        cell_h = 64
        gap_x = 8

        self.items = []
        for idx, v in enumerate(page_vals):
            col = idx % self.cols
            rx = self.panel.left + pad_x + col * (cell_w + gap_x)
            ry = self.panel.top + pad_y
            rect = pygame.Rect(rx, ry, cell_w, cell_h)

            # label: shorten
            label = v
            if v.startswith("theme:"):
                label = v.split(":", 1)[1]
            elif v.startswith("img:"):
                label = v.split(":", 1)[1]

            thumb = thumbs.get(v)
            self.items.append(ThumbButton(rect, label, v, thumb))

    def hit_any(self, pos) -> bool:
        if not self.open:
            return False
        if self.panel.collidepoint(pos):
            return True
        return False


class SnackMenu:
    def __init__(self):
        self.open = False
        self.panel = pygame.Rect(0, 0, 0, 0)
        self.close_btn = Button((0, 0, 0, 0), "X")
        self.prev_btn = Button((0, 0, 0, 0), "<")
        self.next_btn = Button((0, 0, 0, 0), ">")
        self.page = 0
        self.cols = cfg.SNACK_MENU_COLS
        self.rows = cfg.SNACK_MENU_ROWS
        self.items: list[ThumbButton] = []
        self.snack_ids: list[str] = []
        self._max_pages = 1
        self.relayout([], {})

    def toggle(self):
        self.open = not self.open

    def close(self):
        self.open = False

    def relayout(self, snack_ids: list[str], icons: dict):
        # left side panel (avoid right panel)
        w = cfg.RIGHT_X - 16
        h = 120
        x = 8
        y = 52
        self.panel = pygame.Rect(x, y, max(160, w), h)

        self.close_btn.rect = pygame.Rect(self.panel.right - 26, self.panel.top + 8, 20, 18)
        self.prev_btn.rect = pygame.Rect(self.panel.right - 56, self.panel.top + 32, 22, 18)
        self.next_btn.rect = pygame.Rect(self.panel.right - 30, self.panel.top + 32, 22, 18)

        ids = list(snack_ids) if snack_ids else []
        ids = [i for i in ids if isinstance(i, str) and i]
        self.snack_ids = ids

        page_size = self.cols * self.rows
        self._max_pages = max(1, (len(ids) + page_size - 1) // page_size)
        self.page = max(0, min(self.page, self._max_pages - 1))

        start = self.page * page_size
        page_ids = ids[start:start + page_size]

        pad_x = 12
        pad_y = 46
        cell_w = 64
        cell_h = 64
        gap_x = 8

        self.items = []
        for idx, sid in enumerate(page_ids):
            col = idx % self.cols
            rx = self.panel.left + pad_x + col * (cell_w + gap_x)
            ry = self.panel.top + pad_y
            rect = pygame.Rect(rx, ry, cell_w, cell_h)
            thumb = icons.get(sid)
            # icons may be smaller; center as-is
            self.items.append(ThumbButton(rect, sid, sid, thumb))

    def hit_any(self, pos) -> bool:
        if not self.open:
            return False
        if self.panel.collidepoint(pos):
            return True
        return False

def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def cycle_bg(g: Girl, step: int = 1):
    n = max(1, len(cfg.BG_THEMES))
    g.bg_index = (g.bg_index + step) % n


class GearMenu:
    def __init__(self):
        self.btn_gear = Button((cfg.W - 34, 8, 26, 22), "⚙")
        self.open = False

        # settings items (add more freely; layout/paging won't break)
        self.item_bg = Button((0, 0, 0, 0), "BG ▶")
        self.item_frame = Button((0, 0, 0, 0), "FRAME:ON")
        self.item_dock = Button((0, 0, 0, 0), "DOCK:ON")
        self.item_top = Button((0, 0, 0, 0), "TOP:OFF")
        self.item_mute = Button((0, 0, 0, 0), "SFX:ON")
        self.item_up = Button((0, 0, 0, 0), "VOL +")
        self.item_down = Button((0, 0, 0, 0), "VOL -")
        self.item_log = Button((0, 0, 0, 0), "LOG")
        self.item_outfit = Button((0, 0, 0, 0), "OUT:normal")

        self.items = [
            self.item_bg,
            self.item_frame,
            self.item_dock,
            self.item_top,
            self.item_mute,
            self.item_up,
            self.item_down,
            self.item_outfit,
            self.item_log,
        ]

        # paging (future-proof when items grow)
        self.page = 0
        self._max_pages = 1
        self._cols = 2

        # page nav (only shown when max_pages > 1)
        self.btn_prev = Button((0, 0, 0, 0), "◀")
        self.btn_next = Button((0, 0, 0, 0), "▶")
        self.page_label = Button((0, 0, 0, 0), "1/1")  # non-click; drawn via Button

        self.panel = pygame.Rect(0, 0, 0, 0)
        self.relayout()

    def relayout(self):
        # ---- geometry ----
        w, h = 96, 22
        cols = self._cols
        gap_x = 6
        gap_y = 6

        y0 = self.btn_gear.rect.bottom + 6
        max_h = (cfg.H - 8) - y0
        max_h = max(80, max_h)  # safety for tiny windows

        # header area for paging controls
        header_h = 22

        # how many rows fit (at least 1)
        rows_fit = max(
            1,
            int((max_h - 12 - header_h + gap_y) // (h + gap_y)),
        )
        page_size = rows_fit * cols

        n = len(self.items)
        self._max_pages = max(1, (n + page_size - 1) // page_size)
        self.page = max(0, min(self.page, self._max_pages - 1))

        panel_w = cols * w + (cols - 1) * gap_x + 12
        panel_h = header_h + rows_fit * h + (rows_fit - 1) * gap_y + 12

        x0 = cfg.W - panel_w - 8
        self.panel = pygame.Rect(x0, y0, panel_w, panel_h)

        # keep panel inside window vertically (top/bottom)
        overflow = self.panel.bottom - (cfg.H - 8)
        if overflow > 0:
            self.panel.y -= overflow
        underflow = 8 - self.panel.top
        if underflow > 0:
            self.panel.y += underflow

        # ---- paging controls rects ----
        if self._max_pages > 1:
            self.btn_prev.rect = pygame.Rect(self.panel.right - 68, self.panel.top + 6, 20, 18)
            self.btn_next.rect = pygame.Rect(self.panel.right - 24, self.panel.top + 6, 20, 18)
            self.page_label.rect = pygame.Rect(self.panel.right - 46, self.panel.top + 6, 22, 18)
            self.page_label.label = f"{self.page + 1}/{self._max_pages}"
        else:
            self.btn_prev.rect = pygame.Rect(0, 0, 0, 0)
            self.btn_next.rect = pygame.Rect(0, 0, 0, 0)
            self.page_label.rect = pygame.Rect(0, 0, 0, 0)
            self.page_label.label = "1/1"

        # ---- lay out visible items ----
        start = self.page * page_size
        end = start + page_size

        # anchor for grid
        x = self.panel.left + 6
        y = self.panel.top + 6 + header_h

        for i, b in enumerate(self.items):
            if start <= i < end:
                local = i - start
                col = local % cols
                row = local // cols
                bx = x + col * (w + gap_x)
                by = y + row * (h + gap_y)
                b.rect = pygame.Rect(bx, by, w, h)
            else:
                # hide (prevents phantom clicks)
                b.rect = pygame.Rect(0, 0, 0, 0)

    def update_labels(self, g: Girl):
        self.item_frame.label = "FRAME:OFF" if getattr(g, "borderless", False) else "FRAME:ON"
        self.item_dock.label = "DOCK:ON" if getattr(g, "dock_bottom_right", True) else "DOCK:OFF"
        self.item_top.label = "TOP:ON" if getattr(g, "always_on_top", False) else "TOP:OFF"
        self.item_mute.label = "SFX:OFF" if g.sfx_muted else "SFX:ON"
        self.item_outfit.label = f"OUT:{getattr(g, 'outfit', 'normal')}"
        vol = int(round(clamp01(g.sfx_scale) * 100))
        self.item_up.label = f"VOL {vol}% +"
        self.item_down.label = f"VOL {vol}% -"

    def toggle(self):
        self.open = not self.open
        if self.open:
            self.relayout()

    def close(self):
        self.open = False

    def page_prev(self):
        if self._max_pages <= 1:
            return
        self.page = (self.page - 1) % self._max_pages
        self.relayout()

    def page_next(self):
        if self._max_pages <= 1:
            return
        self.page = (self.page + 1) % self._max_pages
        self.relayout()

    def hit_any(self, pos) -> bool:
        if not self.open:
            return False
        return self.panel.collidepoint(pos)

    def all_buttons_for_draw(self):
        if not self.open:
            return [self.btn_gear]
        btns = [self.btn_gear, *self.items]
        if self._max_pages > 1:
            btns.extend([self.btn_prev, self.page_label, self.btn_next])
        return btns
class TalkMenu:
    def __init__(self):
        # NOTE: ボタン配置は make_buttons() でも上書きされる。
        # ここは「初期値としての安全なデフォルト」。
        self.btn_talk = Button((cfg.LEFT_X + 86 * 3, cfg.H - 44, 56, 32), "TALK")
        self.open = False
        self.panel = pygame.Rect(0, 0, 0, 0)

        self.close_btn = Button((0, 0, 0, 0), "X")

        self.btn_yes = Button((0, 0, 0, 0), "YES")
        self.btn_no = Button((0, 0, 0, 0), "NO")

        self.tabs: list[Button] = []
        self.active_cat: str = "girls"

        self.topic_buttons: list[Button] = []
        self.topic_ids: list[str] = []
        self.topic_locked: list[bool] = []
        self.topic_new: list[bool] = []

        self.prev_btn = Button((0, 0, 0, 0), "<")
        self.next_btn = Button((0, 0, 0, 0), ">")
        self.page = 0
        self.page_size = 6
        self._max_pages = 1
        self._tab_h = 18

    def toggle(self):
        self.open = not self.open

    def close(self):
        self.open = False

    def set_category(self, cat_id: str):
        self.active_cat = cat_id
        self.page = 0

    def relayout(self, categories: list[tuple[str, str]], entries: list[tuple[str, str, bool, bool]]):
        """
        categories: [(id,label), ...]
        entries: [(topic_id, title, locked, is_new), ...] for current category
        """
        w = cfg.W - 16
        h = 136
        x = 8
        y = 36
        self.panel = pygame.Rect(x, y, w, h)
        self.close_btn.rect = pygame.Rect(self.panel.right - 26, self.panel.top + 6, 20, 18)

        # tabs
        self.tabs = []
        tx = self.panel.left + 10
        ty = self.panel.top + 8
        for cid, label in categories[:4]:
            bw = 76
            self.tabs.append(Button((tx, ty, bw, self._tab_h), label))
            tx += bw + 6

        # paging
        self.prev_btn.rect = pygame.Rect(self.panel.right - 56, self.panel.top + 28, 22, 18)
        self.next_btn.rect = pygame.Rect(self.panel.right - 30, self.panel.top + 28, 22, 18)

        self._max_pages = max(1, (len(entries) + self.page_size - 1) // self.page_size)
        self.page = max(0, min(self.page, self._max_pages - 1))

        start = self.page * self.page_size
        page_items = entries[start:start + self.page_size]

        self.topic_buttons = []
        self.topic_ids = []
        self.topic_locked = []
        self.topic_new = []

        bx = self.panel.left + 10
        by = self.panel.top + 52
        bw = self.panel.width - 20
        bh = 18
        gap = 4
        for i, (tid, title, locked, is_new) in enumerate(page_items):
            if locked:
                label = f"[LOCKED] {title}"
            else:
                label = f"✨ {title}" if is_new else title
            self.topic_buttons.append(Button((bx, by + i * (bh + gap), bw, bh), label))
            self.topic_ids.append(tid)
            self.topic_locked.append(bool(locked))
            self.topic_new.append(bool(is_new))

        # YES/NO
        yn_y = self.panel.bottom - 30
        self.btn_yes.rect = pygame.Rect(self.panel.left + 12, yn_y, 70, 22)
        self.btn_no.rect = pygame.Rect(self.panel.left + 12 + 78, yn_y, 70, 22)

    def page_prev(self):
        self.page = (self.page - 1) % self._max_pages

    def page_next(self):
        self.page = (self.page + 1) % self._max_pages

    def hit_any(self, pos) -> bool:
        if self.btn_talk.hit(pos):
            return True
        if self.open and self.panel.collidepoint(pos):
            return True
        return False


def make_buttons():
    # ---- bottom-left: SNACK, PET, LIGHTS, TALK ----
    y_bottom = cfg.H - 44
    gap = 6
    btn_w = 80
    btn_h = 32

    btn_snack = Button((cfg.LEFT_X, y_bottom, btn_w, btn_h), "SNACK")
    btn_pet = Button((cfg.LEFT_X + (btn_w + gap) * 1, y_bottom, btn_w, btn_h), "PET")
    btn_light = Button((cfg.LEFT_X + (btn_w + gap) * 2, y_bottom, btn_w, btn_h), "LIGHTS")

    gear = GearMenu()
    talk = TalkMenu()
    wardrobe = WardrobeMenu()
    bg_menu = BackgroundMenu()
    snack_menu = SnackMenu()

    # move TALK to bottom-left row (after LIGHTS)
    talk.btn_talk.rect = pygame.Rect(cfg.LEFT_X + (btn_w + gap) * 3, y_bottom, 56, btn_h)

    # ---- top-right: CHAR, ⚙(gear) ----
    # right aligned, order: [CHAR][⚙]
    top_y = 8
    gear.btn_gear.rect = pygame.Rect(cfg.W - 34, top_y, 26, 22)
    char_w, char_h = 54, 22
    char_x = gear.btn_gear.rect.left - gap - char_w
    btn_char = Button((char_x, top_y, char_w, char_h), "CHAR")
    # relayout settings panel based on updated gear button rect
    gear.relayout()

    return btn_snack, btn_pet, btn_light, btn_char, gear, talk, wardrobe, bg_menu, snack_menu
