from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent


def load_config(path: Path | None = None) -> dict[str, Any]:
    p = path or ROOT / "config.yml"
    with open(p, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    # 环境变量覆盖模型名，方便在 Actions 里切换
    llm = cfg.setdefault("llm", {})
    if os.getenv("JARVIS_SCORE_MODEL"):
        llm["score_model"] = os.environ["JARVIS_SCORE_MODEL"]
    if os.getenv("JARVIS_DIGEST_MODEL"):
        llm["digest_model"] = os.environ["JARVIS_DIGEST_MODEL"]
    return cfg


def paths() -> dict[str, Path]:
    return {
        "root": ROOT,
        "data": ROOT / "data",
        "digests": ROOT / "digests",
        "docs": ROOT / "docs",
        "docs_data": ROOT / "docs" / "data",
        "state": ROOT / "state",
        "profile": ROOT / "profile",
        "fixtures": ROOT / "tests" / "fixtures",
    }
