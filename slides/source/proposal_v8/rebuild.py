# -*- coding: utf-8 -*-
"""Hash-guarded, surgical native V8 update: touch specified shape text and notes XML only."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import re
import zipfile
from pathlib import Path
from lxml import etree
from pptx import Presentation

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(__file__).resolve().parent
FROZEN = SOURCE/'frozen_inputs'
CONTRACT = SOURCE/'input_contract.json'
SHA_V8 = 'b0b362c99b079861bc0cc324d7ab6ed5a7f148671ddfff4debfe26597752ebdd'
FROZEN_HASHES = {
    'narration.json': 'b64ca84e5e9d8beb24224811cb91b2ce5a1050a959dcd0ef0f154ea0e3bc48aa',
    'public_test_results.json': '2d28acd2f2c3e5ce566b9095c6a85477db8faf858d9ce29e974caaedc25674b8',
    'stats_master.json': 'd6940ab49d6b96c0b579b110096338df1f9de51595fc988037785f915b912fb1',
}
NS = {'p':'http://schemas.openxmlformats.org/presentationml/2006/main',
      'a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
A = '{'+NS['a']+'}'

# Exactly one native shape ID per entry. A tuple specifies original paragraph boundaries.
# No image, table, master, layout, animation, or media is recreated.
PATCHES = {
 1: {
  88: ('Fresh Market Price Forecast Agent｜期中提案 v8｜版本日期 2026-11-05',),
  93: ('AIoT 應用與資料分析｜組長：王彥傑',
       '組員：鄭筑云、許嘉修、游雅婷｜正式發表日期：待填'),
 },
 10: {
  291: ('臺中市場均價', '封存10/02・推論日更'),
  303: ('下一步（虛線，未上線）：同店A／B到期驗證・AI助理對話驗收・唯讀分析工具（歷史走勢、跨市場比較）',),
  304: ('網頁：61品項，A／B與瀏覽器內紀錄。MCP：60品項、13市場、僅A、無B與保存；歷史遠端6/6＋5/5通過，AI對話未驗收。',
        '訓練／評估封存至2026-10-02；推論行情自2026-10-30每日自動更新（不重訓）。57品項HGB測試誤差未勝不變價。'),
 },
 19: {
  540: ('期中提案 v8｜主講結束；後附引用與實作索引；完整文獻表與計算見docs/proposal_v5/',),
  544: ('公開評估（含負向）與網頁／MCP上線；公開推論行情已每日自動更新。',),
  547: ('方向未勝動量、MAE未勝不變價；同店零證據、AI對話待驗；模型未重訓。',),
  550: ('真店到期A／B驗證、AI助理對話驗收；訓練／評估封存至2026-10-02。',),
 },
 20: {
  573: ('網頁61品項（A／B，紀錄僅瀏覽器）；MCP60品項／13市場（僅A，無B與保存）。\v訓練／評估封存10/02，推論行情10/30起日更；模型未重訓。同店與AI對話待驗，影片為自驗候選，未公開交付。',),
 }
}
SUPPORT_UPDATES = {
 1: '組長：王彥傑；組員：鄭筑云、許嘉修、游雅婷；正式發表日期待填。原V8的版面與原生物件保留。此為作者自驗候選，須外部獨立複審。',
 10: ('D47（2026-10-28）：MCP有行情品項60個、13市場，僅A，不支援B與保存；遠端原6/6＋新增5/5是歷史實測，'
      'ChatGPT/Gemini介面內真實對話與解釋正確性仍未驗收。網頁有61品項、支援A/B，紀錄只留使用者瀏覽器。'
      'D48（2026-10-30）：訓練／評估封存快照到2026-10-02，推論公開行情自2026-10-30每日自動更新，模型未重訓。'
      '原3品項RF/HGB與57品項HGB僅依既有封存模型預測；57品項模型測試誤差未勝不變價。'
      '數值只出自ForecastEngine，AI只選工具與解釋；不可將公開均價稱為真店價格。'),
 19: ('科研負向結果不變：7/14天macro-F1 0.4218/0.4169低於動量0.4226/0.4306；'
      '相對變化MAE 0.0664/0.0983高於不變價0.0436/0.0748；7天上漲158筆抓到16筆，10.1%。'
      '真店到期A/B效果、AI助理介面內真實對話與解釋仍待驗收。訓練／評估封存至2026-10-02；'
      '推論行情自2026-10-30每日更新，模型不重訓。'),
 20: ('本頁是引用與交付索引。原20頁PPT及同步配音影片為SELF_CHECK候選，外審未執行。'
      '網頁61品項可A/B、紀錄僅瀏覽器；MCP60品項、13市場、僅A，不支援B/保存；'
      '原6/6＋新增5/5為歷史遠端測試，實際AI對話未驗收。'
      '公開推論行情自2026-10-30每日自動更新，2026-10-02封存訓練評估快照與模型保持不變。'
      '真店A/B、YouTube、對教授公開GitHub與課程提交仍待辦。'),
}

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def verify_frozen_sources(frozen_dir: Path = FROZEN) -> dict:
    """Verify the source package against the original immutable V8 evidence."""
    contract = json.loads(CONTRACT.read_text(encoding='utf-8'))
    if contract.get('original_sha256') != SHA_V8 or contract.get('frozen_sha256') != FROZEN_HASHES:
        raise SystemExit('Frozen input contract differs from the independently recorded hashes')
    for name, expected in FROZEN_HASHES.items():
        source = frozen_dir/name
        if not source.is_file() or sha(source) != expected:
            raise SystemExit(f'Frozen input SHA256 mismatch: {source} (expected {expected})')
    return contract

def serial(root):
    return etree.tostring(root,encoding='UTF-8',xml_declaration=True,standalone=True)

def patch_slide(data: bytes, page: int):
    root=etree.fromstring(data)
    changed=[]
    for shape_id, wanted in PATCHES.get(page,{}).items():
        elems=root.xpath(f'.//p:sp[p:nvSpPr/p:cNvPr[@id="{shape_id}"]]',namespaces=NS)
        if len(elems)!=1:raise AssertionError(f'p{page}: shape {shape_id} not unique: {len(elems)}')
        ps=elems[0].xpath('./p:txBody/a:p',namespaces=NS)
        if len(ps)!=len(wanted):
            raise AssertionError(f'p{page} shape {shape_id}: paragraph count {len(ps)} != {len(wanted)}')
        before=[]
        for par,new in zip(ps,wanted):
            texts=par.xpath('.//a:t',namespaces=NS)
            if len(texts)!=1:raise AssertionError(f'p{page} shape {shape_id}: text run topology changed')
            before.append(texts[0].text or '')
            if '\v' in new:
                if not(page==20 and shape_id==573 and new.count('\v')==1):
                    raise AssertionError('Unplanned manual line break')
                original_run=par.xpath('./a:r',namespaces=NS)
                if len(original_run)!=1:raise AssertionError('Expected single native formatted run')
                left,right=new.split('\v')
                texts[0].text=left
                clone=copy.deepcopy(original_run[0])
                clone.xpath('./a:t',namespaces=NS)[0].text=right
                pos=par.index(original_run[0])
                par.insert(pos+1,etree.Element(A+'br'))
                par.insert(pos+2,clone)
            else:
                texts[0].text=new
        changed.append({'shape_id':shape_id,'before':before,'after':list(wanted)})
    return serial(root) if changed else data,changed

def correct_native_table_geometry(data: bytes, page: int):
    """Fix V8's dummy table-frame 3,000,000 EMU extents without flattening its tables.

    The renderer was already using the embedded grid and row dimensions; replacing
    the stale frame extent with their sum leaves exported pixels unchanged. On p5,
    redistribute 0.1605in across spacious columns so Year has a safe 0.76in.
    """
    root=etree.fromstring(data)
    changes=[]
    for frame in root.xpath('.//p:graphicFrame',namespaces=NS):
        names=frame.xpath('./p:nvGraphicFramePr/p:cNvPr/@id',namespaces=NS)
        grids=frame.xpath('.//a:tblGrid/a:gridCol',namespaces=NS)
        rows=frame.xpath('.//a:tbl/a:tr',namespaces=NS)
        ext=frame.xpath('./p:xfrm/a:ext',namespaces=NS)
        if not(grids and rows and len(ext)==1 and len(names)==1):
            continue
        shape_id=int(names[0])
        year_change=None
        if page==5 and shape_id==173:
            # A four-digit Year has a safe native width; same total table width.
            original=int(grids[1].get('w'))
            if original!=548150:raise AssertionError('Original Year width changed')
            target=round(0.76*914400)
            gain=target-original
            donors=[(2,round(0.05*914400)), (3,round(0.04*914400)),
                    (6,round(0.03*914400))]
            donors.append((7,gain-sum(a for _,a in donors)))
            for col,amount in donors:
                current=int(grids[col].get('w'))
                if current-amount<=500000:raise AssertionError('Year width funding too large')
                grids[col].set('w',str(current-amount))
            grids[1].set('w',str(target))
            year_change={'column':'Year','before_emu':original,'after_emu':target,
                         'donors_emu':{str(k):v for k,v in donors}}
        expected=(sum(int(col.get('w')) for col in grids),
                  sum(int(row.get('h')) for row in rows))
        before=(int(ext[0].get('cx')),int(ext[0].get('cy')))
        if before!=(3000000,3000000):
            raise AssertionError(f'Expected inherited dummy table extent on p{page}/id{shape_id}: {before}')
        ext[0].set('cx',str(expected[0]))
        ext[0].set('cy',str(expected[1]))
        changes.append({'shape_id':shape_id,'before_extent_emu':before,
                        'after_extent_emu':expected,'year_width':year_change})
    return (serial(root) if changes else data),changes

def patch_notes(data:bytes,page:int,spoken:str,support:str):
    root=etree.fromstring(data)
    holder=root.xpath('.//p:sp[p:nvSpPr/p:nvPr/p:ph[@type="body"]]/p:txBody',namespaces=NS)
    if len(holder)!=1:raise AssertionError(f'p{page}: notes body missing')
    body=holder[0]
    old=body.findall(A+'p')
    if not old or not old[0].xpath('.//a:t',namespaces=NS):
        raise AssertionError(f'p{page}: original notes paragraphs missing')
    template=copy.deepcopy(old[0])
    for node in old:body.remove(node)
    paragraphs=[f'第{page}頁｜已驗證旁白',spoken,'補充／來源與證據邊界',support]
    for text in paragraphs:
        node=copy.deepcopy(template)
        runs=node.xpath('.//a:t',namespaces=NS)
        runs[0].text=text
        for extra in runs[1:]:extra.text=''
        body.append(node)
    return serial(root)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input',type=Path,default=ROOT/'FMPA_Proposal_v8.pptx')
    ap.add_argument('--output',type=Path,default=ROOT/'slides/proposal_v8/FMPA_Proposal_v8_updated.pptx')
    args=ap.parse_args()
    src=args.input.resolve();dest=args.output.resolve()
    if src==dest or dest.exists():raise SystemExit('Original or existing destination cannot be overwritten')
    if sha(src)!=SHA_V8:raise SystemExit(f'Input V8 SHA256 mismatch: {sha(src)}')
    verify_frozen_sources()
    original=Presentation(src)
    if len(original.slides)!=20:raise SystemExit('Expected native 20-slide V8 deck')
    voice=json.loads((FROZEN/'narration.json').read_text(encoding='utf-8'))
    if len(voice['pages'])!=20:raise SystemExit('Narration must be 20 pages')
    notes=[]
    for i,v in enumerate(voice['pages'],1):
        if v['page']!=i:raise SystemExit('Narration page order changed')
        support=SUPPORT_UPDATES.get(i,original.slides[i-1].notes_slide.notes_text_frame.text)
        notes.append({'page':i,'title':v['title'],'text':v['text'],'supporting_notes':support})
    changed=[]
    native_tables=[]
    dest.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(src,'r') as inp, zipfile.ZipFile(dest,'w') as out:
        for info in inp.infolist():
            name=info.filename; data=inp.read(info)
            m=re.fullmatch(r'ppt/slides/slide(\d+)\.xml',name)
            note=re.fullmatch(r'ppt/notesSlides/notesSlide(\d+)\.xml',name)
            if m:
                page=int(m.group(1))
                data,delta=patch_slide(data,page)
                if delta:changed.append({'page':page,'shapes':delta})
                data,table_delta=correct_native_table_geometry(data,page)
                if table_delta:native_tables.append({'page':page,'tables':table_delta})
            elif note:
                page=int(note.group(1))
                data=patch_notes(data,page,notes[page-1]['text'],notes[page-1]['supporting_notes'])
            out.writestr(info,data)
    notes_out=dest.parent/'SLIDE_NOTES_v8.json'
    notes_out.write_text(json.dumps({'origin_sha256':SHA_V8,'narration_source':'slides/source/proposal_v8/frozen_inputs/narration.json','pages':notes},ensure_ascii=False,indent=2),encoding='utf-8')
    md=['# 期中提案 V8｜逐頁講稿與補充', '', '原生 V8 PPT 更新：20頁。以下「旁白」與隨片文字、字幕採同一個已驗證來源。', '']
    for n in notes:
        md.extend([f'## 第{n["page"]:02d}頁　{n["title"]}', '', '**旁白**', '',n['text'],'','**補充／來源與證據界線**', '',n['supporting_notes'],''])
    (dest.parent/'SLIDE_NOTES_v8.md').write_text('\n'.join(md),encoding='utf-8')
    report=ROOT/'COS_REPORTS'
    report.mkdir(exist_ok=True)
    (report/'slide_text_changes.json').write_text(json.dumps(changed,ensure_ascii=False,indent=2),encoding='utf-8')
    (report/'table_geometry_repairs.json').write_text(json.dumps(native_tables,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'input_sha256':sha(src),'output_sha256':sha(dest),
                      'original_slides':len(original.slides),'changed_visual_pages':sorted({5}|{x['page'] for x in changed}),
                      'changed_shape_count':sum(len(x['shapes']) for x in changed),
                      'repaired_native_tables':sum(len(x['tables']) for x in native_tables),
                      'notes_pages':len(notes),'output':str(dest)},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
