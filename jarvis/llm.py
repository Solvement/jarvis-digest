"""OpenAI 封装：JSON 输出、重试、成本统计。没有 key 时返回 None（走 dry-run）。"""
from __future__ import annotations

import json
import os
import time
from typing import Any


class LLM:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.score_model = cfg.get("score_model", "gpt-5.4-nano")
        self.digest_model = cfg.get("digest_model", "gpt-5.4-mini")
        self.usage: dict[str, dict[str, int]] = {}
        key = os.getenv("OPENAI_API_KEY")
        self.client = None
        if key:
            from openai import OpenAI

            self.client = OpenAI(api_key=key, base_url=os.getenv("OPENAI_BASE_URL") or None)

    @property
    def available(self) -> bool:
        return self.client is not None

    def json(self, model: str, system: str, user: str, *, retries: int = 3) -> Any:
        assert self.client is not None
        last: Exception | None = None
        for i in range(retries):
            try:
                resp = self.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                    response_format={"type": "json_object"},
                )
                u = resp.usage
                if u:
                    acc = self.usage.setdefault(model, {"prompt": 0, "completion": 0, "calls": 0})
                    acc["prompt"] += u.prompt_tokens or 0
                    acc["completion"] += u.completion_tokens or 0
                    acc["calls"] += 1
                text = resp.choices[0].message.content or "{}"
                return json.loads(text)
            except Exception as e:  # noqa: BLE001
                last = e
                print(f"  [llm] {model} attempt {i + 1} failed: {e}")
                time.sleep(2 * (i + 1))
        raise RuntimeError(f"LLM call failed after {retries} tries: {last}")

    def report(self) -> str:
        if not self.usage:
            return "LLM: 未调用（dry-run）"
        parts = [f"{m}: {u['calls']} calls, {u['prompt']} in / {u['completion']} out" for m, u in self.usage.items()]
        return "LLM usage — " + "; ".join(parts)
