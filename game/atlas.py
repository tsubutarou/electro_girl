"""atlas.py
Atlas utilities (v0.1)

- Load atlas.png + atlas_map.json
- Slice into per-slot pygame.Surface
"""
from __future__ import annotations

import json
import os
import pygame

from .image_utils import load_image


def load_atlas_sprites(assets_root: str) -> dict[str, pygame.Surface]:
    """Load sprites from assets/sprite/atlas.png + atlas_map.json.

    Returns: slot_name -> Surface (tile_size).
    """
    atlas_png = os.path.join(assets_root, "sprite", "atlas.png")
    atlas_map = os.path.join(assets_root, "sprite", "atlas_map.json")
    if not (os.path.exists(atlas_png) and os.path.exists(atlas_map)):
        return {}

    try:
        with open(atlas_map, "r", encoding="utf-8") as f:
            m = json.load(f)
        tile_w, tile_h = m.get("tile_size", [64, 64])
        slots = m.get("slots", {})
        atlas = load_image(atlas_png)
    except Exception:
        return {}

    out: dict[str, pygame.Surface] = {}
    for name, pos in slots.items():
        try:
            col = int(pos.get("col"))
            row = int(pos.get("row"))
            rect = pygame.Rect(col * tile_w, row * tile_h, tile_w, tile_h)
            surf = pygame.Surface((tile_w, tile_h), pygame.SRCALPHA)
            surf.blit(atlas, (0, 0), rect)
            out[name] = surf
        except Exception:
            continue
    return out
