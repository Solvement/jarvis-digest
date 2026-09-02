"""为入选条目补充正文上下文，让速览有深度：论文取 arXiv HTML 的引言+方法开头，项目取 README。"""
from __future__ import annotations

import base64
import html as _html
import os
import re

from .collect.http import get
from .models import Item

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"[ \t]+")
_NL = re.compile(r"\n{3,}")


def _clean(text: str) -> str:
    text = _html.unescape(_TAG.sub(" ", text))
    text = _WS.sub(" ", text)
    text = "\n".join(line.strip() for line in text.splitlines())
    return _NL.sub("\n\n", text).strip()


def paper_context(it: Item, max_chars: int = 9000) -> str:
    """arXiv HTML 版（有的论文没有，则退回摘要）。取摘要之后的 max_chars 个字符，通常覆盖 Intro + Method 开头。"""
    pid = it.id.split(":", 1)[1]
    for url in (f"https://arxiv.org/html/{pid}v1", f"https://arxiv.org/html/{pid}"):
        try:
            r = get(url, timeout=25, retries=1)
        except Exception:  # noqa: BLE001
            continue
        if r.status_code != 200 or "ltx_page_main" not in r.text:
            continue
        body = r.text
        m = re.search(r"<div[^>]*class=\"ltx_page_main\"[^>]*>", body)
        if m:
            body = body[m.end():]
        body = re.sub(r"<(script|style|math|svg)[^>]*>.*?</\1>", " ", body, flags=re.S | re.I)
        text = _clean(body)
        # 去掉参考文献之后的内容
        cut = re.search(r"\n(References|REFERENCES|Bibliography)\n", text)
        if cut:
            text = text[: cut.start()]
        return text[:max_chars]
    return ""


def readme_context(it: Item, max_chars: int = 7000) -> str:
    m = re.match(r"https?://github\.com/([^/]+)/([^/#?]+)", it.code_url or it.url)
    if not m:
        return ""
    owner, repo = m.group(1), m.group(2).removesuffix(".git")
    headers = {"Accept": "application/vnd.github+json"}
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        r = get(f"https://api.github.com/repos/{owner}/{repo}/readme", headers=headers, timeout=20, retries=1)
        if r.status_code != 200:
            return ""
        content = base64.b64decode(r.json().get("content", "")).decode("utf-8", errors="ignore")
    except Exception:  # noqa: BLE001
        return ""
    release = ""
    try:
        rr = get(f"https://api.github.com/repos/{owner}/{repo}/releases?per_page=3", headers=headers, timeout=15, retries=1)
        if rr.status_code == 200 and rr.json():
            rel = rr.json()
            release = "最近 release：" + "; ".join(
                f"{r.get('tag_name')}（{(r.get('published_at') or '')[:10]}）" for r in rel[:3]
            ) + "\n" + (rel[0].get("body") or "")[:800] + "\n\n"
    except Exception:  # noqa: BLE001
        pass
    # 去掉徽章、HTML 标签、图片
    content = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", content)
    content = re.sub(r"<[^>]+>", " ", content)
    content = re.sub(r"\[!\[.*?\]\(.*?\)\]\(.*?\)", "", content)
    content = _NL.sub("\n\n", content)
    return (release + content.strip())[:max_chars]


def enrich(items: list[Item]) -> None:
    for it in items:
        try:
            ctx = paper_context(it) if it.kind == "paper" else readme_context(it)
        except Exception as e:  # noqa: BLE001
            print(f"  [enrich] {it.id}: {e}")
            ctx = ""
        it.context = ctx
        print(f"  [enrich] {it.id}: {len(ctx)} chars")
