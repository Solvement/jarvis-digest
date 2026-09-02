"""python -m jarvis run [--date YYYY-MM-DD] [--fixtures] [--no-llm]"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from zoneinfo import ZoneInfo

from .collect import collect_arxiv, collect_github, collect_hf_papers
from .collect.arxiv import parse_arxiv_atom
from .collect.github import parse_trending_html
from .collect.hf_papers import parse_hf_entries
from .config import load_config, paths
from .digest import make_digests, template_digests
from .enrich import enrich
from .llm import LLM
from .models import Item
from .profile import load_concepts, load_interests
from .rank import cap_candidates, dedupe, hard_filter, heuristic_score, llm_score, load_seen, save_seen, select
from .render import write_outputs


def _load_fixtures(p) -> list[Item]:
    fx = p["fixtures"]
    items: list[Item] = []
    f = fx / "hf_daily_papers.json"
    if f.exists():
        items += parse_hf_entries(json.loads(f.read_text(encoding="utf-8")))
    f = fx / "arxiv.xml"
    if f.exists():
        items += parse_arxiv_atom(f.read_text(encoding="utf-8"))
    f = fx / "github_trending.html"
    if f.exists():
        items += parse_trending_html(f.read_text(encoding="utf-8"))
    f = fx / "github_search.json"
    if f.exists():
        for repo in json.loads(f.read_text(encoding="utf-8")).get("items", []):
            items.append(
                Item(
                    id=f"repo:{repo['full_name'].lower()}", kind="project", title=repo["full_name"],
                    url=repo["html_url"], summary=repo.get("description") or "", source="github_search",
                    org=repo["owner"]["login"], stars=repo.get("stargazers_count", 0),
                    language=repo.get("language") or "", code_url=repo["html_url"],
                    keywords=list(repo.get("topics") or [])[:8],
                )
            )
    print(f"  [fixtures] {len(items)} items")
    return items


def run(args: argparse.Namespace) -> None:
    cfg = load_config()
    p = paths()
    tz = ZoneInfo(cfg.get("timezone", "America/New_York"))
    today = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else datetime.now(tz).date()
    print(f"== Jarvis run for {today} ==")

    # 1. collect
    print("[1/4] collect")
    src = cfg.get("sources", {})
    items: list[Item] = []
    if args.fixtures:
        items = _load_fixtures(p)
    else:
        items += collect_github(src)
        if src.get("hf_papers", {}).get("enabled", True):
            try:
                items += collect_hf_papers(src.get("hf_papers", {}), today)
            except Exception as e:  # noqa: BLE001
                print(f"  [hf_papers] failed: {e}")
        if src.get("arxiv", {}).get("enabled", True):
            try:
                items += collect_arxiv(src.get("arxiv", {}))
            except Exception as e:  # noqa: BLE001
                print(f"  [arxiv] failed: {e}")
    collected = len(items)

    # 2. dedupe + filter
    print("[2/4] dedupe + filter")
    items = dedupe(items)
    seen = load_seen(p["state"], cfg["filters"].get("seen_days", 14), today)
    items = hard_filter(items, cfg["filters"], seen)
    items = cap_candidates(items, cfg["llm"].get("max_arxiv_to_score", 150))
    filtered = len(items)
    print(f"  {collected} collected → {filtered} candidates ({len([i for i in items if i.kind=='paper'])} papers, {len([i for i in items if i.kind=='project'])} projects)")

    # 3. score + select
    print("[3/4] score + select")
    interests = load_interests(p["profile"])
    concepts = load_concepts(p["profile"])
    llm = LLM(cfg["llm"])
    use_llm = llm.available and not args.no_llm
    if use_llm:
        llm_score(items, llm, interests, cfg["llm"].get("score_batch_size", 20))
    else:
        print("  no OPENAI_API_KEY (or --no-llm): heuristic scoring")
        heuristic_score(items)
    chosen = select(items, cfg["ranking"])
    print(f"  selected {len(chosen)}: " + ", ".join(f"{c.tier}/{c.kind}" for c in chosen))

    # 4. digest + write
    print("[4/4] digest + write")
    if use_llm:
        if not args.fixtures:
            enrich(chosen)
        make_digests(chosen, llm, interests, concepts)
    else:
        template_digests(chosen, concepts)
    stats = {"collected": collected, "filtered": filtered, "selected": len(chosen), "llm": llm.report()}
    write_outputs(today, chosen, stats, p, cfg.get("site", {}))
    if not args.fixtures:
        for c in chosen:
            seen[c.id] = today.isoformat()
        save_seen(p["state"], seen)
    print("  " + llm.report())
    print(f"  wrote digests/{today}.md, data/{today}.json, docs/data/{today}.json")


def main() -> None:
    ap = argparse.ArgumentParser(prog="jarvis")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="采集 → 打分 → 日报")
    r.add_argument("--date", help="YYYY-MM-DD（默认今天，按 config.timezone）")
    r.add_argument("--fixtures", action="store_true", help="用 tests/fixtures 代替联网采集")
    r.add_argument("--no-llm", action="store_true", help="强制不用 LLM（启发式打分 + 模板速览）")
    args = ap.parse_args()
    if args.cmd == "run":
        run(args)


if __name__ == "__main__":
    main()
