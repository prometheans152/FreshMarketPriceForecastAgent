# -*- coding: utf-8 -*-
"""Minimal native midterm edition built from the SHA-locked V8 PowerPoint."""
from __future__ import annotations

import copy
import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

from lxml import etree
from pptx import Presentation

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "slides/proposal_v8/FMPA_Proposal_v8_updated.pptx"
OUT = ROOT / "slides/midterm"
FROZEN = ROOT / "slides/source/proposal_v8/frozen_inputs"
SOURCE_SHA = "b863486b038aaf34175c9dc81d4c86d6ce27c5d51fe5a1dc10d941b62ce6c8d0"
FROZEN_SHA = {
    "narration.json": "b64ca84e5e9d8beb24224811cb91b2ce5a1050a959dcd0ef0f154ea0e3bc48aa",
    "stats_master.json": "d6940ab49d6b96c0b579b110096338df1f9de51595fc988037785f915b912fb1",
    "public_test_results.json": "2d28acd2f2c3e5ce566b9095c6a85477db8faf858d9ce29e974caaedc25674b8",
}
NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
}
A = "{" + NS["a"] + "}"

# Each replacement keeps the original native shape, font, paragraphs and geometry.
SHAPES = {
    1: {
        88: ["Fresh Market Price Forecast Agent｜期中提案｜資料整理日 2026-11-06"],
    },
    5: {
        171: ["完整文獻與查核層級見 docs/midterm/RESEARCH_NOTES.md；UNKNOWN＝未載明，非「沒有」"],
    },
    7: {
        208: ["[G1] 五思維證據與設計影響見 docs/midterm/RESEARCH_NOTES.md"],
    },
    8: {
        221: ["[G1] 雙方證據與未解問題見 docs/midterm/RESEARCH_NOTES.md"],
    },
    9: {
        248: ["[G1] 十個深問題與參考解答見 docs/midterm/RESEARCH_NOTES.md"],
    },
    10: {
        303: ["下一步（虛線，未上線）：同店A／B到期驗證・AI對話解釋驗證・唯讀分析工具（歷史走勢、跨市場比較）"],
        304: [
            "網頁：61品項，A／B與瀏覽器內紀錄。MCP：60品項、13市場、僅A、無B與保存；可查全臺中參考。ChatGPT匿名A單例成功，其餘待驗。",
            "訓練／評估封存至2026-10-02；推論行情自2026-10-30每日自動更新（不重訓）。57品項HGB測試誤差未勝不變價。",
        ],
    },
    11: {
        327: ["[AD1][DEP1] CURRENT／PARTIAL 與流程設計見 design.md §2–3"],
    },
    12: {
        394: ["[AD1] 帶行號演算法摘要與完整版來源見 design.md §7；LLM不算菜價"],
    },
    19: {
        540: ["期中提案｜主講結束；研究與引文詳見 docs/midterm/RESEARCH_NOTES.md"],
        547: ["方向未勝動量、MAE未勝不變價；同店待驗；ChatGPT匿名A單例成功，其餘待驗。"],
        550: ["真店到期A／B驗證、AI其餘情境與解釋驗證；評估封存至2026-10-02。"],
    },
    20: {
        560: ["完整引文見 docs/midterm/RESEARCH_NOTES.md；評估見 docs/midterm/public_test_results.json"],
        570: ["[研究文件與數據]"],
        571: ["研究與文獻：docs/midterm/RESEARCH_NOTES.md；評估：docs/midterm/public_test_results.json"],
        573: [
            "網頁61品項（A／B）、MCP60品項／13市場（僅A、無B與保存）；ChatGPT匿名A單例成功，其餘待驗。",
            "評估封存10/02、推論行情10/30起日更，真店效果未驗；研究與簡報有AI協助，數字以封存來源核對。",
        ],
    },
}

