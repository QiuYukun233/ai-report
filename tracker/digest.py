"""生成每周 Markdown 周报：digests/YYYY-Www.md"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .store import ROOT

TRACK_TITLES = {
    "interp": "🔬 AI 可解释性",
    "ai-coding": "🤖 AI 辅助编程",
    "engineering": "🛠️ 通用工程",
}


def week_label(dt: datetime) -> str:
    y, w, _ = dt.isocalendar()
    return f"{y}-W{w:02d}"


TOP_N = 10


def _rank_key(i: dict):
    return (i.get("score", 0), i.get("published", ""))


def _entry(i: dict) -> list[str]:
    tags = " ".join(f"`{t}`" for t in i.get("tags", []))
    date = (i.get("published") or "")[:10]
    star = f"★{i['score']} " if "score" in i else ""
    title = i.get("zh_title") or i["title"]
    lines = [f"- [ ] {star}[{title}]({i['url']}) — {i['source']} {date} {tags}".rstrip()]
    if i.get("zh_summary"):
        lines.append(f"  {i['zh_summary']}")
    return lines


def build_digest(items: list[dict], now: datetime | None = None, days: int = 7) -> tuple[str, str]:
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    recent = [i for i in items if datetime.fromisoformat(i["fetched_at"]) >= cutoff]

    groups: dict[str, list[dict]] = defaultdict(list)
    for i in recent:
        groups[i["track"]].append(i)

    label = week_label(now)
    lines = [
        f"# 周报 {label}",
        "",
        f"> 自动生成于 {now:%Y-%m-%d}，覆盖最近 {days} 天抓取的 {len(recent)} 条内容。",
        "> ★ 是 Claude 按兴趣打的相关度（1-5）。勾选读过的条目；值得沉淀的写进 `notes/papers/` 或 `tips/`。",
        "",
    ]
    top = sorted((i for i in recent if i.get("score", 0) >= 4), key=_rank_key, reverse=True)[:TOP_N]
    if top:
        lines += [f"## ⭐ 本周必读 Top {len(top)}", ""]
        for i in top:
            lines += _entry(i)
        lines.append("")

    for track, title in TRACK_TITLES.items():
        group = sorted(groups.get(track, []), key=_rank_key, reverse=True)
        lines += [f"## {title}（{len(group)}）", ""]
        if not group:
            lines += ["_本周无新内容_", ""]
            continue
        main = [i for i in group if i.get("score", 3) >= 3]
        low = [i for i in group if i.get("score", 3) < 3]
        for i in main:
            lines += _entry(i)
        if low:
            lines += ["", f"<details><summary>低相关度 {len(low)} 条</summary>", ""]
            for i in low:
                lines += _entry(i)
            lines += ["", "</details>"]
        lines.append("")
    return label, "\n".join(lines)


def write_digest(items: list[dict], out_dir: Path = ROOT / "digests") -> Path:
    label, text = build_digest(items)
    out_dir.mkdir(exist_ok=True)
    path = out_dir / f"{label}.md"
    path.write_text(text, encoding="utf-8")
    return path
