"""把 tips/**/*.md 与 notes/papers/*.md（带 YAML front matter）索引成 data/tips.json，供看板使用。"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from .store import ROOT

SCAN_DIRS = ["tips", "notes/papers"]


def parse_card(path: Path) -> dict | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    try:
        _, front, body = text.split("---", 2)
    except ValueError:
        return None
    meta = yaml.safe_load(front) or {}
    if meta.get("draft"):
        return None
    rel = path.relative_to(ROOT).as_posix()
    return {
        "id": rel,
        "path": rel,
        "kind": "paper-note" if rel.startswith("notes/") else "tip",
        "title": meta.get("title", path.stem),
        "track": meta.get("track", "engineering"),
        "tags": meta.get("tags", []),
        "date": str(meta.get("date", "")),
        "source": meta.get("source", ""),
        "body": body.strip(),
    }


def build_index(root: Path = ROOT) -> list[dict]:
    cards = []
    for d in SCAN_DIRS:
        for p in sorted((root / d).rglob("*.md")):
            if p.name.startswith("_") or p.name == "README.md":
                continue
            card = parse_card(p)
            if card:
                cards.append(card)
    return sorted(cards, key=lambda c: c["date"], reverse=True)


def write_index(path: Path = ROOT / "data" / "tips.json") -> int:
    cards = build_index()
    path.write_text(json.dumps(cards, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return len(cards)