# Link only the cited path token in a shape.  The original V8 has no hyperlink
# relationships; relative, external native OOXML links are added here.
DOC_LINKS = {
    "docs/midterm/RESEARCH_NOTES.md": "../../docs/midterm/RESEARCH_NOTES.md",
    "docs/midterm/public_test_results.json": "../../docs/midterm/public_test_results.json",
    "design.md": "../../design.md",
}
DOC_LINK_PAGES = {5:{171},7:{208},8:{221},9:{248},11:{327},12:{394},
                  19:{540},20:{560,571}}

# Concise evidence notes, deliberately free of a second narrated script.
SOURCES = [
    "研究與簡報整理使用 AI 工具協助；模型測試數字依封存 JSON 核對。組長王彥傑；組員鄭筑云、許嘉修、游雅婷。發表日期待填。",
    "[D1–D2][W1][N1] 7天配對10,952筆、14天10,680筆；10.5%／16.6%為歷史樣本比例，非未來機率；批發颱風統計及新聞案例只是背景，非店價測試。",
    "[R01][R02] 僅依論文摘要；[R04]依報導，模型未公開；[H17] Team17第一手PDF已讀11/15頁、其餘依查閱筆記。各作品資料和指標不同，不跨資料集比分數。",
    "[R05][R06] 產品功能來自公開介紹，未安裝實測；未公開資訊標 UNKNOWN。研究缺口限所查範圍，不能推論其他產品完全沒有相關功能。",
    "[R01][R02][R06][H17] 教授八欄：Ref／Year／Problem／AI Method／Domain Knowledge／Dataset／Findings／Limitation。主講精選4件；文獻來源與查核層級見 docs/midterm/RESEARCH_NOTES.md。",
    "[P1][E1] RQ1公開市場封存測試已有負向答案；RQ2真店A/B增益尚無到期資料；RQ3介面有人因測試需求，尚未驗證易用性。",
    "[G1][S1] 思維依可比性、時間資訊、基線、公開與私人資料、決策效益整理；跨訓練／驗證／測試邊界刪除1,386列，0代表缺報價。",
    "[G1][E1][H17] 三爭論為市場均價能否推店價、複雜模型能否勝基線、新增資料是否真有增益；立場均受可得證據與待做實驗限制。",
    "[G1] 十題與參考解答及研究背景見 docs/midterm/RESEARCH_NOTES.md；涵蓋 Why／What-if／Trade-off／Failure Case／Evidence／Comparison／Design。",
    "[DEP1] 網頁61品項可A/B、紀錄僅瀏覽器；MCP兩工具、60品項13市場、僅匿名A、不保存。品項、當日價和單位齊全而未指定市場時，post_forecast採all_markets，對有效市場7／14天變化率各取中位數，作未經準確率驗證的全臺中參考；get_market_quote仍需市場。ChatGPT一個匿名A真實對話成功；其他情境、Gemini及文字解釋全面忠實性待驗。推論行情每日更新；模型與2026-10-02評估快照封存。",
    "[AD1][DEP1] 必填品項、價格、單位；日期可預設今天；MCP僅A。資料過期目前警告，不是全面拒絕；保存僅網頁本機，真店到期核對未驗，LLM解釋全面忠實性未驗；CURRENT／PARTIAL 與流程來源：design.md §2–3。",
    "[AD1] 10步為主講摘要；完整41行偽碼見design.md §7。D1–D9、T1/T3對應現況與PARTIAL；數字只由ForecastEngine提供。",
    "[D1][M3][S1] 臺中13個有效公有零售市場，2025-10-04至2026-10-02，元／台斤；905個零值轉缺測。訓練至2026-05-08、驗證至2026-07-21、測試2026-07-22～10-02；清除跨邊界1,386列。測試7天n=2,085、14天n=1,859；公開均價不是單店真值。",
    "[M1] t起算精確7／14日曆天；相對變化(r)=(到期價−當日價)÷當日價；±5%含邊界均判持平；缺少可用到期值不能製造標籤。",
    "[M2] 32元、−4.1%、30.7元為教學假設，不是實際店價實驗；A錨定只縮放顯示價，不會改變預測相對變化或方向。",
    "[M2] 32/28元、公開+1%均為教學假設；B係數α=0.3為固定規則、未訓練。須同店、同規格、同單位和可比日期；增益尚無到期真值驗證。",
    "[E1] 封存原三品項：7／14天macro-F1模型0.4218／0.4169，未勝動量0.4226／0.4306；相對變化MAE模型0.0664／0.0983，未勝不變價0.0436／0.0748。上漲召回10.1%／8.6%，未作顯著性證明；57品項HGB展示擴充不得套用相同分數。來源：docs/midterm/public_test_results.json。",
    "[U1][DEP1] 2026-10-03本機原型真截圖，頁面只裁切放大7天A/B；B結果不是前頁教學例。雲端61品項現況與截圖時點不同，真店到期效果未驗。",
    "[E1][DEP1] 公開市場評估含負向結果，模型未重訓；ChatGPT匿名A僅一個實際對話已通，全面解釋與Gemini未驗；同店A/B到期、人因效益未驗。",
    "[R01–R10][H17] 參考文獻、原作者、來源網址與查核層級見 docs/midterm/RESEARCH_NOTES.md；封存測試數字見 docs/midterm/public_test_results.json。研究整理、程式與簡報有AI協助；科學限制與負向結果如實保留。",
]

