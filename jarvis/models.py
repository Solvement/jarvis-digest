"""统一的数据结构：一条候选（项目或论文）。"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class Item:
    id: str                      # 全局唯一：paper:2608.31046 / repo:owner/name
    kind: str                    # "paper" | "project"
    title: str
    url: str
    summary: str = ""            # 原始摘要 / README 描述（英文）
    source: str = ""             # hf_papers | arxiv | github_trending | github_search
    published: str = ""          # ISO 日期
    authors: list[str] = field(default_factory=list)
    org: str = ""                # 机构 / owner
    # 热度信号
    hf_upvotes: int = 0
    stars: int = 0
    stars_today: int = 0
    forks: int = 0
    language: str = ""
    code_url: str = ""
    pdf_url: str = ""
    categories: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    # LLM 打分
    core_score: float = 0.0
    wide_score: float = 0.0
    score_reason: str = ""
    tier: str = ""               # "core" | "wide"
    ptype: str = ""              # paper | skill | tutorial | tool | infra | model
    board: str = ""              # github trending: daily | weekly | monthly
    # 速览
    digest: dict[str, Any] = field(default_factory=dict)
    # 正文上下文（论文 Intro/Method 或 README），只用于生成速览，不写入输出
    context: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("context", None)
        return d

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Item":
        known = {f for f in Item.__dataclass_fields__}
        return Item(**{k: v for k, v in d.items() if k in known})

    @property
    def heat(self) -> float:
        """无 LLM 时的启发式热度，用于 dry-run 和粗排。"""
        if self.kind == "paper":
            return self.hf_upvotes * 3 + (self.stars ** 0.5 if self.stars else 0)
        return self.stars_today * 2 + self.stars ** 0.5
