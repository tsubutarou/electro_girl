from __future__ import annotations
import time
from typing import Any

from .model import Girl

MAX_LOG = 120

def add_log(g: Girl, text: str, topic_id: str | None = None, topic_title: str | None = None):
    entry: dict[str, Any] = {
        "t": time.time(),
        "text": text,
    }
    if topic_id:
        entry["topic_id"] = topic_id
    if topic_title:
        entry["topic_title"] = topic_title

    if not hasattr(g, "journal") or g.journal is None:
        g.journal = []
    g.journal.append(entry)
    # 上限
    if len(g.journal) > MAX_LOG:
        g.journal = g.journal[-MAX_LOG:]
