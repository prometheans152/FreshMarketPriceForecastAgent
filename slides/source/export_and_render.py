# -*- coding: utf-8 -*-
"""P6b/c：PowerPoint COM 匯出 PDF＋逐頁匯出 PNG 供目視檢查。

執行：.venv/Scripts/python.exe slides/source/export_and_render.py
"""
import json
from pathlib import Path

import win32com.client

ROOT = Path(__file__).resolve().parents[2]
PPTX = ROOT / "slides" / "TW01_菜價預測_研究提案與初步成果_v1.pptx"
PDF = PPTX.with_suffix(".pdf")
RENDER = ROOT / "outputs/proposal_delivery/run1_20261004/slides_render"
RENDER.mkdir(parents=True, exist_ok=True)

app = win32com.client.Dispatch("PowerPoint.Application")
try:
    pres = app.Presentations.Open(str(PPTX), WithWindow=False)
    # PDF
    pres.SaveAs(str(PDF), 32)  # ppSaveAsPDF
    # 逐頁 PNG
    n = pres.Slides.Count
    for i in range(1, n + 1):
        pres.Slides(i).Export(str(RENDER / f"slide_{i:02d}.png"), "PNG", 1600, 900)
    pres.Close()
finally:
    app.Quit()

pages_ppt = n
pages_pdf = None
try:
    import PyPDF2  # 若無則跳過
    with open(PDF, "rb") as f:
        pages_pdf = len(PyPDF2.PdfReader(f).pages)
except Exception:
    try:
        from pypdf import PdfReader
        pages_pdf = len(PdfReader(str(PDF)).pages)
    except Exception:
        pages_pdf = "未驗（無PDF解析庫；以目視核對）"

(RENDER / "render_meta.json").write_text(
    json.dumps({"pptx_slides": pages_ppt, "pdf_pages": pages_pdf, "pngs": len(list(RENDER.glob('slide_*.png')))}, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print(f"PPT slides={pages_ppt} PDF pages={pages_pdf} PNGs={len(list(RENDER.glob('slide_*.png')))}")
