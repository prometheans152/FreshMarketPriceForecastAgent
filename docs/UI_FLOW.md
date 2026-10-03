# UI_FLOW：現場菜價預測手機網頁（T21）

更新日期：2026-10-03。本文說明 `web/` 靜態網頁的頁面流程、輸入欄位與 API 欄位對應、A／B 顯示邏輯、錯誤情境與已知限制。欄位語意以 [forecast.schema.json](../contracts/forecast.schema.json) 為準；品項與單位列舉對齊 `configs/project.yaml`。

## 1. 檔案與部署假設

| 檔案 | 內容 |
| --- | --- |
| `web/index.html` | 頁面結構（單欄、手機優先、繁體中文） |
| `web/app.js` | 內建清單、表單組裝、fetch 呼叫、結果與錯誤呈現、localStorage |
| `web/style.css` | 樣式（CSS 變數、system font、支援深色模式） |

- **同源假設**：頁面與 API 由同一個 server 提供（例如 API server 直接 serve `web/` 目錄）。`fetch` 使用相對路徑 `forecast`（無前導斜線），頁面所在目錄即 API 根目錄時可作用；若日後 API 掛在其他路徑，改 `app.js` 開頭的 `API_FORECAST` 常數即可。
- 純靜態、無 npm／build 工具鏈、無外部 CDN、無字型下載、無追蹤碼，離線可載入（查詢仍需後端）。
- 之端點：僅使用 `POST /forecast`。`GET /health`、`GET /metadata` 目前未使用（見已知限制）。

## 2. 頁面流程

1. **載入**：JS 填入品項／市場／單位下拉選單（內建列表），從 localStorage 預填上次品項、市場、單位與匿名店號（首次預設 `store-a`）；觀察日期／時間預設為現在。
2. **輸入必填**：品項、參考市場、今天價格（>0）、單位（元／台斤或元／公斤）、觀察日期與時間。
3. **選填上週**：開關「有上週價格嗎？」打開才展開上週價格、上週實際日期（預設帶入觀察日期 −7 天）、上週單位（預設同今天；今天單位變更時自動同步，因不同單位不可比）。
4. **模式自動判斷**：開關未開 → `mode=without_last_week`；打開且填妥 → `mode=both`（要求 A／B 並列；B 是否真的可用由 server 判定）。
5. **查詢**：按下「查詢預測」→ 前端驗證 → `fetch POST forecast`（JSON）→ 顯示結果或錯誤。成功後才把品項／市場／單位／店號存回 localStorage（**不存任何價格**）。
6. **結果閱讀**：每個期限（7／14 天）一張卡片；有 A／B 時並排兩欄對照；B 不可用時先顯示原因再只顯示 A。

## 3. 輸入欄位與 `ForecastRequest` 對應

| 網頁欄位 | Request 欄位 | 轉換說明 |
| --- | --- | --- |
| 品項下拉 | `crop_id` | 值直接用標準 ID：`cabbage`／`bok_choy`／`sponge_gourd`（configs `crops.first_version`） |
| 參考市場下拉 | `market_id` | 直接使用臺中來源標準化市場名稱（見第 8 點限制）；清單內建於 `app.js` 的 `MARKETS`，不含停用的「(停)建國市場」 |
| 今天價格 | `current_price` | number，前端驗證 > 0 |
| 單位下拉 | `price_unit` | `元／台斤 → NTD_per_taiwan_jin`、`元／公斤 → NTD_per_kg`；顆／把／袋屬不可比單位，不提供輸入 |
| 觀察日期＋時間 | `observed_at` | 組成 `{date}T{time}:00+08:00`（ISO8601，固定 Asia/Taipei +08:00） |
| 匿名店號 | `store_id` | 選填；`^[A-Za-z0-9_-]+$`，預設 `store-a`，存 localStorage；空白則不送此欄位 |
| 上週價格（選填） | `previous_price` | 開關打開才送；前端驗證 > 0 |
| 上週實際日期（選填） | `previous_observed_at` | 組成 `{date}T00:00:00+08:00`（使用者只知道日期，時間以 00:00 送出；7±2 天判定由 server 依日期做） |
| 上週單位（選填） | `previous_price_unit` | 預設同今天單位，可手動改；不同單位時 server 會判 B 不可比 |
| 有上週價格開關 | `mode` | 未開 → `without_last_week`；開 → `both` |
| （不送） | `request_id`、`specification`、`promotion` | `request_id` 由 server 產生；規格／促銷欄位本版 UI 未提供輸入，視為未知（null），不由前端偽造 |

## 4. 回應顯示與 A／B 邏輯

依 `ForecastResponse`：

