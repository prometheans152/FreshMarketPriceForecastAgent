# -*- coding: utf-8 -*-
"""從 notes_v3.json 單一底稿生成 docs/SLIDE_NOTES.md（與 PPT 內嵌備註同源）。

執行：.venv/Scripts/python.exe slides/source/make_slide_notes.py --notes slides/source/notes_v3.json --out docs/SLIDE_NOTES.md
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--notes", default=str(ROOT / "slides/source/notes_v3.json"))
    ap.add_argument("--out", default=str(ROOT / "docs/SLIDE_NOTES.md"))
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    import json
    data = json.loads(Path(args.notes).read_text(encoding="utf-8"))
    out = Path(args.out)
    if out.exists() and not args.force:
        print(f"REFUSE: {out} 已存在（用 --force 覆寫）", file=sys.stderr)
        raise SystemExit(2)

    meta = data["meta"]
    main_slides = [s for s in data["slides"] if s["kind"] == "main"]
    total_sec = sum(s["seconds"] for s in main_slides)
    lines = [
        "# TW01 研究提案投影片：逐頁講稿與備註（v3 修訂版）",
        "",
        f"配套檔案：`slides/TW01_菜價預測_研究提案與初步成果_v2.pptx`（同名 PDF，各 {meta['slides_total']} 頁＝主講 {meta['main_slides']}＋附錄 {meta['slides_total'] - meta['main_slides']}）。",
        "本檔由 `slides/source/notes_v3.json` 單一底稿生成（與 PPT 內嵌講者備註同源；生成器 `make_slide_notes.py`）。",
        f"數字口徑＝run2 stats_master.json（±5% 含邊界 eps=1e-9）；主張對照 `outputs/proposal_delivery/run2_20261004_01/claims_master.csv`。",
        "",
        f"- 主講 {meta['main_slides']} 頁合計約 **{total_sec // 60} 分 {total_sec % 60:02d} 秒**；10 分鐘快版路徑：{meta['quick_10min']}",
        "- 這是**講稿設計**，尚未錄影；組員名單與正式發表日期仍為待填。",
        "",
        "---",
        "",
    ]
    sec_no = 0
    for s in data["slides"]:
        if s["kind"] == "main":
            sec_no += 1
            head = f"## 主講 第 {sec_no} 頁｜{s['title']}（約 {s['seconds']} 秒）"
        else:
            head = f"## 附錄 {s['slide_id'].upper()}（第 {int(s['slide_id'][1:])} 頁，不計時）｜{s['title']}"
        lines.append(head)
        lines.append("")
        lines.append(f"> {s['script']}")
        lines.append("")
        if s.get("sources"):
            lines.append("- 來源：")
            for src in s["sources"]:
                lines.append(f"  - {src}")
            lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")
    print("saved:", out, f"({len(data['slides'])} slides)")


if __name__ == "__main__":
    main()
