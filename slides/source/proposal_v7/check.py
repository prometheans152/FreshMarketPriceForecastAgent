# -*- coding: utf-8 -*-
"""Check the authored v7 (20-page midterm, condensed v6) deck against its frozen sources and same-version notes."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from pptx import Presentation
from pptx.oxml.ns import qn
from pypdf import PdfReader

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def norm(text):return ''.join(text.split())
def texts(slide):
    values=[]
    for sh in slide.shapes:
        if sh.has_text_frame:values.append(sh.text)
        if sh.has_table:values.extend(c.text for row in sh.table.rows for c in row.cells)
    return values

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',required=True,type=Path);ap.add_argument('--package',required=True,type=Path);ap.add_argument('--render',required=True,type=Path);ap.add_argument('--out',required=True,type=Path)
    a=ap.parse_args();root=a.root.resolve();out=a.package.resolve();checks=[]
    def check(name,condition,detail=None):checks.append({'check':name,'passed':bool(condition),'detail':detail})
    pptx=next(out.glob('*.pptx'));pdf=pptx.with_suffix('.pdf');p=Presentation(str(pptx));q=PdfReader(str(pdf));notes=json.loads((out/'notes_v7.json').read_text(encoding='utf-8'));md=(out/'SLIDE_NOTES_v7.md').read_text(encoding='utf-8');refs=(out/'SOURCES.md').read_text(encoding='utf-8');ev=json.loads((root/'outputs/evaluation/public/public_test_results.json').read_text(encoding='utf-8'));st=json.loads((root/'outputs/proposal_delivery/run3_20261004_01/stats_master.json').read_text(encoding='utf-8'))
    check('ppt_pdf_notes_are_20',len(p.slides)==len(q.pages)==len(notes['slides'])==20)
    check('professor_limit_20_pages',len(p.slides)<=20 and len(q.pages)<=20)
    check('main_19_appendix_1',sum(x['kind']=='主講' for x in notes['slides'])==19 and sum(x['kind']=='附錄' for x in notes['slides'])==1)
    check('source_versions_v7',notes['version']=='v7' and all('v4' not in x and 'v3' not in x for s in p.slides for x in texts(s)))
    for s,r in zip(p.slides,notes['slides']):
        check('notes_page_'+str(r['page']),s.has_notes_slide and norm(s.notes_slide.notes_text_frame.text)==norm(r['notes_text']) and norm(r['script']) in norm(md) and all('['+key+']' in refs for key in r['source_ids']))
    for h in ['h=7','h=14']:
        e=ev['horizons'][h]
        actual=' '.join(texts(p.slides[16]))
        expected=[e['selected']['direction']['macro_f1'],e['baselines']['flat_no_change']['direction']['macro_f1'],e['baselines']['past_change_continues']['direction']['macro_f1']]
        check('direction_scores_'+h,all(f'{n:.4f}' in actual for n in expected))
        actual=' '.join(texts(p.slides[16]));expected=[e['selected']['return_mae'],e['baselines']['flat_no_change']['return_mae']]
        check('mae_scores_'+h,all(f'{n:.4f}' in actual for n in expected))
    motivation=' '.join(texts(p.slides[1]))
    check('motivation_counts',all(str(v) in motivation for v in ['10.5%','16.6%','1,149','10,952','1,773','10,680']))
    check('motivation_2025_evidence',all(k in motivation for k in ['10–40%','380']))
    teaching=' '.join(texts(p.slides[14])+texts(p.slides[15]))
    check('teaching_values_labelled','全部數值為教學假設' in teaching and '30.688' in teaching and '−0.11%' in teaching)
    check('frozen_eval_unchanged',sha(root/'outputs/evaluation/public/public_test_results.json')=='2d28acd2f2c3e5ce566b9095c6a85477db8faf858d9ce29e974caaedc25674b8')
    data=' '.join(texts(p.slides[12]))
    check('data_eval_merged_page',all(k in data for k in ['data.gov.tw 84539','13市場','905格','2026-05-08','2026-07-21','2026-10-02','RF，300棵樹','HGB，200輪','1,386列']))
    check('purge_total_matches_stats',f"{sum(r['rows'] for b in st['purge']['segments'].values() for r in b.values()):,}" in data)
    # Architecture page 11: five groups + dashed future + legend + arrows + CURRENT boundary.
    diagram=' '.join(texts(p.slides[9]))
    check('numbered_function_groups',all(x in diagram for x in ['① 使用者與手機','② Agent查詢處理','③ 菜價計算','④ 公開歷史','⑤ 預測紀錄']))
    check('arch_dashed_future','PROPOSED' in diagram and '非猜菜價' in diagram and '圖例' in diagram)
    check('arch_current_tools','get_market_quote' in diagram and 'post_forecast' in diagram and '/records' in diagram)
    check('arch_relations',len(p.slides[9].shapes._spTree.findall(qn('p:cxnSp')))>=7 and all(x in diagram for x in ['唯讀載入','查閱','自願保存','回傳']))
    dashed_lines=[ln for ln in p.slides[9].shapes._spTree.iter(qn('a:ln')) if ln.find(qn('a:prstDash')) is not None]
    check('arch_dashed_linestyle_present',len(dashed_lines)>=2)
    # Flowchart page 12: decision branches D1..D9, side behaviours, PARTIAL markers.
    flow=' '.join(texts(p.slides[10]))
    check('flowchart_branches',all(x in flow for x in ['D1','D2','D3','D4','D5','D6','D7','D8','D9']))
    check('flowchart_behaviours',all(x in flow for x in ['追問缺失欄位','拒絕並說明','降級僅A','資料不足','不用LLM補值','無法核對']) and len(p.slides[10].shapes._spTree.findall(qn('p:cxnSp')))>=20)
    check('flowchart_status_marks','PARTIAL' in flow and 'post_forecast' in flow)
    # Pseudocode page 13 (main, 10 steps) and appendix page 28 (full 41 lines).
    code=' '.join(texts(p.slides[11]))
    check('pseudocode_ten_steps',all(f'{n:02d}' in code for n in range(1,11)) and all(x in code for x in ['CURRENT','PARTIAL','PROPOSED','ForecastEngine','get_market_quote','post_forecast']))
    check('pseudocode_full_version_pointer','AGENT_DESIGN.md' in code)
    # Article summary tables: 8 columns on pages 5, 24, 25, 26.
    for pgno in (5,):
        sh=[s for s in p.slides[pgno-1].shapes if s.has_table]
        cols=[len(t.columns) for t in (x.table for x in sh)]
        hdr=[c.text for t in (x.table for x in sh) for c in t.rows[0].cells]
        check(f'summary_8cols_p{pgno}',cols and max(cols)==8 and all(h in hdr for h in ['Ref.','Year','Problem','AI Method','Domain Knowledge','Dataset','Findings','Limitation']))
    refs_all=' '.join(texts(p.slides[4])+texts(p.slides[19]))
    check('summary_refs_present',all(k in refs_all for k in ['R01','R02','R03','R04','R05','R06','R07','R10','H17','W1']))
    # Table geometry readback (REVIEW_R2 V1-V4): re-read actual column widths from the PPTX,
    # not the add_table() nominal width; totals must match a nominal width actually used by
    # the generator (exact allowlist, tol 0.06); Year column must hold a 4-digit year (>=0.75in).
    NOMINAL={11.93,12.10,11.80,11.85,11.50,11.69,6.10,11.60,11.75,12.25,11.73,7.45}
    bad_tables=[]
    for i,s in enumerate(p.slides,1):
        for sh in s.shapes:
            if sh.has_table:
                t=sh.table
                total=sum(c.width for c in t.columns)/914400.0
                if not any(abs(total-n)<=0.06 for n in NOMINAL):
                    bad_tables.append({'page':i,'colwidths_sum_in':round(total,2)})
                hdr=[c.text.strip() for c in t.rows[0].cells]
                if 'Year' in hdr:
                    yw=t.columns[hdr.index('Year')].width/914400.0
                    if yw<0.75:
                        bad_tables.append({'page':i,'year_col_in':round(yw,2)})
    check('tables_geometry_readback',not bad_tables,bad_tables)
    # Deep research pages 7/8/9.
    dr7=' '.join(texts(p.slides[6]));dr8=' '.join(texts(p.slides[7]));dr9=' '.join(texts(p.slides[8]))
    check('mindsets_five',all(k in dr7 for k in ['M1','M2','M3','M4','M5','可比性','時間資訊完整性','簡單基線','公開≠私人','誤差≠效益']))
    check('controversies_three',all(k in dr8 for k in ['①','②','③','觀點A','觀點B','本案']))
    check('questions_ten',sum(dr9.count(f'{i} ') for i in range(1,11))==10 or all(f'{i} ' in dr9 for i in range(1,11)))
    # Agent principles page 10.
    # The separate principles page was dropped; its safety core must survive on the algorithm page.
    check('agent_safety_on_algorithm_page',all(k in code for k in ['ForecastEngine','白名單','227','PROPOSED','get_market_quote','LLM不算菜價']))
    # Team17 comparison page 3 states no direct ranking.
    rel=' '.join(texts(p.slides[2]))
    check('team17_stated',all(k in rel for k in ['Team 17','未來五天','0.81']))
    pictures=[(i+1,sh) for i,s in enumerate(p.slides) for sh in s.shapes if sh.shape_type==13]
    tables=sum(sh.has_table for s in p.slides for sh in s.shapes)
    check('editable_not_flattened',len(pictures)==1 and pictures[0][0]==18 and tables>=9,{'pictures':len(pictures),'tables':tables})
    outside=[]
    for i,s in enumerate(p.slides,1):
        for sh in s.shapes:
            if sh.left<0 or sh.top<0 or sh.left+sh.width>p.slide_width+100 or sh.top+sh.height>p.slide_height+100:outside.append({'page':i,'name':sh.name})
    check('objects_inside_slide',not outside,outside)
    # Footer-band overlap guard: any shape starting above the footer band (7.0in) must end above it.
    # Catches text/tables overlapping the footer citation line even when still inside the slide.
    band_viol=[]
    for i,s in enumerate(p.slides,1):
        for sh in s.shapes:
            try:
                top=sh.top/914400.0; bottom=(sh.top+sh.height)/914400.0
            except TypeError:
                continue
            if top<7.0 and bottom>6.98: band_viol.append({'page':i,'name':sh.name,'top':round(top,2),'bottom':round(bottom,2)})
    check('footer_band_clear',not band_viol,band_viol)
    effects=[]
    for i,s in enumerate(p.slides,1):
        for sh in s.shapes:
            if sh._element.findall('.//'+qn('a:outerShdw')):effects.append(i)
            for ref in sh._element.findall('.//'+qn('a:effectRef')):
                if ref.get('idx')!='0':effects.append(i)
    check('no_theme_shadow',not effects,effects)
    check('no_animations',all(s._element.find(qn('p:timing')) is None for s in p.slides))
    meta=json.loads((a.render/'render_meta.json').read_text(encoding='utf-8'));check('actual_office_export',meta['page_count_match'] and meta['source_unchanged'] and not meta['application_quit_called'])
    check('final_plain_text_height',not [x for x in meta['text_height_candidates'] if 'overflow_pt' in x])
    stale=[(i,x) for i,s in enumerate(p.slides,1) for x in texts(s)+[s.notes_slide.notes_text_frame.text]
           if any(k in x for k in ('TW01','候選版','待獨立複審','自驗候選'))]
    check('no_old_name_or_review_status',not stale,stale[:5])
    dangling=[(i,x[:60]) for i,s in enumerate(p.slides,1) for x in texts(s)+[s.notes_slide.notes_text_frame.text] if '附錄A' in x]
    check('no_dangling_appendix_refs',not dangling,dangling[:5])
    check('pdf_has_extractable_text',all(len(pg.extract_text().strip())>10 for pg in q.pages))
    result={'passed':all(x['passed'] for x in checks),'checks':checks,'pptx_sha256':sha(pptx),'pdf_sha256':sha(pdf),'limits':'Author automated checks only — NOT a visual acceptance. Per-page visual inspection is recorded separately in this run visual_review.md (GLM self-inspection of rendered PNGs; independent review belongs to ChatGPT). COM cell-level text geometry unavailable; table readability checked on per-page renders. r3 adds: generator fail-fast table-geometry guard (validate_table_geometry) and PPTX column-width readback incl. Year column minimum.'}
    a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'passed':result['passed'],'checks':len(checks),'failures':[x for x in checks if not x['passed']]},ensure_ascii=False,indent=2))
    if not result['passed']:raise SystemExit(1)

if __name__=='__main__':main()
