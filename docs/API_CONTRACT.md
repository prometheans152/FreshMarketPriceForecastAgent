# 菜價 API 契約（T20）

日期：2026-10-03。實作：`src/aiot_price/api/app.py`；測試：`tests/api/test_forecast_api.py`（12 項，對真模型包）。契約語意：`contracts/forecast.schema.json`。本機啟動：

```bash
PYTHONPATH=src .venv/Scripts/python.exe -m uvicorn aiot_price.api.app:app --host 127.0.0.1 --port 8000
```

環境變數 `AIOT_RELEASE_DIR`（預設 `models/releases/0.1.0`）。`web/` 存在時同源服務手機頁。

## 端點

### GET /health

就緒狀態＋模型/資料版本＋公開資料截止日＋可用模式。模型包損毀時回 `not_ready` 與原因（截斷），不假裝就緒。

### GET /metadata

可用品項（含別名）、市場清單、可接受單位、不可比單位、模式、期限、能力邊界說明（B 實驗性、機率不輸出）、來源與授權。不含任何秘密。

### POST /forecast

請求＝ForecastRequest（見 schema）；回應＝ForecastResponse。驗證由 `ForecastEngine` 統一處理，API 不另造轉換。

| 狀態 | 情境 |
| --- | --- |
| 200 | 成功；`results`（7/14）、`results_without_last_week`／`results_with_last_week`（mode=both）、`warnings` |
| 400 | 非 JSON、缺必要欄位（`bad_request`） |
| 422 | 未支援品項/市場、單位不可比、價格/日期無效 |
| 503 | 公開資料不足無法估計（`stale_data_unusable`） |

`mode_executed`：`without_last_week`／`with_last_week`／`both`／`fallback_without_last_week`（B 不可比自動降級，附 `b_unavailable_reason`）。

每個期限結果必含：`target_date`（從使用者今天起算）、`direction`、`relative_change_estimate`、`price_estimate`（可 null）、`target_scope`、`validation_scope`、`warnings`、`evidence_summary`；`probability`/`interval_*` 一律 null（未校準）。

## 範例

```bash
curl -s -X POST http://127.0.0.1:8000/forecast -H "Content-Type: application/json" -d '{
  "crop_id": "高麗菜", "market_id": "中義市場", "current_price": 32,
  "price_unit": "NTD_per_taiwan_jin", "observed_at": "2026-10-02T10:00:00+08:00",
  "mode": "without_last_week"}'
```

## 安全（T28 前過渡）

本版僅綁定 127.0.0.1 本機使用；SERVER 對外開放前依 T28 加存取控制、節流與日誌遮罩（屆時更新本文件）。
