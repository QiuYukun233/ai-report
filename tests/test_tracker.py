from datetime import datetime, timezone

from tracker import fetchers
from tracker.digest import build_digest
from tracker.store import auto_tag, merge
from tracker.tips import build_index


ARXIV = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2601.01234v2</id>
    <published>2026-10-30T17:59:01Z</published>
    <title>Scaling Sparse Autoencoders
      for Circuit Discovery</title>
    <summary>We train a sparse autoencoder (SAE) and use activation patching.</summary>
    <author><name>Ada Lovelace</name></author>
    <author><name>Alan Turing</name></author>
  </entry>
</feed>"""

RSS = """<?xml version="1.0"?><rss version="2.0"><channel>
  <item><title>Steering vectors in practice</title><link>https://ex.com/a</link>
    <pubDate>Mon, 02 Nov 2026 10:00:00 GMT</pubDate><description>&lt;p&gt;An interpretability post&lt;/p&gt;</description></item>
  <item><title>My vacation</title><link>https://ex.com/b</link><description>beach</description></item>
</channel></rss>"""

ATOM_BLOG = """<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">
  <entry><title>Using Claude Code with tests</title>
    <link rel="alternate" href="https://ex.com/c"/><updated>2026-11-01T00:00:00Z</updated>
    <summary>agent workflows</summary></entry>