- **結果來源**：`mode_executed=both` 時用 `results_without_last_week`（A）與 `results_with_last_week`（B）；其他模式用 `results`（單欄，標 A 或 B 依 `mode_executed`）。
- **A／B 並排**：每個期限（7、14 天）一列，左 A 右 B；某側缺該期限時顯示「無資料／未提供」佔位。
- **B 不可用**（`b_unavailable_reason` 或 `results_with_last_week` 為空）：先顯示「B 模式不可用：{原因}」，之後只顯示 A 卡片；`mode_executed=fallback_without_last_week` 時模式說明列改為「上週資料不可比，自動改用模式 A」。
- **每張卡片**：期限（7／14 天後）、`target_date` 到期日、方向（`up` 上漲▲紅、`down` 下跌▼綠、`flat` 持平—灰、`insufficient_data` 資料不足？淺灰）、`relative_change_estimate` 百分比（null 顯示「—」，不以 0 代替未知）、`price_estimate`＋`price_estimate_unit`（null 顯示「—」）、`target_scope`＋`validation_scope` 小字、該期限 `warnings` 逐條顯示。
- **卡片外**：查詢條件回顧（品項・市場・觀察時間）、`mode_executed` 說明、回應層 `warnings` 逐條、`public_data_cutoff`（含 `public_data_age_days` 天前）與 `model_version`／`data_version` 小字。
- 頁尾固定聲明：「公開市場均價模型（臺中）；店價估計為現價錨定推估，未在同店驗證」。

## 5. 錯誤情境

| 情境 | 處理 |
| --- | --- |
| 必填未填、價格 ≤ 0、日期空白、店號格式不符 | 前端擋下，紅框顯示中文訊息（不發請求） |
| HTTP 非 2xx 且 body 有 `error.message` | 顯示 `error.message`，附 `error.code` 小標籤（如 `non_comparable_unit`） |
| HTTP 非 2xx 且無可讀 body | 顯示「伺服器回應錯誤（HTTP {status}）」 |
| 200 但回應帶 `error` 物件 | 顯示 `error.message` 與代碼，不渲染結果 |
| 回應不是 JSON | 顯示「伺服器回應不是有效的 JSON…」 |
| `fetch` 拋出例外（斷網、DNS、連線被拒） | try/catch 攔下，顯示「無法連線到伺服器，請確認服務已啟動或網路狀態。」 |
| 回應缺 `results`／`results_without_last_week` | 顯示「伺服器回應缺少預測結果。」 |
| 單位不可比、品項不支援等訊息 | 不換算、不代換，直接呈現 server 的使用者可懂訊息 |

所有動態字串以 escape 後再插入 DOM，避免後端字串注入 HTML。

## 6. localStorage

- 僅一個鍵 `tw01_ui_prefs_v1`，JSON：`{ crop_id, market_id, price_unit, store_id }`。
- **不存任何價格、日期或預測結果**；無痕模式寫入失敗時靜默忽略，不影響查詢。
- 鍵名前綴 `tw01_` 避免與其他站台衝突；清除瀏覽器網站資料即可移除。

## 7. 已知限制

1. **同源假設**：未處理 CORS、跨網域 API 或反向代理子路徑；`API_FORECAST` 是相對路徑 `forecast`。API（T20，`src/aiot_price/api/app.py` 尚未實作）需直接 serve `web/` 或同目錄掛載。
2. **無帳號、無登入**：匿名店號僅存本機，換裝置不會同步；`store_id` 只保證格式，不驗證唯一性。
3. **資料只在本機**：不保存查詢結果（保存與到期對照屬 T22）；無任何遙測。
4. **品項／市場為內建列表**：未呼叫 `GET /metadata` 動態更新；T20 metadata 定案正式 market_id 清單後需同步 `app.js`（目前 `market_id` 直接用來源市場中文名稱）。
5. **時區**：`observed_at` 固定組 `+08:00`；裝置時鐘不在台灣時區時，日期／時間輸入值仍以裝置本地時鐘預填，可能與實際台北時間差一天（日界）。
6. **單位輸入限兩種**：元／台斤、元／公斤；顆／把／袋等不可比單位契約上「只能記錄」，本版 UI 不提供輸入（未來加輸入也只能得到「不可比」說明，不會有預測）。
7. **規格／促銷**：契約有 `specification`／`promotion` 欄位，本版 UI 未提供輸入，一律視為未知（不宣稱「完全相同」）；B 模式可比性由 server 依既有規則判定。
8. **未做實機瀏覽器驗證**：本版自檢為 HTTP 可取回與 JS 語法檢查；T21 驗收要求的實際手機尺寸輸入、鍵盤、空值與更正操作仍待後端可查詢後一併驗證。

## 8. 自檢紀錄（2026-10-03，本機 Windows）

- `node --check web/app.js` → 通過（僅語法檢查，不含執行行為）。
- `python -m http.server 8766 --bind 127.0.0.1 --directory .../web` 背景啟動後，`curl` 取回：
  - `index.html` → HTTP 200（開頭 `<!DOCTYPE html>`、`lang="zh-Hant"` 正確）
  - `app.js` → HTTP 200
  - `style.css` → HTTP 200
- 未執行瀏覽器操作與真實 API 查詢（T20 後端尚未實作），API 欄位對應以 `contracts/forecast.schema.json` 靜態核對。
