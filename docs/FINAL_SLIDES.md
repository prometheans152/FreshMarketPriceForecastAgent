# 期末投影片大綱（T33 初稿）：現場菜價 7／14 天預測與分析代理人

> **格式說明**：當屆期末格式未確認（Notion 無法讀取，見 [DELIVERY_CHECKLIST](DELIVERY_CHECKLIST.md)），此為初稿結構；期中逐字稿提到約 15 頁、10 分鐘影片**僅為期中語境**，不當成期末硬規則。正式公告後對齊頁數與時長。
>
> 所有數字與 [FINAL_REPORT.md](FINAL_REPORT.md) 一致並標來源；「建議圖表」指製作實際投影片時應放的圖，本檔為大綱不含圖檔。資料來源文件：[PUBLIC_MODEL_EVALUATION](PUBLIC_MODEL_EVALUATION.md)、[MODEL_SELECTION](MODEL_SELECTION.md)、[BASELINE_REPORT](BASELINE_REPORT.md)、[MODEL_CARD](MODEL_CARD.md)、[ERROR_ANALYSIS](ERROR_ANALYSIS.md)、[RELATED_WORK_MATRIX](RELATED_WORK_MATRIX.md)、[DATA_CARD](DATA_CARD.md)、[DATA_QUALITY_REPORT](DATA_QUALITY_REPORT.md)、[STORE_ADAPTATION_METHOD](STORE_ADAPTATION_METHOD.md)、[LABEL_CONTRACT](LABEL_CONTRACT.md)；JSON 實際數字：`outputs/evaluation/public/public_test_results.json`、`outputs/training/training_results.json`、`outputs/data_quality/prepare_summary.json`。

---

## 第 1 頁　封面

- **標題（工作題名）**：現場菜價 7／14 天預測與分析代理人（TW01）
- 組員名單：**待補**（組員未確認，分組≤4 人、一組交一份——[DELIVERY_CHECKLIST](DELIVERY_CHECKLIST.md)）
- 課程名稱與日期：**待補**
- 建議圖表：手機查價示意（可沿用 `outputs/e2e/ui_ab_mobile_390x844.png` 概念圖）

## 第 2 頁　問題與動機

- 情境：在蔬果行現場看到今天單品報價，想知道「現在買還是等一／兩週」
- 現有工具缺口：查價 App 只比對當日行情、批發走勢工具無店價基準（[RELATED_WORK_MATRIX](RELATED_WORK_MATRIX.md)）
- 本案作法：輸入今天同店價（上週價選填）→ 預測**從今天算起** 7／14 天方向與分析（[design.md](../design.md) 第 1 節）
- 對應課程要求：模型＋領域分析代理人＋量化評估＋網路成果（[DELIVERY_CHECKLIST](DELIVERY_CHECKLIST.md)）
- 建議圖表：使用者情境流程圖（輸入→預測→到期對照）

## 第 3 頁　相關工作與本案差異

- 農產分析 App：輸入現價**比對當日**行情，不預測未來（[RELATED_WORK_MATRIX](RELATED_WORK_MATRIX.md) 第四節）
- 農業大數據平台（2018）：29 億筆電子發票建 15 項農產品零售預測，品項與本案重疊；供內部決策、無消費者輸入
- 白菜即時 App：批發行情＋AI 走勢與採購建議；未見 7／14 天期限與同店到期驗證
- 李岱鑫（清華 2015）：批發價預測＋私人紀錄增益比較；非消費者現場報價、非零售
- 本案另測：現場單筆報價為基準的 t＋7／t＋14 預測＋A/B 同店到期驗證設計——查核範圍內未見相同做法，**不宣稱全球首次**
- 建議圖表：前作對照表（輸入現價？預測未來？同店驗證？三欄打勾表）

## 第 4 頁　資料來源與授權

- 臺中市政府公有零售市場每日蔬果價格（data.gov.tw dataset 84539）
- 授權：政府資料開放授權條款第 1 版；免帳號直接下載、三次下載 SHA256 相同（[DATA_CARD](DATA_CARD.md)）
- 快照：2025-10-04～2026-10-02、364 個日期、4,450 列×63 欄、14 市場
- 單位：元／臺斤（1 台斤＝0.6 公斤）；**0＝無價格（缺測），不是 0 元**
- 建議圖表：資料時間軸＋來源授權標示

## 第 5 頁　資料品質與前處理

