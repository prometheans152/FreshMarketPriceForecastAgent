# -*- coding: utf-8 -*-
"""Export an untitled read-only copy; never quit the shared PowerPoint application."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def inspect_shape(shape, page: int, context: str, results: list) -> None:
    try:
        if shape.Type == 6:  # group: inspect contained native objects
            for i in range(1, shape.GroupItems.Count + 1):
                inspect_shape(shape.GroupItems(i), page, context + '/group', results)
        if shape.HasTable:
            for r in range(1, shape.Table.Rows.Count + 1):
                for c in range(1, shape.Table.Columns.Count + 1):
                    inspect_shape(shape.Table.Cell(r,c).Shape, page, f'{context}/cell-{r}-{c}', results)
        if shape.HasTextFrame and shape.TextFrame2.HasText:
            f = shape.TextFrame2
            text = str(f.TextRange.Text)
            if not text.strip():
                return
            bound = float(f.TextRange.BoundHeight)
            available = float(shape.Height) - float(f.MarginTop) - float(f.MarginBottom)
            if bound > available + 1.7:
                results.append({'page': page, 'context': context, 'text': text,
                                'bound_height_pt': bound, 'available_height_pt': available,
                                'overflow_pt': bound-available})
    except Exception as ex:
        results.append({'page': page, 'context': context, 'inspection_error': type(ex).__name__})

def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pptx',required=True,type=Path)
    p.add_argument('--pdf',required=True,type=Path)
    p.add_argument('--render',required=True,type=Path)
    args=p.parse_args()
    pptx,pdf,render=args.pptx.resolve(),args.pdf.resolve(),args.render.resolve()
    if not pptx.is_file():raise FileNotFoundError(pptx)
    if pdf.exists() or render.exists():raise FileExistsError('Use a new PDF/render destination; old output is preserved.')
    before=sha(pptx);render.mkdir(parents=True);pdf.parent.mkdir(parents=True,exist_ok=True)
    import pythoncom
    import win32com.client
    from pypdf import PdfReader
    pythoncom.CoInitialize()
    app=win32com.client.Dispatch('PowerPoint.Application')
    initial_count=int(app.Presentations.Count)
    owned=None
    overflows=[]
    try:
        # Untitled=True makes a distinct copy, even if the user's original is open.
        # ReadOnly=True and no Save on the source protect the PPTX file.
        owned=app.Presentations.Open(str(pptx),ReadOnly=True,Untitled=True,WithWindow=False)
        count=int(owned.Slides.Count)
        owned.SaveAs(str(pdf),32)
        for i in range(1,count+1):
            slide=owned.Slides(i)
            slide.Export(str(render/f'slide_{i:02d}.png'),'PNG',1600,900)
            for j in range(1,slide.Shapes.Count+1):
                inspect_shape(slide.Shapes(j),i,f'shape-{j}',overflows)
    finally:
        if owned is not None:
            owned.Close()  # Close only the distinct copy opened above.
        # No app.Quit(): ownership of a COM application is not assumed.
        remaining_count=int(app.Presentations.Count)
        pythoncom.CoUninitialize()
    pages=len(PdfReader(str(pdf)).pages)
    record={'pptx':str(pptx),'pdf':str(pdf),'render':str(render),
            'pptx_slides':count,'pdf_pages':pages,'png_pages':len(list(render.glob('slide_*.png'))),
            'page_count_match':count==pages==len(list(render.glob('slide_*.png'))),
            'initial_open_presentations':initial_count,'remaining_open_presentations':remaining_count,
            'opened_copy_read_only':True,'opened_copy_untitled':True,'application_quit_called':False,
            'source_sha256_before':before,'source_sha256_after':sha(pptx),'source_unchanged':before==sha(pptx),
            'text_height_candidates':overflows,'note':'Text geometry is a screening aid, not a replacement for visual inspection.'}
    (render/'render_meta.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(record,ensure_ascii=False,indent=2))
    if not record['page_count_match'] or not record['source_unchanged']:
        raise SystemExit(3)

if __name__=='__main__':main()
