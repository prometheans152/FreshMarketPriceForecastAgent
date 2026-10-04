# 代理人方向：GLM API 先行、本機 Qwen3.8-27B 可替換

**D44 暫緩通知（2026-10-04）：** 使用者目前先保留現有介面，代理人整合／修復暫緩。本輪改執行 [研究與正式投影片計畫](PROPOSAL_DELIVERY_PLAN.md)，不把本文件的API／Hermes／SERVER項目當前置門檻。下方是保留的未來方向，不表示已刪除、不表示已通過，也不在本批修改實作。

更新：2026-10-04；直接依據：使用者本次指示，決策 D41。

## 1. 已確定、暫定及尚未實作

**使用者已確定：** 本機模型是 **Qwen3.8-27B**，不是 Qwen3-8B，也不再要求使用者重新確認 27B 的原意；專案必須能替換成 GLM API，現在先用使用者已有的 GLM API 開發及驗證代理人。既有 TRAIN_LOCAL／SERVER_3090 分工保持不變。

**暫定框架：** 使用者說「應該會用 HARMES」，本文件按 **NousResearch Hermes Agent** 查證與規劃；拼寫對應是助理解讀，框架仍是暫定，不冒充已安裝或最終選定。這裡的 Hermes 指代理人框架，不是 Hermes 系列語言模型。

**尚未確定：** Qwen 的量化檔、revision、推論引擎與 context；GLM 的實際平台／Base URL、可用模型 ID 及本機金鑰位置。Qwen 型號已確定，不等於量化與硬體測試已通過。

**本輪產出只限需求、設計方向和交接更新。** 截至本次檢查，HEAD 仍為 `44dabe3`，既有程式是規則調度＋Qwen 解釋，尚未接入 Hermes 或 GLM API；沒有進行 GLM 付費請求、安裝 Hermes、啟動 SERVER、下載權重或修復 R01–R08。

## 2. 分清三種角色

| 角色 | 責任 | 可以替換什麼 |
| --- | --- | --- |
| 菜價模型／ForecastEngine | 用封存的已訓練工件計算 7／14 天 A／B 結果，維持資料與驗證邊界 | 不因切换代理人而換模、重訓或改評估 |
| 代理人執行框架（Hermes 暫定） | 對話、選工具、驗證參數、執行有限工具、處理失敗與回傳結果 | 框架與供應商解耦，先查驗可用整合介面 |
| 代理人語言模型後端 | 理解需求、提出工具呼叫、依真結果解釋 | 現階段 GLM API；之後本機 Qwen3.8-27B |

開發路徑：手機網頁／本機介面 → 專案後端 → Hermes（暫定）＋GLM API → 本機菜價工具 → 結構化結果與說明。

目標路徑：同一網頁、後端與工具契約 → Hermes（暫定）＋SERVER_3090 自架 Qwen3.8-27B 端點 → 同一菜價工具。

Hermes 不代替載入 Qwen 權重的推論服務。若採 GGUF，另由相容推論引擎提供模型端點；具體引擎及版本須測試後決定。外部 GLM 提供推理，菜價工具仍由受控的本機／SERVER 執行，不把電腦 shell 權限交給 API。

## 3. 可切換不等於改一個名稱

實作須集中管理 provider、model、base_url、key_env、timeout、context／輸出限制；禁止用 `QwenBackend` 的名稱連 GLM 卻仍顯示 Qwen。前端和預測保存須記錄實際 provider／model／runtime、是否降級及原因，不能把配置目標當實際執行結果。

共用的有限工具至少包括查公開行情與呼叫菜價預測。可透過 Hermes 支援的 MCP 或官方擴充介面接入，但應先驗證整合方式，不硬編不存在的 SDK。網頁相容層、工具參數驗證、結果卡與保存契約不能依供應商另建互相分歧的版本。

驗收須看到真正的「模型提出工具呼叫 → 白名單及參數驗證 → 真菜價引擎 → 工具結果回送 → 回答」紀錄；只是把已算好的 JSON 交 GLM 改寫，仍只能算解釋層，不算新代理人流程完成。

需求切換預設為明確配置切換；**不自動從本機 Qwen 偷切雲端 GLM**。未經明確允許的雲端 fallback 關閉。GLM 失敗時保留直接菜價工具結果或明確錯誤，不能用規則模板假裝 GLM 成功。

## 4. 先 GLM、後 Qwen 的執行順序

