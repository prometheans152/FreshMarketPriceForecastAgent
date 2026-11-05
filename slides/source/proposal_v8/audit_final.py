# -*- coding: utf-8 -*-
"""Reconcile final native V8 artifacts against the actual PowerPoint build6 export."""
import hashlib
import json
from pathlib import Path

from PIL import Image
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[3]
FINAL = ROOT/'outputs/v8_final'
OFFICE = ROOT/'outputs/v8_candidate/build6'
ORIGINAL_PNG = ROOT/'outputs/v8_candidate/original/png'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ppt = 'FMPA_Proposal_v8_updated.pptx'
    pdf = 'FMPA_Proposal_v8_updated.pdf'
    source_meta = json.loads((OFFICE/'png/render_meta.json').read_text(encoding='utf8'))
    deck_hash = sha(FINAL/ppt)
    if deck_hash != sha(OFFICE/ppt) or deck_hash != source_meta['source_sha256_after']:
        raise SystemExit('Office export came from a different PPTX; cannot reuse')
    if not source_meta['source_unchanged'] or source_meta['slide_count'] != 20 or source_meta['exported_png'] != 20 or source_meta['pdf_pages'] != 20 or source_meta['close_error']:
        raise SystemExit('Source Office render did not finish safely')
    if sha(FINAL/pdf) != sha(OFFICE/pdf) or len(PdfReader(FINAL/pdf).pages) != 20:
        raise SystemExit('PDF is not the exact verified Office export')
    png_hashes = {}
    changed = []
    identical = []
    for n in range(1, 21):
        name = f'slide_{n:02d}.png'
        p = FINAL/'png'/name
        if not p.is_file() or Image.open(p).size != (1600, 900) or sha(p) != sha(OFFICE/'png'/name):
            raise SystemExit(f'PNG not the same verified Office export: {name}')
        png_hashes[name] = sha(p)
        if Image.open(p).convert('RGB').tobytes() == Image.open(ORIGINAL_PNG/name).convert('RGB').tobytes():
            identical.append(n)
        else:
            changed.append(n)
    if changed != [1, 5, 10, 19, 20]:
        raise SystemExit(f'Unexpected visible change distribution: {changed}')
    notes = json.loads((FINAL/'SLIDE_NOTES_v8.json').read_text(encoding='utf8'))
    if len(notes['pages']) != 20:
        raise SystemExit('Final notes are not 20 pages')
    manifest = {
        'reuse_basis': 'Full PPTX SHA256 identical to previously completed, safe PowerPoint COM export',
        'office_source_metadata': 'outputs/v8_candidate/build6/png/render_meta.json',
        'office_source_pptx_sha256': source_meta['source_sha256_after'],
        'final_pptx_sha256': deck_hash,
        'final_pdf_sha256': sha(FINAL/pdf),
        'final_notes_json_sha256': sha(FINAL/'SLIDE_NOTES_v8.json'),
        'final_notes_md_sha256': sha(FINAL/'SLIDE_NOTES_v8.md'),
        'exported_office_pages': 20,
        'png_dimensions': [1600, 900],
        'png_sha256': png_hashes,
        'changed_vs_original_pages': changed,
        'unchanged_pixel_identical_pages': identical,
        'office_export_source_unchanged': True,
        'source_file_path_from_prior_report_is_historical': True,
        'final_export_reused': True,
    }
    (FINAL/'export_reuse_evidence.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf8')
    current = {
        'pptx': str((FINAL/ppt).resolve()),
        'pdf': str((FINAL/pdf).resolve()),
        'png': str((FINAL/'png').resolve()),
        'source_sha256': deck_hash,
        'reused_office_export': True,
        'office_export_proof': str((OFFICE/'png/render_meta.json').resolve()),
        'pdf_pages': 20,
        'png_count': 20,
    }
    (FINAL/'png/render_meta.json').write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps({'office_hash_match':True,'pages':20,'png_count':len(png_hashes),
                      'changed':changed,'identical':len(identical),'pptx_sha256':deck_hash},indent=2))


if __name__ == '__main__':
    main()
