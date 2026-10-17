# Fresh Market Price Forecast Agent — GLM Coding Agent 工作與品質管線（AGENTS.md）

> 本檔是 `C:\Users\prometheans\Documents\AIOT_FinishProject` 的常駐工作規範，ZCode／GLM coding agent 每次接手必須先讀；是否由工具自動載入需依實際設定確認。
> **GLM 是執行者；ChatGPT（透過 COS）是外部獨立審查者。** 專案產品內的「Domain AI Agent」不是 GLM coding agent。
> 使用者本次明確指示優先；教授原始規範／逐字稿／檔案是研究與驗收來源，**不是額外授權**。本檔只要求更嚴格的檢查，不得自行擴張工作範圍。

## 0. 啟動時先讀：不靠歷史「全 PASS」接手

1. 確認工作目錄是 **`C:\Users\prometheans\Documents\AIOT_FinishProject`**；核對 `git rev-parse HEAD`、`git status --short`、`git diff --name-only`，先列出既有未追蹤產物。只動本次授權的檔案。
2. 依任務按需讀取 `README.md`、`TASKS.md`、`design.md`、`docs/DECISIONS.md`、`docs/COURSE_REQUIREMENTS.md`、`docs/PROPOSAL_REPORT.md`、`docs/RELATED_WORK_MATRIX.md`、`docs/REFERENCES.md`、`docs/proposal_v5/` 與 `slides/source/proposal_v5/`。不得只讀先前摘要或 GLM 自己的驗收結論。
3. **讀最近的 ChatGPT 獨立審查原文**，目前為 outputs/audits/proposal_v5_r3_independent_20261009_01/REVIEW_R3.md，結論 **EXTERNAL_PASS（僅 Proposal v5 r3）**；此前 r2 Request changes 已關閉，為歷史證據。每次均以最新審查及其實際範圍為準，GLM 自驗不能代替外審。
4. 不要自動恢復已暫緩的產品 Agent／Hermes／GLM API／Qwen3.8-27B／SERVER 部署。Proposal 文件工作與產品 Agent 開發是**不同關卡**。
5. 若工作區、工具、資料或審查原檔不可讀：明確寫 `BLOCKED` 與原始錯誤；**不能用臆測或成功的歷史紀錄替代本次操作**。

## 1. 不變的專題定義

- 正式題目 **「現場菜價 7／14 天預測與分析代理人」（Fresh Market Price Forecast Agent；選題期編號 TW01，歷史文件仍以此稱呼）**；禁止重新找題、換題、恢復整籃採買或另開正式專案。
- 使用者在市場看到**今天單店、單品項價格**；上週**同店、同品項、同規格**價格選填。A＝今天店價＋公開歷史；B＝再納入可比的上週價；兩者從使用者當天 `t` 算**精確 t+7／t+14 日曆日**，沒有 B 仍可用 A。
- 公開市場均價 **不是** 個店真值。0＝無報價／缺測，不是零元；不拿公開 t−7 冒充私人店價；不拿市場測試分數冒充店價準確率。
- 正式菜價預測值來自 **ForecastEngine／已訓練 RF（7天）與 HGB（14天）**，不是 LLM 猜價。B 的 `α=0.3` 是固定實驗規則，**非**學得增益。真店 A/B 到期配對驗證尚無證據，不可寫已成功。
- 既有測試必須如實呈現：7天 macro-F1 `0.4218` vs 動量 `0.4226`；14天 `0.4169` vs 動量 `0.4306`；相對變化 MAE 分別 `0.0664/0.0983`，均未勝不變價 `0.0436/0.0748`；上漲召回約 `10.1%/8.6%`。**以封存 JSON 的完整精度為準**，以上僅口頭展示四捨五入值。不得重訓、偷調門檻、換指標或藏負向結果讓簡報好看。
- 本機 Windows 是 `TRAIN_LOCAL`；另一台 RTX 3090 是 `SERVER_3090`（連線與部署資訊未確認）。產品語言模型原定 **Qwen3.8-27B**，2026-10-17 起**封存**（未廢棄，見 docs/DECISIONS.md D46）；可替換 GLM API；Hermes 只是暫定框架；三者接線／實機後端皆不能假稱完成。