沿用 TASKS 的 T25–T28，不另建一套互相衝突的任務表：

1. 先閱讀第三輪獨立審查 `outputs/audits/2026-10-04_round3_independent/REVIEW_44dabe3.md`。R01–R05 的真值、輸入與紀錄可信性必須優先修；R06–R08 同步追蹤。更換框架不會使既有缺陷自動消失。
2. T26 本機子項：建立供應商無關工具契約、Hermes 整合探測與 GLM 路徑，測工具白名單、真正 tool_calls、失敗降級及前端保存。缺金鑰只阻擋真 GLM 請求，不阻擋本機程式及協議測試；缺 SERVER 不阻擋此階段。
3. T27 分開記錄「離線／模擬協議測試」「真 GLM API 工具與忠實性測試」「真 Qwen3.8-27B 測試」。GLM 通過不能代替 Qwen 通過；沿用同一案例集便於後續比較。
4. T23/T24/T25 依實際 SERVER 權限完成部署、Qwen 載入、顯存及速度測試，再以配置切換到本機模型；重跑工具、拒答、數字／期限／單位、保存與降級案例。

T16 真店到期驗證、T32 外網手機、正式发布及當屆課程細則仍各自等待必要條件，不能用 GLM 聊天成功補成 PASS。

## 5. 隱私、金鑰與 API 方案

GLM 是外部 API；啟用前應顯示會傳送的必要查詢／工具結果範圍，限制用量與逾時。不得上傳整個專案、逐字稿、原始私人紀錄庫、真實店名／地址或憑證；本機 Qwen 模式不能暗中借用雲端輔助模型。Hermes 自帶工具／記憶／輔助模型的啟用范围也要核對，不能只限制自家兩個工具就宣稱整體安全。

金鑰只放使用者指定的本機環境或被忽略的秘密設定，不寫进瀏覽器、追蹤 JSON、提示詞、Markdown 或 Git。只回報設定是否存在，不印出值；不搜索或挪用其他專案帳密。

本次僅檢查 COS 當前程序的 `GLM_API_KEY`、`ZAI_API_KEY`、`AIOT_GLM_API_KEY` 等常見名稱，以及此專案根的 `.env`／`.env.local`；均未配置或不存在。這不代表使用者沒有 API，也未檢查其他軟體的私密設定。接線需實際平台／Base URL、模型 ID 與金鑰位置，不能由「有 GLM API」猜成某個付費方案。

一般模型 API 與 Coding Plan 專用端點／使用權益須區分。技術上連得上，不等於帳戶方案允許本專題場景；依使用者實際供應商與方案核對，不預設 Coding Plan 能用作任意應用後端，也不擅自改用其他付費服務。

## 6. 外部查證（2026-10-04）

以下是本次讀到的官方文件，不是本專案實測結果：

- Hermes 官方專案：https://github.com/NousResearch/hermes-agent
- Hermes providers：https://hermes-agent.nousresearch.com/docs/integrations/providers/ —— 列 `zai`／GLM 及自架 OpenAI-compatible endpoint；兩條模型來源有框架支援。僅協議相容不保證每個模型工具呼叫皆正確。
- Hermes MCP：https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp/ —— 支援接入工具及逐伺服器白名單；本案應只開必要工具，另驗證停用無關內建工具。
- Z.AI 一般 API：https://docs.z.ai/api-reference/introduction —— 一般 Base URL `https://api.z.ai/api/paas/v4`、Bearer API key；未替使用者選定此平台。
- 智譜 BigModel HTTP API：https://docs.bigmodel.cn/cn/guide/develop/http/introduction —— 一般 Base URL `https://open.bigmodel.cn/api/paas/v4/`；與 Z.AI 不互換猜測。
- Z.AI Coding Plan FAQ：https://docs.z.ai/devpack/faq —— 套餐限官方支援工具與場景；需區分專用端點與一般 API，實際帳戶尚未核對。

## 7. 交給 GLM 實作者的要求

先讀本文件、D41、TASKS 與第三輪獨立審查。GLM「開發執行者」和程式內「GLM API 模型後端」是兩個角色，不得混淆。先修本機缺陷，再接供應商可替換的代理人流程；本機正式模型及封存評估不可重訓、換分数或改寫。所用 Hermes／GLM／Qwen 版本、真實測試命令、輸入與工具追蹤須保存。尚無金鑰、尚無 SERVER、未測 Hermes 的狀態各自明列，不用它們阻擋所有可獨立完成的工作。
