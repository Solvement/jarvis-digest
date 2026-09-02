"""GitHub 项目采集：Trending 页面（HTML）+ Search API（近期新建的 AI 主题仓库）。"""
from __future__ import annotations

import html
import os
import re
from datetime import datetime, timedelta, timezone

from ..models import Item
from .http import get

TRENDING_URL = "https://github.com/trending/{lang}"
API_SEARCH = "https://api.github.com/search/repositories"

_ARTICLE = re.compile(r"<article[^>]*class=\"[^\"]*Box-row[^\"]*\"[\s\S]*?</article>", re.I)
_NAME = re.compile(r"<h2[^>]*>[\s\S]*?<a[^>]+href=\"/([^/\"]+/[^/\"#?]+)\"", re.I)
_DESC = re.compile(r"<p[^>]*class=\"[^\"]*col-9[^\"]*\"[^>]*>([\s\S]*?)</p>", re.I)
_LANG = re.compile(r"itemprop=\"programmingLanguage\"[^>]*>([^<]+)<", re.I)
_STARS = re.compile(r"href=\"/[^\"]+/stargazers\"[^>]*>([\s\S]*?)</a>", re.I)
_FORKS = re.compile(r"href=\"/[^\"]+/forks\"[^>]*>([\s\S]*?)</a>", re.I)
_TODAY = re.compile(r"([\d,]+)\s+stars\s+(today|this week|this month)", re.I)
_TAGS = re.compile(r"<[^>]+>")


def _num(s: str) -> int:
    s = _TAGS.sub("", s).strip().replace(",", "")
    m = re.search(r"\d+", s)
    return int(m.group()) if m else 0


def parse_trending_html(page: str, lang_label: str = "", board: str = "daily") -> list[Item]:
    items: list[Item] = []
    for block in _ARTICLE.findall(page):
        m = _NAME.search(block)
        if not m:
            continue
        full = m.group(1).strip()
        desc = ""
        dm = _DESC.search(block)
        if dm:
            desc = html.unescape(_TAGS.sub("", dm.group(1))).strip()
        lm = _LANG.search(block)
        sm = _STARS.search(block)
        fm = _FORKS.search(block)
        tm = _TODAY.search(block)
        items.append(
            Item(
                id=f"repo:{full.lower()}",
                kind="project",
                title=full,
                url=f"https://github.com/{full}",
                summary=desc,
                source="github_trending",
                org=full.split("/")[0],
                stars=_num(sm.group(1)) if sm else 0,
                forks=_num(fm.group(1)) if fm else 0,
                stars_today=_num(tm.group(1)) if tm else 0,
                language=(lm.group(1).strip() if lm else lang_label),
                code_url=f"https://github.com/{full}",
                board=board,
            )
        )
    return items


def fetch_trending(languages: list[str], boards: list[str] | None = None) -> list[Item]:
    """日榜 / 周榜 / 月榜都抓；同一仓库多榜出现时在 dedupe 里合并，board 取最短周期。"""
    out: list[Item] = []
    for board in boards or ["daily"]:
        for lang in languages:
            url = TRENDING_URL.format(lang=lang)
            r = get(url, params={"since": board}, headers={"Accept": "text/html"})
            if r.status_code != 200:
                print(f"  [github_trending] {board}/{lang or 'all'}: HTTP {r.status_code}")
                continue
            got = parse_trending_html(r.text, lang, board)
            print(f"  [github_trending] {board}/{lang or 'all'}: {len(got)} repos")
            out.extend(got)
    return out


def fetch_search(queries: list[str], days: int, per_query: int) -> list[Item]:
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    out: list[Item] = []
    for q in queries:
        full_q = f"{q} created:>{since}"
        r = get(API_SEARCH, params={"q": full_q, "sort": "stars", "order": "desc", "per_page": per_query}, headers=headers)
        if r.status_code != 200:
            print(f"  [github_search] {q!r}: HTTP {r.status_code}")
            continue
        for repo in r.json().get("items", []):
            full = repo["full_name"]
            out.append(
                Item(
                    id=f"repo:{full.lower()}",
                    kind="project",
                    title=full,
                    url=repo["html_url"],
                    summary=repo.get("description") or "",
                    source="github_search",
                    org=repo["owner"]["login"],
                    published=(repo.get("created_at") or "")[:10],
                    stars=repo.get("stargazers_count", 0),
                    forks=repo.get("forks_count", 0),
                    language=repo.get("language") or "",
                    code_url=repo["html_url"],
                    keywords=list(repo.get("topics") or [])[:8],
                )
            )
        print(f"  [github_search] {q!r}: {len(out)} cumulative")
    return out


def collect_github(cfg: dict) -> list[Item]:
    items: list[Item] = []
    t = cfg.get("github_trending", {})
    if t.get("enabled", True):
        try:
            items += fetch_trending(t.get("languages", [""]), t.get("boards", ["daily"]))
        except Exception as e:  # noqa: BLE001
            print(f"  [github_trending] failed: {e}")
    s = cfg.get("github_search", {})
    if s.get("enabled", True):
        try:
            items += fetch_search(s.get("queries", []), s.get("days", 14), s.get("per_query", 15))
        except Exception as e:  # noqa: BLE001
            print(f"  [github_search] failed: {e}")
    return items
