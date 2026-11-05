# -*- coding: utf-8 -*-
"""Read-only baseline and original native V8 inventory (no repo model access)."""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path
from pptx import Presentation

ROOT = Path(__file__).resolve().parents[3]
def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def walk(shapes):
    for shape in shapes:
        d = {'id': shape.shape_id, 'name': shape.name,
             'type': str(shape.shape_type), 'pos': [shape.left, shape.top, shape.width, shape.height]}
        if shape.has_text_frame:
            d['paragraphs'] = [''.join(run.text for run in par.runs) for par in shape.text_frame.paragraphs]
            d['text'] = shape.text
        if shape.has_table:
            d['cols'] = [c.width for c in shape.table.columns]
            d['rows'] = [r.height for r in shape.table.rows]
            d['table'] = [[shape.table.cell(i,j).text for j in range(len(shape.table.columns))] for i in range(len(shape.table.rows))]
        yield d
        if shape.shape_type == 6:
            yield from walk(shape.shapes)

def main():
    inp = json.loads((ROOT/'BASELINE_INPUTS.json').read_text(encoding='utf-8'))
    errors = []
    for name, spec in inp.items():
        path = ROOT / name.replace('\\', '/')
        if not path.exists(): errors.append(f'missing: {name}'); continue
        val = sha(path)
        if val != spec['sha256'] or path.stat().st_size != spec['size']:
            errors.append(f'bad: {name} hash={val} bytes={path.stat().st_size}')
    print('BASELINE',len(inp),'mismatches',len(errors))
    for x in errors: print(x)
    original = Presentation(str(ROOT/'FMPA_Proposal_v8.pptx'))
    inventory = {'pages':len(original.slides),'slide_size':[original.slide_width,original.slide_height], 'slides':[]}
    for idx,s in enumerate(original.slides,1):
        shapes=list(walk(s.shapes))
        note = s.notes_slide.notes_text_frame.text if s.has_notes_slide else None
        inventory['slides'].append({'page':idx,'shapes':shapes,'notes':note})
        lines=[]
        for item in shapes:
            if item.get('text', '').strip():
                lines.append(f'{item["id"]}:{item["text"].replace(chr(10)," / ")[:240]}')
            if 'table' in item:
                lines.append(f'{item["id"]}:TABLE {len(item["rows"])}x{len(item["cols"])} '+repr(item['table'])[:300])
        print(f'PAGE {idx:02d} shapes={len(shapes)} notes={bool(note)}', ' | '.join(lines)[:2400])
    verified=json.loads((ROOT/'inputs/verified_current/narration.json').read_text(encoding='utf-8'))
    original_n=json.loads((ROOT/'inputs/original_r4/narration.json').read_text(encoding='utf-8'))
    changes=[{'page':p['page'],'before':original_n['pages'][i]['text'],'after':p['text']} for i,p in enumerate(verified['pages']) if original_n['pages'][i]['text']!=p['text']]
    print('NARRATION differences original r4 -> verified:',len(changes), [i['page'] for i in changes])
    out=ROOT/'COS_REPORTS'
    out.mkdir(exist_ok=True)
    (out/'original_v8_inventory.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'narration_diff.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'baseline_check.json').write_text(json.dumps({'checked':len(inp),'errors':errors,'original_sha256':sha(ROOT/'FMPA_Proposal_v8.pptx')},ensure_ascii=False,indent=2),encoding='utf-8')
    if errors or len(original.slides)!=20 or len(verified['pages'])!=20:sys.exit(2)

if __name__ == '__main__':main()
