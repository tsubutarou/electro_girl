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

def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def cycle_bg(g: Girl, step: int = 1):
    n = max(1, len(cfg.BG_THEMES))
    g.bg_index = (g.bg_index + step) % n


class GearMenu:
    def __init__(self):
        self.btn_gear = Button((cfg.W - 34, 8, 26, 22), "⚙")
        self.open = False

        self.item_bg = Button((0, 0, 0, 0), "BG ▶")
        self.item_frame = Button((0, 0, 0, 0), "FRAME:ON")
        self.item_dock = Button((0, 0, 0, 0), "DOCK:ON")
        self.item_mute = Button((0, 0, 0, 0), "SFX:ON")
        self.item_up = Button((0, 0, 0, 0), "VOL +")
        self.item_down = Button((0, 0, 0, 0), "VOL -")
        self.item_log = Button((0, 0, 0, 0), "LOG")
        self.item_outfit = Button((0, 0, 0, 0), "OUT:normal")

        self.items = [self.item_bg, self.item_frame, self.item_dock, self.item_mute, self.item_up, self.item_down, self.item_outfit, self.item_log]
        self.panel = pygame.Rect(0, 0, 0, 0)
        self.relayout()

    def relayout(self):
        w, h = 96, 22
        x = cfg.W - w - 8
        y0 = self.btn_gear.rect.bottom + 6
        for i, b in enumerate(self.items):
            b.rect = pygame.Rect(x, y0 + i * (h + 6), w, h)

        if self.items:
            top = self.items[0].rect.top - 6
            bottom = self.items[-1].rect.bottom + 6
            self.panel = pygame.Rect(x - 6, top, w + 12, bottom - top)

            # If menu goes off-screen (small window height), shift it upward.
            overflow = self.panel.bottom - (cfg.H - 8)
            if overflow > 0:
                for b in self.items:
                    b.rect.y -= overflow
                self.panel.y -= overflow

            # Keep a small top margin too
            underflow = 8 - self.panel.top
            if underflow > 0:
                for b in self.items:
                    b.rect.y += underflow
                self.panel.y += underflow

    def update_labels(self, g: Girl):
        self.item_frame.label = "FRAME:OFF" if getattr(g, "borderless", False) else "FRAME:ON"
        self.item_dock.label = "DOCK:ON" if getattr(g, "dock_bottom_right", True) else "DOCK:OFF"
        self.item_mute.label = "SFX:OFF" if g.sfx_muted else "SFX:ON"
        self.item_outfit.label = f"OUT:{getattr(g, 'outfit', 'normal')}"
        vol = int(round(clamp01(g.sfx_scale) * 100))
        self.item_up.label = f"VOL {vol}% +"
        self.item_down.label = f"VOL {vol}% -"

    def toggle(self):
        self.open = not self.open

    def close(self):
        self.open = False

    def hit_any(self, pos) -> bool:
        if self.btn_gear.hit(pos):
            return True
        if self.open and self.panel.collidepoint(pos):
            return True
        return False

    def all_buttons_for_draw(self):
        return [self.btn_gear, *self.items] if self.open else [self.btn_gear]


class TalkMenu:
    def __init__(self):
        self.btn_talk = Button((cfg.W - 64, cfg.H - 44, 56, 32), "TALK")
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
    btn_snack = Button((cfg.LEFT_X, cfg.H - 44, 80, 32), "SNACK")
    btn_pet = Button((cfg.LEFT_X + 86, cfg.H - 44, 80, 32), "PET")
    btn_light = Button((cfg.LEFT_X + 172, cfg.H - 44, 80, 32), "LIGHTS")

    gear = GearMenu()
    talk = TalkMenu()
    return btn_snack, btn_pet, btn_light, gear, talk