## 2. 十關品質管線：每關輸出是下一關的輸入

**本檔借用 MCU 工作法的分關、獨立審查、失敗退回，但沒有 STM32／CubeMX／燒錄步驟。**
工作包的**全部授權範圍內**可以連續做到 GLM 自驗完成，不必每個細節都問使用者；在 `★` 停點或超出授權時才停。未來產品 Agent 改造需另外明確授權，不能因本規範存在就啟動。

| 關 | 關卡 | 必交證據／過關條件 |
| --- | --- | --- |
| S00 | 環境、任務、範圍與保護基準 | 原任務、允許/禁止改檔、最新外審、Git 快照、基準檔 hash、真實工具權限 |
| S10 | 需求與來源檢核 | 教授要求逐項矩陣；研究/網頁/PDF 實際讀取範圍；UNKNOWN 清單 |
| S20 | 研究與領域證據 | Abstract/Intro/Related Work、Team17 差異、5思維/3爭論/10問題、可追溯引用 |
| S30 | Proposed Agent 設計 | Architecture、Flowchart、行號 Pseudocode 三者對照；CURRENT/PARTIAL/PROPOSED；工具真名映射 |
| S40 | 文件產物及一致性 | Proposal、Article Summary、Domain Knowledge、設計差異、來源與數值雙向對照 |
| S50 | 簡報／影片候選產生 | PPTX/講稿同源、PDF、每頁 PNG、contact sheets、安全匯出與頁數一致 |
| S60 | 自動與反向測試 | 產品/全 repo 適用測試、失敗用例、資料/模型保護 hash、引用/文件連結、幾何檢查 |
| S70 | **獨立輸出目視＋來源複核** | **每頁實際渲染圖（非僅 contact sheet）與 PDF 逐頁查文字；重疊、裁切、表格 cell 溢出、圖文矛盾全部關閉** |
| S80 ★ | **GLM 自驗→ChatGPT 獨立複審交接** | 未通過外審只能標「GLM 自驗候選」，不可寫「正式最終 PASS」；外審 Request changes 退相應關 |
| S90 ★ | 產品 Agent／真店／SERVER／期末對外交付 | **另外經使用者授權**才啟動產品改碼、模型改動、SERVER、GitHub/YouTube/課程提交等操作 |
| S99 | 收尾 | 更新獲授權的正式入口與決策、完整驗收報告；未通過項保持 HOLD/BLOCKED |

**目前狀態（2026-10-09）：** Proposal v5 r3 的33頁簡報和研究文件通過 S80 獨立複審（REVIEW_R3.md）。r2 第3/4頁錯版、年份欄和 Agent 角色誤標已關閉；下一個 S90 的真 LLM Planner、T16 真店、SERVER、影片、GitHub 仍分別 HOLD/PROPOSED，不能當成全案 PASS。

## 3. 六角色／六檢查點：檢查者不能只看作者自述

每個有實質變更的工作包都走**輸入→輸入檢查→執行→執行檢查→輸出→輸出審核**六檢查點：

1. **Input Producer：** 列原始規範、檔案、截止日、權限、可信來源與本輪不動清單。
2. **Input Auditor：** 自己看來源，確認原文沒有讀錯；不能只看 Producer 的摘要。
3. **Implementer：** 在授權範圍改候選檔案／程式，完整記錄變更與原因。
4. **Implementation Auditor：** 從原規範＋實際 diff／原始程式獨立核對語意、破壞風險、測試是否能抓錯。
5. **Output Producer：** 實際產出 PPT/PDF/圖、測試結果與必要原始 log，不只給清單。
6. **Output Auditor：** 不看作者的「ALL PASS」當依據；直接開每頁渲染、重查報表來源、重算關鍵數字、執行驗收命令，給出可定位缺陷。

**主 GLM 控制範圍、依賴、停點與紀錄。** 若 ZCode 支援獨立 subagent，讓輸入/實作/輸出 Auditor 以不同上下文、只給「原始規範＋原始產物＋相關原始程式」，**不給作者自驗結論、不暗示預期 PASS**。不可把自己在同一上下文重複檢查當作三位獨立代理人。

