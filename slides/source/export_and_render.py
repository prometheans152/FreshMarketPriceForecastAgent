# -*- coding: utf-8 -*-
"""匯出 PDF＋逐頁 PNG（D44-R06 v2 參數化）。

執行範例：
  .venv/Scripts/python.exe slides/source/export_and_render.py \
    --pptx slides/TW01_菜價預測_研究提案與初步成果_v2.pptx \
    --render outputs/proposal_delivery/run2_20261004_01/slides_render_v2
安全：以 Dispatch 開啟 PowerPoint、只 Close 本輪開的簡報、最後 Quit 本輪應用實例；未指定 --force 時拒絕覆寫既有輸出。
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pptx", required=True)
    ap.add_argument("--pdf", default=None, help="預設同 pptx 路徑換 .pdf")
    ap.add_argument("--render", required=True, help="逐頁 PNG 輸出目錄")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    pptx = Path(args.pptx).resolve()
    pdf = (Path(args.pdf) if args.pdf else pptx.with_suffix(".pdf")).resolve()
    render = Path(args.render).resolve()
    if not pptx.exists():
        print(f"FAIL: 找不到 {pptx}", file=sys.stderr); raise SystemExit(3)
    if (pdf.exists() or render.exists() and any(render.glob("slide_*.png"))) and not args.force:
        print(f"REFUSE: {pdf} 或 {render} 已有輸出（用 --force 覆寫）", file=sys.stderr)
        raise SystemExit(2)
    render.mkdir(parents=True, exist_ok=True)

    import win32com.client
    app = win32com.client.Dispatch("PowerPoint.Application")
    n = 0
    try:
        pres = app.Presentations.Open(str(pptx), WithWindow=False)
        try:
            pres.SaveAs(str(pdf), 32)  # ppSaveAsPDF
            n = pres.Slides.Count
            for i in range(1, n + 1):
                pres.Slides(i).Export(str(render / f"slide_{i:02d}.png"), "PNG", 1600, 900)
        finally:
            pres.Close()  # 只關本輪開的簡報
    finally:
        app.Quit()  # 關閉本輪 Dispatch 的應用實例

    pages_pdf = None
    try:
        from pypdf import PdfReader
        pages_pdf = len(PdfReader(str(pdf)).pages)
    except Exception:
        pages_pdf = "未驗（無 pypdf）"

    meta = {
        "pptx": str(pptx), "pdf": str(pdf), "render_dir": str(render),
        "pptx_slides": n, "pdf_pages": pages_pdf,
        "pngs": len(list(render.glob("slide_*.png"))),
        "match": (pages_pdf == n and len(list(render.glob("slide_*.png"))) == n),
    }
    (render / "render_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"PPT slides={n} PDF pages={pages_pdf} PNGs={meta['pngs']} match={meta['match']}")


if __name__ == "__main__":
    main()
