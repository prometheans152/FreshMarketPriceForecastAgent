# ForecastEngine API v1 — Workers 對接契約

> **改名（2026-10-16／17）：** 本文已改用新名稱 `fresh-market-price-agent-*`／`FMPA_*`。Oracle 主機已於 2026-10-17 遷移完成，最後一項 certbot 續期排程也已於 2026-10-20 改成 `fresh-market-price-agent-certbot-renew.*`；新 Worker `fresh-market-price-agent` 已部署並通過 6/6，但 ChatGPT 仍連舊的 `tw01-forecast-mcp`（保留到切換為止）。進度見 [RENAME_MIGRATION.md](../../deploy/RENAME_MIGRATION.md)。

> 2026-10-15 最新：免帳號密碼的 HTTPS 網頁 https://161.33.19.220/web/ 顯示官方 61 品項價資料。原 v0.1.0 RF/HGB 模型**仍只用於原三種菜**；其他 57 個有行情品項已**另外訓練並獨立測試兩個新的 HGB ML 模型 multi-crop-ml/1.0.0**，網頁依品項選用。HGB 在留出測試的 7/14 天 MAE **都未優於不變價基準**，且均未有同店真價驗證。牛心柿全 0 缺測，不能預測。**這不是 Workers API v1 的變更**：以下兩條 Bearer Token 保護的 /v1 POST 仍只接舊三種菜、只提供匿名 A／行情；Token 和舊模型不變。雲端網頁保存紀錄只在使用者瀏覽器，Windows 本機 A/B 與私人紀錄維持原樣。另見 docs/deployment/POOLED_ML_MODEL_CARD_V1.md。

狀態（2026-10-15）：**同一 Oracle VPS 已正式改用 Docker Compose 運算，對外 HTTPS Origin、原 IP-SAN 憑證與 /v1 契約不變，Windows 外網真模型跨平台 14/14 PASS；原 Cloudflare Workers MCP → Oracle Docker 真實端到端 6/6 PASS**。ChatGPT/Gemini 各自的原生客戶端 UI 接線仍需另外驗證，不能把伺服端 E2E PASS 冒稱每個客戶端都已連通。新部署與安全回滾詳見 deploy/docker/oracle/ORACLE_DOCKER_OPERATIONS.md。此文件不含任何秘密。

## 1. 路由與基底網址

| Method | Path | Bearer Token | 用途 |
| --- | --- | --- | --- |
| GET | `/healthz` | 不必 | 非敏感健康與凍結版本資訊 |
| POST | `/v1/market-quote` | **必須** | 原生 `AgentTools.get_market_quote` 公開行情 |
| POST | `/v1/forecast` | **必須** | 原生 `AgentTools.post_forecast`，匿名 A 模式 |

**已驗收 HTTPS Base URL**：`https://161.33.19.220`。由 Let's Encrypt 簽發的正式 IP SAN TLS 憑證，有效期 **2026-10-14 06:25:54 UTC 至 2026-10-20 22:25:53 UTC**；本機外網的驗證結果 `ssl_verify_result=0`、HTTP 200，續期 Dry-run 成功，Oracle 上續期 timer 為 enabled/active。Workers 必須正常驗證公開信任鏈及 IP SAN，**禁止** `insecure`／略過 TLS 驗證；不准連 127.0.0.1 或明文 HTTP 作為正式 Origin。

驗證：`Authorization: Bearer <部署專用秘密>`；只允許此單一 Bearer scheme，完整 Header 不得寫入日誌、Git 或聊天。Workers 以自己的 Secrets 保存對應 Token。請求 `Content-Type: application/json`，UTF-8；拒絕重複 JSON 欄名、NaN、Infinity、過大請求與未列白名單欄位。`POST` 超時上限 **15 秒**，Workers 的 origin fetch timeout 建議 **20 秒**，不重試有歧義的非冪等處理。沒有任何保存/修改/執行路由。

## 2. 共享詞彙與 schema

`crop_id` 僅接受 `cabbage`、`bok_choy`、`sponge_gourd`。`market_id` 僅接受：`中義市場`、`南屯市場`、`合作市場`、`大甲第二市場`、`東光市場`、`梧棲第一市場`、`沙鹿市場`、`清水第一市場`、`第三市場`、`第二市場`、`第五市場`、`豐原第一市場`、`霧峰市場`。Workers 端使用與原專案 `chatgpt_contracts.py` 同一列舉值，不自行翻譯。

`price_unit` 只接受 `NTD_per_taiwan_jin`（元／台斤）或 `NTD_per_kg`（元／公斤）；無箱重的箱／袋／顆／把、`unknown` 一律不可比。1 台斤＝0.6 公斤；API **不計算價格**，原 ForecastEngine 負責單位轉換與估計。

