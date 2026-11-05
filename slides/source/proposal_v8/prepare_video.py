# -*- coding: utf-8 -*-
"""Initialize the isolated V8 video build using only verified, pre-existing speech."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[3]
RUN=ROOT/'recordings/midterm_v8_cos_20261105'
SRC=ROOT/'inputs/verified_current'
TOOLS=Path('C:/Users/prometheans/Documents/AIOT_FinishProject/tools/video_tools/ffmpeg/bin')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    if (RUN/'audio_hashes.json').exists():raise SystemExit('Completed run preparation exists; no overwrite.')
    runwork=RUN/'work'
    runwork.mkdir(parents=True,exist_ok=True)
    narration=json.loads((SRC/'narration.json').read_text(encoding='utf8'))
    if len(narration['pages'])!=20:raise SystemExit('Expected verified 20 page narration')
    narration['deck']='User native V8 edited: slides/proposal_v8/FMPA_Proposal_v8_updated.pptx'
    narration['source_verified_sha256']=sha(SRC/'narration.json')
    (RUN/'narration.json').write_text(json.dumps(narration,ensure_ascii=False,indent=2),encoding='utf8')
    itemhash=[]
    for i,page in enumerate(narration['pages'],1):
        n=page['page']
        if n!=i:raise AssertionError('Unexpected narration sequence')
        names=[f'p{n:02d}.mp3',f'p{n:02d}.words.json']
        for name in names:
            src=SRC/'work'/name
            if not src.is_file():raise SystemExit('Verified file unavailable: '+str(src))
            if name.endswith('.words.json'):
                words=json.loads(src.read_text(encoding='utf8'))
                if words['text']!=page['text']:raise SystemExit('Speech/word text mismatch: '+name)
            if (runwork/name).exists():
                if sha(src)!=sha(runwork/name):raise SystemExit('Existing copy differs: '+name)
            else:
                shutil.copy2(src,runwork/name)
            itemhash.append({'file':name,'source_sha256':sha(src),'candidate_sha256':sha(runwork/name)})
    for which in ('make_video.py','verify_video.py'):
        s=(SRC/which).read_text(encoding='utf8')
        s=s.replace("Path('tools/video_tools/ffmpeg/bin/ffmpeg.exe')",repr_path(TOOLS/'ffmpeg.exe'))
        s=s.replace("Path('tools/video_tools/ffmpeg/bin/ffprobe.exe')",repr_path(TOOLS/'ffprobe.exe'))
        if 'make_video' in which:
            s=s.replace('import edge_tts','',1)  # all speech must be pre-existing
            s=s.replace("            words = asyncio.run(tts(p['text'], a.rate, mp3))\n            wj.write_text(json.dumps({'text': p['text'], 'rate': a.rate, 'words': words}, ensure_ascii=False), encoding='utf-8')",
                        "            raise RuntimeError(f'Missing/mismatched verified audio for slide {n}; TTS is disabled')")
            s=s.replace("'-preset', 'medium'", "'-preset', 'veryfast'")
            if 'TTS is disabled' not in s:raise AssertionError('TTS fallback could not be removed')
        if "Path('tools/video_tools/ffmpeg/bin" in s:
            raise AssertionError('Failed to resolve installed ffmpeg paths')
        (RUN/which).write_text(s,encoding='utf8')
    (RUN/'audio_hashes.json').write_text(json.dumps({'files':itemhash,'all_identical':all(x['source_sha256']==x['candidate_sha256'] for x in itemhash),
                                                   'narration_verified_sha256':sha(SRC/'narration.json')},indent=2),encoding='utf8')
    print('PREPARED',RUN,'mp3s',len([x for x in itemhash if x['file'].endswith('.mp3')]),'hash_protected',all(x['source_sha256']==x['candidate_sha256'] for x in itemhash))

def repr_path(path: Path)->str:
    return 'Path('+repr(path.as_posix())+')'

if __name__=='__main__':main()
