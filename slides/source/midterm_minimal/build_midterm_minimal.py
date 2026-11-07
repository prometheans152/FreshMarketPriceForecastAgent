# -*- coding: utf-8 -*-
"""Editable 20-slide minimal midterm. Frozen formal PPT is always the input.

Safe by design: no network, no training, no main-tree write. Uses python-pptx to
edit native objects, and transplants only authorized slide/notes XML from the
edited package into the frozen PPT package. Unchanged slides remain byte-identical
at the OOXML part level. Invoke with --source, --out and --input-dir in isolation.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import zipfile
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.xmlchemy import OxmlElement
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[3]
FORMAL_SOURCE_SHA = "b96812ad8c8bfbde2b1b14096780e104e0cabb19308a6ef032665d035b7fa0bd"
AUTHOR_SLIDES = {6, 10, 11, 12, 19, 20}
PAGES_WITH_NOTES_CHANGED = AUTHOR_SLIDES

FLOW = """flowchart TD
    A["輸入：Web 或 MCP 預測"] --> B["檢查欄位與單位；取得公開歷史"]
    B --> C{"輸入合法、資料可用？"}
    C -->|否| G["追問缺項／明確報錯，不猜價格"]
    C -->|是| D["已訓練模型預測 7／14 天"]
    D -->|模型失敗| G
    D -->|成功| E["計算 A；Web 可比才 B"]
    E --> F["顯示日期、方向、來源與警示"]"""

STEPS = [
    "收品項、今日價、單位、日期及入口；上週價選填",
    "缺項追問；價格、單位或日期不合法就拒絕",
    "換算元／台斤；MCP匿名A，缺市場用all_markets",
    "只用t−1前歷史做特徵；資料不足就報錯",
    "行情過舊先警示；公開均價不是今天店價",
    "已訓練模型估計7／14天相對變動率",
    "模型或工具失敗就報錯，不能猜價",
    "全臺中參考：各期限取至少3個有效市場變動率中位數",
    "A＝今日店價×（1＋相對變動率）",
    "Web上週同店價可比時，依§5固定規則另算B",
    "否則只有A；A／B按±5%分類，日期t＋7／14",
    "回傳價、方向、日期、來源與警示；LLM只解釋工具值",
]
assert len(STEPS) == 12

DARK = RGBColor(38, 48, 58)
BLUE = RGBColor(49, 89, 112)
MUTED = RGBColor(101, 115, 129)
BORDER = RGBColor(200, 212, 222)
PALE = RGBColor(239, 244, 246)
WHITE = RGBColor(255, 255, 255)
FONT = "Microsoft JhengHei"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def shape(slide, shape_id: int):
    found = [s for s in slide.shapes if s.shape_id == shape_id]
    if len(found) != 1:
        raise ValueError(f"Missing/duplicate shape id {shape_id}")
    return found[0]


def edit_native_text(sh, lines: str | list[str]):
    """Update first styled run in each pre-existing paragraph; retain its style."""
    if isinstance(lines, str):
        lines = lines.split("\n")
    paragraphs = sh.text_frame.paragraphs
    if len(paragraphs) != len(lines):
        raise ValueError(
            f"Shape {sh.shape_id} paragraphs {len(paragraphs)} != {len(lines)}"
        )
    for p, value in zip(paragraphs, lines):
        if p.runs:
            p.runs[0].text = value
            for r in p.runs[1:]:
                r.text = ""
        else:
            p.add_run().text = value
    sh.text_frame.word_wrap = True


def edit_group_text(slide, group_id: int, item_id: int, lines):
    grp = shape(slide, group_id)
    for child in grp.shapes:
        if child.shape_id == item_id:
            edit_native_text(child, lines)
            return
    raise ValueError(f"Group item missing: {group_id}/{item_id}")


def remove_id(slide, shape_id: int):
    sh = shape(slide, shape_id)
    sh._element.getparent().remove(sh._element)


def add_box(slide, x, y, w, h, text, *,
            font_size=17, color=DARK, border=BORDER,
            fill=WHITE, weight=False, kind=MSO_SHAPE.RECTANGLE):
    sh = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid()
    sh.fill.fore_color.rgb = fill
    sh.line.color.rgb = border
    sh.line.width = Pt(1.2)
    # Native PowerPoint's default theme effect on new shapes casts a shadow.
    # The original PPT's boxes are flat; disable the effect reference.
    style = sh._element.find(
        "{http://schemas.openxmlformats.org/presentationml/2006/main}style")
    if style is not None:
        effect = style.find(
            "{http://schemas.openxmlformats.org/drawingml/2006/main}effectRef")
        if effect is not None:
            effect.set("idx", "0")
    tf = sh.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.09)
    tf.margin_top = tf.margin_bottom = Inches(0.03)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = text
    r.font.name = FONT
    r.font.size = Pt(font_size)
    r.font.bold = weight
    r.font.color.rgb = color
    return sh


def add_text(slide, x, y, w, h, txt, size=16,
             color=DARK, weight=False, align=PP_ALIGN.LEFT):
    sh = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = sh.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.02)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = txt
    r.font.name = FONT
    r.font.size = Pt(size)
    r.font.bold = weight
    r.font.color.rgb = color
    return sh


def connector(slide, x1, y1, x2, y2, color=BLUE):
    c = slide.shapes.add_connector(
        MSO_CONNECTOR.STRAIGHT,
        Inches(x1), Inches(y1), Inches(x2), Inches(y2)
    )
    c.line.color.rgb = color
    c.line.width = Pt(1.6)
    ln = c._element.spPr.find(
        "{http://schemas.openxmlformats.org/drawingml/2006/main}ln")
    if ln is not None:
        arrow = OxmlElement("a:tailEnd")
        arrow.set("type", "triangle")
        ln.append(arrow)
    return c


def update_p6(slide):
    edit_group_text(slide, 186, 188, "RQ1：固定7／14天市場方向評估")
    edit_group_text(slide, 186, 189, [
        "比對不變價、動量與模型的同一封存樣本。",
        "方向與誤差如實呈現，也包含負向結果。",
    ])
    edit_group_text(slide, 190, 192, "RQ2：A／B輸入是否有增益？")
    edit_group_text(slide, 190, 193, [
        "A用今天店價；B選填可比較的上週同店價。",
        "是否改善，將以同店到期實價另行比較。",
    ])
    edit_group_text(slide, 194, 196, "RQ3：低負擔、來源清楚的查詢")
    edit_group_text(slide, 194, 197, [
        "主要輸入為品項、今天價與單位。",
        "結果提供7／14日期、來源及使用範圍。",
    ])
    edit_native_text(shape(slide, 198), "研究設計與貢獻")
    edit_native_text(shape(slide, 199), [
        "C1：固定7／14天、公開均價與強基線的公平評估",
        "C2：今天價A與選填上週同店價B，規劃到期配對比較",
        "C3：Web／MCP提供期限、來源及限制清楚的查詢原型",
    ])
    edit_native_text(shape(slide, 184),
                     "[P1] 研究問題與設計貢獻；同店A／B增益屬後續驗證")


def update_p10(slide):
    edit_native_text(shape(slide, 270), "系統架構：Web／AI助理兩入口")
    edit_native_text(shape(slide, 279), [
        "AI 助理",
        "選工具＋解釋",
    ])
    edit_native_text(shape(slide, 282), [
        "Cloudflare MCP",
        "兩工具：查行情／預測",
    ])
    edit_native_text(shape(slide, 285), [
        "API／驗證",
        "請求轉送",
    ])
    edit_native_text(shape(slide, 276), [
        "雲端網頁",
        "61品項・A/B・7／14天",
    ])
    edit_native_text(shape(slide, 272),
                     "[DEP1] 兩入口、五模組；資料與結果沿原路回傳")
    for sid in (302, 303, 304, 305):
        remove_id(slide, sid)
    note = shape(slide, 306)
    edit_native_text(note, "LLM只選工具與解釋；菜價由④ForecastEngine計算。")
    note.top = Inches(5.35)
    note.height = Inches(0.5)
    add_text(
        slide, 0.83, 6.02, 11.9, 0.62,
        "查行情工具：指定市場直接讀公開資料，不先跑模型。\n"
        "預測工具：未指定市場可用all_markets；結果沿原路返回。",
        size=15.2, color=MUTED
    )


def update_p11(slide):
    edit_native_text(shape(slide, 325), "查詢流程圖：從輸入到7／14天結果")
    edit_native_text(shape(slide, 327),
                     "[AD1] 流程與12行演算法詳見 design.md §6")
    preserved={324,325,326,327,328}
    for sh in list(slide.shapes):
        if sh.shape_id not in preserved:
            sh._element.getparent().remove(sh._element)
    x=2.12; w=6.95; h=0.61
    positions = {
        "A":1.72,"B":2.47,"C":3.22,"D":4.12,"E":4.93,"F":5.74
    }
    add_box(slide,x,positions["A"],w,h,"使用者輸入：Web或MCP預測",font_size=18,weight=True)
    add_box(slide,x,positions["B"],w,h,"檢查欄位、單位，取得公開歷史",font_size=17.8)
    # A diamond's text area is only its inscribed half-width rectangle, so a
    # narrow diamond wrapped this label onto two lines that crossed the outline.
    # Widen it and keep the label on one line through the widest middle band.
    diamond_w=5.40
    diamond_x=x+(w-diamond_w)/2
    decision=add_box(slide,diamond_x,positions["C"],diamond_w,0.68,
            "輸入合法、資料可用？",font_size=17,
            fill=PALE,weight=True,kind=MSO_SHAPE.DIAMOND)
    decision.text_frame.word_wrap=False
    add_box(slide,x,positions["D"],w,h,"已訓練模型預測7／14天",font_size=18)
    add_box(slide,x,positions["E"],w,h,"計算A；Web可比才B",font_size=18)
    add_box(slide,x,positions["F"],w,h,"顯示日期、方向、來源與警示",
            font_size=18,fill=PALE,weight=True)
    add_box(slide,9.68,3.38,2.80,1.00,
            "追問缺項／明確報錯\n不猜價格",
            font_size=17.3,fill=WHITE)
    center=x+w/2
    connector(slide,center,2.33,center,2.47)
    connector(slide,center,3.08,center,3.22)
    connector(slide,center,3.90,center,4.12)
    connector(slide,center,4.73,center,4.93)
    connector(slide,center,5.54,center,5.74)
    diamond_right=diamond_x+diamond_w  # actual right vertex, not the wide-row box edge
    connector(slide,diamond_right,3.56,9.68,3.72)
    connector(slide,x+w,4.42,9.68,4.25)
    add_text(slide,8.20,3.25,0.43,0.25,"否",size=12.6,color=MUTED)
    add_text(slide,9.06,4.48,0.60,0.25,"失敗",size=12.5,color=MUTED)


def update_p12(slide):
    edit_native_text(shape(slide, 392), "Algorithm 1：菜價7／14天預測（12步）")
    edit_native_text(shape(slide, 394),
                     "[AD1] 與 design.md §6 同源的12行偽碼；LLM不算菜價")
    preserved={391,392,393,394,395}
    for sh in list(slide.shapes):
        if sh.shape_id not in preserved:
            sh._element.getparent().remove(sh._element)
    add_text(slide,0.82,1.56,11.8,0.37,
             "輸入 → 檢查 → 公開歷史 → 已訓練模型 → A／B → 結果",
             size=15.0,color=MUTED)
    for index, step in enumerate(STEPS):
        col=index//6
        row=index%6
        x=0.80 if col==0 else 6.74
        y=2.02+row*0.68
        add_text(slide,x,y,0.52,0.59,f"{index+1:02d}",
                 size=14.7,color=BLUE,weight=True)
        add_text(slide,x+0.62,y,5.20,0.60,step,
                 size=15.0,color=DARK)
    add_text(slide,0.87,6.25,11.70,0.44,
             "LLM只解釋工具結果，不自行推算菜價；失敗要明確說明。",
             size=16.3,color=BLUE,weight=True)

def update_p19(slide):
    edit_native_text(shape(slide, 538), "結論：成果、範圍與下一步")
    edit_native_text(shape(slide, 543), "核心成果")
    edit_native_text(shape(slide, 544),
                     "建立7／14天公開市場評估與Web／MCP查詢原型，附來源與警示。")
    edit_native_text(shape(slide, 546), "研究適用範圍")
    edit_native_text(shape(slide, 547),
                     "方向未勝動量、誤差未勝不變價；市場均價不能代表單店真價。")
    edit_native_text(shape(slide, 549), "未來研究")
    edit_native_text(shape(slide, 550),
                     "收集同店同品項同規格的到期售價，配對比較A／B是否有增益。")
    edit_native_text(shape(slide, 551),
                     "資料來源：臺中公有零售市場；完整封存結果與引文見附錄。")
    edit_native_text(shape(slide, 540),
                     "研究與引文：docs/midterm/RESEARCH_NOTES.md；公開封存數據見附錄")


def p20_links(slide):
    # Existing citations and test JSON links in shape 571 remain intact.
    edit_native_text(shape(slide, 558), "附錄｜研究來源、文件與 AI 使用")
    edit_native_text(shape(slide, 570), "[提案／設計／研究文件]")
    edit_native_text(shape(slide, 572), "[AI 使用與研究範圍]")
    box = shape(slide, 573)
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = Inches(0.02)
    tf.margin_top = Inches(0.01)
    tf.margin_bottom = Inches(0.01)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    top = tf.paragraphs[0]
    top.alignment = PP_ALIGN.LEFT
    items = [
        ("完整 Proposal：", None),
        ("docs/midterm/PROPOSAL.md", "../../docs/midterm/PROPOSAL.md"),
        ("；DESIGN：", None),
        ("design.md", "../../design.md"),
    ]
    for label, target in items:
        run = top.add_run()
        run.text = label
        run.font.name = FONT
        run.font.size = Pt(13.0)
        run.font.color.rgb = BLUE if target else MUTED
        if target:
            run.hyperlink.address = target
            run.font.underline = True
    second = tf.add_paragraph()
    second.alignment = PP_ALIGN.LEFT
    run = second.add_run()
    run.text = "AI協助研究、程式與文稿；研究數字以原始來源和封存結果核對。"
    run.font.name = FONT
    run.font.size = Pt(12.6)
    run.font.color.rgb = MUTED
    edit_native_text(shape(slide, 560),
                     "研究引文與讀取層級見RESEARCH_NOTES；測試原始精度見public_test_results")


def revise_design(text: str) -> str:
    if "## 6. Algorithm" not in text:
        raise ValueError("DESIGN section 6 is missing")
    # The original document named §9 "Limitations"; after adoption the heading
    # becomes "研究範圍與未來工作".  Both are legitimate frozen inputs.
    section9 = list(re.finditer(r"(?m)^## 9\.[^\n]*$", text))
    if len(section9) != 1:
        raise ValueError("DESIGN must have exactly one numbered section 9")
    text = text.replace(
        "![系統架構：PPT 第 10 頁](slides/midterm/png/slide_10.png)",
        "![系統架構：PPT 第 10 頁](slides/midterm_minimal/png/slide_10.png)"
    )
    text = text.replace("Web 瀏覽器支援 A／B 與自願瀏覽器保存", "Web 瀏覽器支援 A／B")
    text = text.replace("（無 B／保存）", "（不提供 B）")
    text = text.replace(
        "；CLI 支援 `scripts/predict_local.py --request-file <JSON 檔>`。模型包未隨 Git 提供，新環境安裝未重測。",
        "；CLI 支援 `scripts/predict_local.py --request-file <JSON 檔>`。"
    )
    # Put the scope/validation caveats in §9, without repeating them in
    # §3/§5/§7. Preserve the actual method and all §8 test/baseline numbers.
    text = text.replace(
        "再以今日店價錨定；**全臺中聚合尚未評估準確率**。查",
        "再以今日店價錨定。查"
    )
    text = text.replace(
        "都回 A 並說明；真店 B 增益尚未評估。",
        "都回 A 並說明。"
    )
    text = text.replace(
        "| `deploy/oracle-forecastengine/all_markets/` | 市場中位數路徑，**準確率未評估** |",
        "| `deploy/oracle-forecastengine/all_markets/` | 分期限有效市場預測變動率中位數 |"
    )
    start = text.index("## 6. Algorithm")
    end = text.index("## 7. Implementation Mapping")
    block = """## 6. Algorithm：Flowchart 與 Pseudocode

