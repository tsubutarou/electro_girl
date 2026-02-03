from __future__ import annotations
import json
import os
import random
import time
from collections import deque

from .model import Girl, clamp


class Dialogue:
    # assets/dialogue/lines.json を読み込み、タグで台詞を引く。ホットリロード対応。
    def __init__(self, path: str):
        self.path = path
        self.mtime = 0.0
        self.lines = []
        self.by_tag: dict[str, list[dict]] = {}
        self.interval = (6.0, 13.0)
        self.chance = 1.0
        self.recent_ids = deque(maxlen=10)
        self.next_chatter_at = time.time() + random.uniform(*self.interval)
        self.load_if_needed(force=True)

    def load_if_needed(self, force: bool = False):
        try:
            m = os.path.getmtime(self.path)
        except Exception:
            return
        if (not force) and m <= self.mtime:
            return

        self.mtime = m
        with open(self.path, "r", encoding="utf-8") as f:
            data = json.load(f)

        chatter = data.get("chatter", {})
        itv = chatter.get("interval_sec", [6.0, 13.0])
        self.interval = (float(itv[0]), float(itv[1]))
        self.chance = float(chatter.get("chance_per_tick", 1.0))

        self.lines = data.get("lines", [])
        self.by_tag = {}
        for ln in self.lines:
            for tag in ln.get("tags", []):
                self.by_tag.setdefault(tag, []).append(ln)

        self.next_chatter_at = time.time() + random.uniform(*self.interval)

    def pick(self, tag: str) -> str | None:
        pool = self.by_tag.get(tag, [])
        if not pool:
            return None
        candidates = [x for x in pool if x.get("id") not in self.recent_ids]
        choice = random.choice(candidates) if candidates else random.choice(pool)
        self.recent_ids.append(choice.get("id"))
        return choice.get("text", "……")

    def schedule_next_chatter(self, now: float):
        self.next_chatter_at = now + random.uniform(*self.interval)

    def should_chatter(self, now: float) -> bool:
        return now >= self.next_chatter_at and (random.random() <= self.chance)


def set_line(g: Girl, now: float, text: str, t=(2.5, 5.0)):
    g.line = text
    g.line_until = now + random.uniform(*t)


def greet_on_start(g: Girl, dlg: Dialogue, now: float):
    if g.last_seen > 0:
        dt = now - g.last_seen
        if dt >= 3 * 60 * 60:
            text = dlg.pick("greet_long") or "ひさしぶり。"
            g.mood = clamp(g.mood - 4)
        else:
            text = dlg.pick("greet_short") or "おかえり。"
        set_line(g, now, text, (3.0, 6.0))
    else:
        set_line(g, now, "…はじめまして", (4.0, 6.0))
