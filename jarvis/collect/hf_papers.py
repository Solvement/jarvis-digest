"""Hugging Face Daily Papers —— 社区投票筛过一轮的论文，是最好的"热度"信号。"""
from __future__ import annotations

from datetime import date, timedelta

from ..models import Item
from .http import get

API = "https://huggingface.co/api/daily_papers"


def parse_hf_entries(entries: list[dict]) -> list[Item]:
    items: list[Item] = []
    for e in entries:
        p = e.get("paper") or e
        pid = str(p.get("id") or "").strip()
        if not pid:
            continue
        authors = []
        for a in p.get("authors") or []:
            if isinstance(a, dict):
                if a.get("name"):
                    authors.append(a["name"])
            elif isinstance(a, str):
                authors.append(a)
        items.append(
            Item(
                id=f"paper:{pid}",
                kind="paper",
                title=(p.get("title") or e.get("title") or "").strip(),
                url=f"https://arxiv.org/abs/{pid}",
                pdf_url=f"https://arxiv.org/pdf/{pid}",
                summary=(p.get("summary") or e.get("summary") or "").strip(),
                source="hf_papers",
                published=str(p.get("publishedAt") or e.get("publishedAt") or "")[:10],
                authors=authors[:6],
                hf_upvotes=int(p.get("upvotes") or 0),
                code_url=p.get("githubRepo") or "",
                stars=int(p.get("githubStars") or 0),
                keywords=list(p.get("ai_keywords") or [])[:10],
            )
        )
    return items


def collect_hf_papers(cfg: dict, today: date) -> list[Item]:
    days = int(cfg.get("days", 2))
    out: list[Item] = []
    for i in range(days):
        d = today - timedelta(days=i)
        r = get(API, params={"date": d.isoformat(), "limit": 100})
        if r.status_code != 200:
            print(f"  [hf_papers] {d}: HTTP {r.status_code}")
            continue
        got = parse_hf_entries(r.json())
        print(f"  [hf_papers] {d}: {len(got)} papers")
        out.extend(got)
    return out
