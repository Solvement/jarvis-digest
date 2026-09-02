"""把 arXiv 论文抓成 markdown + 图片，供 deep-read skill 使用。

用法：python scripts/fetch_paper.py 2608.31046
输出：notes/papers/assets/<id>/paper.md  和  notes/papers/assets/<id>/fig-*.png
依赖：pip install pymupdf requests
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    pid = re.sub(r"^.*?(\d{4}\.\d{4,5})(v\d+)?.*$", r"\1", sys.argv[1])
    out = ROOT / "notes" / "papers" / "assets" / pid
    out.mkdir(parents=True, exist_ok=True)
    pdf = out / "paper.pdf"
    if not pdf.exists():
        r = requests.get(f"https://arxiv.org/pdf/{pid}", timeout=60, headers={"User-Agent": "jarvis/0.1"})
        r.raise_for_status()
        pdf.write_bytes(r.content)
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("pip install pymupdf")
        sys.exit(1)
    doc = fitz.open(pdf)
    md: list[str] = [f"# arXiv:{pid}\n"]
    n_img = 0
    for i, page in enumerate(doc):
        md.append(f"\n\n<!-- page {i + 1} -->\n")
        md.append(page.get_text("text"))
        for j, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            try:
                pix = fitz.Pixmap(doc, xref)
                if pix.width < 200 or pix.height < 120:
                    continue
                if pix.n >= 5:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                n_img += 1
                fp = out / f"fig-p{i + 1}-{j + 1}.png"
                pix.save(fp)
                md.append(f"\n![fig p{i + 1}-{j + 1}]({fp.name})\n")
            except Exception:  # noqa: BLE001
                continue
    (out / "paper.md").write_text("".join(md), encoding="utf-8")
    print(f"wrote {out / 'paper.md'} ({len(doc)} pages, {n_img} figures)")


if __name__ == "__main__":
    main()
