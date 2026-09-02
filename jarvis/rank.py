"""去重 → 硬过滤 → LLM 打分 → 分档选择。"""
from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path

from .llm import LLM
from .models import Item

# 用于 arXiv 粗排的关键词（只在候选过多时用来截断，不做最终判断）
_HOT_WORDS = [
    "llm", "language model", "agent", "agentic", "rag", "retrieval", "reasoning", "reinforcement",
    "rlhf", "dpo", "grpo", "distillation", "multimodal", "vision-language", "vlm", "diffusion",
    "video", "generation", "moe", "mixture of experts", "attention", "kv cache", "quantization",
    "speculative", "inference", "pretraining", "scaling", "benchmark", "tool", "planning", "memory",
    "embodied", "robot", "vla", "long context", "lora", "fine-tuning", "alignment", "safety",
]

_NOISE_REPO = re.compile(
    r"awesome|roadmap|interview|cheatsheet|cheat-sheet|tutorial|course|book|wallpaper|theme|icon|font|"
    r"dotfiles|leetcode|algorithm-visual|template|boilerplate|starter",
    re.I,
)


# ---------------------------------------------------------------- dedupe
def dedupe(items: list[Item]) -> list[Item]:
    merged: dict[str, Item] = {}
    for it in items:
        if it.id in merged:
            a = merged[it.id]
            # 合并信号：HF 的 upvotes、arXiv 的分类、任一方的代码链接
            a.hf_upvotes = max(a.hf_upvotes, it.hf_upvotes)
            a.stars = max(a.stars, it.stars)
            a.code_url = a.code_url or it.code_url
            a.categories = a.categories or it.categories
            a.keywords = a.keywords or it.keywords
            a.summary = a.summary if len(a.summary) >= len(it.summary) else it.summary
            if it.source == "hf_papers":
                a.source = "hf_papers"
            if it.source == "github_trending":
                a.source = "github_trending"
            order = {"daily": 0, "weekly": 1, "monthly": 2}
            if it.board and (not a.board or order.get(it.board, 9) < order.get(a.board, 9)):
                a.board, a.stars_today = it.board, it.stars_today   # 涨星数跟最短周期的榜走
            elif not a.board and not it.board:
                a.stars_today = max(a.stars_today, it.stars_today)
        else:
            merged[it.id] = it
    return list(merged.values())


# ---------------------------------------------------------------- seen state
def load_seen(state_dir: Path, keep_days: int, today: date) -> dict[str, str]:
    p = state_dir / "seen.json"
    if not p.exists():
        return {}
    seen = json.loads(p.read_text(encoding="utf-8"))
    cutoff = (today - timedelta(days=keep_days)).isoformat()
    return {k: v for k, v in seen.items() if cutoff <= v < today.isoformat()}


