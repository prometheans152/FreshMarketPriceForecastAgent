# TW01 現場菜價 7／14 天預測與分析代理人

**AIoT 應用與資料分析期末專題・研究提案與初步成果（2026-10-04，D44-R01–R06 修訂版）**
組員：待填（≤4 人，組長待填）｜正式發表日期：待填｜[本機重現入口](#本機使用與重現)見文末

## 一句話情境

消費者站在蔬果行，看到今天甘藍一台斤 32 元——**未來 7／14 天，這個價格相對今天是漲、平還是跌？** 使用者輸入今天單品價格（上週同店同規格價選填），系統以臺中公開市場均價模型預測方向、以現價錨定估計店價，並附來源、期限與驗證狀態標示。

## 研究問題

| # | 問題 | 狀態 |
| --- | --- | --- |
| RQ1 | 臺中公開市場均價的固定 7／14 天方向預測，相對「不變價」與「動量」強基線表現如何？ | 已有封存測試答案（含負向結果） |
| RQ2 | 現價錨定（A）與選填上週同店價（B）的增益，如何以真店到期價驗證？ | 協議就緒；增益零證據，待驗證 |
| RQ3 | 低輸入負擔與可追溯呈現能否兼顧？ | 原型就緒；人因未測 |

## 三項貢獻（誠實標狀態）

1. **C1（已驗證）**：固定 7/14 日曆期限、強基線對照、含負向結果的臺中零售方向預測評估——材料可重現，預計隨課程交付公開。
2. **C2（待驗證）**：A/B 現價／上週價輸入與**真店到期配對驗證協議**（B 目前為 α=0.3 固定實驗規則，未訓練）。
3. **C3（初步）**：主張狀態可追溯的消費者端研究流程與原型（使用者效益未驗證）。

## 方法概覽

- **資料**：data.gov.tw 84539 臺中 13 市場每日零售均價（2025-10-04～2026-10-02；元/台斤；0=無價）。
- **標籤契約（凍結）**：r_h = m(t+h)/m(t) − 1；±5% 含邊界為持平；期限從使用者今天 t 起算之精確日曆日 t+7/t+14。
- **防洩漏**：時間切分＋成熟清除（兩段共 1,386 列）＋封存測試一次性。
- **模型**：驗證集 macro-F1 選型→7 天 RandomForest、14 天 HistGradientBoosting；輸入＝12 個數值特徵＋品項 one-hot。
- **A/B**：A 現價錨定（p>0 時 [p(1+r̂)−p]/p=r̂，同一 ±5% 分類器方向不變）；B 加上週價差動量（α=0.3 實驗規則）。

## 初步結果（正向與負向並列）

- 方向 macro-F1：7 天 **0.4218**、14 天 **0.4169**——勝全持平基線（0.3092/0.2954）、**未勝動量基線**（0.4226/0.4306）。
- 點估計 MAE **未勝不變價**（0.0664 vs 0.0436；0.0983 vs 0.0748）→ 點估計僅供參考。
- 上漲召回僅約 10%：模型偏保守報持平。無檢定不寫「顯著」。
- 誠實結論：我們交付的不是「很準的預測」，而是一個**誠實、可驗證**的預測與增益評估框架。

## 正式交付入口（本輪 v2）

| 交付物 | 位置 |
| --- | --- |
| **投影片（可編輯）** | `slides/TW01_菜價預測_研究提案與初步成果_v2.pptx`（主講 15＋附錄 4＝19 頁） |
| **投影片 PDF** | `slides/TW01_菜價預測_研究提案與初步成果_v2.pdf`（19 頁，與 PPTX 同源） |
| **逐頁講稿（約 10–11 分鐘設計）** | [docs/SLIDE_NOTES.md](docs/SLIDE_NOTES.md)（與 PPT 內嵌備註同一底稿 `slides/source/notes_v2.json`） |
| **研究提案全文（A–Z）** | [docs/PROPOSAL_REPORT.md](docs/PROPOSAL_REPORT.md) |
| **設計藍圖** | [design.md](design.md)（架構①–⑤／資料流／公式／切分與驗證） |
| **研究動機與 RQ** | [docs/RESEARCH_MOTIVATION.md](docs/RESEARCH_MOTIVATION.md) |
| **相關研究** | [矩陣](docs/RELATED_WORK_MATRIX.md)｜[缺口](docs/RESEARCH_GAP.md)｜[引用清單](docs/REFERENCES.md) |
| **三貢獻** | [docs/CONTRIBUTIONS.md](docs/CONTRIBUTIONS.md) |
| **規格管理** | `openspec/`（OpenSpec 1.14.0 局部安裝；validate --strict 通過）｜[工作流說明](docs/OPENSPEC_WORKFLOW.md) |
| **主張→證據追溯** | `outputs/proposal_delivery/run2_20261004_01/claims_master.csv`（27 列） |
| **本輪修訂報告** | [docs/D44_REVISION_REPORT.md](docs/D44_REVISION_REPORT.md)（R01–R06 逐項） |
| **驗收狀態** | [docs/PROPOSAL_ACCEPTANCE.md](docs/PROPOSAL_ACCEPTANCE.md) |

## 已完成／待驗證／暫緩（如實分列）

**已完成（本機、可重現）**：公開資料管線、模型訓練與封存評估（含負向結果）、模型包 v0.1.0、HTTP API、手機網頁原型（A/B 並列＋保存到期核對）、規則代理人（展示載體）、研究提案全套文稿與 v2 簡報。

**待驗證（有協議、未執行）**：真店 A/B 到期增益（T16，缺真店到期價）；B 之 α=0.3 未訓練；使用者人因評估；參數敏感度與近期方法同資料比較。

**暫緩（D44 決議不修不驗）**：GLM API／Qwen3.8-27B／SERVER_3090 部署與外網展示（T23–T32）；代理人語言模型後端整合（保留已知缺口，見 [代理人方向](docs/AGENT_RUNTIME_DIRECTION.md)）。

**未完成交付**：**影片未錄製**；**GitHub／YouTube／課程提交未發布**（待授權）；組員／組長／正式日期待填。

## 本機使用與重現

- 環境：Windows＋`.venv`（pandas 2.3.3、pyarrow 25.0.1、scikit-learn、python-pptx 1.0.2、matplotlib 3.11.2、pywin32 312、pypdf 6.19.0；PowerPoint（COM 匯出用）與微軟正黑體）。本清單為現有環境盤點，未做乾淨環境重建驗證。
- 啟動 API（規則模式展示）：`.venv\Scripts\python.exe -m uvicorn aiot_price.api.app:app`（詳 [design.md](design.md)）。
- 重建 v2 簡報（全部參數化、防覆寫）：
  1. `.venv/Scripts/python.exe slides/source/build_stats_master.py --out <新run>/stats_master.json`
  2. `.venv/Scripts/python.exe slides/source/make_assets.py --out <新素材目錄> --stats <新run>/stats_master.json`
  3. `.venv/Scripts/python.exe slides/source/make_pptx.py --pptx <新pptx> --assets <素材> --notes slides/source/notes_v2.json --stats <新run>/stats_master.json`
  4. `.venv/Scripts/python.exe slides/source/export_and_render.py --pptx <新pptx> --render <新run>/render`
- 製作工具測試：`.venv/Scripts/python.exe -m pytest slides/source/test_make_tools.py -q`（15 項）。
- 版本管理：本地 Git（未推送）；`data/`、`private/`、`models/`、`outputs/` 不入庫。

---

## 歷史與輔助文件（選題已完成，以下僅供追溯）

本專題選題已定為 TW01，不再重新選題；舊規則與清單僅屬歷史。執行狀態主入口是 [TASKS.md](TASKS.md) 與 [docs/GLM_PROGRESS.md](docs/GLM_PROGRESS.md)；決策紀錄見 [docs/DECISIONS.md](docs/DECISIONS.md)。

| 類別 | 文件 |
| --- | --- |
| 執行與審查 | [TASKS.md](TASKS.md)｜[GLM_PROGRESS.md](docs/GLM_PROGRESS.md)｜[D44 修訂報告](docs/D44_REVISION_REPORT.md)｜[來源核對](docs/PROPOSAL_SOURCE_AUDIT_20261004.md)｜[修訂工作單](docs/GLM_D44_R01_R06_REVISION_20261004.md) |
| 工程與模型 | [MODEL_VALIDATION_PLAN.md](docs/MODEL_VALIDATION_PLAN.md)｜[MODEL_CARD](docs/MODEL_CARD.md)｜[公開評估](docs/PUBLIC_MODEL_EVALUATION.md)｜[資料卡](docs/DATA_CARD.md)｜[資料品質](docs/DATA_QUALITY_REPORT.md)｜[標籤契約](docs/LABEL_CONTRACT.md) |
| 課程與背景 | [課程要求](docs/COURSE_REQUIREMENTS.md)｜[專案背景](docs/PROJECT_CONTEXT.md)｜[AGENTS.md](AGENTS.md)｜[代理人方向](docs/AGENT_RUNTIME_DIRECTION.md)｜[交付清單](docs/DELIVERY_CHECKLIST.md)｜[TW01 需求與歷史](docs/ideas/TW01_VEGETABLE_BASKET.md) |
| 選題歷史（全數已結案） | [U01–U50](docs/ORDINARY50_TOPIC_CATALOG.md)｜[G01–G50](docs/GENERAL50_TOPIC_CATALOG.md)｜[H01–H16](docs/H16_TOPIC_CATALOG.md)｜[W01–W50](docs/WORK50_TOPIC_CATALOG.md)｜[N01–N50](docs/NEW50_TOPIC_CATALOG.md)｜[臺灣短名單](docs/TAIWAN_TOPIC_SHORTLIST.md)｜[原 50 題](docs/TOPIC_CATALOG.md)｜[保留備案 N18/G02/G41](docs/DECISIONS.md) |
| 前作查核（歷史輪） | [TW01 菜價重查](docs/research/TW01_RELATED_WORK_RECHECK.md)｜[TW01 零售公開資料](docs/research/TW01_PUBLIC_RETAIL_DATA.md)｜[G02/G41 重查](docs/research/G02_G41_RELATED_WORK_RECHECK.md) |

## 版本管理附註

- 原始逐字稿 `會議錄音 10.txt` 保留原位，不入 Git（課堂原始內容）。
- `data/`、`private/`、`recordings/`、`models/`、`outputs/` 及環境檔預設忽略。
- 歷史提交：`6eb4adf`（D44 首輪六包）← `2f7199e`（第五輪 S01–S09 自驗）← 更早各輪；修訂輪提交見 Git log。各輪獨立審查報告在 `outputs/audits/`（本機）。
