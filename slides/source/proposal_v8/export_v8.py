# -*- coding: utf-8 -*-
"""Dedicated Office-instance native V8 export from an unsaved read-only untitled copy."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from pypdf import PdfReader

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--pptx',type=Path,required=True)
    ap.add_argument('--pdf',type=Path,required=True)
    ap.add_argument('--render',type=Path,required=True)
    args=ap.parse_args()
    src=args.pptx.resolve(); pdf=args.pdf.resolve(); render=args.render.resolve()
    if not src.is_file() or pdf.exists() or render.exists():
        raise SystemExit('Source absent or output already exists; use new isolated output paths.')
    before=digest(src)
    render.mkdir(parents=True)
    pdf.parent.mkdir(parents=True,exist_ok=True)
    import pythoncom
    import win32com.client
    pythoncom.CoInitialize()
    app=win32com.client.DispatchEx('PowerPoint.Application')  # isolated, owned Office process
    copy=None
    count=0; n=0; close_error=None
    try:
        copy=app.Presentations.Open(str(src),ReadOnly=True,Untitled=True,WithWindow=False)
        count=copy.Slides.Count
        copy.SaveAs(str(pdf),32)
        for i in range(1,count+1):
            copy.Slides(i).Export(str(render/f'slide_{i:02d}.png'),'PNG',1600,900)
            n+=1
            print(f'slide_{i:02d} exported',flush=True)
    finally:
        if copy is not None:
            try:copy.Close()  # close only owned copy
            except Exception as ex:close_error=str(ex)
        # app belongs to this process, but don't Quit COM application or any shared user instance
        app=None
        pythoncom.CoUninitialize()
    result={'pptx':str(src),'pdf':str(pdf),'png':str(render),'slide_count':count,'exported_png':n,
            'pdf_pages':len(PdfReader(pdf).pages),'source_sha256_before':before,
            'source_sha256_after':digest(src),'source_unchanged':before==digest(src),
            'read_only':True,'untitled':True,'dedicated_dispatch_ex':True,'quit_shared_app':False,
            'close_error':close_error}
    (render/'render_meta.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
    if not(n==count==result['pdf_pages']==20 and result['source_unchanged'] and close_error is None):
        raise SystemExit(3)

if __name__=='__main__':main()
