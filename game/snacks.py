from __future__ import annotations

import json
import os
from dataclasses import dataclass

import pygame

from . import config as cfg


@dataclass
class Snack:
    id: str
    name: str
    icon: str = ""
    hunger: float = 0.0
    mood: float = 0.0
    affection: int = 0
    react_tag: str = "react_snack"


class Snacks:
    """assets/snacks/snacks.json を読む。軽いホットリロード対応。"""

    def __init__(self, path: str = cfg.SNACKS_PATH):
        self.path = path
        self.mtime = 0.0
        self.items: list[Snack] = []
        self.by_id: dict[str, Snack] = {}
        self.icons: dict[str, pygame.Surface] = {}

    def load_if_needed(self, *, force: bool = False, icon_scale: int = 1):
        try:
            m = os.path.getmtime(self.path)
        except Exception:
            return
        if (not force) and m <= self.mtime:
            return

        self.mtime = m
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

        raw = data.get("snacks", []) if isinstance(data, dict) else []
        items: list[Snack] = []
        by_id: dict[str, Snack] = {}
        for s in raw:
            try:
                sn = Snack(
                    id=str(s.get("id", "")),
                    name=str(s.get("name", "")),
                    icon=str(s.get("icon", "")),
                    hunger=float(s.get("hunger", 0.0)),
                    mood=float(s.get("mood", 0.0)),
                    affection=int(s.get("affection", 0)),
                    react_tag=str(s.get("react_tag", "react_snack")),
                )
            except Exception:
                continue
            if not sn.id or not sn.name:
                continue
            items.append(sn)
            by_id[sn.id] = sn

        self.items = items
        self.by_id = by_id

        # icons
        self.icons = {}
        for sn in self.items:
            if not sn.icon:
                continue
            p = os.path.join(cfg.SNACKS_ICON_DIR, sn.icon)
            if not os.path.exists(p):
                continue
            try:
                img = pygame.image.load(p).convert_alpha()
                if icon_scale != 1:
                    w, h = img.get_size()
                    img = pygame.transform.scale(img, (w * icon_scale, h * icon_scale))
                self.icons[sn.id] = img
            except Exception:
                continue

    def get(self, snack_id: str) -> Snack | None:
        return self.by_id.get(snack_id)
