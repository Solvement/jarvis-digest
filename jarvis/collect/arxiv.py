"""arXiv API（Atom）—— 补充 HF 没收录但刚提交的论文。"""
from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

from ..models import Item
from .http import get

API = "https://export.arxiv.org/api/query"
NS = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


def parse_arxiv_atom(xml_text: str) -> list[Item]:
    root = ET.fromstring(xml_text)
    items: list[Item] = []
    for entry in root.findall("a:entry", NS):
        raw_id = (entry.findtext("a:id", default="", namespaces=NS) or "").strip()
        m = re.search(r"abs/([\d.]+)(v\d+)?", raw_id)
        if not m:
            continue
        pid = m.group(1)
        title = re.sub(r"\s+", " ", entry.findtext("a:title", default="", namespaces=NS) or "").strip()
        summary = re.sub(r"\s+", " ", entry.findtext("a:summary", default="", namespaces=NS) or "").strip()
        published = (entry.findtext("a:published", default="", namespaces=NS) or "")[:10]
        authors = [a.findtext("a:name", default="", namespaces=NS) for a in entry.findall("a:author", NS)]
        cats = [c.get("term", "") for c in entry.findall("a:category", NS)]
        comment = entry.findtext("arxiv:comment", default="", namespaces=NS) or ""
        code = ""
        gm = re.search(r"https?://github\.com/[\w.-]+/[\w.-]+", summary + " " + comment)
        if gm:
            code = gm.group(0)
        items.append(
            Item(
                id=f"paper:{pid}",
                kind="paper",
                title=title,
                url=f"https://arxiv.org/abs/{pid}",
                pdf_url=f"https://arxiv.org/pdf/{pid}",
                summary=summary,
                source="arxiv",
                published=published,
                authors=[a for a in authors if a][:6],
                categories=cats,
                code_url=code,
            )
        )
    return items


def collect_arxiv(cfg: dict) -> list[Item]:
    cats = cfg.get("categories", ["cs.AI", "cs.CL", "cs.LG"])
    max_results = int(cfg.get("max_results", 200))
    window = timedelta(hours=int(cfg.get("window_hours", 48)))
    q = " OR ".join(f"cat:{c}" for c in cats)
    out: list[Item] = []
    start = 0
    page = min(100, max_results)
    cutoff = datetime.now(timezone.utc) - window
    while start < max_results:
        r = get(
            API,
            params={
                "search_query": q,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
                "start": start,
                "max_results": page,
            },
            timeout=60,
        )
        if r.status_code != 200:
            print(f"  [arxiv] HTTP {r.status_code}")
            break
        got = parse_arxiv_atom(r.text)
        if not got:
            break
        out.extend(got)
        # 停止条件：这一页最后一篇已经超出时间窗
        last_pub = got[-1].published
        try:
            if datetime.fromisoformat(last_pub).replace(tzinfo=timezone.utc) < cutoff:
                break
        except ValueError:
            pass
        start += page
        time.sleep(3)  # arXiv 要求 3s 间隔
    out = [
        it
        for it in out
        if it.published and datetime.fromisoformat(it.published).replace(tzinfo=timezone.utc) >= cutoff
    ]
    print(f"  [arxiv] {len(out)} papers within {window}")
    return out