`observed_on` 為 *可選* 的嚴格 `YYYY-MM-DD` 日曆日期，不能是未來日。省略時以 **Asia/Taipei 當下日期**作為 t；顯式日期不會被替換。內部唯一標準化規則：`observed_at = observed_on + 'T12:00:00+08:00'`，`mode=without_last_week`，`store_id=null`。預測目標日是 **t+7、t+14 精確日曆日**，不是交易日、週均值或公開資料截止日起算。查詢日 `query_date` 為 Asia/Taipei 的**服務端實際當日**。

**POST `/v1/market-quote` request schema**：

```json
{
  "type": "object", "additionalProperties": false,
  "required": ["crop_id", "market_id"],
  "properties": {
    "crop_id": {"type": "string", "enum": ["cabbage", "bok_choy", "sponge_gourd"]},
    "market_id": {"type": "string", "description": "需為前述 13 個市場精確名稱"}
  }
}
```

**POST `/v1/forecast` request schema**：

```json
{
  "type": "object", "additionalProperties": false,
  "required": ["crop_id", "market_id", "current_price", "price_unit"],
  "properties": {
    "crop_id": {"type": "string", "enum": ["cabbage", "bok_choy", "sponge_gourd"]},
    "market_id": {"type": "string", "description": "需為前述 13 個市場精確名稱"},
    "current_price": {"type": "number", "exclusiveMinimum": 0, "maximum": 1000000},
    "price_unit": {"type": "string", "enum": ["NTD_per_taiwan_jin", "NTD_per_kg"]},
    "observed_on": {"type": "string", "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"}
  }
}
```

`current_price` 必須為 (0, 1000000] 的有限數值（不接受 `bool`、數字字串、0、負值、NaN/Infinity）。不接受 `previous_price`、`mode`、`store_id`、`save`、`url` 等額外欄位；Workers API **只有匿名 A**。

## 3. 成功 JSON 回應（200）

**GET `/healthz`：**

```json
{
  "status":"ready", "model_version":"0.1.0",
  "data_version":"172dffc76e82", "public_data_cutoff":"2026-10-02",
  "modes":["A"], "horizons_days":[7,14]
}
```

模型不存在、hash 不符或依賴異常時 `/healthz` 改回 503 `status=not_ready`，不吐出內部路徑或 traceback。

**POST `/v1/market-quote`：** 以 `AgentTools.get_market_quote` 原始回傳為 `engine_result`，不變更價錢或觀測日期：

```json
{
  "tool":"get_market_quote",
  "input_echo":{"crop_id":"cabbage","market_id":"中義市場"},
  "normalized_request":null,
  "query_date":"2026-10-14",
  "engine_result": {
    "ok":true, "market_id":"中義市場", "crop_id":"cabbage",
    "price": 30.0, "unit":"NTD_per_taiwan_jin",
    "observed_date":"2026-10-02", "public_data_cutoff":"2026-10-02",
    "price_age_days_at_cutoff":0
  },
  "price_age_days_at_query":12,
  "limits":["公開市場均價不等於個別店家真值，也不是即時報價。"],
  "fact_text":"以本次原生結果實際產生的中文說明"
}
```

上方行情數值與日期取自 **2026-10-14 正式 HTTPS 驗收的原工具回應**；`fact_text` 和縮略 `limits` 僅說明欄位位置，完整原文保留於驗收 JSON。30.0 是觀測日 2026-10-02 的公開市場均價，**不是今日現場單店報價**，不得快取成後續新的查詢真值。

**POST `/v1/forecast`：** 直接提供原生 `ForecastEngine.forecast` *完整* `engine_result`，不可由 API/Workers 重新算數值、方向或警告：

```json
{
  "tool":"post_forecast",
  "input_echo":{"crop_id":"cabbage","market_id":"中義市場","current_price":32.0,"price_unit":"NTD_per_taiwan_jin","observed_on":"2026-10-14"},
  "normalized_request":{"crop_id":"cabbage","market_id":"中義市場","current_price":32.0,"price_unit":"NTD_per_taiwan_jin","observed_at":"2026-10-14T12:00:00+08:00","mode":"without_last_week","store_id":null},
  "query_date":"2026-10-14",
  "engine_result": {
    "request_id":"req-<由 ForecastEngine 產生>",
    "mode_executed":"without_last_week", "model_version":"0.1.0",
    "data_version":"172dffc76e82", "public_data_cutoff":"2026-10-02",
    "input_observed_at":"2026-10-14T12:00:00+08:00",
    "crop_id":"cabbage", "market_id":"中義市場", "store_id":null,
    "results":[{"horizon_days":7,"target_date":"2026-10-21","direction":"由原模型產生","relative_change_estimate":null,"price_estimate":null,"price_estimate_unit":"NTD_per_taiwan_jin","target_scope":"store_price_estimate","validation_scope":"unvalidated","probability":null,"interval_low":null,"interval_high":null,"warnings":[],"evidence_summary":"原模型輸出"}],
    "results_without_last_week":[], "results_with_last_week":[],
    "b_unavailable_reason":null,"warnings":[],"error":null
  },
  "price_age_days_at_query":12,
  "limits":["公開方向模型未勝動量基線；點估計 MAE 未勝不變價基線。"],
  "fact_text":"以本次原生結果實際產生的中文說明"
}
```

