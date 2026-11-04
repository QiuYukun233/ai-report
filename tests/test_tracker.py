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