本節只描述 **Web 預測／MCP `post_forecast`**；`get_market_quote` 獨立查公開行情，不經預測模型。

![查詢流程圖：PPT 第 11 頁](slides/midterm_minimal/png/slide_11.png)

**Algorithm 1：7／14 天菜價查詢（12 行）**

```text
""" + "\n".join(f"{i:02d} {step}" for i, step in enumerate(STEPS, 1)) + """
```

**對照**：輸入／檢查／資料（PPT ①②③⑤）→01–05；模型④→06–08；A／B與沿原路返回→09–12。公開行情過舊先警示；沒有可用資料或模型失敗就明確報錯，不補數值。A／B 詳細公式見 §5。

"""
    text = text[:start] + block + text[end:]
    section9 = list(re.finditer(r"(?m)^## 9\.[^\n]*$", text))
    if len(section9) != 1:
        raise ValueError("Cannot locate single section 9 after section 6 update")
    start = section9[0].start()
    text = text[:start] + """## 9. 研究範圍與未來工作（Limitations / Future Work）

**目前範圍**：證據來自臺中公有市場均價，不能直接代表個別店價；全臺中聚合效果亦未獨立評估。原模型與簡單基線的完整比較見 §8。

**未來工作**：B 採固定 α=0.3 規則；後續蒐集同店同品項同規格的到期售價，配對比較 A／B 是否有增益。文獻與查核層級見[研究補充](docs/midterm/RESEARCH_NOTES.md)。
"""
    return text


def revise_proposal_links(text: str) -> str:
    replacements = {
        "../../slides/midterm/FMPA_Midterm.pptx":
            "../../slides/midterm_minimal/FMPA_Midterm_Minimal.pptx",
        "../../slides/midterm/FMPA_Midterm.pdf":
            "../../slides/midterm_minimal/FMPA_Midterm_Minimal.pdf",
        "../../slides/midterm/SLIDE_NOTES.md":
            "../../slides/midterm_minimal/SLIDE_NOTES.md",
    }
    for before, after in replacements.items():
        if before not in text and after not in text:
            raise ValueError(f"Proposal link not found: {before}")
        text = text.replace(before, after)
    return text


def revise_notes(original: dict) -> dict:
    notes = copy.deepcopy(original)
    assert len(notes["pages"]) == 20
    # Keep existing academic evidence on other pages untouched.
    replacements = {
        6: {
            "title": "研究問題與研究設計",
            "narration": "我們有三個研究問題：第一，固定七天與十四天的公開市場預測要和不變價、動量公平比較；封存結果也保留未勝基線的負向發現。第二，今天價 A 和選填上週同店價 B 是否真的改善店價？這仍是研究問題，後續用同店到期價配對驗證。第三，如何讓使用者少輸入，但仍看到期限、來源和適用範圍。",
            "references_and_limits": "[P1][E1] RQ1 已有公開市場封存結果；RQ2 同店 A/B 增益未實證；RQ3 為低輸入負擔與可追溯設計，使用者效益尚待驗證。",
        },
        10: {
            "title": "五模組系統架構",
            "narration": "這張圖有五個模組：第一是 Web 或 AI 助理入口。AI 助理經第二個 MCP 模組選工具，第三個 Oracle API 驗證欄位並轉送。預測由第四個 ForecastEngine 計算，使用第五個公開市場歷史；結果沿原路回到使用者。Web 可以比較 A/B，MCP 只有匿名 A。要注意，get_market_quote 查指定市場公開行情，並不先跑模型；post_forecast 才進預測流程。LLM 只選工具和解釋，不能自己編菜價。",
            "references_and_limits": "[DEP1][A1] Web 61 品項；MCP 60 有行情品項、13 市場、兩工具匿名 A；get_market_quote 須指定市場，post_forecast 未指定市場可用 all_markets。公開歷史更新不等於模型重訓，聚合準確率未評估。",
        },
        11: {
            "title": "七節點查詢流程",
            "narration": "整個預測流程只需要記住六個主步驟：使用者輸入、驗證欄位及取得公開歷史、判斷資料是否可用、呼叫已訓練模型、計算 A 或可用的 B、回覆日期方向和來源。不合法或資料不足就追問或報錯；如果模型失敗，也走同一個錯誤出口，絕不能猜價格。公開行情比較舊時先給警示。",
            "references_and_limits": "[AD1] 同一七節點流程見 design.md §6；Web 可用可比較的 B、MCP 僅匿名 A；失敗不出預測數字，行情舊先警示。",
        },
        12: {
            "title": "演算法一：12 行白話偽碼",
            "narration": "這十二行與設計文件完全對應：先核對品項、正價格、單位、日期和市場，只用能看見的公開歷史做特徵，再交給已訓練的模型估計七天與十四天相對變化。A 是今天店價乘上市場變動比例；Web 的上週同店價各項條件都能比較時，才計算 B。最後按正負百分之五分類，標示來源與資料日期。全臺中參考要每期限取有效市場預測變動率中位數。AI 不自行算菜價。",
            "references_and_limits": "[AD1] 12 行與 design.md §6 同源；B 係數 α=0.3 是固定實驗規則，並未證明增益。全臺中參考至少三個有效市場、逐期限取變動率中位數。",
        },
        19: {
            "title": "核心成果與研究範圍",
            "narration": "我們完成了臺中公開市場七天與十四天預測的固定評估，並有 Web 與 MCP 查詢原型。實驗的方向沒有勝過動量基線、相對變化誤差沒有勝過不變價，因此只能作為有來源的參考，不能當成已證實的單店價格。未來主要研究是收集同店同品項同規格的到期售價，事先保留 A 和 B，配對比較究竟有沒有改善。",
            "references_and_limits": "[E1][P1] 公開市場 7/14 天封存結果與負向基線比較見 public_test_results.json；目前沒有同店到期價及 A/B 改善證據。",
        },
        20: {
            "title": "文獻與 AI 使用",
            "narration": "這一頁保留研究與引文的可追溯入口。論文以實際查閱的摘要或簡報為界，不把未取得的全文內容當證據。研究整理、程式及簡報有 AI 協助，數字和主張仍以原始資料、程式與封存測試結果核對。完整提案、DESIGN 與研究補充都有文件連結，謝謝聆聽。",
            "references_and_limits": "[R01–R10][H17] 文獻查核層級見 docs/midterm/RESEARCH_NOTES.md；正式研究 Proposal / DESIGN、原封存測試 JSON 有對應入口。AI 使用非獨立實證，店價效果未驗。",
        },
    }
    for entry in notes["pages"]:
        if entry["page"] in replacements:
            entry.update(replacements[entry["page"]])
    notes["title"] = "現場菜價 7／14 天預測與分析代理人｜精簡期中提案"
    return notes


def markdown_notes(notes: dict) -> str:
    lines = [
        "# 期中提案｜逐頁講稿（精簡版）", "",
        "每頁只有一段正式旁白及來源界線；保存不列核心流程、到期同店比較列未來研究。", "",
    ]
    for page in notes["pages"]:
        lines += [
            f"## 第{page['page']:02d}頁｜{page['title']}", "",
            "**正式旁白**", "", page["narration"], "",
            "**來源與限制**", "", page["references_and_limits"], "",
        ]
    return "\n".join(lines)


def edit_notes_slide(slide, page: dict):
    if not slide.has_notes_slide:
        raise ValueError(f"No notes on page {page['page']}")
    tf = slide.notes_slide.notes_text_frame
    tf.text = (
        f"第{page['page']:02d}頁｜正式旁白\n"
        + page["narration"]
        + "\n來源與限制：" + page["references_and_limits"]
    )


def save_merged_presentation(original: Path, updated: Path, destination: Path):
    if destination.exists():
        raise FileExistsError(f"Output already exists: {destination}")
    modified = {
        f"ppt/slides/slide{n}.xml" for n in AUTHOR_SLIDES
    } | {
        f"ppt/notesSlides/notesSlide{n}.xml" for n in PAGES_WITH_NOTES_CHANGED
    } | {
        "ppt/slides/_rels/slide20.xml.rels",
    }
    with zipfile.ZipFile(original) as zin, zipfile.ZipFile(updated) as changed:
        original_names = set(zin.namelist())
        for name in modified:
            if name not in original_names or name not in changed.namelist():
                raise ValueError(f"OOXML part missing: {name}")
        with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_DEFLATED) as zout:
            for info in zin.infolist():
                data = changed.read(info.filename) if info.filename in modified else zin.read(info.filename)
                zout.writestr(info, data)
    return sorted(modified)

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path,
                    default=ROOT / "slides/midterm/FMPA_Midterm.pptx")
    ap.add_argument("--out", type=Path,
                    default=ROOT / "slides/midterm_minimal/FMPA_Midterm_Minimal.pptx")
    ap.add_argument("--design-source", type=Path, default=ROOT / "design.md")
    ap.add_argument("--proposal-source", type=Path,
                    default=ROOT / "docs/midterm/PROPOSAL.md")
    ap.add_argument("--notes-source", type=Path,
                    default=ROOT / "slides/midterm/SLIDE_NOTES.json")
    ap.add_argument("--audit", type=Path, default=ROOT / "slides/midterm_minimal/build_meta.json")
    args = ap.parse_args()

    src = args.source.resolve()
    out = args.out.resolve()
    audit = args.audit.resolve()
    slide_dir = out.parent
    target_root = out.parents[2]
    input_paths = {
        "pptx": src,
        "design": args.design_source.resolve(),
        "proposal": args.proposal_source.resolve(),
        "notes": args.notes_source.resolve(),
    }
    for key, path in input_paths.items():
        if not path.is_file():
            raise FileNotFoundError(f"Missing frozen input {key}: {path}")
    if sha(src) != FORMAL_SOURCE_SHA:
        raise ValueError(f"Frozen formal PPT SHA mismatch: {sha(src)}")
    expected_parent = target_root / "slides" / "midterm_minimal"
    if slide_dir != expected_parent:
        raise ValueError(f"Unexpected out directory: {slide_dir}, expected {expected_parent}")

    expected_outputs = [
        out, slide_dir / "SLIDE_NOTES.json", slide_dir / "SLIDE_NOTES.md",
        target_root / "design.md", target_root / "PROPOSAL_links.md",
        slide_dir / "README.md", audit,
    ]
    if any(p.exists() for p in expected_outputs):
        raise FileExistsError("Refusing overwrite of an existing output")

    notes = revise_notes(json.loads(input_paths["notes"].read_text(encoding="utf-8")))
    content = revise_design(input_paths["design"].read_text(encoding="utf-8"))
    proposal = revise_proposal_links(input_paths["proposal"].read_text(encoding="utf-8"))
    if len(notes["pages"]) != 20 or [n["page"] for n in notes["pages"]] != list(range(1, 21)):
        raise ValueError("Notes page order incorrect")
    if (content.count("## 6. Algorithm") != 1
            or "![查詢流程圖：PPT 第 11 頁](slides/midterm_minimal/png/slide_11.png)"
            not in content
            or len(STEPS) != 12):
        raise ValueError("DESIGN and PPT source contracts not synchronized")

    slide_dir.mkdir(parents=True, exist_ok=True)
    audit.parent.mkdir(parents=True, exist_ok=True)
    native = audit.parent / "working_native.pptx"
    if native.exists():
        raise FileExistsError(f"Staging PPT exists: {native}")

    pres = Presentation(src)
    if len(pres.slides) != 20:
        raise ValueError(f"Expected 20 slides, got {len(pres.slides)}")
    update_p6(pres.slides[5])
    update_p10(pres.slides[9])
    update_p11(pres.slides[10])
    update_p12(pres.slides[11])
    update_p19(pres.slides[18])
    p20_links(pres.slides[19])
    for entry in notes["pages"]:
        if entry["page"] in PAGES_WITH_NOTES_CHANGED:
            edit_notes_slide(pres.slides[entry["page"] - 1], entry)
    pres.save(native)
    parts = save_merged_presentation(src, native, out)

    (slide_dir / "SLIDE_NOTES.json").write_text(
        json.dumps(notes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (slide_dir / "SLIDE_NOTES.md").write_text(
        markdown_notes(notes), encoding="utf-8")
    (target_root / "design.md").write_text(content, encoding="utf-8")
    (target_root / "PROPOSAL_links.md").write_text(proposal, encoding="utf-8")
    readme = r"""# 期中精簡版簡報