- 三品項 905 格 0 值轉缺測（[DATA_QUALITY_REPORT](DATA_QUALITY_REPORT.md)）
- 排除「(停)建國市場」：1,062 列、甘藍沿用價 run 最長 44 天（176 個沿用 run 密集於此）→ 13 市場
- 品項：甘藍（正價觀測 3,786）、青江白菜（4,355）、絲瓜（4,304）；南屯甘藍覆蓋 0% 走資料不足路徑
- 不採用：臺北月表（無逐日）、高雄（來源已下架）（[DATA_CARD](DATA_CARD.md)）
- 建議圖表：市場×品項覆蓋率熱圖（正價格率）

## 第 6 頁　系統架構

- 三節點：TRAIN_LOCAL（本機訓練，CPU）→ SERVER_3090（推論＋Qwen 代理人）→ 手機網頁（[design.md](../design.md) 第 3 節）
- 模型工件 `models/releases/0.1.0/`（manifest＋hash＋fixtures 3/3 重現）；本機 FastAPI `/health`／`/metadata`／`/forecast`（API 層 22 項測試通過、延遲約 200ms）
- 現況：本機已完成（含代理人規則層）；SERVER 待連線（T23 HOLD）
- 建議圖表：架構圖（沿用 [design.md](../design.md) 第 3 節 mermaid 圖重繪）

## 第 7 頁　方法（一）：標籤契約

- 起點 t＝使用者今天（非資料最新日）；目標日 t＋7／t＋14 精確配對，不以前後日暗替（[LABEL_CONTRACT](LABEL_CONTRACT.md)）
- 回歸標籤 r_h＝m(t+h)/m(t)−1；方向：|r_h|≤5% flat、＞+5% up、＜−5% down
- 缺標籤＝`insufficient_data`（不是「未漲」）；標籤成熟＝目標日＋1 日（發布延遲保守假設，未實測）
- 手算邊界例：30→31.5 元（r=+5%）屬 flat；40→42.1 元屬 up
- 建議圖表：標籤定義示意圖（時間軸 t 與 t＋h、門檻帶）

## 第 8 頁　方法（二）：時間切分與特徵

- 切分以日期為單位：train 13,009 列（～2026-05-08）／validation 3,855（～2026-07-21）／test 4,680（2026-07-22～10-02）；清除 1,386 列隔離 14 天標籤重疊；凍結清單 SHA256 `4e136574…`（`prepare_summary.json`）
- 特徵只用查詢時點已可見資料：最新價與年齡、7/14/28 天滾動統計、7/14 天報酬、星期／月、品項 one-hot；無市場 one-hot（未見市場可推論）（[MODEL_CARD](MODEL_CARD.md)）
- 標籤分佈（類別不平衡）：h=7 flat 9,803／down 608／up 541；h=14 flat 8,907／down 902／up 871（`prepare_summary.json`）
- 建議圖表：時間軸切分圖（train／purged／val／test）＋方向類別長條圖

## 第 9 頁　方法（三）：模型候選與選型

- 選型標準（看測試前凍結）：主指標＝驗證集方向 macro-F1（accuracy 被 flat 多數主導）；點 MAE 未優於不變價基線者不作點宣稱；機率／區間未校準不輸出（[MODEL_SELECTION](MODEL_SELECTION.md)）
- 驗證集 macro-F1：h=7 ridge 0.4183／hgb_reg 0.3888／rf_reg **0.4334**／hgb_clf 0.3261／dummy 0.2991；h=14 ridge 0.3811／hgb_reg **0.4591**／rf_reg 0.4428／hgb_clf 0.3624／dummy 0.2857（`training_results.json`）
- 選定：h=7 rf_reg（300 樹、leaf≥5、seed 42）；h=14 hgb_reg（200 迭代、seed 42）；CPU 訓練
- 建議圖表：候選×期限 macro-F1 分組長條圖（標出選定者與 dummy 基線）

## 第 10 頁　量化結果（一）：封存測試總表

- 測試區 2026-07-22～10-02（73 日期、13 市場，一次性執行、凍結 hash 校驗通過）
- h=7 rf_reg：n=2,085、macro-F1 **0.4218** vs 持平基線 0.3092、accuracy 0.7655 vs 0.8647
- h=14 hgb_reg：n=1,859、macro-F1 **0.4169** vs 0.2954、accuracy 0.7106 vs 0.7956
- **點 MAE 未優於不變價基線**：0.0664 vs 0.0436（h=7）；0.0983 vs 0.0748（h=14）——負向結果照實呈報（`public_test_results.json`）
- 建議圖表：模型 vs 基線雙指標對照圖（macro-F1 柱狀＋MAE 柱狀並列）

## 第 11 頁　量化結果（二）：混淆矩陣與分品項