</feed>"""

RULES = {"sae": ["sparse autoencoder", "SAE"], "patching": ["activation patching"],
         "steering": ["steering"], "python-tooling": ["uv"]}


def test_parse_arxiv():
    [item] = fetchers.parse_arxiv(ARXIV, "interp")
    assert item["url"] == "https://arxiv.org/abs/2601.01234"  # 版本号被去掉
    assert item["title"] == "Scaling Sparse Autoencoders for Circuit Discovery"
    assert item["authors"] == ["Ada Lovelace", "Alan Turing"]
    assert item["published"] == "2026-10-30T17:59:01+00:00"


def test_parse_rss_and_keyword_filter():
    items = fetchers.parse_feed(RSS, "Blog", "interp")
    assert len(items) == 2
    assert items[0]["summary"] == "An interpretability post"  # HTML 被清理
    assert items[0]["published"].startswith("2026-11-02")
    kept = fetchers.keep_by_keywords(items, ["interpretab"])
    assert [i["url"] for i in kept] == ["https://ex.com/a"]


def test_parse_atom_blog():
    [item] = fetchers.parse_feed(ATOM_BLOG, "SW", "ai-coding")
    assert item["url"] == "https://ex.com/c"
    assert item["published"].startswith("2026-11-01")


def test_parse_github_releases_skips_prerelease():
    data = [
        {"name": "v2.0", "tag_name": "v2.0", "html_url": "https://gh/r/1", "published_at": "2026-11-01T00:00:00Z", "body": "x"},
        {"name": "v2.1rc", "tag_name": "v2.1rc", "html_url": "https://gh/r/2", "prerelease": True},
    ]
    items = fetchers.parse_github_releases(data, "o/r", "interp")
    assert [i["title"] for i in items] == ["o/r v2.0"]


def test_auto_tag_short_keywords_are_whole_word():
    item = {"title": "SAE features", "summary": "we use activation patching"}
    assert auto_tag(item, RULES) == ["patching", "sae"]
    # "uv" 不应命中 "ultraviolet"/"fluvial" 之类子串
    assert auto_tag({"title": "fluvial maps", "summary": ""}, RULES) == []
    assert auto_tag({"title": "Faster installs with uv", "summary": ""}, RULES) == ["python-tooling"]


def test_merge_dedupes_and_keeps_first_fetch_time():
    [item] = fetchers.parse_arxiv(ARXIV, "interp")
    items, added = merge([], [dict(item)], RULES)
    assert len(added) == 1
    first = items[0]["fetched_at"]
    items2, added2 = merge(items, [dict(item)], RULES)
    assert added2 == [] and len(items2) == 1 and items2[0]["fetched_at"] == first


def test_digest_groups_by_track():
    now = datetime(2026, 11, 4, tzinfo=timezone.utc)
    items = [
        {"title": "A", "url": "u1", "source": "arXiv", "track": "interp", "tags": ["sae"],
         "published": "2026-11-01T00:00:00+00:00", "fetched_at": "2026-11-03T00:00:00+00:00"},
        {"title": "Old", "url": "u2", "source": "x", "track": "interp", "tags": [],
         "published": "", "fetched_at": "2026-09-01T00:00:00+00:00"},
    ]
    label, text = build_digest(items, now=now)
    assert label == "2026-W45"
    assert "- [ ] [A](u1)" in text and "Old" not in text
    assert "AI 辅助编程（0）" in text


def test_tips_index_reads_repo_cards():
    cards = build_index()
    assert cards, "仓库里应至少有一张种子卡片"
    assert all({"title", "track", "body"} <= c.keys() for c in cards)
    assert {c["track"] for c in cards} <= {"interp", "ai-coding", "engineering"}


def test_passes_filter_age_and_whole_word():
    now = datetime(2026, 11, 4, tzinfo=timezone.utc)
    new = {"title": "Using MCP with coding agents", "summary": "", "published": "2026-10-20T00:00:00+00:00"}
    old = dict(new, published="2021-01-01T00:00:00+00:00")
    assert fetchers.passes_filter(new, ["MCP"], 90, now)
    assert not fetchers.passes_filter(old, ["MCP"], 90, now)
    # 全大写短词整词且区分大小写："SAE" 不命中 "Saeed"
    assert not fetchers.passes_filter({"title": "Interview with Saeed", "summary": ""}, ["SAE"])


def test_prune_reapplies_current_rss_rules():
    from tracker.__main__ import prune
    cfg = {"rss": [{"name": "HF", "require_keywords": ["interpretab"]}]}
    items = [
        {"source": "HF", "title": "Interpretability tools", "summary": ""},
        {"source": "HF", "title": "Diffusion news", "summary": ""},
        {"source": "arXiv", "title": "Diffusion paper", "summary": ""},
    ]
    assert [i["title"] for i in prune(items, cfg)] == ["Interpretability tools", "Diffusion paper"]


def test_short_keyword_allows_plural():
    assert fetchers.matches("llm", "Running LLMs locally")
    assert not fetchers.matches("uv", "fluvial")


# ---------------------------------------------------------------- Claude 打分（用假客户端，不联网）
import json as _json
from types import SimpleNamespace

from tracker import summarize as sm


class FakeClient:
    """模拟 client.beta.messages.create：按输入 id 返回固定分数，并记录请求参数。"""

    def __init__(self, stop_reason="end_turn"):
        self.calls = []
        self.stop_reason = stop_reason
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self.create))

    def create(self, **kw):
        self.calls.append(kw)
        ids = [x["id"] for x in _json.loads(kw["messages"][0]["content"])]
        out = {"items": [{"id": i, "score": 4, "zh_title": f"标题{i}", "zh_summary": " 摘要 "} for i in ids]
                         + [{"id": "unknown", "score": 5, "zh_title": "x", "zh_summary": "x"}]}
        return SimpleNamespace(stop_reason=self.stop_reason,
                               content=[SimpleNamespace(type="text", text=_json.dumps(out))])


def _items(n):
    return [{"id": f"i{k}", "source": "arXiv", "title": f"T{k}", "summary": "s",
             "published": f"2026-11-0{k + 1}T00:00:00+00:00"} for k in range(n)]


def test_summarize_batches_only_unscored_items():
    items = _items(5)
    items[0]["score"] = 2  # 已打过分的跳过
    client = FakeClient()
    done = sm.summarize(items, {"batch_size": 3, "model": "m", "interests": "SAE"}, client=client)
    assert done == 4 and len(client.calls) == 2
    assert items[0]["score"] == 2 and "zh_title" not in items[0]
    assert items[1] == {**items[1], "score": 4, "zh_title": "标题i1", "zh_summary": "摘要", "scored_by": "m"}
    assert "unknown" not in {i["id"] for i in items}
    req = client.calls[0]
    assert req["output_config"]["format"]["type"] == "json_schema"
    assert "SAE" in req["system"]


def test_summarize_skips_batch_on_refusal():
    items = _items(2)
    assert sm.summarize(items, {}, client=FakeClient(stop_reason="refusal")) == 0
    assert all("score" not in i for i in items)  # 下次运行会重试


def test_summarize_without_key_is_noop(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert sm.summarize(_items(2), {}) == 0


def test_digest_top_section_and_low_score_fold():
    now = datetime(2026, 11, 4, tzinfo=timezone.utc)
    base = {"source": "arXiv", "track": "interp", "tags": [], "fetched_at": "2026-11-03T00:00:00+00:00",
            "published": "2026-11-02T00:00:00+00:00"}
    items = [
        {**base, "title": "Hi", "url": "u1", "score": 5, "zh_title": "高分", "zh_summary": "很重要"},
        {**base, "title": "Lo", "url": "u2", "score": 1, "zh_title": "低分", "zh_summary": "无关"},
    ]
    _, text = build_digest(items, now=now)
    assert "本周必读 Top 1" in text
    assert "- [ ] ★5 [高分](u1)" in text and "  很重要" in text
    assert text.index("低相关度 1 条") < text.index("[低分](u2)")
