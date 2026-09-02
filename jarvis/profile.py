"""读取 profile/ 下的兴趣画像与已掌握概念。"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_LINE = re.compile(r"^\s*-\s*\[( |x|X)\]\s*(.+?)\s*$")


@dataclass
class Concept:
    name: str
    aliases: list[str]
    known: bool

    def matches(self, text: str) -> bool:
        t = text.lower()
        for a in [self.name, *self.aliases]:
            a = a.lower().strip()
            if a and a in t:
                return True
        return False


def load_interests(profile_dir: Path) -> str:
    p = profile_dir / "interests.md"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def load_concepts(profile_dir: Path) -> list[Concept]:
    p = profile_dir / "known.md"
    if not p.exists():
        return []
    out: list[Concept] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        m = _LINE.match(line)
        if not m:
            continue
        checked = m.group(1).lower() == "x"
        body = m.group(2)
        name, _, alias_str = body.partition("|")
        aliases = [a.strip() for a in alias_str.split(",") if a.strip()]
        out.append(Concept(name=name.strip(), aliases=aliases, known=checked))
    return out


def classify_prereqs(prereqs: list[str], concepts: list[Concept]) -> list[dict]:
    """把 LLM 给出的前置概念对照 known.md，标记 known / unknown / unlisted。"""
    out = []
    for pr in prereqs:
        status = "unlisted"
        for c in concepts:
            if c.matches(pr) or pr.lower() in (c.name.lower(), *[a.lower() for a in c.aliases]):
                status = "known" if c.known else "unknown"
                break
        out.append({"name": pr, "status": status})
    return out
