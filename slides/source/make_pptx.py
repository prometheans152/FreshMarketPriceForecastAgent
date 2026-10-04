# -*- coding: utf-8 -*-
"""P6（D44-R06 v2 參數化）：產生正式可編輯 PPTX（15 主講＋4 附錄，16:9，微軟正黑體）。

執行範例：
  .venv/Scripts/python.exe slides/source/make_pptx.py \
    --pptx slides/TW01_菜價預測_研究提案與初步成果_v2.pptx \
    --assets slides/assets_v2 \
    --notes slides/source/notes_v2.json \
    --stats outputs/proposal_delivery/run2_20261004_01/stats_master.json
講者備註由 notes_v2.json 單一底稿寫入（與 SLIDE_NOTES.md 同源）。未指定 --force 時拒绝覆寫既有 PPTX。
數字來源：stats_master.json（動機統計）＋ outputs/evaluation/public/public_test_results.json（凍結）。
"""
import argparse
import json
import sys
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parents[2]

DARK = RGBColor(0x1F, 0x3B, 0x5C)
ACCENT = RGBColor(0x2E, 0x75, 0xB6)
GRAY = RGBColor(0x59, 0x59, 0x59)
LIGHT = RGBColor(0xF2, 0xF6, 0xFA)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
RED = RGBColor(0xB0, 0x30, 0x30)
GREEN = RGBColor(0x2F, 0x7D, 0x32)
AMBER = RGBColor(0xC0, 0x7A, 0x00)
FONT = "微軟正黑體"