def save_seen(state_dir: Path, seen: dict[str, str]) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "seen.json").write_text(json.dumps(seen, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")


# ---------------------------------------------------------------- hard filter
def hard_filter(items: list[Item], f: dict, seen: dict[str, str]) -> list[Item]:
    out = []
    for it in items:
        if it.id in seen:
            continue
        if it.kind == "project":
            if _NOISE_REPO.search(it.title) or _NOISE_REPO.search(it.summary[:80]):
                continue
            if it.stars < f.get("repo_min_total_stars", 200):
                continue
            if it.source == "github_trending":
                need = {"daily": f.get("repo_min_today_stars", 30), "weekly": f.get("repo_min_week_stars", 300),
                        "monthly": f.get("repo_min_month_stars", 1000)}.get(it.board or "daily", 30)
                if it.stars_today < need:
                    continue
            if not it.summary:
                continue
        else:
            if not it.summary or len(it.title) < 8:
                continue
        out.append(it)
    return out


def _keyword_hits(it: Item) -> int:
    t = (it.title + " " + it.summary[:600]).lower()
    return sum(1 for w in _HOT_WORDS if w in t)


def cap_candidates(items: list[Item], max_arxiv: int) -> list[Item]:
    """arXiv 候选过多时，HF 论文与项目全留，纯 arXiv 按关键词粗排截断。"""
    keep = [it for it in items if not (it.kind == "paper" and it.source == "arxiv")]
    arx = [it for it in items if it.kind == "paper" and it.source == "arxiv"]
    arx.sort(key=_keyword_hits, reverse=True)
    return keep + arx[:max_arxiv]


# ---------------------------------------------------------------- LLM scoring
SCORE_SYSTEM = """你是一位资深 AI 研究员，替一名研二学生筛选每日情报。
你会拿到他的兴趣画像和一批候选（论文或开源项目）。对每条给出：
- core_score (1-10)：与他"核心方向"的相关性 × 质量/重要性。10 = 必读；6 = 值得看一眼；≤3 = 无关或质量差。
- wide_score (1-10)：不考虑方向，这条在整个 AI 圈的热度/重要性。旗舰发布、新范式、破圈项目给高分。
- tags：2-4 个英文短标签（小写，如 "agent", "rl", "diffusion", "inference", "moe", "benchmark", "vlm"）。
- reason：不超过 30 字的中文理由。
原则：热度（star / upvote）只是注意力信号，不是质量信号；分数看的是对读者有没有用。
严格判断"减分项"：与 AI 无关的项目、awesome 列表、教程合集、套壳客户端、纯 UI 模板 core 和 wide 都给 ≤2。
每条给 is_ai（true/false）：是否属于 AI / ML / LLM / agent / 数据与模型基础设施范畴。不是的一律 false（例如通用 API 列表、浏览器、桌面工具、游戏）。
项目额外给 ptype：skill（给 agent 用的 skill/prompt 包）/ tutorial（教学）/ tool（工具/应用）/ infra（框架/运行时/训练推理基础设施）/ model（模型或权重发布）。论文填 "paper"。
只输出 JSON：{"scores": [{"id": "...", "is_ai": true, "core_score": n, "wide_score": n, "ptype": "...", "tags": [...], "reason": "..."}]}"""


def _fmt_candidate(it: Item) -> str:
    meta = []
    if it.kind == "paper":
        if it.hf_upvotes:
            meta.append(f"HF upvotes={it.hf_upvotes}")
        if it.code_url:
            meta.append(f"code={it.code_url} stars={it.stars}")
        if it.categories:
            meta.append("cats=" + ",".join(it.categories[:3]))
    else:
        meta.append(f"stars={it.stars} today+{it.stars_today} lang={it.language}")
        if it.keywords:
            meta.append("topics=" + ",".join(it.keywords[:6]))
    return f"[{it.id}] ({it.kind}) {it.title}\n  {'; '.join(meta)}\n  {it.summary[:700]}"


def _apply_scores(batch: list[Item], data: dict) -> list[Item]:
    """把 LLM 返回写回条目，返回没匹配上的条目。"""
    by_id: dict[str, dict] = {}
    for sc in data.get("scores", []):
        if isinstance(sc, dict) and sc.get("id"):
            by_id[str(sc["id"]).strip().lower()] = sc
    missing: list[Item] = []
    for it in batch:
        sc = by_id.get(it.id.lower()) or by_id.get(it.id.split(":", 1)[1].lower())
        if not sc:
            missing.append(it)
            continue
        it.core_score = float(sc.get("core_score", 0) or 0)
        it.wide_score = float(sc.get("wide_score", 0) or 0)
        if sc.get("is_ai") is False:
            it.core_score = min(it.core_score, 2.0)
            it.wide_score = min(it.wide_score, 2.0)
        it.keywords = [str(t) for t in (sc.get("tags") or [])][:4] or it.keywords
        it.score_reason = str(sc.get("reason", ""))[:60]
        if it.kind == "project":
            it.ptype = str(sc.get("ptype", "") or "")
    return missing


def llm_score(items: list[Item], llm: LLM, interests: str, batch_size: int) -> None:
    def run(batch: list[Item]) -> list[Item]:
        user = "## 兴趣画像\n" + interests + "\n\n## 候选\n" + "\n\n".join(_fmt_candidate(it) for it in batch)
        try:
            return _apply_scores(batch, llm.json(llm.score_model, SCORE_SYSTEM, user))
        except Exception as e:  # noqa: BLE001
            print(f"  [score] batch of {len(batch)} failed: {e}")
            return list(batch)

    leftover: list[Item] = []
    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]
        leftover += run(batch)
        print(f"  [score] batch {i // batch_size + 1}: {len(batch) - len(leftover)} scored so far")
    # 没匹配/失败的条目：小批重试一次；仍失败则启发式打分并封顶，保证不会因为没经过 LLM 判断而混进日报
    if leftover:
        print(f"  [score] retrying {len(leftover)} unscored in small batches")
        still: list[Item] = []
        for i in range(0, len(leftover), 5):
            still += run(leftover[i : i + 5])
        if still:
            heuristic_score(still)
            for it in still:
                it.core_score = min(it.core_score, 4.0)
                it.wide_score = min(it.wide_score, 4.0)
                it.score_reason = "LLM 未打分（已封顶，不入选）"
            print(f"  [score] {len(still)} items capped after fallback")


def heuristic_score(items: list[Item]) -> None:
    """无 key 时的启发式：热度 + 关键词命中。"""
    for it in items:
        hits = _keyword_hits(it)
        heat = it.heat
        import math
        it.core_score = round(min(10.0, 2 + hits * 0.7 + math.log1p(heat) * 0.5), 1)
        it.wide_score = round(min(10.0, 1 + math.log1p(heat) * 0.9), 1)
        it.score_reason = "启发式打分（无 API key）"
        if not it.keywords:
            it.keywords = [w for w in _HOT_WORDS if w in (it.title + it.summary[:300]).lower()][:3]


# ---------------------------------------------------------------- selection
def select(items: list[Item], r: dict) -> list[Item]:
    min_core = float(r.get("core_min_score", 6))
    papers = sorted([i for i in items if i.kind == "paper"], key=lambda x: (x.core_score, x.heat), reverse=True)
    projects = sorted([i for i in items if i.kind == "project"], key=lambda x: (x.core_score, x.heat), reverse=True)
    chosen: list[Item] = []
    for it in papers[: r.get("papers_core", 8)]:
        if it.core_score >= min_core:
            it.tier = "core"
            chosen.append(it)
    for it in projects[: r.get("projects_core", 6)]:
        if it.core_score >= min_core:
            it.tier = "core"
            chosen.append(it)
    chosen_ids = {c.id for c in chosen}
    rest = sorted([i for i in items if i.id not in chosen_ids], key=lambda x: (x.wide_score, x.heat), reverse=True)
    for it in rest[: r.get("wide", 4)]:
        if it.wide_score >= 5:
            it.tier = "wide"
            chosen.append(it)
    return chosen
