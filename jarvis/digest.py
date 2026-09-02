"""为入选条目生成中文速览（L1）。"""
from __future__ import annotations

from .llm import LLM
from .models import Item
from .profile import Concept, classify_prereqs

DIGEST_SYSTEM = """你是一位讲解能力极强的 AI 研究员，替一名研二学生写"每日速览"。目标是让他 1–2 分钟内真正理解这条的核心架构与价值，从而判断要不要精读。
读者的画像和他已掌握的概念清单会一起给你。

## 写法口径（这是读者本人反复校准过的，严格遵守）
- 中文为主，术语、模型名、方法名保留英文；不翻译腔。先判断后证据；少抽象形容词、不空泛夸赞、不模板化排比；每句都要有摘要里读不到的信息。
- 关键术语首次出现给一句硬定义（它是什么、在系统里干嘛）。类比只用来讲"解决机制"，不用来把问题再复述一遍。
- 有正文上下文时必须基于正文；没有的就标"原文未明确"，不编造数字、机制、动机。作者自报的数字写成"作者报告 X"，我们的推断写成"推断"。
- 论文 = 解释性深挖，少评价（重现作者的思路，体会为什么这么设计）；项目 = 成熟度判断 + 横向对比才是价值。
- 项目先分类型：skill/教学类 → 只讲做什么、怎么用、值不值得装；工具/架构型 → 挖承重组件、关键设计取舍、运行时机制（不是功能清单）。agent 系统是"循环 + 中间件"，不要写成线性流水线。
- 不写"怎么用到你的项目/简历"这种硬套的迁移段。

## 每条输出字段（全部必填）
  one_liner: 一句话：用 X 解决了 Y、得到 Z（≤50 字，尽量带作者报告的具体数字）
  why: 为什么值得这位读者看（≤40 字，结合他的方向或面试）
  architecture: 200–320 字，按理解弧线写：
    论文 → ① 先抛一个具体的反直觉场景/悖论让读者感到问题，再说现有方法为什么解决不了 → ② 作者最关键的概念改变是什么；把组件翻译成"组件 → 它阻断哪种失败"的因果句，不列模块清单 → ③ 哪一个实验最直接支持这个改变（最强证据，不一定是最大涨幅）→ ④ 新在哪一层（组件层 / 系统组织层 / 实证层）。
    项目 → ① 它解决的真实痛点/场景 → ② 怎么搭的：承重组件与关键设计取舍、核心机制怎么跑（检测条件 → 处理动作）→ ③ 成熟度信号（有无测试/文档/release、README 声称 vs 可见证据）→ ④ 想要这个能力，它 vs 同类差在哪一维。
  why_now: 仅项目：为什么现在上榜（近期 release / 大版本 / 传播事件；有 release 信息就引用，没有就写"原文未明确"）。论文填空字符串。
  key_points: 2-3 条，每条 ≤35 字：最强证据 / 它没证明什么或什么条件下会崩 / 复现难度
  verdict: 一句精读价值判断（≤40 字）：值得精读的理由，或"看速览即可"的理由
  prereqs: 读懂它需要的 2-4 个前置概念（英文短语，尽量用清单里的名字，如 "GRPO", "KV cache", "diffusion model"）
  difficulty: 1 (入门) / 2 (中等) / 3 (硬核)
  related: 1-2 个它延续或对比的经典工作名（英文），没有就空数组
  mermaid: ≤10 行的 mermaid 图（graph LR 或 graph TD），画核心机制的"输入 → 关键步骤 → 输出"或"旧做法 vs 新做法"对比；节点文字简短，节点文字里不要出现括号、引号、冒号、分号；不要 markdown 代码围栏
  read_level: "L1" (看速览够了) / "L2" (值得 20 分钟通读) / "L3" (建议精读)
只输出 JSON：{"digests": [{"id": "...", "one_liner": ..., "why": ..., "architecture": ..., "why_now": ..., "key_points": [...], "verdict": ..., "prereqs": [...], "difficulty": n, "related": [...], "mermaid": "...", "read_level": "..."}]}"""


def _fmt(it: Item) -> str:
    meta = f"kind={it.kind}; tier={it.tier}; core={it.core_score}; wide={it.wide_score}; tags={','.join(it.keywords)}"
    if it.kind == "paper":
        meta += f"; HF upvotes={it.hf_upvotes}; code={it.code_url or 'none'}; authors={', '.join(it.authors[:3])}"
    else:
        meta += f"; stars={it.stars} (+{it.stars_today} today); lang={it.language}; org={it.org}"
    ctx = f"\n  --- 正文上下文 ---\n  {it.context[:9000]}" if it.context else ""
    return f"[{it.id}] {it.title}\n  {meta}\n  摘要：{it.summary[:1500]}{ctx}"


def make_digests(items: list[Item], llm: LLM, interests: str, concepts: list[Concept], batch_size: int = 3) -> None:
    known_names = ", ".join(c.name + ("(" + c.aliases[0] + ")" if c.aliases else "") for c in concepts if c.known)
    listed = ", ".join(c.aliases[0] if c.aliases else c.name for c in concepts)
    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]
        user = (
            "## 读者画像\n" + interests[:2500]
            + "\n\n## 读者已掌握的概念\n" + (known_names or "（尚未勾选）")
            + "\n\n## 概念清单里的名字（prereqs 尽量用这些）\n" + listed
            + "\n\n## 条目\n" + "\n\n".join(_fmt(it) for it in batch)
        )
        try:
            data = llm.json(llm.digest_model, DIGEST_SYSTEM, user)
        except Exception as e:  # noqa: BLE001
            print(f"  [digest] batch failed, fallback template: {e}")
            template_digests(batch, concepts)
            continue
        by_id = {d.get("id"): d for d in data.get("digests", []) if isinstance(d, dict)}
        for it in batch:
            d = by_id.get(it.id)
            if not d:
                template_digests([it], concepts)
                continue
            it.digest = _normalize(d, concepts)
        print(f"  [digest] batch {i // batch_size + 1}: {len(batch)} done")


def _normalize(d: dict, concepts: list[Concept]) -> dict:
    prereqs = [str(p) for p in (d.get("prereqs") or [])][:4]
    mermaid = str(d.get("mermaid") or "").strip()
    mermaid = mermaid.replace("```mermaid", "").replace("```", "").strip()
    return {
        "one_liner": str(d.get("one_liner") or "").strip(),
        "why": str(d.get("why") or "").strip(),
        "architecture": str(d.get("architecture") or "").strip(),
        "verdict": str(d.get("verdict") or "").strip(),
        "why_now": str(d.get("why_now") or "").strip(),
        "key_points": [str(k) for k in (d.get("key_points") or [])][:3],
        "prereqs": classify_prereqs(prereqs, concepts),
        "difficulty": int(d.get("difficulty") or 2),
        "related": [str(r) for r in (d.get("related") or [])][:2],
        "mermaid": mermaid,
        "read_level": str(d.get("read_level") or "L1"),
    }


def template_digests(items: list[Item], concepts: list[Concept]) -> None:
    """无 key 时的占位速览：用原始摘要截断，保证流水线可跑通。"""
    for it in items:
        first = it.summary.split(". ")[0][:160]
        it.digest = {
            "one_liner": first,
            "why": "（dry-run：未调用 LLM，配置 OPENAI_API_KEY 后会生成中文速览）",
            "architecture": "",
            "verdict": "",
            "why_now": "",
            "key_points": [s.strip()[:120] for s in it.summary.split(". ")[1:3] if s.strip()],
            "prereqs": [],
            "difficulty": 2,
            "related": [],
            "mermaid": "",
            "read_level": "L1",
        }