上方 `results` 僅展示一列*欄位位置*；**真實成功結果必須有 7、14 天各一筆，且相對變化與估計價均須為原模型的非 null 有限數值，這份範例不是模擬結果**。每筆 `direction=up|flat|down`，`probability=null`、`interval_low=null`、`interval_high=null`。`engine_result` 另含 `public_data_age_days`、`simulated`、`client_ref` 等原始欄位，保留而不裁剪。頂層 `query_date` 隨日變、引擎產生的 `request_id` 每次不同。

## 4. HTTP 失敗結構

所有失敗回應均為 `{"error":{"code":"代碼","message":"不含秘密的簡短訊息"}}`，`/healthz` not_ready 可附 `status`。不得包含本機絕對路徑、Token、環境變數值、traceback、Shell 或檔案內容。

| HTTP | `error.code` | 情境 |
| --- | --- | --- |
| 401 | `unauthorized` | POST 缺 Bearer／金鑰錯誤／格式不對 |
| 400 | `bad_request` | 空本文、非 JSON 物件、重複 JSON key、NaN/Infinity、不合型別 |
| 413 | `payload_too_large` | Body 超過 4096 bytes |
| 415 | `unsupported_media_type` | 不是 JSON content type |
| 422 | `unsupported_crop` | 品項不受支援 |
| 422 | `unsupported_market` | 市場不受支援 |
| 422 | `invalid_price` | 價格非有限正數 |
| 422 | `non_comparable_unit` | 沒有重量的單位、無效單位 |
| 422 | `invalid_date` | 日期格式／不存在／未來日期 |
| 422 | `unsupported_field` | 額外欄位（包括 B、保存、URL、檔案等） |
| 503 | `stale_data_unusable` | 指定日期之前公開資料不足、原工具沒有有效價格 |
| 503 | `not_ready` | 凍結工件、服務初始化或依賴不可用 |
| 504 | `forecast_timeout` | 運算超過 15 秒；無數值結果 |
| 429 | `rate_limited` | 節流或同時查詢上限 |
| 500 | `internal_error` | 非預期錯誤；回傳遮罩，不洩漏例外細節 |

## 5. 模型與研究邊界（必須保留）

- 7 天 RF、14 天 HGB、`model_version=0.1.0`；凍結 JSON SHA256 = `172dffc76e8249026ac2ad89cc1a9f68bcfb686fd64a2820b38e949fe7e2e259`；公開資料截止 `2026-10-02`；不能自動刷新或重訓。
- ±5% 門檻由原版決定。A 的方向由公開市場模型主導；店價估計是**現價錨定的未驗證推估**。
- 既有公開 macro-F1 7d/14d = `0.4218`／`0.4169`，低於動量基線 `0.4226`／`0.4306`；MAE `0.0664`／`0.0983` 高於不變價 `0.0436`／`0.0748`；上漲 recall 約 `10.1%`／`8.6%`。
- 真店到期配對 A/B 尚未完成；不能宣稱真正店家預測準確，也不能產生虛構機率、區間或省錢效益。
- 原 Windows 本機 Web A/B 和私人記錄獨立保留；此服務完全不暴露 `/records`、私人資料、B 模式、管理／Shell／任意 URL 功能。

## 6. 實作與交接定位

- 唯一 HTTP 層負責目錄：`deploy/oracle-forecastengine/`；**不修改** `deploy/cloudflare-workers-mcp/`。
- ForecastEngine 正式真值來源：`src/aiot_price/models/predict.py` ＋ `src/aiot_price/agent/tools.py`，以及已存在的 `src/aiot_price/integrations/chatgpt_adapter.py` 的凍結拷貝/hash 檢查與工具驗證。
- Token 交接僅經使用者核准的安全設定或秘密管理方式，**不寫在此檔**。Workers 需以 `engine_result` 作唯一真值，不以 HTTP 範例中的示意數字展示真行情。
- 已實測 HTTPS Origin 路由及 TLS 證據位於 `outputs/quality_runs/oracle_forecastengine_acceptance_20261014_160405_c44b7d_Windows5800X/`。**Workers 秘密設定與 ChatGPT E2E 尚待 Workers 對話執行**；HTTPS Origin 的 PASS 只證明第二層，不代表整段端到端連線已完成。
