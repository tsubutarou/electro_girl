from __future__ import annotations
import json
import os
import time
from dataclasses import dataclass
from typing import Any

from .model import Girl


@dataclass
class Category:
    id: str
    label: str


@dataclass
class Topic:
    id: str
    title: str
    category: str
    unlock: dict
    sequence: list[dict]
    tags: list[str]


class Topics:
    def __init__(self, path: str):
        self.path = path
        self.mtime = 0.0
        self.categories: list[Category] = []
        self.topics: list[Topic] = []
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

        cats: list[Category] = []
        for c in data.get("categories", []) or []:
            cid = str(c.get("id", "")).strip()
            lab = str(c.get("label", "")).strip()
            if cid and lab:
                cats.append(Category(cid, lab))
        self.categories = cats

        out: list[Topic] = []
        for t in data.get("topics", []) or []:
            out.append(
                Topic(
                    id=str(t.get("id", "")),
                    title=str(t.get("title", "")),
                    category=str(t.get("category", "")) or "misc",
                    unlock=t.get("unlock", {"type": "always"}) or {"type": "always"},
                    sequence=t.get("sequence", []) or [],
                    tags=t.get("tags", []) or [],
                )
            )
        self.topics = [x for x in out if x.id and x.title]

    def get(self, topic_id: str) -> Topic | None:
        for t in self.topics:
            if t.id == topic_id:
                return t
        return None

    def list_all(self) -> list[Topic]:
        return list(self.topics)

    def category_order(self) -> list[Category]:
        return list(self.categories)


def _parse_hhmm(s: str) -> tuple[int, int] | None:
    try:
        hh, mm = s.split(":")
        return int(hh), int(mm)
    except Exception:
        return None


def unlock_ok(g: Girl, unlock: dict[str, Any], now: float | None = None) -> bool:
    if now is None:
        now = time.time()

    typ = (unlock.get("type") or "always").strip()

    if typ == "always":
        return True

    if typ == "affection_gte":
        v = int(unlock.get("value", 0))
        return int(getattr(g, "affection", 0)) >= v

    if typ == "days_since_first_gte":
        v = int(unlock.get("value", 0))
        first = float(getattr(g, "first_seen", 0.0) or 0.0)
        if first <= 0:
            return False
        days = (now - first) / (60 * 60 * 24)
        return days >= v

    if typ == "flag_true":
        name = str(unlock.get("name", ""))
        flags = getattr(g, "flags", {}) or {}
        return bool(flags.get(name, False))

    if typ == "weekday_in":
        vals = unlock.get("values", [])
        try:
            vals = [int(x) for x in vals]
        except Exception:
            vals = []
        lt = time.localtime(now)
        wd = lt.tm_wday  # 0=Mon
        return wd in vals

    if typ == "time_range":
        fr = _parse_hhmm(str(unlock.get("from", "")) or "")
        to = _parse_hhmm(str(unlock.get("to", "")) or "")
        if not fr or not to:
            return False
        lt = time.localtime(now)
        cur = lt.tm_hour * 60 + lt.tm_min
        a = fr[0] * 60 + fr[1]
        b = to[0] * 60 + to[1]
        if a <= b:
            return a <= cur <= b
        return cur >= a or cur <= b

    if typ in ("all", "any"):
        conds = unlock.get("conds", []) or []
        checks = [unlock_ok(g, c, now) for c in conds if isinstance(c, dict)]
        if typ == "all":
            return all(checks) if checks else True
        else:
            return any(checks) if checks else False

    return False


def describe_unlock(unlock: dict[str, Any]) -> str:
    """
    LOCKED を押した時の“匂わせ”文。
    雑に短く、でも手がかりになる感じを狙う。
    """
    typ = (unlock.get("type") or "always").strip()

    if typ == "always":
        return "これは本当は、もう話せるはずなんだけど…？（バグかも）"

    if typ == "affection_gte":
        v = int(unlock.get("value", 0))
        return f"❤が{v}以上になったら…話そ。"

    if typ == "days_since_first_gte":
        v = int(unlock.get("value", 0))
        return f"{v}日くらい一緒にいたら、続き話す。"

    if typ == "flag_true":
        return "ある会話のあとで、解放されるかも。"

    if typ == "weekday_in":
        return "特定の曜日に、こっそり開く話題。"

    if typ == "time_range":
        fr = str(unlock.get("from", ""))
        to = str(unlock.get("to", ""))
        if fr and to:
            return f"{fr}〜{to}のあいだに、解放される。"
        return "時間帯が合うと、開く話題。"

    if typ == "all":
        return "条件がいくつかある。積み重ねタイプ。"

    if typ == "any":
        return "条件がいくつかある。どれか満たせばOK。"

    return "条件を満たしたら、話せる。"