def build(pptx_path: Path, assets: Path, notes_data: dict, stats: dict, force: bool):
    if pptx_path.exists() and not force:
        print(f"REFUSE: {pptx_path} 已存在（用 --force 覆寫）", file=sys.stderr)
        raise SystemExit(2)
    EVAL = json.loads((ROOT / "outputs/evaluation/public/public_test_results.json").read_text(encoding="utf-8"))
    d = stats["descriptive"]
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    BLANK = prs.slide_layouts[6]
    SW, SH = prs.slide_width, prs.slide_height
    notes_by_id = {s["slide_id"]: s for s in notes_data["slides"]}

    def add_slide():
        return prs.slides.add_slide(BLANK)

    def txbox(slide, l, t, w, h, text, size=18, color=DARK, bold=False, align=PP_ALIGN.LEFT, wrap=True):
        box = slide.shapes.add_textbox(Emu(int(l)), Emu(int(t)), Emu(int(w)), Emu(int(h)))
        tf = box.text_frame
        tf.word_wrap = wrap
        for i, ln in enumerate(text.split("\n")):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = align
            r = p.add_run(); r.text = ln
            r.font.size = Pt(size); r.font.color.rgb = color; r.font.bold = bold; r.font.name = FONT
        return box

    def title_bar(slide, title, subtitle=None):
        bar = slide.shapes.add_shape(1, 0, 0, SW, Inches(0.95))
        bar.fill.solid(); bar.fill.fore_color.rgb = DARK; bar.line.fill.background()
        tf = bar.text_frame; tf.word_wrap = True
        p = tf.paragraphs[0]
        r = p.add_run(); r.text = title
        r.font.size = Pt(28); r.font.bold = True; r.font.color.rgb = WHITE; r.font.name = FONT
        if subtitle:
            p2 = tf.add_paragraph()
            r2 = p2.add_run(); r2.text = subtitle
            r2.font.size = Pt(13); r2.font.color.rgb = RGBColor(0xC9, 0xD8, 0xE8); r2.font.name = FONT

    def footer(slide, page, src):
        txbox(slide, Inches(0.4), Inches(7.05), Inches(10.5), Inches(0.4), f"來源：{src}", size=10, color=GRAY)
        txbox(slide, Inches(12.2), Inches(7.05), Inches(0.9), Inches(0.4), str(page), size=12, color=GRAY, align=PP_ALIGN.RIGHT)

    def bullets(slide, items, l=Inches(0.55), t=Inches(1.25), w=Inches(12.3), size=18, gap=Pt(8)):
        box = slide.shapes.add_textbox(l, t, w, SH - t - Inches(0.6))
        tf = box.text_frame; tf.word_wrap = True
        first = True
        for it in items:
            text, lv = (it if isinstance(it, tuple) else (it, 0))
            p = tf.paragraphs[0] if first else tf.add_paragraph()
            first = False
            p.space_after = gap
            r = p.add_run(); r.text = ("▪ " if lv == 0 else "– ") + text
            r.font.size = Pt(size - lv * 2)
            r.font.color.rgb = DARK if lv == 0 else GRAY
            r.font.name = FONT
        return box

    def add_table(slide, rows, cols, l, t, w, h, data, header_fill=DARK, size=12):
        tblshape = slide.shapes.add_table(rows, cols, l, t, w, h)
        tbl = tblshape.table
        for ri, row in enumerate(data):
            for ci, val in enumerate(row):
                cell = tbl.cell(ri, ci)
                cell.text = str(val)
                for p in cell.text_frame.paragraphs:
                    for r in p.runs:
                        r.font.size = Pt(size); r.font.name = FONT
                        r.font.color.rgb = WHITE if ri == 0 else DARK
                        r.font.bold = ri == 0
                cell.fill.solid()
                cell.fill.fore_color.rgb = header_fill if ri == 0 else (LIGHT if ri % 2 == 0 else WHITE)
        return tbl

    def pic(slide, name, l, t, w=None, h=None):
        p = assets / f"{name}.png"
        if not p.exists():
            print(f"FAIL: 缺圖 {p}", file=sys.stderr)
            raise SystemExit(3)
        if w is not None:
            slide.shapes.add_picture(str(p), l, t, width=w)
        else:
            slide.shapes.add_picture(str(p), l, t, height=h)

    def notes(slide, slide_id):
        rec = notes_by_id[slide_id]
        src_lines = "\n".join(f"來源：{s}" for s in rec.get("sources", []))
        sec = f"（約 {rec['seconds']} 秒）" if rec.get("seconds") else "（附錄，不計時）"
        slide.notes_slide.notes_text_frame.text = f"{rec['script']}\n\n{src_lines}\n\n{sec}"

    def arrow(slide, x1, y1, x2, y2, label=None, color=ACCENT):
        from pptx.enum.shapes import MSO_CONNECTOR
        from lxml import etree
        cxn = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, x1, y1, x2, y2)
        cxn.line.color.rgb = color; cxn.line.width = Pt(2)
        ln = cxn.line._get_or_add_ln()
        te = etree.SubElement(ln, "{http://schemas.openxmlformats.org/drawingml/2006/main}tailEnd")
        te.set("type", "triangle")
        if label:
            txbox(slide, int((x1 + x2) / 2) - int(Inches(1.1)), int((y1 + y2) / 2) - int(Inches(0.22)), int(Inches(2.4)), Inches(0.35), label, size=10, color=color, align=PP_ALIGN.CENTER)

    # ================= 主講 15 頁 =================

    # --- p01 封面 ---
    s = add_slide()
    bg = s.shapes.add_shape(1, 0, 0, SW, SH); bg.fill.solid(); bg.fill.fore_color.rgb = DARK; bg.line.fill.background()
    txbox(s, Inches(0.8), Inches(1.5), Inches(11.7), Inches(1.6), "現場菜價 7／14 天預測與分析代理人", size=40, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
    txbox(s, Inches(0.8), Inches(3.1), Inches(11.7), Inches(0.6), "TW01・研究提案與初步成果（v2 修訂版，2026-10-04）", size=20, color=RGBColor(0xC9, 0xD8, 0xE8), align=PP_ALIGN.CENTER)
    txbox(s, Inches(0.8), Inches(4.1), Inches(11.7), Inches(1.5),
          "摘要：消費者在蔬果行輸入今天單品價格（上週同店價選填），系統以臺中公開市場均價模型\n預測 7／14 天方向並以現價錨定估計店價；A/B 輸入增益以真店到期價驗證（待驗證）。",
          size=15, color=WHITE, align=PP_ALIGN.CENTER)
    txbox(s, Inches(0.8), Inches(6.2), Inches(11.7), Inches(0.5), "組員：待填（≤4人）｜版本日期：2026-10-04（正式發表日期待填）｜課程：AIoT 應用與資料分析", size=14, color=RGBColor(0x9F, 0xB8, 0xD0), align=PP_ALIGN.CENTER)
    notes(s, "p01")

    # --- p02 動機 ---
    s = add_slide()
    title_bar(s, "為什麼值得做：菜價會動，但消費者看不到未來", "動機（證據可查；歷史比例非未來機率）")
    pic(s, "volatility", Inches(0.5), Inches(1.2), w=Inches(7.0))
    bullets(s, [
        (f"實算：7 天脫離 ±5% 持平區合併 {d['h7|ALL']['percent_display']}（{d['h7|ALL']['nonflat']:,}／{d['h7|ALL']['n']:,}）", 0),
        (f"14 天 {d['h14|ALL']['percent_display']}（{d['h14|ALL']['nonflat']:,}／{d['h14|ALL']['n']:,}）", 0),
        ("官方回溯（2004–2009 批發週均價）：颱風後第 1 週平均 +10%–40%（王鎬杰 2010）", 0),
        ("公視 2025-08-13 楊柳颱風「1把蔥380元」（早於本案資料期間，僅歷史背景）", 1),
        ("極端例：合作市場甘藍 2026-07-02→07-09 45→85 元（+88.9%；成因不作主張）", 1),
        ("同時誠實：7 天完全同價佔 86.7–92.8% → 必須跟強基線比", 0),
    ], l=Inches(7.75), t=Inches(1.3), w=Inches(5.15), size=14)
    txbox(s, Inches(0.5), Inches(6.05), Inches(12.4), Inches(0.75),
          "母體＝市場×品項×起算日×期限之歷史觀測配對（含各 split；非獨立天數、非未來機率、非封存測試 n）；正式口徑 ±5% 含邊界（eps=1e-9）——直接浮點 abs(r)>0.05 會多 21 列絲瓜邊界資料，本稿採正式標籤。",
          size=12, color=GRAY)
    footer(s, 2, "run2 stats_master.json（±5%含邊界）；農政與農情219期；data.gov.tw/84539")
    notes(s, "p02")

    # --- p03 RQ ---
    s = add_slide()
    title_bar(s, "研究問題", "RQ1–RQ3")
    bullets(s, [
        ("RQ1｜公開市場固定期限方向預測：臺中均價的 7/14 天方向預測，相對「不變價」與「動量」兩個強基線表現如何？（macro-F1）", 0),
        ("RQ2｜現價／上週價增益：A（今天店價錨定）與 B（＋選填上週同店價）的增益，應如何以真實同店 7/14 天到期價驗證？——目前零證據，屬待驗證", 0),
        ("RQ3｜低負擔與可追溯：單品兩欄輸入、附來源與驗證狀態的呈現，能否兼顧可用與可核對？（人因評估為未來工作）", 0),
        ("使用情境：高麗菜今天 32 元/台斤 → 7 天後（10-11）、14 天後（10-18）相對今天是漲、平還是跌？", 1),
    ], size=18)
    rq_cards = [
        ("RQ1 → C1", "固定期限評估基準", "已驗證", GREEN),
        ("RQ2 → C2", "A/B 輸入增益", "待驗證", AMBER),
        ("RQ3 → C3", "低負擔可追溯呈現", "初步", GRAY),
    ]
    for i, (top_t, mid_t, st, c) in enumerate(rq_cards):
        x = Inches(0.55 + i * 4.25)
        card = s.shapes.add_shape(5, x, Inches(4.6), Inches(4.0), Inches(1.9))
        card.fill.solid(); card.fill.fore_color.rgb = LIGHT; card.line.color.rgb = c; card.line.width = Pt(1.5)
        tf = card.text_frame; tf.word_wrap = True
        p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
        r = p.add_run(); r.text = top_t; r.font.size = Pt(18); r.font.bold = True; r.font.color.rgb = DARK; r.font.name = FONT
        p2 = tf.add_paragraph(); p2.alignment = PP_ALIGN.CENTER
        r2 = p2.add_run(); r2.text = mid_t; r2.font.size = Pt(15); r2.font.color.rgb = DARK; r2.font.name = FONT
        p3 = tf.add_paragraph(); p3.alignment = PP_ALIGN.CENTER
        r3 = p3.add_run(); r3.text = f"證據狀態：{st}"; r3.font.size = Pt(13); r3.font.bold = True; r3.font.color.rgb = c; r3.font.name = FONT
    footer(s, 3, "docs/RESEARCH_MOTIVATION.md；狀態對應 docs/CONTRIBUTIONS.md")
    notes(s, "p03")

    # --- p04 前作分類 ---
    s = add_slide()
    title_bar(s, "相關研究：三類前作", "分類討論（核心 8 件＋官方動向；R08/R09 降待查線索）")
    add_table(s, 5, 4, Inches(0.5), Inches(1.2), Inches(12.3), Inches(4.6), [
        ["類別", "代表前作", "已做到（實讀確認）", "未做／UNKNOWN"],
        ["批發・市場價格預測", "陳泯宏2024[R01]；林沂臻2017[R03]；NCHU 2025[R07]；廖啜翔2021[R11]", "R01：2012–22批發、ARIMA/ETS/TDNN/LSTM，摘要列 RMSE/MAD/MAPE/方向正確率", "消費者店價輸入；固定7/14日曆期限；R11僅書目層級"],
        ["零售・私人資料", "農業大數據平台2018[R04]；李岱鑫2015[R02]", "R04：29億筆電子發票零售估計+颱風情境；R02：私有中盤商資料預測下週批發價（RMSE/MAE）", "消費者輸入；單店真值前瞻到期驗證"],
        ["消費者行情工具", "白菜即時[R05]；農產分析[R06]", "R05官網列中長期趨勢預測/零售換算/價格溫度計；R06輸入買價比對當日行情", "R05模型與效果未公開（UNKNOWN）；R06未列未來期限預測"],
        ["官方動向", "農糧署115年度徵件[R10]", "「生成式AI＋預測式ML＋農產價格」獲政策重視", "生產端決策；公告非成果"],
    ], size=12)
    footer(s, 4, "docs/RELATED_WORK_MATRIX.md（歷史回測/前瞻到期分欄）；run2/r02_work_checks_v2.json")
    notes(s, "p04")

    # --- p05 前作比較 ---
    s = add_slide()
    title_bar(s, "與最接近前作的差異", "本次查核範圍內未見相同組合；不宣稱全球首次")
    add_table(s, 5, 5, Inches(0.4), Inches(1.2), Inches(12.5), Inches(4.2), [
        ["維度", "李岱鑫2015 [R02]", "大數據平台2018 [R04]", "農產分析 [R06]", "本案 TW01"],
        ["輸入", "中盤商手寫筆記(私有)+公開登記", "電子發票（無輸入）", "使用者買價（比對當日）", "今天店價＋選填上週同店價"],
        ["目標", "下週高麗菜批發價(高雄)", "15項農產零售估計+情境模擬", "當日價差合理性", "從今天起 t+7/t+14 方向"],
        ["評估", "歷史回測(RMSE/MAE)", "估計模型(細節未公開)", "無預測指標", "封存測試(macro-F1)+前瞻同店到期協議"],
        ["主要限制", "批發對象；66週小樣本", "通路段估計非店價", "止於當日比對", "B增益零證據；僅一年臺中"],
    ], size=12)
    txbox(s, Inches(0.5), Inches(5.6), Inches(12.3), Inches(0.9),
          "三組缺口：①今天店價基準＋固定日曆期限的評估 ②消費者選填上週價＋同店到期配對驗證 ③低輸入負擔＋主張狀態可追溯的介面（詳 RESEARCH_GAP.md；未重現前作協議，不跨資料比分數）", size=13, color=GRAY)
    footer(s, 5, "docs/RESEARCH_GAP.md；R02=NYCU ETD GH02102077503（摘要實讀）")
    notes(s, "p05")

    # --- p06 三貢獻 ---
    s = add_slide()
    title_bar(s, "三項貢獻與證據狀態", "如實標示：已驗證／待驗證／初步")
    cards = [
        ("C1（已驗證）", "固定 7/14 日曆期限的臺中零售\n方向預測評估：強基線、時間切分、\n封存測試，含負向結果；材料\n可重現（預計隨課程交付公開）", GREEN),
        ("C2（待驗證）", "現價／上週價 A/B 輸入與真店\n到期配對驗證協議；B 目前為\nα=0.3 固定實驗規則（未訓練）", AMBER),
        ("C3（初步）", "主張狀態可追溯的消費者端流程\n與原型：來源、期限、驗證範圍\n標示貫穿文件與介面；效益未驗證", GRAY),
    ]
    for i, (h, body, c) in enumerate(cards):
        x = Inches(0.5 + i * 4.25)
        card = s.shapes.add_shape(5, x, Inches(1.3), Inches(4.0), Inches(0.55))
        card.fill.solid(); card.fill.fore_color.rgb = c; card.line.fill.background()
        p = card.text_frame.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
        r = p.add_run(); r.text = h; r.font.size = Pt(16); r.font.bold = True; r.font.color.rgb = WHITE; r.font.name = FONT
        txbox(s, x, Inches(2.0), Inches(4.0), Inches(2.2), body, size=13, color=DARK)
    bullets(s, [
        ("C1 已有可重現證據：方向 macro-F1 0.4218/0.4169；勝全持平（0.3092/0.2954）、未勝動量（0.4226/0.4306）；點 MAE 未勝不變價", 0),
        ("C2 的增益是本提案明列的待驗證問題；C3 的使用者研究未執行——兩者皆不寫成已證實", 1),
    ], t=Inches(4.35), size=14)
    txbox(s, Inches(0.55), Inches(5.75), Inches(12.2), Inches(0.8),
          "狀態圖例：綠＝已驗證（封存測試可重現）｜黃＝待驗證（協議就緒、證據未取得）｜灰＝初步（原型存在、效益未驗）\n「查核範圍內未見相同組合」是差異描述，不是原創性宣稱；C1 材料預計隨課程交付公開（目前為本地版本控制）。",
          size=13, color=GRAY)
    footer(s, 6, "docs/CONTRIBUTIONS.md；outputs/evaluation/public/")
    notes(s, "p06")

    # --- p07 資料 ---
    s = add_slide()
    title_bar(s, "資料：臺中公有市場每日零售均價", "資料卡與品質報告（口徑如實標示）")
    bullets(s, [
        ("範圍：2025-10-04 ～ 2026-10-02；14 市場排除「(停)建國」→ 13（甘藍有效列涵蓋 12 市場）", 0),
        ("364＝整份原始資料的訪價日數（不代表每市場每品項無缺測）；905＝前三品項 0 值轉缺測格數", 0),
        ("單位：元/台斤（1 台斤 = 0.6 kg）；0 = 當日無價（缺測），不是 0 元", 0),
        ("首版品項：甘藍（平地高麗菜）、青江白菜、絲瓜；無個店 ID——是市場均價，不是某家店", 0),
        ("有效配對（正式標籤）：7 天 10,952（起算至 2026-09-25）／14 天 10,680（至 2026-09-18）", 1),
        ("限制：僅一年、單一城市；發布延遲以保守假設 +1 天處理（未實測）", 1),
        ("來源：data.gov.tw 84539（政府開放授權1.0）；快照 SHA256 172dffc7…（可稽核）", 1),
    ], size=15)
    stats_cards = [("364", "原始資料訪價日"), ("13", "納入市場"), ("10,952", "7天有效配對"), ("905", "缺測格（0=無價）")]
    for i, (num, lab) in enumerate(stats_cards):
        x = Inches(0.55 + i * 3.15)
        card = s.shapes.add_shape(5, x, Inches(5.0), Inches(2.9), Inches(1.45))
        card.fill.solid(); card.fill.fore_color.rgb = LIGHT; card.line.color.rgb = ACCENT; card.line.width = Pt(1.25)
        tf = card.text_frame; tf.word_wrap = True
        p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
        r = p.add_run(); r.text = num; r.font.size = Pt(26); r.font.bold = True; r.font.color.rgb = ACCENT; r.font.name = FONT
        p2 = tf.add_paragraph(); p2.alignment = PP_ALIGN.CENTER
        r2 = p2.add_run(); r2.text = lab; r2.font.size = Pt(12); r2.font.color.rgb = DARK; r2.font.name = FONT
    footer(s, 7, "docs/DATA_CARD.md；docs/DATA_QUALITY_REPORT.md；run2 stats_master.json")
    notes(s, "p07")

    # --- p08 架構（含連接箭頭） ---
    s = add_slide()
    title_bar(s, "系統架構：現況與暫緩", "實線箭頭=已實作之請求/資料流；黃底虛線=暫緩（未部署）")
    boxes = {
        "ui":   (Inches(0.6), Inches(1.5), Inches(3.0), Inches(1.3), "① 手機網頁\n表單/自然語言輸入", LIGHT, True),
        "api":  (Inches(4.6), Inches(1.5), Inches(3.4), Inches(1.3), "② HTTP API (FastAPI)\n/forecast /agent/query /records", LIGHT, True),
        "eng":  (Inches(8.9), Inches(1.5), Inches(3.6), Inches(1.3), "③ ForecastEngine\nRF(7天)/HGB(14天) 封存v0.1.0", LIGHT, True),
        "hist": (Inches(8.9), Inches(3.4), Inches(3.6), Inches(1.1), "④ 凍結公開歷史\npublic_history（唯讀快照）", LIGHT, True),
        "rule": (Inches(4.6), Inches(3.4), Inches(3.4), Inches(1.1), "⑤ 規則代理人+保存層\nrule模式／records凍結預測", LIGHT, True),
        "glm":  (Inches(4.6), Inches(5.35), Inches(3.4), Inches(1.0), "未來A：GLM API 後端\n金鑰未配置", RGBColor(0xFA, 0xF3, 0xE3), False),
        "qwen": (Inches(8.9), Inches(5.35), Inches(3.6), Inches(1.0), "未來B：Qwen3.8-27B 端點\nSERVER 未部署", RGBColor(0xFA, 0xF3, 0xE3), False),
        "herm": (Inches(0.6), Inches(5.35), Inches(3.0), Inches(1.0), "未來C：Hermes 0.19.0\n離線驗證未接真模型", RGBColor(0xFA, 0xF3, 0xE3), False),
    }
    for l, t, w, h, text, fill, solid in boxes.values():
        sh = s.shapes.add_shape(5, l, t, w, h)
        sh.fill.solid(); sh.fill.fore_color.rgb = fill
        sh.line.color.rgb = DARK if solid else GRAY
        sh.line.dash_style = None if solid else 4
        sh.line.width = Pt(1.5) if solid else Pt(1)
        tf = sh.text_frame; tf.word_wrap = True
        p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
        r = p.add_run(); r.text = text; r.font.size = Pt(12); r.font.name = FONT
        r.font.color.rgb = DARK; r.font.bold = solid
    # 連接箭頭（請求↓／回傳↑／資料讀取↓）
    arrow(s, Inches(3.6), Inches(2.15), Inches(4.6), Inches(2.15), "請求")
    arrow(s, Inches(4.6), Inches(2.55), Inches(3.6), Inches(2.55), "回傳")
    arrow(s, Inches(8.0), Inches(2.15), Inches(8.9), Inches(2.15), "叫用")
    arrow(s, Inches(8.9), Inches(2.85), Inches(8.0), Inches(2.85), "預測")
    arrow(s, Inches(10.7), Inches(2.8), Inches(10.7), Inches(3.4), "讀取")
    arrow(s, Inches(6.0), Inches(2.8), Inches(6.0), Inches(3.4), "保存")
    arrow(s, Inches(6.6), Inches(3.4), Inches(6.6), Inches(2.8), "查閱")
    txbox(s, Inches(0.6), Inches(6.55), Inches(12.2), Inches(0.5), "虛線黃底＝D44 暫緩（不修復、不驗收、不接線）；規則代理人設計上不呼叫語言模型，介面以規則模式作展示載體，不宣稱已通過課程全部代理人要求", size=11, color=GRAY)
    footer(s, 8, "design.md §1（①–⑤與未來A–C）；docs/AGENT_RUNTIME_DIRECTION.md")
    notes(s, "p08")

    # --- p09 時間切分（真實清除帶） ---
    s = add_slide()
    title_bar(s, "7／14 天目標與時間切分", "防洩漏設計；清除帶為實際 purge 分布")
    pic(s, "time_split", Inches(0.7), Inches(1.25), w=Inches(10.2))
    bullets(s, [
        ("標籤契約（凍結於看測試前）：r_h = m(t+h)/m(t) − 1；±5% 含邊界為持平（eps=1e-9）；缺到期價＝無標籤", 0),
        ("同日 13 市場進同區；成熟清除實際兩段：train 尾 04-25～05-09（695 列）＋ val 尾 07-08～07-21（691 列）＝1,386 列/30 起算日", 0),
        ("封存測試一次性（清單 SHA256 4e136574…）；期限永遠從使用者今天 t 起算", 1),
    ], t=Inches(4.6), size=14)
    footer(s, 9, "docs/LABEL_CONTRACT.md；run2 stats_master.json purge（唯讀重算）；manifest.json splits")
    notes(s, "p09")

    # --- p10 A/B（教學例標示） ---
    s = add_slide()
    title_bar(s, "A/B 兩種輸入與一個數字例", "A=現價錨定；B=上週價實驗規則；數字例含教學假設（已標）")
    txbox(s, Inches(0.5), Inches(1.2), Inches(6.2), Inches(0.5), "公式", size=17, bold=True)
    txbox(s, Inches(0.5), Inches(1.7), Inches(6.2), Inches(2.6),
          "A 店價估計：p̂(t+h) = p(t) × (1 + r̂_h)\nB 調整：r_B = r_A + α × (Δ店價7日 − Δ公開同期)\n　α = 0.3（開發期固定；未經同店資料訓練）\n\n錨定不變向：p>0 時 [p(1+r̂)−p]/p = r̂\n→ 同一 ±5% 分類器方向不變；輸入現價只改金額\nsign 為負 ≠ down（−4.1% 仍屬持平）",
          size=14)
    txbox(s, Inches(0.5), Inches(4.5), Inches(6.2), Inches(0.5), "輸入負擔", size=17, bold=True)
    txbox(s, Inches(0.5), Inches(5.0), Inches(6.2), Inches(1.4), "A：1 個必填（今天價格）＋品項\nB：再加 2 個選填（上週價＋實際日期）\n上週不可比（7±2天外/換店/換規格/跨品項）→ 自動回 A 並說明", size=14)
    card = s.shapes.add_shape(5, Inches(7.1), Inches(1.2), Inches(5.7), Inches(5.3))
    card.fill.solid(); card.fill.fore_color.rgb = LIGHT; card.line.color.rgb = ACCENT
    txbox(s, Inches(7.35), Inches(1.4), Inches(5.3), Inches(0.5), "數字例（甘藍；教學計算非真店實驗）", size=15, bold=True)
    txbox(s, Inches(7.35), Inches(1.95), Inches(5.3), Inches(4.4),
          "輸入：今天 32 元/台斤〔教學假設〕；上週同店 28 元〔教學假設〕\n\n模型（市場）：r̂_7 = −4.1% → 持平〔封存 fixture 輸出〕\n　　　　　　r̂_14 = −0.9% → 持平〔封存 fixture 輸出〕\n\nA：7天後 ≈ 30.7 元、14天後 ≈ 31.7 元\n\nB：店價週變化 = 32/28−1 = +14.29%〔教學〕\n　公開同期 +1.0%〔教學〕\n　r_B = −4.1% + 0.3×13.29% ≈ −0.11%（仍持平；\n　接近 0，非接近 ±5% 門檻）\n\n回應附：資料截止日、點估計僅供參考、B 實驗性未驗證",
          size=12.5)
    footer(s, 10, "r̂＝封存 fixtures；32/28/+1%＝教學假設；store_adapter.py（α=0.3）")
    notes(s, "p10")

    # --- p11 模型（候選修正） ---
    s = add_slide()
    title_bar(s, "模型與公平比較設計", "選型凍結於看測試前")
    bullets(s, [
        ("候選：回歸（Ridge／HistGradientBoostingRegressor／RandomForestRegressor）預測 r_h；分類（DummyMajority／HistGradientBoostingClassifier）；以驗證集 macro-F1 選型（凍結後才碰封存測試）", 0),
        ("選定：7 天 RF(300樹)、14 天 HGB(200輪)；seed 42；輸入＝12 個數值特徵（t−1 前可見）＋品項 one-hot（非無條件 12 維）", 0),
        ("兩個強基線（與模型同測試列）：不變價（全持平）、動量（過去同長度變化延續）", 0),
        ("指標：方向 macro-F1（持平多數使 accuracy 易誤導）；r 的 MAE（非元、非準確率）", 0),
        ("未做（列為計畫，不補造）：參數敏感度、特徵消融、與近期代表方法在同資料上的直接比較", 1),
    ], size=15)
    design_cards = [
        ("選型時序", "驗證集 macro-F1 選型\n→ 凍結（看測試前）\n→ 封存測試一次性"),
        ("兩個強基線", "不變價（全預測持平）\n動量（過去同長度\n變化延續）"),
        ("指標選擇", "macro-F1（持平多數下\naccuracy 易誤導）\n＋ r 之 MAE（非元）"),
    ]
    for i, (h, body) in enumerate(design_cards):
        x = Inches(0.55 + i * 4.25)
        card = s.shapes.add_shape(5, x, Inches(4.75), Inches(4.0), Inches(1.75))
        card.fill.solid(); card.fill.fore_color.rgb = LIGHT; card.line.color.rgb = ACCENT; card.line.width = Pt(1.25)
        tf = card.text_frame; tf.word_wrap = True
        p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
        r = p.add_run(); r.text = h; r.font.size = Pt(15); r.font.bold = True; r.font.color.rgb = DARK; r.font.name = FONT
        p2 = tf.add_paragraph(); p2.alignment = PP_ALIGN.CENTER
        r2 = p2.add_run(); r2.text = body; r2.font.size = Pt(13); r2.font.color.rgb = GRAY; r2.font.name = FONT
    footer(s, 11, "src/aiot_price/models/train.py（唯讀）；docs/MODEL_SELECTION.md；training_results.json")
    notes(s, "p11")

    # --- p12 結果 ---
    s = add_slide()
    title_bar(s, "封存測試結果（公開市場均價）", "正向與負向並列——這是誠實的成績單")
    pic(s, "f1_vs_baselines", Inches(0.45), Inches(1.1), w=Inches(5.7))
    pic(s, "mae_negative", Inches(0.45), Inches(4.21), w=Inches(5.7))
    bullets(s, [
        ("方向 macro-F1：7 天 0.4218、14 天 0.4169", 0),
        ("勝全持平基線（0.3092 / 0.2954）", 1),
        ("未勝動量基線（0.4226 / 0.4306）", 1),
        ("點估計 MAE 未勝不變價（0.0664 vs 0.0436；0.0983 vs 0.0748）→ 點估計僅供參考", 0),
        ("up 召回 10.1%/8.6%：模型偏保守報持平，「會漲」警示價值受限", 0),
        ("無檢定 → 不寫「顯著」；樣本相關 → 不當獨立", 1),
    ], l=Inches(7.1), t=Inches(1.3), w=Inches(5.8), size=14)
    footer(s, 12, "public_test_results.json（SHA256 2d28acd2…，可重算）；n=2,085/1,859")
    notes(s, "p12")

    # --- p13 介面 ---
    s = add_slide()
    title_bar(s, "介面現況與限制", "原型截圖（2026-10-03，本機瀏覽器）")
    shot = ROOT / "outputs/e2e/ui_ab_mobile_390x844.png"
    if shot.exists():
        s.shapes.add_picture(str(shot), Inches(0.7), Inches(1.2), height=Inches(5.4))
    bullets(s, [
        ("已實作（本機）：表單/自然語言兩入口、A/B 並列、保存→到期核對、匯出/刪除（request_id 綁定伺服器預測）", 0),
        ("主張狀態進畫面：資料截止日、驗證範圍、B 實驗性警示", 0),
        ("限制：本機原型（規則模式）；未部署外網（T32 HOLD）；代理人後端整合暫緩", 1),
        ("截圖為 2026-10-03 原型，展示當時已實作之功能範圍", 1),
    ], l=Inches(4.3), t=Inches(1.5), w=Inches(8.5), size=15)
    footer(s, 13, "outputs/e2e/ui_ab_mobile_390x844.png；docs/UI_FLOW.md")
    notes(s, "p13")

    # --- p14 驗證/OpenSpec ---
    s = add_slide()
    title_bar(s, "分階段驗證計畫與規格管理", "design.md 藍圖＋OpenSpec 變更管理")
    add_table(s, 4, 3, Inches(0.5), Inches(1.25), Inches(12.3), Inches(3.0), [
        ["C/RQ", "證據", "狀態"],
        ["C1 / RQ1", "封存測試 JSON+CSV（可重算）；基線並列", "已驗證（含負向）"],
        ["C2 / RQ2", "A/B 協議＋凍結預測保存；真店 7/14 天到期價", "協議就緒／增益待驗證（T16）"],
        ["C3 / RQ3", "原型＋主張→來源→狀態追溯鏈（claims_master.csv）", "初步／人因未測"],
    ], size=14)
    bullets(s, [
        ("規格管理：OpenSpec 1.14.0（局部安裝）；change「prepare-tw01-proposal-package」含 D44 修訂 tasks；validate --strict 通過（格式通過≠內容驗收）", 0),
        ("時間表（日期待填）：真店收集啟動 → 參數敏感度 → SERVER 部署與外網 → 期末全案驗收（各項單獨驗收，不互相冒充）", 0),
    ], t=Inches(4.6), size=14)
    footer(s, 14, "run2 openspec CLI 紀錄；docs/OPENSPEC_WORKFLOW.md")
    notes(s, "p14")

    # --- p15 結論 ---
    s = add_slide()
    title_bar(s, "結論與下一步")
    bullets(s, [
        ("回答 RQ1：固定期限＋強基線的零售評估可行且可重現；模型方向訊號存在（勝持平）但未勝動量、點誤差未勝不變價", 0),
        ("回答 RQ2/RQ3：協議與原型就緒；增益與人因皆待驗證——這是接下來的工作，不是已完成的成果", 0),
        ("下一步：①啟動真店到期收集（T16） ②參數敏感度與近期方法同資料比較 ③SERVER 部署與外網評估（T24/T29/T32） ④使用者研究", 0),
        ("一句話總結：我們交付的不是「很準的預測」，而是一個誠實可驗證的預測與增益評估框架", 1),
    ], size=16)
    txbox(s, Inches(0.55), Inches(5.6), Inches(12.2), Inches(0.8), "感謝聆聽——歡迎提問（附錄：分品項/混淆矩陣/文獻/公式）", size=16, bold=True, align=PP_ALIGN.CENTER)
    footer(s, 15, "docs/PROPOSAL_REPORT.md W–Z")
    notes(s, "p15")

    # ================= 附錄 =================
    s = add_slide()
    title_bar(s, "附錄 A1：分品項 macro-F1", "公開市場均價測試")
    pic(s, "by_crop", Inches(1.2), Inches(1.3), w=Inches(9.0))
    txbox(s, Inches(1.2), Inches(5.8), Inches(10.5), Inches(0.9), "甘藍方向事件最少（7 天脫離持平 6.8%），macro-F1 最低屬預期；絲瓜 12.7%、青江白菜 11.6%，事件多、訊號較強；14 天各為 12.8%/18.3%/18.3%。樣本數見圖上標註（正式口徑 ±5% 含邊界）。", size=13, color=GRAY)
    footer(s, "A1", "public_test_results.json by_crop；run2 stats_master.json")
    notes(s, "p16")

    s = add_slide()
    title_bar(s, "附錄 A2：7 天混淆矩陣", "列=實際；RF")
    pic(s, "confusion_h7", Inches(0.6), Inches(1.3), w=Inches(5.3))
    bullets(s, [
        ("up 召回 = 16/158 約 10.1%：預測過保守", 0),
        ("down 召回 = 57/124 約 46%：跌勢抓得相對好", 0),
        ("flat 精確率 0.90：報持平時多半正確", 0),
        ("門檻 ±5%（含邊界）的敏感度分析未執行（計畫）", 1),
    ], l=Inches(6.35), t=Inches(1.8), w=Inches(6.2), size=15)
    footer(s, "A2", "public_test_results.json confusion")
    notes(s, "p17")

    s = add_slide()
    title_bar(s, "附錄 A3：引用清單（[R01…R11]）")
    refs = [
        "R01 陳泯宏(2024) 國產大宗蔬菜價格預測模型之比較. 臺大統計碩士學位學程. (摘要全文實讀；DOI 10.6342/NTU202400875)",
        "R02 李岱鑫(2015) 高雄果菜運銷公司高麗菜批發價格預測之研究—蒐集私有資料的價值. 清華. (摘要實讀)",
        "R03 林沂臻(2017) HHT菜價預測. 中山醫大碩士. (索引摘要)",
        "R04 農委會×財政資訊中心(2018) 農業大數據平台零售估計. 豐年社報導. (報導全文)",
        "R05 flux6lab 白菜即時 App/官網. (官網實讀 2026-10-04；中長期趨勢預測/零售換算文案)",
        "R06 鹿中創客 農產分析 App. (Google Play 文案實讀 2026-10-04)",
        "R07 YuehChun(2025) NCHU-Data-Mining-Project. GitHub. (repo)",
        "R11 廖啜翔(2021) 以深度學習方式探討臺灣結球白菜之價格. 臺大農經碩士. (僅書目)",
        "R10 農糧署(2026) 115年度AI+ML農產價格先導研究徵件. (PDF全文)",
        "R08 洪士育(北科大)、R09 陳澤維(政大)：書目未定位 → 待查線索，不作核心引用",
    ]
    bullets(s, [(r, 0) for r in refs], l=Inches(0.6), t=Inches(1.15), w=Inches(12.2), size=12, gap=Pt(4))
    footer(s, "A3", "docs/REFERENCES.md（完整書目/入口/讀取層級）")
    notes(s, "p18")

    s = add_slide()
    title_bar(s, "附錄 A4：公式彙整與課程要求對照")
    txbox(s, Inches(0.5), Inches(1.15), Inches(6.1), Inches(5.4),
          "公式彙整\n\nr_h = m(t+h)/m(t) − 1\n方向：±5% 含邊界（eps=1e-9）；|r|≤5% flat\n\nA：p̂(t+h) = p(t)·(1+r̂_h)\nB：r_B = r_A + 0.3·(Δ店價7日 − Δ公開同期)\n單位：1 台斤 = 0.6 kg；50元/kg ≡ 30元/台斤\n\n錨定不變向：p>0 ⇒ [p(1+r)−p]/p = r\n→ 同一 ±5% 分類器方向不變\nsign 負 ≠ down（−4.1% 仍 flat）；α 屬 B 實驗規則非命題條件", size=13)
    add_table(s, 6, 2, Inches(6.9), Inches(1.2), Inches(5.9), Inches(3.6), [
        ["課程要求", "本案對應"],
        ["一定要有模型", "RF/HGB 封存評估（T15）"],
        ["希望使用 Agent", "介面原型＋後端整合暫緩（如實標示）"],
        ["量化評估", "macro-F1/MAE/混淆矩陣＋基線"],
        ["網路上可操作", "本機原型；外網部署待 SERVER（T32）"],
        ["design.md 藍圖", "D44-R05 修訂版＋OpenSpec 管理"],
    ], size=12)
    footer(s, "A4", "design.md §3；docs/COURSE_REQUIREMENTS.md")
    notes(s, "p19")

    pptx_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(pptx_path))
    print("saved:", pptx_path)
    print("slides:", len(prs.slides._sldIdLst))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pptx", default=str(ROOT / "slides/TW01_菜價預測_研究提案與初步成果_v2.pptx"))
    ap.add_argument("--assets", default=str(ROOT / "slides/assets_v2"))
    ap.add_argument("--notes", default=str(ROOT / "slides/source/notes_v2.json"))
    ap.add_argument("--stats", default=str(ROOT / "outputs/proposal_delivery/run2_20261004_01/stats_master.json"))
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    notes_data = json.loads(Path(args.notes).read_text(encoding="utf-8"))
    stats = json.loads(Path(args.stats).read_text(encoding="utf-8"))
    build(Path(args.pptx), Path(args.assets), notes_data, stats, args.force)


if __name__ == "__main__":
    main()