若沒有 subagent，仍強制六個**分離的查核動作**，但報告要明寫「同一 GLM 自驗，沒有真正獨立 reviewer」，留待 ChatGPT/COS 複審。**不得捏造 subagent、執行次數、工具輸出或第三方核准。**

**退回規則：** 任一 Auditor 發現重要缺陷→標 `FAIL`，回到該缺陷最早源頭那一關修復，再重跑受影響範圍。**同一原因連續兩次修失敗**→主 GLM 停止盲目重試，查上游資料／模板／生成器／檢查器的根因；可用時請第三方獨立診斷，否則列 `BLOCKED` 向使用者或 ChatGPT 說明。不可無限「測到全綠」或為通過而削弱斷言。

## 4. 證據矩陣：每個 PASS 必須可重現

每個任務建一張表：`要求 / 原始來源 / 實際檔案(行或頁) / 驗證方式 / 執行命令與退出碼 / 結果 / 限制 / 審查者`。

- **狀態分開：** `TODO`、`DOING`、`GLM_SELF_PASS`、`FAIL`、`HOLD`、`BLOCKED`、`EXTERNAL_PASS`。GLM 只能授予 `GLM_SELF_PASS`，不能代 ChatGPT 授予 `EXTERNAL_PASS`；正式 `TASKS.md` 原狀態字樣不擅改。
- **聲明分級：** 「檔案存在」≠「可開」≠「能重建」≠「自動測試通過」≠「可視無錯」≠「使用者／ChatGPT 驗收」。
- **測試不要拿固定數當護身符。** 每輪回報真實命令、環境變數、測試收集數、PASS/FAIL、exit code、警告、報告路徑與時間。Windows CP950／UTF-8 可造成不同結果，兩者分開記；不可把 `tests/` 227 passed 冒充整 repo 全綠。
- **保護基準：** 若本輪不准動模型與舊檔，先讀 `outputs/proposal_delivery/run3_20261004_01/protected_before.json` 中 14 組 path/hash/size，逐檔 hash/size 比對前後；有任何不符立即 FAIL。基準檔本身不可「重抓新 hash」來掩蓋污染。也要看 Git tracked diff 與被忽略產物是否被覆寫。
- **測試須有反向能力：** 對可安全隔離的輸入，至少準備一個故意錯誤／缺圖／非法欄寬等案例，確認檢查真的會非零退出（negative control）。只在臨時候選副本操作，不改正式模型或使用者資料；若無法做，要列明限制。
- **每個 GLM SELF PASS 要有輸出路徑。** 不能只貼「69/69 PASS」「已目視」而沒有原生檔、重建命令、逐頁輸出和實際錯誤追蹤。

## 5. Research 與 Domain Knowledge 檢查

- Proposal 規範：Abstract A–F；Introduction 六要素；Related Work AI Technology＋Domain Know-how 約 1:1；八欄 Article Summary（Ref/Year/Problem/AI Method/Domain Knowledge/Dataset/Findings/Limitation）；Existing→Limitations→Gap→Our Project；Deep Research **5 Core Mindsets＋3 Controversies＋10 Deep Questions**；Architecture＋Flowchart＋有行號 Pseudocode；GitHub 與 DESIGN 文件交付狀態分開。
- Domain Know-how 包括：批發／零售傳導、單店與均價區別、品種品質促銷、台斤／公斤、缺測、供給與天氣、時間延遲、風險與決策效用。不是只列 RF/LSTM/HGB 就說有 Domain。
- 依序實查 **原論文/PDF→摘要→官網/商店文案→他人整理**。每個來源標 `full/abstract/page/report/notes`、頁次、年份、查核日；**只讀 11/15 頁就寫 11/15**，不能說全份讀完。找不到資料標 `UNKNOWN`，不把「未查到」寫成「不存在」；不要捏造 2025–2026 文獻或數字。
- Team17（同課程）與本專題同為菜價預測，但 Team17 主要是市場＋氣象 LightGBM、五天採購指南；本專題的研究差異是**當日單店價錨定＋選填上週同店資料＋7／14天固定期限＋同店到期 A/B 驗證設計**，不是換模型、換菜名。Team17 的 R²/RMSE/MAE 和本專題的 macro-F1 不得直接比較。
- 所有數值主張需對 `outputs/evaluation/public/public_test_results.json`、`stats_master.json` 或可定位原始研究逐項核對；列分母、單位、日期、範圍與假設；32/28/-4.1% 等教學例不可說成真店實驗。
- Proposal 階段的「已有公開市場結果」與「尚缺真店、LLM Planner、使用者測試」分開。不要因文件完成就宣稱產品 Domain Agent 達老師最終要求。