# Revise only the two spoken passages whose old claims contradict the verified
# 2026-11-05 ChatGPT single-case result. They require re-recording in video.
SPOKEN_REPLACEMENTS = {
    10: (
        "遠端實測原六項加新品項五項通過，AI 助理介面內的實際對話驗收還沒做。",
        "工具已遠端驗證；ChatGPT 匿名 A 模式有一次真實對話成功，其他情境與解釋仍待驗證。",
    ),
    19: (
        "下一步是收集同店的到期真值，並補上 AI 助理實際對話驗收。",
        "下一步是收集同店的到期真值，並擴大 AI 助理其他情境與解釋的驗證。",
    ),
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def xml_bytes(root) -> bytes:
    return etree.tostring(root, encoding="UTF-8", xml_declaration=True, standalone=True)


def update_slide(data: bytes, page: int):
    root = etree.fromstring(data)
    updates = []
    for shape_id, lines in SHAPES.get(page, {}).items():
        holder = root.xpath(f'.//p:sp[p:nvSpPr/p:cNvPr[@id="{shape_id}"]]', namespaces=NS)
        if len(holder) != 1:
            raise RuntimeError(f"p{page}: shape {shape_id} missing/ambiguous")
        paragraphs = holder[0].xpath("./p:txBody/a:p", namespaces=NS)
        if len(paragraphs) != len(lines) and not (page == 20 and shape_id == 573 and len(paragraphs) == 1 and len(lines) == 2):
            raise RuntimeError(f"p{page} shape {shape_id}: paragraph topology changed")
        if page == 20 and shape_id == 573:
            texts = paragraphs[0].xpath(".//a:t", namespaces=NS)
            if len(texts) != 2:
                raise RuntimeError("p20 manual line break must remain native and editable")
            before = [x.text or "" for x in texts]
            for t, new in zip(texts, lines):
                t.text = new
        else:
            before = []
            for p, line in zip(paragraphs, lines):
                texts = p.xpath(".//a:t", namespaces=NS)
                if len(texts) != 1:
                    raise RuntimeError(f"p{page}/shape{shape_id}: unexpected styled runs")
                before.append(texts[0].text or "")
                texts[0].text = line
        if before != lines:
            updates.append({"page": page, "shape_id": shape_id, "before": before, "after": lines})
    return (xml_bytes(root) if updates else data), updates


def add_document_links(data: bytes, page: int, link_ids: dict[str, str]):
    """Link only an actual source path, never the enclosing citation or author."""
    if not link_ids:
        return data, 0
    root = etree.fromstring(data)
    count = 0
    for shape_id in DOC_LINK_PAGES[page]:
        holders = root.xpath(f'.//p:sp[p:nvSpPr/p:cNvPr[@id="{shape_id}"]]', namespaces=NS)
        if len(holders) != 1:
            raise RuntimeError(f"Missing link target p{page} shape {shape_id}")
        for paragraph in holders[0].xpath("./p:txBody/a:p", namespaces=NS):
            for run in list(paragraph.xpath("./a:r", namespaces=NS)):
                target = run.find(A + "t")
                if target is None or not target.text:
                    continue
                parts = re.split("(" + "|".join(re.escape(s) for s in DOC_LINKS) + ")", target.text)
                if len(parts) == 1:
                    continue
                index = paragraph.index(run)
                paragraph.remove(run)
                for part in parts:
                    if not part:
                        continue
                    new_run = copy.deepcopy(run)
                    new_run.find(A + "t").text = part
                    if part in link_ids:
                        rpr = new_run.find(A + "rPr")
                        if rpr is None:
                            rpr = etree.Element(A + "rPr")
                            new_run.insert(0, rpr)
                        etree.SubElement(rpr, A + "hlinkClick", {R_ID: link_ids[part]})
                        count += 1
                    paragraph.insert(index, new_run)
                    index += 1
    if count == 0:
        raise RuntimeError(f"Expected native hyperlink paths on p{page}")
    return xml_bytes(root), count


R_ID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
HYPERLINK_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink"


def prepare_native_link_relationships(z: zipfile.ZipFile):
    updated = {}
    by_page = {}
    for page, shape_ids in DOC_LINK_PAGES.items():
        name = f"ppt/slides/_rels/slide{page}.xml.rels"
        root = etree.fromstring(z.read(name))
        occupied = {el.get("Id") for el in root}
        ids = {}
        requested = {token for shape_id in shape_ids for line in SHAPES[page][shape_id]
                     for token in DOC_LINKS if token in line}
        for token in sorted(requested):
            candidate = 1
            while f"rId{candidate}" in occupied:
                candidate += 1
            rid = f"rId{candidate}"
            occupied.add(rid)
            etree.SubElement(root, "{" + REL_NS + "}Relationship",
                             Id=rid, Type=HYPERLINK_TYPE, Target=DOC_LINKS[token],
                             TargetMode="External")
            ids[token] = rid
        if not ids:
            raise RuntimeError(f"No source links prepared for page {page}")
        updated[name] = xml_bytes(root)
        by_page[page] = ids
    return updated, by_page


def update_notes(data: bytes, page: int, narration: str, evidence: str) -> bytes:
    root = etree.fromstring(data)
    holders = root.xpath('.//p:sp[p:nvSpPr/p:nvPr/p:ph[@type="body"]]/p:txBody', namespaces=NS)
    if len(holders) != 1:
        raise RuntimeError(f"p{page}: notes body missing")
    body = holders[0]
    existing = body.findall(A + "p")
    if not existing or not existing[0].xpath(".//a:t", namespaces=NS):
        raise RuntimeError(f"p{page}: note paragraph template missing")
    template = copy.deepcopy(existing[0])
    for elem in existing:
        body.remove(elem)
    for phrase in (f"第{page:02d}頁｜正式旁白", narration, "來源與限制：" + evidence):
        para = copy.deepcopy(template)
        runs = para.xpath(".//a:t", namespaces=NS)
        runs[0].text = phrase
        for extra in runs[1:]:
            extra.text = ""
        body.append(para)
    return xml_bytes(root)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", type=Path, default=OUT)
    ap.add_argument("--changes-out", type=Path, default=ROOT/"COS_REPORTS/build_manifest.json")
    args = ap.parse_args()
    outdir = args.outdir.resolve()
    changes_out = args.changes_out.resolve()
    if outdir.exists():
        raise SystemExit(f"Output already exists; leave it untouched: {outdir}")
    if changes_out.exists():
        raise SystemExit(f"Change log already exists; leave it untouched: {changes_out}")
    if not outdir.is_relative_to(ROOT) or not changes_out.is_relative_to(ROOT/"COS_REPORTS"):
        raise SystemExit("Output paths must remain in the isolated project and reports folder")
    if digest(SOURCE) != SOURCE_SHA:
        raise SystemExit("V8 source SHA mismatch; refusing edit")
    for name, sha in FROZEN_SHA.items():
        if digest(FROZEN / name) != sha:
            raise SystemExit(f"Frozen source modified: {name}")
    old = Presentation(SOURCE)
    old_notes = json.loads((ROOT / "slides/proposal_v8/SLIDE_NOTES_v8.json").read_text(encoding="utf-8"))["pages"]
    if not (len(old.slides) == len(old_notes) == len(SOURCES) == 20):
        raise SystemExit("Slide count/source notes mismatch")
    new_notes = []
    spoken_changes = []
    for i, entry in enumerate(old_notes, 1):
        spoken = entry["text"]
        if i in SPOKEN_REPLACEMENTS:
            before, after = SPOKEN_REPLACEMENTS[i]
            if spoken.count(before) != 1:
                raise SystemExit(f"p{i}: expected original spoken text missing")
            spoken = spoken.replace(before, after)
            spoken_changes.append({"page": i, "before": before, "after": after, "requires_new_audio": True})
        new_notes.append({"page": i, "title": entry["title"], "narration": spoken, "references_and_limits": SOURCES[i - 1]})
    outdir.mkdir(parents=True)
    destination = outdir / "FMPA_Midterm.pptx"
    changes = []
    link_count = 0
    with zipfile.ZipFile(SOURCE, "r") as zin, zipfile.ZipFile(destination, "w") as zout:
        rel_updates, link_ids_by_page = prepare_native_link_relationships(zin)
        for info in zin.infolist():
            data = zin.read(info)
            slide_match = re.fullmatch(r"ppt/slides/slide(\d+)\.xml", info.filename)
            notes_match = re.fullmatch(r"ppt/notesSlides/notesSlide(\d+)\.xml", info.filename)
            if slide_match:
                page = int(slide_match.group(1))
                data, delta = update_slide(data, page)
                data, linked = add_document_links(data, page, link_ids_by_page.get(page, {}))
                link_count += linked
                changes.extend(delta)
            elif notes_match:
                n = int(notes_match.group(1))
                data = update_notes(data, n, new_notes[n - 1]["narration"], new_notes[n - 1]["references_and_limits"])
            elif info.filename in rel_updates:
                data = rel_updates[info.filename]
            zout.writestr(info, data)
    notes_json = {
        "title": "現場菜價 7／14 天預測與分析代理人｜期中提案",
        "research_notes": "docs/midterm/RESEARCH_NOTES.md",
        "public_test_results": "docs/midterm/public_test_results.json",
        "pages": new_notes,
    }
    (outdir / "SLIDE_NOTES.json").write_text(json.dumps(notes_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# 期中提案｜逐頁正式講稿", "", "每頁只有一段正式旁白；另列必要研究來源與限制。", ""]
    for x in new_notes:
        lines.extend([f"## 第{x['page']:02d}頁｜{x['title']}", "", "**正式旁白**", "", x["narration"], "", "**來源與限制**", "", x["references_and_limits"], ""])
    (outdir / "SLIDE_NOTES.md").write_text("\n".join(lines), encoding="utf-8")
    changes_out.parent.mkdir(exist_ok=True)
    changes_out.write_text(json.dumps({
        "slide_text": changes,
        "spoken_changes": spoken_changes,
        "notes_simplified": list(range(1, 21)),
        "unchanged_audio_pages": [n for n in range(1, 21) if n not in SPOKEN_REPLACEMENTS],
        "new_audio_required_pages": sorted(SPOKEN_REPLACEMENTS),
        "original_pptx_sha256": SOURCE_SHA,
        "new_pptx_sha256": digest(destination),
        "native_hyperlinks_added": link_count,
        "link_relationships": {str(p):v for p,v in link_ids_by_page.items()},
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(destination), "hash": digest(destination),
        "changed_visible_pages": sorted({x["page"] for x in changes}),
        "changed_shapes": len(changes),
        "notes_pages": len(new_notes),
        "native_hyperlinks": link_count,
        "spoken_re_record_pages": sorted(SPOKEN_REPLACEMENTS),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
