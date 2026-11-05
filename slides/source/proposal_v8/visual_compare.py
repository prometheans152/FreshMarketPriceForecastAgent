# -*- coding: utf-8 -*-
"""Contact sheets and pixel-level per-slide comparison of PowerPoint's own PNG exports."""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageChops, ImageStat, ImageDraw

def contact(folder, out):
    frames = [Image.open(folder / f'slide_{i:02d}.png').convert('RGB') for i in range(1, 21)]
    size = (420, 237)
    grid = Image.new('RGB', (5 * 440, 4 * 267), 'white')
    draw = ImageDraw.Draw(grid)
    for i, source in enumerate(frames):
        img = source.resize(size)
        x, y = (i % 5) * 440 + 10, (i // 5) * 267 + 28
        grid.paste(img, (x, y))
        draw.text((x, y-20), f'Slide {i+1:02d}', fill='black')
    out.parent.mkdir(parents=True,exist_ok=True)
    grid.save(out)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--original',type=Path,required=True)
    ap.add_argument('--updated',type=Path)
    ap.add_argument('--outdir',type=Path,required=True)
    args=ap.parse_args()
    contact(args.original,args.outdir/'contact_original.png')
    if args.updated is None:return
    contact(args.updated,args.outdir/'contact_updated.png')
    result={}
    allowed={1,5,10,19,20}
    for i in range(1,21):
        a=Image.open(args.original / f'slide_{i:02d}.png').convert('RGB')
        b=Image.open(args.updated / f'slide_{i:02d}.png').convert('RGB')
        diff=ImageChops.difference(a,b)
        bbox=diff.getbbox()
        result[i]={'changed':bbox is not None,'diff_bbox':bbox,'mean_rgb_difference':ImageStat.Stat(diff).mean}
        if bbox and i not in allowed:
            diff.save(args.outdir/f'unexpected_diff_{i:02d}.png')
    (args.outdir/'pixel_comparison.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('PIXEL_CHANGES', [i for i,x in result.items() if x['changed']])
    print('UNEXPECTED_CHANGES', [i for i,x in result.items() if x['changed'] and i not in allowed])
    if any(x['changed'] for i,x in result.items() if i not in allowed):
        raise SystemExit(3)

if __name__ == '__main__':main()