## 6. Product Agent／ML 邊界檢查（僅在獲准工作包內驗證，不自動開發）

- 現有 `src/aiot_price/agent/tools.py` 的 `AgentTools` 是**兩工具**：`get_market_quote`、`post_forecast`；`/records` 是 API，不是第三個 AgentTool。提案中的 `get_public_quote`、`call_forecast`、`save_record` 是抽象目標，最後一個尚未工具化。
- **工具呼叫防護**：現有 `ToolCallLimiter.check()` 只以計數限制單查詢工具呼叫次數；工具是否有 timeout、參數 schema 與錯誤隔離，均需分別從各執行路徑和測試核對，不能只查名稱或常數。
- 說明 `CURRENT`、`PARTIAL`、`PROPOSED` 必須對照**真實函式和呼叫路徑**，不能只看常數、類別名或架構圖：`TOOL_TIMEOUT_SECONDS=10` 存在不等於每條工具路徑都有強制 timeout；`validate_qwen_answer()` 存在不等於 `RuleBackend` 每次回覆均走過它；公開行情落後超三天目前會先警告，不等於所有過期都 hard-fail。
- 正式數值路徑：`ForecastEngine → 程式驗證 → 結構化結果／UI`；文字路徑：`工具真值 → Agent 限定解釋 → 必要驗證`。沒有有效工具值就顯示資料不足，**LLM 不得自己算價、機率、預期省錢、天氣因果、未經校準區間**。
- 真正 Tool-calling/Planner 啟用後才可宣稱「Agent 自主選工具」；先檢查工具白名單、schema、參數可比性、工具上限、失敗降級、單店保存、資料/模型版本、安全提示與無工具值時的拒絕行為。
- 若使用者未授權產品程式改動，本節是文件審查與驗收參考，**不能自行去修 `src/` 或重訓**。

## 7. PPT／PDF／影片：GLM 必做的多層視覺驗收

每次改簡報，不許只產出 `.pptx` 或只看檔案雜湊。至少執行：

1. **可編輯生成**：從 source 重建到隔離輸出；不得覆寫用戶手開的 PPT；不亂 Quit 共用 PowerPoint。先記錄 PPTX 封面頁、主講頁、附錄頁、notes 頁數與版本來源。
2. **實際匯出**：用 PowerPoint/安全匯出工具產生 PDF＋每頁 PNG，核對 PPTX/PDF/PNG 頁數、來源 hash 不變、備註同源。影片要以實際音訊/影格長度量測，不能把預估講稿秒數當實測片長。
3. **表格不變量（最重要）**：`sum(colwidths)` 必須等於指定總寬（容許微小浮點差）；實際重新讀 PPTX shape width 與欄寬，不能只看 `add_table(width=...)` 參數。**Year／年份欄必須能單行容納四位年份**；長字欄/中文自動換行需量測 cell 文字高度與 row 高度，過長則改版面／移附錄，不能縮到難辨認。
4. **幾何與字體**：檢查 shape 出界、shape 互相重疊、文字框超高、表格 cell 文字外溢、引用/footer 侵占；幾何 PASS 不等於文字 PASS。不可只靠 `objects_inside_slide` 或 `footer_band_clear`。需有**輸出 PNG 視覺證據**。
5. **雙重目視**：先看全主講 contact sheets，再**逐張開原始解析度主講 PNG**；附錄至少逐張檢查所有表格、演算法、架構圖、來源頁。特別檢查頁 3/4 表格、Year 欄、p8/p11 頁尾、p13 主講伪碼及其完整附錄——頁次改了以實際內容定位。
6. **語意交叉**：Architecture 的箭頭／群組索引↔Flowchart 分支↔Pseudocode 行號一致；資料來源、A/B 例、引用、指標、負向結果、CURRENT/PROPOSED 註記↔講稿一一對應。
7. **故意造錯測試**：在隔離的臨時候選生成器測「表格欄寬總和與指定寬不同」或「缺必要 UI 圖」時須 FAIL；避免真實渲染錯版卻自動 73/73 PASS。測試用副本，不能改正式來源來製造失敗。
8. **不可自封視覺驗收**：若只有模型自己的 contact sheet 快速看圖，寫「GLM 自驗目視」，不寫「32/32 外部視覺 PASS」。發現一頁重疊就撤回該輪整份視覺全過宣稱、修完重看全主講。

