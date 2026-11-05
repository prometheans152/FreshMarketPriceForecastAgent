# -*- coding: utf-8 -*-
"""Isolated negative controls: native V8 checker must reject bad scores and Year width."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
from lxml import etree

ROOT=Path(__file__).resolve().parents[3]
PPT=ROOT/'slides/proposal_v8/FMPA_Proposal_v8_updated.pptx'
TEST=ROOT/'slides/source/proposal_v8/check_v8.py'
OUT=ROOT/'outputs/v8_candidate/negative_controls'
NS={'p':'http://schemas.openxmlformats.org/presentationml/2006/main',
    'a':'http://schemas.openxmlformats.org/drawingml/2006/main'}

def corrupt(data:bytes,fixture:str):
    root=etree.fromstring(data)
    if fixture=='score':
        matches=root.xpath('.//a:t[text()="0.4218"]',namespaces=NS)
        if len(matches)!=1:raise AssertionError('Expected exactly one model F1 0.4218')
        matches[0].text='0.9999'
    else:
        frames=root.xpath('.//p:graphicFrame[p:nvGraphicFramePr/p:cNvPr[@id="173"]]',namespaces=NS)
        if len(frames)!=1:raise AssertionError('Expected one original Year table')
        cols=frames[0].xpath('.//a:tblGrid/a:gridCol',namespaces=NS)
        width=int(cols[1].get('w'))
        if width<680000:raise AssertionError('Expected repaired Year width ~0.76in')
        delta=width-450000
        cols[1].set('w','450000')
        cols[7].set('w',str(int(cols[7].get('w'))+delta))
        # Keep frame extent internally consistent, still break the real Year constraint.
    return etree.tostring(root,encoding='UTF-8',xml_declaration=True,standalone=True)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--pptx',type=Path,default=PPT)
    ap.add_argument('--pdf',type=Path,default=ROOT/'slides/proposal_v8/FMPA_Proposal_v8_updated.pdf')
    ap.add_argument('--png',type=Path,default=ROOT/'slides/proposal_v8/png')
    ap.add_argument('--notes',type=Path)
    ap.add_argument('--outdir',type=Path,default=OUT)
    ap.add_argument('--report',type=Path,default=ROOT/'COS_REPORTS/v8_negative_tests.json')
    a=ap.parse_args()
    if not a.pptx.is_file():raise SystemExit('Final candidate PPTX is missing')
    a.outdir.mkdir(parents=True,exist_ok=True)
    results=[]
    for name,page,wanted_label in (('score',17,'full_precision_rounding_7_macro_f1'),
                                   ('year',5,'year_columns_at_least_0_75in')):
        target=a.outdir/f'negative_{name}.pptx'
        if target.exists():raise SystemExit(f'Negative fixture already exists: {target}')
        with zipfile.ZipFile(a.pptx,'r') as inp,zipfile.ZipFile(target,'w') as output:
            for info in inp.infolist():
                data=inp.read(info)
                if info.filename==f'ppt/slides/slide{page}.xml':
                    data=corrupt(data,name)
                output.writestr(info,data)
        resultpath=a.outdir/f'{name}_check.json'
        cmd=[sys.executable,str(TEST),'--pptx',str(target),
             '--pdf',str(a.pdf),'--png',str(a.png),
             '--notes',str(a.notes or a.pptx.parent/'SLIDE_NOTES_v8.json'),
             '--out',str(resultpath)]
        run=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,encoding='utf-8',errors='replace')
        result=json.loads(resultpath.read_text(encoding='utf8')) if resultpath.exists() else {}
        errors=[x['label'] for x in result.get('failed',[])]
        passed=run.returncode!=0 and wanted_label in errors
        results.append({'fixture':name,'pptx':str(target),'check_exit':run.returncode,
                        'expected_failure':wanted_label,'observed_failures':errors,'passed':passed})
        print(name,'exit',run.returncode,'detected',wanted_label in errors,'errors',errors,flush=True)
    # Frozen-source tampering must also be detected without changing the production files.
    frozen_source=ROOT/'slides/source/proposal_v8/frozen_inputs'
    mutated=a.outdir/'tampered_frozen_inputs'
    if mutated.exists():raise SystemExit(f'Negative fixture already exists: {mutated}')
    shutil.copytree(frozen_source,mutated)
    changed=mutated/'public_test_results.json'
    changed.write_bytes(changed.read_bytes()+b' ')
    resultpath=a.outdir/'frozen_check.json'
    cmd=[sys.executable,str(TEST),'--pptx',str(a.pptx),'--pdf',str(a.pdf),
         '--png',str(a.png),'--notes',str(a.notes or a.pptx.parent/'SLIDE_NOTES_v8.json'),
         '--frozen-dir',str(mutated),'--out',str(resultpath)]
    run=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,encoding='utf-8',errors='replace')
    result=json.loads(resultpath.read_text(encoding='utf8')) if resultpath.exists() else {}
    errors=[x['label'] for x in result.get('failed',[])]
    passed=run.returncode!=0 and 'frozen_source_hashes' in errors
    results.append({'fixture':'frozen_hash','input':str(changed),'check_exit':run.returncode,
                    'expected_failure':'frozen_source_hashes','observed_failures':errors,'passed':passed})
    print('frozen_hash','exit',run.returncode,'detected',passed,flush=True)
    report={'passed':all(x['passed'] for x in results),'cases':results}
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    if not report['passed']:raise SystemExit(1)

if __name__=='__main__':main()
