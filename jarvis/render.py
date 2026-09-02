"""输出：digests/YYYY-MM-DD.md（Obsidian）+ docs/data/*.json（网页）。"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from .models import Item

_DIFF = {1: "入门", 2: "中等", 3: "硬核"}
_LEVEL = {"L1": "看速览即可", "L2": "值得通读 (20 min)", "L3": "建议精读"}


def _prereq_md(prs: list[dict]) -> str:
    parts = []
    for p in prs:
        if p["status"] == "known":
            parts.append(f"✅ {p['name']}")
        elif p["status"] == "unknown":
            parts.append(f"🔲 [[{p['name']}]]")
        else:
            parts.append(f"◽ {p['name']}")
    return " · ".join(parts)


def _item_md(n: int, it: Item) -> str:
    d = it.digest
    icon = "📄" if it.kind == "paper" else "🧰"
    star = "⭐ " if it.tier == "core" else "🌐 "
    lines = [f"### {n}. {star}{icon} {it.title}"]
    meta = []
    if it.kind == "paper":
        pid = it.id.split(":", 1)[1]
        meta.append(f"arXiv [{pid}]({it.url})")
        if it.hf_upvotes:
            meta.append(f"HF 🔥 {it.hf_upvotes}")
        if it.authors:
            meta.append(", ".join(it.authors[:3]) + (" 等" if len(it.authors) > 3 else ""))
        meta.append(f"[PDF]({it.pdf_url})")
        if it.code_url:
            meta.append(f"[代码]({it.code_url})" + (f" ★{it.stars}" if it.stars else ""))
    else:
        period = {"daily": "今日", "weekly": "本周", "monthly": "本月"}.get(it.board, "近期")
        meta.append(f"[GitHub]({it.url}) ★{it.stars:,}" + (f" (+{it.stars_today} {period})" if it.stars_today else ""))
        if it.board:
            meta.append(f"Trending {it.board}")
        if it.ptype and it.ptype != "paper":
            meta.append(it.ptype)
        if it.language:
            meta.append(it.language)
    lines.append(" · ".join(meta))
    lines.append("")
    if d.get("one_liner"):
        lines.append(f"**一句话**：{d['one_liner']}")
    if d.get("why"):
        lines.append(f"**为什么值得你看**：{d['why']}")
    if d.get("architecture"):
        lines.append("")
        lines.append(f"**核心架构**：{d['architecture']}")
        lines.append("")
    for k in d.get("key_points", []):
        lines.append(f"- {k}")
    if d.get("why_now"):
        lines.append(f"**为什么现在上榜**：{d['why_now']}")
    if d.get("verdict"):
        lines.append(f"**精读价值**：{d['verdict']}")
    if d.get("related"):
        lines.append("**关联**：" + "、".join(f"[[{r}]]" for r in d["related"]))
    tail = []
    if it.keywords:
        tail.append(" ".join(f"#{k.replace(' ', '-')}" for k in it.keywords[:4]))
    tail.append(f"难度：{_DIFF.get(d.get('difficulty', 2), '中等')}")
    tail.append(f"建议：{_LEVEL.get(d.get('read_level', 'L1'), '看速览即可')}")
    lines.append(" · ".join(tail))
    if d.get("prereqs"):
        lines.append(f"前置：{_prereq_md(d['prereqs'])}")
    if d.get("mermaid"):
        lines += ["", "```mermaid", d["mermaid"], "```"]
    if it.score_reason:
        lines.append(f"<sub>打分理由：{it.score_reason}（core {it.core_score:.0f} / wide {it.wide_score:.0f}）</sub>")
    return "\n".join(lines) + "\n"


def render_markdown(today: date, items: list[Item], stats: dict) -> str:
    core_p = [i for i in items if i.tier == "core" and i.kind == "paper"]
    core_r = [i for i in items if i.tier == "core" and i.kind == "project"]
    wide = [i for i in items if i.tier == "wide"]
    out = [
        "---",
        f"date: {today.isoformat()}",
        "type: daily-digest",
        f"papers: {len([i for i in items if i.kind == 'paper'])}",
        f"projects: {len([i for i in items if i.kind == 'project'])}",
        "---",
        "",
        f"# Jarvis 日报 · {today.isoformat()}",
        "",
        f"候选 {stats.get('collected', 0)} → 过滤后 {stats.get('filtered', 0)} → 入选 {len(items)}。"
        "图例：⭐ 核心方向 · 🌐 全领域热点 · ✅ 已掌握前置 · 🔲 需补前置",
        "",
    ]
    n = 1
    if core_p:
        out.append("## 📄 论文 · 核心方向\n")
        for it in core_p:
            out.append(_item_md(n, it))
            n += 1
    if core_r:
        out.append("## 🧰 项目 · 核心方向\n")
        for it in core_r:
            out.append(_item_md(n, it))
            n += 1
    if wide:
        out.append("## 🌐 全领域热点\n")
        for it in wide:
            out.append(_item_md(n, it))
            n += 1
    out.append("---")
    out.append("想精读哪一篇？在 Claude 里说：`精读 " + today.isoformat() + " 第 N 条`，Jarvis 会按你的 known.md 只讲你不会的部分。")
    return "\n".join(out)


def write_outputs(today: date, items: list[Item], stats: dict, p: dict[str, Path], site_cfg: dict) -> None:
    ds = today.isoformat()
    p["digests"].mkdir(parents=True, exist_ok=True)
    p["data"].mkdir(parents=True, exist_ok=True)
    p["docs_data"].mkdir(parents=True, exist_ok=True)

    (p["digests"] / f"{ds}.md").write_text(render_markdown(today, items, stats), encoding="utf-8")

    payload = {"date": ds, "stats": stats, "items": [it.to_dict() for it in items]}
    js = json.dumps(payload, ensure_ascii=False, indent=1)
    (p["data"] / f"{ds}.json").write_text(js, encoding="utf-8")
    (p["docs_data"] / f"{ds}.json").write_text(js, encoding="utf-8")

    # index.json：所有日期 + 计数（网页用）
    index = []
    for f in sorted(p["docs_data"].glob("????-??-??.json"), reverse=True):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        its = d.get("items", [])
        index.append(
            {
                "date": d.get("date", f.stem),
                "papers": len([i for i in its if i.get("kind") == "paper"]),
                "projects": len([i for i in its if i.get("kind") == "project"]),
                "top": (its[0]["title"] if its else ""),
            }
        )
    (p["docs_data"] / "index.json").write_text(
        json.dumps({"site": site_cfg, "days": index}, ensure_ascii=False, indent=1), encoding="utf-8"
    )
