# -*- coding: utf-8 -*-
"""Native PDF/PNG export from the supplied PPTX in an isolated Office instance."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from pypdf import PdfReader

def digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--pptx",type=Path,required=True)
    ap.add_argument("--pdf",type=Path,required=True)
    ap.add_argument("--render",type=Path,required=True)
    a=ap.parse_args()
    src=a.pptx.resolve()
    pdf=a.pdf.resolve()
    render=a.render.resolve()
    if not src.is_file() or pdf.exists() or render.exists():
        raise SystemExit("Source missing or export target already exists")
    before=digest(src)
    render.mkdir(parents=True)
    pdf.parent.mkdir(parents=True,exist_ok=True)
    import pythoncom
    import win32com.client
    pythoncom.CoInitialize()
    copy=None
    app=None
    count=0
    n=0
    close_error=None
    try:
        app=win32com.client.DispatchEx("PowerPoint.Application")
        copy=app.Presentations.Open(str(src),ReadOnly=True,Untitled=True,WithWindow=False)
        count=copy.Slides.Count
        copy.SaveAs(str(pdf),32)
        for page in range(1,count+1):
            copy.Slides(page).Export(str(render/f"slide_{page:02d}.png"),"PNG",1600,900)
            n+=1
            print(f"slide_{page:02d}.png",flush=True)
    finally:
        if copy is not None:
            try:copy.Close()
            except Exception as exc:close_error=str(exc)
        # Office belongs to this isolated COM dispatch; never Quit shared PowerPoint.
        copy=None
        app=None
        pythoncom.CoUninitialize()
    result={
        "slide_count":count,"exported_png":n,"pdf_pages":len(PdfReader(pdf).pages),
        "png_resolution":[1600,900],
        "source_sha256_before":before,"source_sha256_after":digest(src),
        "source_unchanged":before==digest(src),
        "dedicated_dispatch_ex":True,"read_only":True,"untitled":True,
        "quit_called":False,"close_error":close_error,
    }
    (render/"render_meta.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf8")
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
    if not(count==n==result["pdf_pages"]==20 and result["source_unchanged"] and close_error is None):
        raise SystemExit(3)

if __name__=="__main__":
    main()
