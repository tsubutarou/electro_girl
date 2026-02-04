"""ui_bubble.py
Speech bubble (multiline + paging) helpers.
"""
from __future__ import annotations

import pygame


def wrap_text_to_lines(text: str, font: pygame.font.Font, max_w: int) -> list[str]:
    """Wrap text into multiple lines so each rendered line fits within max_w.

    - Newlines force line breaks.
    - Japanese is wrapped per-character (safe default).
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


def paginate_lines(lines: list[str], max_lines: int) -> list[list[str]]:
    if max_lines <= 0:
        return [lines]
    return [lines[i:i + max_lines] for i in range(0, len(lines), max_lines)]