- h=7 混淆矩陣（down/flat/up）：[[57,64,3],[234,1523,46],[43,99,16]]；down recall 0.460、**up recall 0.101**
- h=14：[[61,39,12],[205,1237,37],[74,171,23]]；down recall 0.545、**up recall 0.086**
- 負向結果：up 召回 9–10%，模型偏保守報 flat，「上漲」敏感度有限是本版最大限制（[ERROR_ANALYSIS](ERROR_ANALYSIS.md)）；測試集 momentum 基線 macro-F1 0.4226／0.4306 與選定模型相當（`public_test_results.json`）
- 分品項：絲瓜最強（macro-F1 0.447／0.449）、甘藍 accuracy 最高但 macro-F1 最低（0.320／0.307，漲跌事件少）
- 建議圖表：兩期限混淆矩陣熱圖＋分品項 macro-F1 長條圖

## 第 12 頁　A/B 兩種輸入與同店驗證狀態

- A（無上週價）：方向＝公開模型；店價估計 p(t)×(1+r̂)。**錨定不改方向**——現價輸入只做金額換算，標 `unvalidated`（[STORE_ADAPTATION_METHOD](STORE_ADAPTATION_METHOD.md)）
- B（有上週價）：r_B＝r_A＋0.3×(店價一週變化−公開同期變化)；**實驗性規則，α=0.3 未經任何同店資料擬合**，輸出一律帶警示
- B 可比性：上週須在 t−9～t−5（7±2 天）、單位規格一致；不符自動回 A 附原因
- **T16 HOLD**：缺真實同店到期真值，B 增益尚無證據——不把公開分數寫成同店成果
- 建議圖表：A/B 流程對照圖＋「已驗證／實驗性／未驗證」三色標示

## 第 13 頁　代理人設計

- 責任分界：Qwen 理解、呼叫工具、解釋；菜價模型負責預測；代理人不得編價格／機率／原因／準確率（[design.md](../design.md) 第 5 節）
- 有限工具：`get_market_quote`（取得可用公開行情）、`post_forecast`（呼叫 `POST /forecast`）；入口 `POST /agent/query`；限工具名／端點／次數／超時（[TASKS](../TASKS.md) T26：**本機規則層完成、Qwen 實機待 SERVER**）
- 忠實原則：回答不改變工具方向與數字；Qwen 失敗時顯示真實模型結果，模型失敗不用 LLM 編替代預測（[TASKS](../TASKS.md) T27：本機測試補強中）
- Qwen 候選：使用者指定 Qwen3.8，型號／量化／框架待官方核實與 3090 實測（T25，TODO）
- 建議圖表：代理人工具呼叫時序圖（使用者→Qwen→工具→API→回覆）

## 第 14 頁　本機實作成果與限制

- 已完成（本機，2026-10-04 狀態，98 項自動化測試全過，[GLM_PROGRESS](GLM_PROGRESS.md)）：資料管線、訓練與封存測試、模型打包（fixtures 3/3）、本機 API（API 層 22 項測試）、手機網頁（390×844 實測 A/B 並排與錯誤處理）、公開行情更新與代理人本機規則層
- 限制：點 MAE 未優於不變價基線；up 召回低；僅一年臺中資料；市場均價非單店真值；發布延遲假設 1 日未實測；機率／區間不輸出（[MODEL_CARD](MODEL_CARD.md)）
- 邊界外：囤貨省錢保證、跨年度／颱風行情泛化、同店效果宣稱（[ERROR_ANALYSIS](ERROR_ANALYSIS.md)）
- 建議圖表：本機成果截圖（網頁 A/B 並排）＋限制清單

## 第 15 頁　進行中事項（結尾頁）

- **SERVER 部署（T23 HOLD）**：待使用者提供 OS／位址／連線／目錄／端口／外網方案；之後依序 T24 部署→T25 Qwen 實測→T26/T27 代理人→T29/T32 外網手機
- **同店 A/B 驗證（T16 HOLD）**：待使用者依 [STORE_DATA_PROTOCOL](STORE_DATA_PROTOCOL.md) 記錄同店報價，7／14 天後回填到期真值
- **Qwen3.8 型號核實（T25 TODO）**：官方來源確認名稱／大小／量化／工具呼叫支援
- **期末交付細則**：當屆 Notion 公告無法讀取，格式／期限／影片長度待確認（[DELIVERY_CHECKLIST](DELIVERY_CHECKLIST.md)）
- **組員與分工**：待補
- **期末影片（T35）**：待規格確認後錄製真流程（雙模式、SERVER 代理人、量化與限制）
- 建議圖表：甘特圖或待辦清單（標 HOLD／TODO 與依賴關係）
