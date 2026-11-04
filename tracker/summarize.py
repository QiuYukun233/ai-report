"""用 Claude 给条目打相关度分数（1-5）并写中文标题和摘要。

只处理还没有 score 的条目，所以每天运行只会花新增条目的钱。
没有设置 ANTHROPIC_API_KEY 时直接跳过，不影响其余流程。
"""
from __future__ import annotations

import json
import os
import sys

import anthropic

SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "score": {"type": "integer", "enum": [1, 2, 3, 4, 5]},
                    "zh_title": {"type": "string"},
                    "zh_summary": {"type": "string"},
                },
                "required": ["id", "score", "zh_title", "zh_summary"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["items"],
    "additionalProperties": False,
}

SYSTEM = """你在帮一位读者筛选每天的技术资讯。读者的兴趣：

{interests}

对每个条目：
- score：和读者兴趣的相关度与价值，1-5 的整数。
  5 = 必读（核心方向上的重要新结果、能直接上手的方法或工具）；
  4 = 值得读；3 = 有点相关，可略读；2 = 关系不大；1 = 无关。
  打分要拉开差距，大多数条目应在 2-3 分；不要因为标题里有热门词就给高分。
  工具的版本发布：只有包含重要新功能时才给 4 分以上，常规修复给 1-2 分。
- zh_title：简洁准确的中文标题；专有名词（模型名、库名、SAE 等术语）保留英文。
- zh_summary：一到两句中文，说清楚"做了什么、为什么值得关注"。只依据给出的信息，不要编造细节；信息不足时如实写短一点。

为输入中的每个 id 各输出一条结果，id 原样返回。"""


def pending(items: list[dict], limit: int) -> list[dict]:
    """尚未打分的条目，最新的优先。"""
    todo = [i for i in items if "score" not in i]
    todo.sort(key=lambda i: i.get("published") or i.get("fetched_at", ""), reverse=True)
    return todo[:limit]


def build_user_content(batch: list[dict]) -> str:
    payload = [{
        "id": i["id"],
        "source": i["source"],
        "title": i["title"],
        "summary": i.get("summary", "")[:600],
    } for i in batch]
    return json.dumps(payload, ensure_ascii=False)


def score_batch(client, batch: list[dict], cfg: dict) -> list[dict]:
    response = client.beta.messages.create(
        model=cfg.get("model", "claude-opus-5-5"),
        max_tokens=16000,
        output_config={"effort": cfg.get("effort", "low"), "format": {"type": "json_schema", "schema": SCHEMA}},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        system=SYSTEM.format(interests=cfg.get("interests", "").strip()),
        messages=[{"role": "user", "content": build_user_content(batch)}],
    )
    if response.stop_reason != "end_turn":
        raise RuntimeError(f"stop_reason={response.stop_reason}")
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)["items"]


def apply_results(items: list[dict], results: list[dict], model: str) -> int:
    by_id = {i["id"]: i for i in items}
    n = 0
    for r in results:
        item = by_id.get(r.get("id"))
        if item is None:
            continue
        item["score"] = int(r["score"])
        item["zh_title"] = r["zh_title"].strip()
        item["zh_summary"] = r["zh_summary"].strip()
        item["scored_by"] = model
        n += 1
    return n


def summarize(items: list[dict], cfg: dict, client=None) -> int:
    """原地给 items 打分，返回成功处理的条数。"""
    if client is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            print("未设置 ANTHROPIC_API_KEY，跳过打分")
            return 0
        client = anthropic.Anthropic()

    todo = pending(items, cfg.get("max_items_per_run", 300))
    size = cfg.get("batch_size", 20)
    done = 0
    for start in range(0, len(todo), size):
        batch = todo[start:start + size]
        try:
            done += apply_results(items, score_batch(client, batch, cfg), cfg.get("model", ""))
        except anthropic.AuthenticationError:
            print("  ✗ API key 无效，停止打分", file=sys.stderr)
            break
        except (anthropic.APIError, RuntimeError, ValueError, KeyError, StopIteration) as e:
            # 单批失败不影响其他批；没打上分的条目下次运行会重试
            print(f"  ✗ 第 {start // size + 1} 批失败: {e.__class__.__name__}: {e}", file=sys.stderr)
    print(f"打分 {done}/{len(todo)} 条")
    return done