- [可編輯 PowerPoint](FMPA_Midterm_Minimal.pptx)
- [20 頁 PDF](FMPA_Midterm_Minimal.pdf)
- [20 張 PNG 預覽](png/slide_01.png)
- [逐頁講稿 Markdown](SLIDE_NOTES.md)／[JSON](SLIDE_NOTES.json)

第 11 頁原生流程圖與第 12 頁 12 行偽碼，
與專案根目錄 `design.md` 第 6 節同步。

## 採用後重新產生（在正式專案根目錄執行）

下列指令只在新的 `outputs/quality_runs/` 子目錄產生候選檔，
不覆寫正式 DESIGN 或現有 PPT；原正式 PPT 輸入經固定 SHA-256 驗證。

```powershell
.\.venv\Scripts\python.exe slides/source/midterm_minimal/build_midterm_minimal.py --source slides/midterm/FMPA_Midterm.pptx --design-source design.md --proposal-source docs/midterm/PROPOSAL.md --notes-source slides/midterm/SLIDE_NOTES.json --out outputs/quality_runs/minimum_sync_rebuild_check_20261107_02/slides/midterm_minimal/FMPA_Midterm_Minimal.pptx --audit outputs/quality_runs/minimum_sync_rebuild_check_20261107_02/build_meta.json
```

