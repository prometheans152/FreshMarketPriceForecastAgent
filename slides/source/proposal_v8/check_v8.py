# -*- coding: utf-8 -*-
"""Native V8 semantic, frozen-value, geometry, notes, provenance, export checks."""
import argparse
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path
import zipfile
from pptx import Presentation
from pypdf import PdfReader
from PIL import Image
from rebuild import FROZEN, SHA_V8, verify_frozen_sources

ROOT=Path(__file__).resolve().parents[3]
ALLOWED_VISUAL={1,5,10,19,20}
TABLE_GEOMETRY_PAGES={3,4,5,7,13,14,15,16,17}
ORIGINAL=ROOT/'FMPA_Proposal_v8.pptx'
UPDATED=ROOT/'slides/proposal_v8/FMPA_Proposal_v8_updated.pptx'
NOTES=ROOT/'slides/proposal_v8/SLIDE_NOTES_v8.json'

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def four(x):return str(Decimal(str(x)).quantize(Decimal('0.0001'),rounding=ROUND_HALF_UP))
def one(x):return str(Decimal(str(x)).quantize(Decimal('0.1'),rounding=ROUND_HALF_UP))

def all_text(slide):
    s=[]
    def walk(shapes):
        for shape in shapes:
            if shape.has_text_frame:s.append(shape.text)
            if shape.has_table:
                for row in shape.table.rows:
                    for cell in row.cells:s.append(cell.text)
            if shape.shape_type==6:
                walk(shape.shapes)
    walk(slide.shapes)
    return '\n'.join(s)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--pptx',type=Path,default=UPDATED)
    ap.add_argument('--pdf',type=Path,default=ROOT/'slides/proposal_v8/FMPA_Proposal_v8_updated.pdf')
    ap.add_argument('--png',type=Path,default=ROOT/'slides/proposal_v8/png')
    ap.add_argument('--out',type=Path,default=ROOT/'COS_REPORTS/v8_check.json')
    ap.add_argument('--original',type=Path,default=ORIGINAL)
    ap.add_argument('--notes',type=Path)
    ap.add_argument('--frozen-dir',type=Path,default=FROZEN)
    args=ap.parse_args()
    tests=[]
    def test(label,ok,info=''):
        tests.append({'label':label,'passed':bool(ok),'detail':info})
        if not ok:print('FAIL',label,info,flush=True)
    try:
        verify_frozen_sources(args.frozen_dir)
        test('frozen_source_hashes',True)
    except (SystemExit, ValueError, KeyError) as ex:
        test('frozen_source_hashes',False,str(ex))
    test('immutable:original_v8',args.original.is_file() and digest(args.original)==SHA_V8)
    # The extra baseline includes desktop provenance and original SRT. It exists in
    # the handoff worktree, but is intentionally absent in a clean reproducibility kit.
    baseline_path=ROOT/'BASELINE_INPUTS.json'
    if baseline_path.is_file():
        baseline=json.loads(baseline_path.read_text(encoding='utf8'))
        for name in ('FMPA_Midterm_v8.srt',
                     'outputs/evaluation/public/public_test_results.json',
                     'outputs/proposal_delivery/run3_20261004_01/stats_master.json',
                     'inputs\\desktop\\README.md','inputs\\desktop\\design.md','inputs\\desktop\\資訊圖表.png'):
            p=ROOT/name.replace('\\','/')
            test('immutable:'+name,p.is_file() and digest(p)==baseline[name]['sha256'])
    else:
        test('portable_without_COS_baseline',True)
    ppt=Presentation(args.pptx)
    test('native_20_slide',len(ppt.slides)==20)
    orig=Presentation(args.original)
    test('native_shape_types_and_ids_match',all([(s.shape_id,s.shape_type)==(o.shape_id,o.shape_type)
        for page,other in zip(ppt.slides,orig.slides) for s,o in zip(page.shapes,other.shapes)])
        and all(len(a.shapes)==len(b.shapes) for a,b in zip(ppt.slides,orig.slides)))
    contents=[all_text(slide) for slide in ppt.slides]
    test('team_and_version',all(x in contents[0] for x in
         ('v8','2026-11-05','王彥傑','鄭筑云','許嘉修','游雅婷','正式發表日期：待填')))
    p10=contents[9]
    test('D47_MCP_boundary',all(x in p10 for x in ('MCP：60品項、13市場','僅A','無B與保存','6/6＋5/5','AI對話未驗收')))
    test('D48_frozen_vs_rolling',all(x in p10 for x in
        ('訓練／評估封存至2026-10-02','推論行情自2026-10-30每日自動更新','不重訓')))
    test('61_web_AB_browser_only',all(x in p10 for x in
         ('61品項','A／B與瀏覽器內紀錄')))
    test('no_stale_next_steps',all(x not in '\n'.join(contents) for x in
         ('每天更新行情','行情只到10月2日','只開放原3品項','每日行情更新、同店驗證')))
    test('page19_conclusion',all(x in contents[18] for x in
        ('未勝動量','未勝不變價','同店零證據','AI對話待驗','訓練／評估封存至2026-10-02')))
    test('page20_delivery_status',all(x in contents[19] for x in
        ('MCP60品項／13市場','僅A','推論行情10/30起日更','影片為自驗候選')))
    test('model_and_A_B_experimental_examples',all(x in (contents[14]+'\n'+contents[15]) for x in
        ('32','30.7','−4.1%','28','14.29%','0.3','−0.11%')))
    pub=json.loads((args.frozen_dir/'public_test_results.json').read_text(encoding='utf8'))
    stats=json.loads((args.frozen_dir/'stats_master.json').read_text(encoding='utf8'))
    f1_table=ppt.slides[16].shapes
    all17=contents[16]
    for h,desc in ((7,'7'),(14,'14')):
        val=pub['horizons'][f'h={h}']
        for label,x in (
            ('macro_f1',val['selected']['direction']['macro_f1']),
            ('momentum_f1',val['baselines']['past_change_continues']['direction']['macro_f1']),
            ('flat_f1',val['baselines']['flat_no_change']['direction']['macro_f1']),
            ('model_mae',val['selected']['return_mae']),
            ('flat_mae',val['baselines']['flat_no_change']['return_mae']),
        ):
            test(f'full_precision_rounding_{h}_{label}',four(x) in all17,{'expected':four(x)})
    up=pub['horizons']['h=7']['selected']['direction']['per_class']['up']
    mat=pub['horizons']['h=7']['selected']['direction']['confusion_matrix']
    test('actual_up_16_of_158',up['support']==158.0 and mat[2][2]==16
         and '158筆' in all17 and '16筆' in all17)
    test('recall_10.1_percent',one(up['recall']*100)=='10.1' and '10.1%' in all17)
    test('historical_nonflat_share',all(one(stats['descriptive'][s]['percent_exact'])+'%' in contents[1]
        for s in ('h7|ALL','h14|ALL')))
    test('13_markets',stats['descriptive']['h7|ALL']['n_markets']==13 and '13市場' in p10)
    test('negative_results_retained',pub['horizons']['h=7']['selected']['direction']['macro_f1'] <
         pub['horizons']['h=7']['baselines']['past_change_continues']['direction']['macro_f1']
         and pub['horizons']['h=14']['selected']['return_mae'] >
         pub['horizons']['h=14']['baselines']['flat_no_change']['return_mae'])

    # Inspect true native table widths, including narrow Year column, plus physical shape bounds.
    bounds=[];tables=[];years=[]
    for n,slide in enumerate(ppt.slides,1):
        for sh in slide.shapes:
            if sh.left < -1000 or sh.top < -1000 or sh.left+sh.width > ppt.slide_width+1000 or sh.top+sh.height > ppt.slide_height+1000:
                bounds.append((n,sh.shape_id,sh.left,sh.top,sh.width,sh.height))
            if sh.has_table:
                table=sh.table;calc=sum(c.width for c in table.columns)
                tables.append((n,sh.shape_id,int(sh.width),int(calc)))
                if len(table.rows) and len(table.columns)>1:
                    for j in range(len(table.columns)):
                        if table.cell(0,j).text.strip().lower()=='year':
                            years.append((n,float(table.columns[j].width/914400)))
    test('all_shapes_inside_slide',not bounds,bounds[:10])
    test('table_column_width_sums',all(abs(a-b)<=100 for _,_,a,b in tables),tables)
    test('year_columns_at_least_0_75in',bool(years) and all(w>=0.75 for _,w in years),years)
    notes_path=args.notes if args.notes is not None else args.pptx.parent/'SLIDE_NOTES_v8.json'
    metadata=json.loads(notes_path.read_text(encoding='utf8'))
    verified=json.loads((args.frozen_dir/'narration.json').read_text(encoding='utf8'))
    test('notes_json_20',len(metadata['pages'])==20)
    test('notes_provenance',metadata.get('origin_sha256')==SHA_V8 and
         metadata.get('narration_source')=='slides/source/proposal_v8/frozen_inputs/narration.json')
    for i,slide in enumerate(ppt.slides):
        spoken=metadata['pages'][i]['text']
        expected=verified['pages'][i]['text']
        test(f'notes_and_narration_{i+1}',spoken==expected and spoken in slide.notes_slide.notes_text_frame.text)
    # Native table-frame extent repair affects nine slide XML parts. Year width
    # redistribution is an intentional visible change on p5; all other table
    # frame fixes must be pixel-identical, confirmed by the render diff.
    with zipfile.ZipFile(args.original) as a,zipfile.ZipFile(args.pptx) as b:
        same_names=set(a.namelist())==set(b.namelist())
        changed=[n for n in a.namelist() if n in b.namelist() and a.read(n)!=b.read(n)]
    permitted={f'ppt/slides/slide{i}.xml' for i in (ALLOWED_VISUAL|TABLE_GEOMETRY_PAGES)}
    permitted.update(f'ppt/notesSlides/notesSlide{i}.xml' for i in range(1,21))
    test('native_xml_delta_scoped',same_names and set(changed)<=permitted and
         set(f'ppt/slides/slide{i}.xml' for i in ALLOWED_VISUAL)<=set(changed),
         {'changed_parts':len(changed),'unexpected':sorted(set(changed)-permitted)})
    if args.pdf.exists():
        test('pdf_20_pages',len(PdfReader(args.pdf).pages)==20)
        images=sorted(args.png.glob('slide_*.png'))
        test('png_20_1600x900',len(images)==20 and all(Image.open(p).size==(1600,900) for p in images))
    else:
        test('pdf_and_png_export_exists',False)
    passed=all(x['passed'] for x in tests)
    result={'passed':passed,'checks':len(tests),'failed':[t for t in tests if not t['passed']],
            'pptx_sha256':digest(args.pptx),'pdf_sha256':digest(args.pdf) if args.pdf.exists() else None,
            'native_tables':tables,'year_column_width_in':years,'shape_outliers':bounds,'changed_zip_parts':changed}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'passed':passed,'checks':len(tests),'failures':result['failed'],
                       'tables':len(tables),'shapes_out_of_bounds':len(bounds)},ensure_ascii=False,indent=2))
    raise SystemExit(0 if passed else 1)

if __name__=='__main__':main()