白底、短標題、大字、一頁一個問題，數據與重點限制可讀。不要把 hash、CLI、無關工程修復史塞滿口頭主講頁。主講約10分鐘是設計目標；**Final** PPT 須 >20 頁、Final Video >10分鐘屬最終交付條件，不能寫成 Proposal 階段已完成。

## 8. 代碼／測試與故障回退

- 改程式前先盤點真函式、呼叫者、schema、現有測試與影響範圍。禁止改模型或資料來追求漂亮數值。允許/不允許改動範圍以**使用者本輪任務**為準。
- 適當執行 `.venv\Scripts\python.exe -m pytest tests -q`，及全 repository `pytest -q`；Windows 必須記錄 `PYTHONUTF8` / `PYTHONIOENCODING`。2026-10-08 曾有 `tests/` 227 passed、repo-wide 設 UTF-8 249 passed、未設 UTF-8 部分安全測試 CP950 解碼失敗；這是**歷史觀測不是永遠固定的分數**。
- 如測試失敗先保留原始 traceback、判斷「本次引入 vs 既有」「業務錯誤 vs 測試器編碼/環境」。不得直接隱藏失敗、改掉原本斷言、刪除測試或把錯誤歸咎環境而不重現。
- 任何檢查器自身更動都要跑**檢查器的失敗測試**，確認壞輸入會 FAIL；不可只看正常檔通過。
- 不允許 `git reset --hard`、`git clean`、盲目 `git add -A`；不得清理未追蹤 `歷屆/`、`slides/simple_v4/`、`slides/proposal_v5/`。不要自動 git commit/push，亦不得改外部帳號/公開庫。
- 維護 rollback：變更前 hash／可逆備份／隔離候選；有重大不符先停止，不覆寫原證據來「修好」。

## 9. 進度、對外驗收與報告格式

在本輪允許的忽略輸出目錄（例如 `outputs/quality_runs/<task_id>/`）記錄：
`state.yaml`（關卡、允許改檔、結果/阻擋）、`evidence.md`（每條要求→證據）、`commands.log`（實際執行命令/exit code）、`visual_review.md`（逐頁結果）、`diff_scope.txt`（前後狀態）。**沒有執行的測試不得偽造 log；沒有產生的檔案不得假稱存在。**

每次回報用繁體中文，先說結論，再說證據與缺口。最後至少包含：

1. **狀態**：`GLM_SELF_PASS / FAIL / BLOCKED / HOLD`，以及是否**已經**由 ChatGPT 獨立驗收（沒有就寫沒有）。
2. **本次範圍**：原始要求／允許與禁止修改的檔案。
3. **檔案/程式改動**：實際路徑、重點 diff、對應研究/系統功能。
4. **驗證證據**：命令、退出碼、測試數、hash、PPT/PDF/PNG/notes頁數、逐頁目視、來源引用與數字核對。
5. **失敗和返修史**：至少列曾失敗項、根因、已修證據與未修項；不能只給「最後全部 PASS」。
6. **未完成**：LLM、真店到期 A/B、SERVER、外網、影片、GitHub/YouTube/課程發布，依真實狀態分開。
7. **外部審查交接**：交付精確資料夾與重建指令；外審未回 PASS 不能將候選升格 final。

**停點：** S80 等 ChatGPT 獨立複審，外審若提出 Request changes，**只修指定缺口，迴圈至指定關卡，不擴大重做**；S90 的產品部署與公開提交需使用者另外明確授權。主 GLM 無權自填「ChatGPT 已驗收」。
