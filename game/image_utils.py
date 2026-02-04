"""image_utils.py
Small, dependency-light image helpers to avoid circular imports.
"""
from __future__ import annotations

import os
import pygame


def load_image(path: str) -> pygame.Surface:
    """Load an image with alpha. Raises if pygame can't load it."""
    return pygame.image.load(path).convert_alpha()


def safe_load_image(path: str, fallback_size: tuple[int,int]=(64,64)) -> pygame.Surface:
    """Load image if exists, otherwise return transparent placeholder."""
    if not os.path.exists(path):
        return pygame.Surface(fallback_size, pygame.SRCALPHA)
    try:
        return load_image(path)
    except Exception:
        return pygame.Surface(fallback_size, pygame.SRCALPHA)


def scale_nearest(surf: pygame.Surface, scale: int) -> pygame.Surface:
    """Integer scaling with nearest-neighbor (pixel art friendly)."""
    if scale == 1:
        return surf
    return pygame.transform.scale(surf, (surf.get_width()*scale, surf.get_height()*scale))
