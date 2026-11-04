"""命令行入口。

    python -m tracker fetch    # 抓取所有来源 -> data/items.json
    python -m tracker summarize  # 用 Claude 给新条目打分、写中文摘要（需 ANTHROPIC_API_KEY）
    python -m tracker digest   # 生成本周周报 -> digests/
    python -m tracker tips     # 索引 tips/ 与 notes/ -> data/tips.json
    python -m tracker site     # 把 data/ 拷到 site/data/，供看板读取
    python -m tracker all      # 以上全部
"""
from __future__ import annotations

import argparse
import shutil
import sys

import yaml

from . import fetchers
from .digest import write_digest
from .store import ROOT, load_items, merge, save_items
from .summarize import summarize
from .tips import write_index


def load_config() -> dict:
    return yaml.safe_load((ROOT / "config" / "sources.yaml").read_text(encoding="utf-8"))


def prune(items: list[dict], cfg: dict) -> list[dict]:
    """按当前配置重新过滤已存的 RSS 条目，这样改了过滤规则后旧数据也会跟着清理。"""
    rules = {f["name"]: f for f in cfg.get("rss", [])}
    kept = [i for i in items if i["source"] not in rules or fetchers.passes_filter(
        i, rules[i["source"]].get("require_keywords"), rules[i["source"]].get("max_age_days"))]
    if len(kept) < len(items):
        print(f"按当前过滤规则清理旧条目 {len(items) - len(kept)} 条")
    return kept


def cmd_fetch() -> int:
    cfg = load_config()
    jobs = []
    ax = cfg.get("arxiv", {})
    for q in ax.get("queries", []):
        jobs.append((f"arXiv[{q['track']}]",
                     lambda q=q: fetchers.fetch_arxiv(q["search"], q["track"], ax.get("max_results", 40))))
    for f in cfg.get("rss", []):
        jobs.append((f["name"], lambda f=f: fetchers.fetch_feed(
            f["name"], f["url"], f["track"], f.get("require_keywords"), f.get("max_age_days"))))
    for g in cfg.get("github_releases", []):
        jobs.append((g["repo"], lambda g=g: fetchers.fetch_github_releases(g["repo"], g["track"])))

    collected, failures = [], []
    for name, job in jobs:
        try:
            got = job()
            print(f"  ✓ {name}: {len(got)}")
            collected += got
        except Exception as e:  # 单个来源失败不影响整体
            print(f"  ✗ {name}: {e.__class__.__name__}: {e}", file=sys.stderr)
            failures.append(name)

    items, added = merge(prune(load_items(), cfg), collected, cfg.get("tags", {}))
    save_items(items)
    print(f"新增 {len(added)} 条，共 {len(items)} 条；失败来源 {len(failures)}/{len(jobs)}")
    return 1 if failures and len(failures) == len(jobs) else 0


def cmd_summarize() -> int:
    items = load_items()
    if summarize(items, load_config().get("llm", {})):
        save_items(items)
    return 0


def cmd_digest() -> int:
    print(f"周报: {write_digest(load_items()).relative_to(ROOT)}")
    return 0


def cmd_tips() -> int:
    print(f"索引卡片 {write_index()} 张")
    return 0


def cmd_site() -> int:
    dst = ROOT / "site" / "data"
    dst.mkdir(parents=True, exist_ok=True)
    for name in ("items.json", "tips.json"):
        src = ROOT / "data" / name
        if src.exists():
            shutil.copy(src, dst / name)
    print("已同步 data/ -> site/data/")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(prog="tracker")
    p.add_argument("command", choices=["fetch", "summarize", "digest", "tips", "site", "all"])
    cmd = p.parse_args().command
    if cmd == "all":
        rc = cmd_fetch()
        cmd_summarize(); cmd_digest(); cmd_tips(); cmd_site()
        return rc
    return {"fetch": cmd_fetch, "summarize": cmd_summarize, "digest": cmd_digest, "tips": cmd_tips, "site": cmd_site}[cmd]()


if __name__ == "__main__":
    sys.exit(main())
