"""从 arXiv / RSS·Atom / GitHub Releases 抓取条目，统一成 Item 字典。

每个 parse_* 函数只做解析（便于离线测试），fetch_* 负责网络请求。
"""
from __future__ import annotations

import hashlib
import html
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import requests

USER_AGENT = "ai-interp-tracker/0.1 (+https://github.com)"
TIMEOUT = 30
ATOM = "{http://www.w3.org/2005/Atom}"

Item = dict[str, Any]


def _clean(text: str | None, limit: int = 600) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", html.unescape(text))
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _iso(value: str | None) -> str:
    """把各种日期格式规整成 ISO8601 (UTC)。解析失败返回空串。"""
    if not value:
        return ""
    value = value.strip()
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            dt = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def make_id(url: str) -> str:
    return hashlib.sha1(url.encode()).hexdigest()[:12]


def _item(*, title, url, source, source_type, track, published="", summary="", authors=None) -> Item:
    return {
        "id": make_id(url),
        "title": _clean(title, 300),
        "url": url,
        "source": source,
        "source_type": source_type,
        "track": track,
        "published": _iso(published),
        "summary": _clean(summary),
        "authors": authors or [],
    }


def _get(url: str, **kw) -> requests.Response:
    headers = {"User-Agent": USER_AGENT, **kw.pop("headers", {})}
    resp = requests.get(url, headers=headers, timeout=TIMEOUT, **kw)
    resp.raise_for_status()
    return resp


# ---------------------------------------------------------------- arXiv
def parse_arxiv(xml_text: str, track: str) -> list[Item]:
    root = ET.fromstring(xml_text)
    items = []
    for entry in root.findall(f"{ATOM}entry"):
        url = (entry.findtext(f"{ATOM}id") or "").strip()
        # 去掉版本号，避免 v1/v2 重复
        url = re.sub(r"v\d+$", "", url).replace("http://", "https://")
        if not url:
            continue
        authors = [a.findtext(f"{ATOM}name", "").strip() for a in entry.findall(f"{ATOM}author")]
        items.append(_item(
            title=entry.findtext(f"{ATOM}title"),
            url=url,
            source="arXiv",
            source_type="paper",
            track=track,
            published=entry.findtext(f"{ATOM}published"),
            summary=entry.findtext(f"{ATOM}summary"),
            authors=authors[:8],
        ))
    return items


def fetch_arxiv(search: str, track: str, max_results: int = 40) -> list[Item]:
    resp = _get("https://export.arxiv.org/api/query", params={
        "search_query": " ".join(search.split()),
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": max_results,
    })
    return parse_arxiv(resp.text, track)


# ---------------------------------------------------------------- RSS / Atom
def parse_feed(xml_text: str, name: str, track: str) -> list[Item]:
    root = ET.fromstring(xml_text)
    items = []
    if root.tag == f"{ATOM}feed":
        for e in root.findall(f"{ATOM}entry"):
            link = ""
            for l in e.findall(f"{ATOM}link"):
                if l.get("rel", "alternate") == "alternate":
                    link = l.get("href", "")
                    break
            if not link:
                continue
            items.append(_item(
                title=e.findtext(f"{ATOM}title"), url=link, source=name,
                source_type="blog", track=track,
                published=e.findtext(f"{ATOM}published") or e.findtext(f"{ATOM}updated"),
                summary=e.findtext(f"{ATOM}summary") or e.findtext(f"{ATOM}content"),
            ))
    else:  # RSS 2.0
        for e in root.iter("item"):
            link = (e.findtext("link") or "").strip()
            if not link:
                continue
            items.append(_item(
                title=e.findtext("title"), url=link, source=name,
                source_type="blog", track=track,
                published=e.findtext("pubDate"), summary=e.findtext("description"),
            ))
    return items


def matches(keyword: str, text: str) -> bool:
    """短关键词（<=4 个字符，如 SAE、uv）按整词匹配（允许复数 s）；全大写的还区分大小写。其余按子串、不区分大小写。"""
    if len(keyword) <= 4 and keyword.replace(".", "").isalnum():
        flags = 0 if keyword.isupper() else re.IGNORECASE
        return re.search(rf"\b{re.escape(keyword)}s?\b", text, flags) is not None
    return keyword.lower() in text.lower()


def passes_filter(item: Item, keywords: list[str] | None = None,
                  max_age_days: int | None = None, now: datetime | None = None) -> bool:
    if keywords and not any(matches(k, f"{item['title']} {item['summary']}") for k in keywords):
        return False
    if max_age_days and item.get("published"):
        now = now or datetime.now(timezone.utc)
        if datetime.fromisoformat(item["published"]) < now - timedelta(days=max_age_days):
            return False
    return True


def keep_by_keywords(items: list[Item], keywords: list[str] | None) -> list[Item]:
    return [i for i in items if passes_filter(i, keywords)]


def fetch_feed(name: str, url: str, track: str, require_keywords=None, max_age_days=None) -> list[Item]:
    resp = _get(url)
    return [i for i in parse_feed(resp.text, name, track)
            if passes_filter(i, require_keywords, max_age_days)]


# ---------------------------------------------------------------- GitHub
def parse_github_releases(data: list[dict], repo: str, track: str) -> list[Item]:
    items = []
    for r in data:
        if r.get("draft") or r.get("prerelease"):
            continue
        items.append(_item(
            title=f"{repo} {r.get('name') or r.get('tag_name')}",
            url=r["html_url"], source=repo, source_type="release", track=track,
            published=r.get("published_at"), summary=r.get("body") or "",
        ))
    return items


def fetch_github_releases(repo: str, track: str, per_page: int = 5) -> list[Item]:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = _get(f"https://api.github.com/repos/{repo}/releases",
                params={"per_page": per_page}, headers=headers)
    return parse_github_releases(resp.json(), repo, track)
