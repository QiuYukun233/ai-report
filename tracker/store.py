"""data/items.json 的读写、去重、打标签。"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .fetchers import matches

ROOT = Path(__file__).resolve().parent.parent
ITEMS_PATH = ROOT / "data" / "items.json"
MAX_ITEMS = 3000  # 防止文件无限增长


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_items(path: Path = ITEMS_PATH) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def save_items(items: list[dict], path: Path = ITEMS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    items = sorted(items, key=lambda i: i.get("published") or i["fetched_at"], reverse=True)
    path.write_text(json.dumps(items[:MAX_ITEMS], ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def auto_tag(item: dict, rules: dict[str, list[str]]) -> list[str]:
    text = f"{item['title']} {item['summary']}"
    return sorted(tag for tag, kws in rules.items() if any(matches(k, text) for k in kws))


def merge(existing: list[dict], new: list[dict], tag_rules: dict) -> tuple[list[dict], list[dict]]:
    """合并新条目，返回 (全部条目, 真正新增的条目)。已有条目保留首次抓取时间。"""
    by_id = {i["id"]: i for i in existing}
    added = []
    stamp = now_iso()
    for item in new:
        item["tags"] = auto_tag(item, tag_rules)
        if item["id"] in by_id:
            continue
        item["fetched_at"] = stamp
        by_id[item["id"]] = item
        added.append(item)
    return list(by_id.values()), added