預設路徑由專案根目錄計算；已有目標檔時會拒絕覆寫。
PDF／PNG 需以隔離的 Office DispatchEx 另行安全匯出；
只開候選（ReadOnly／Untitled），不可 Quit 共用 PowerPoint。

研究證據以公開市場均價為主；真店 A/B 效益需另行配對驗證。
"""
    (slide_dir / "README.md").write_text(readme, encoding="utf-8")
    audit_payload = {
        "status": "AUTHOR_GENERATED_NOT_EXTERNAL_REVIEWED",
        "source_sha256": sha(src),
        "input_sha256": {name: sha(path) for name, path in input_paths.items()},
        "slide_count": 20,
        "native_edited_slide_pages": sorted(AUTHOR_SLIDES),
        "notes_changed_pages": sorted(PAGES_WITH_NOTES_CHANGED),
        "oo_xml_modified_parts": parts,
        "flow_source": FLOW,
        "pseudocode_steps": STEPS,
        "output_sha256": {
            str(path.relative_to(target_root)): sha(path)
            for path in expected_outputs[:-1]
        },
        "no_model_training_inference_deployment": True,
        "external_review_pass": False,
    }
    audit.write_text(
        json.dumps(audit_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    print(json.dumps({
        "status": "AUTHOR_BUILD_COMPLETE",
        "pptx": str(out), "sha256": sha(out),
        "modified_slides": sorted(AUTHOR_SLIDES),
        "notes_pages": len(notes["pages"]),
        "native_editable": True,
        "new_files": [str(p) for p in expected_outputs],
    }, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
