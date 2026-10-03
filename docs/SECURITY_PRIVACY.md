# 安全與隱私（T28）

日期：2026-10-03。實作：`src/aiot_price/api/app.py` middleware；測試：`tests/api/test_access_limits.py`（6 項）。狀態：**本機層完成；SERVER 對外開放前依實際部署補強**（T29 更新本文件）。

## 已實作（本機 API，2026-10-03 實測）

| 防線 | 設定 | 測試 |
| --- | --- | --- |
| 請求大小上限 | Content-Length > 8KB → 413（不讀 body） | `test_oversized_body_rejected_413` |
| 速率限制 | 每客戶端 IP 每分鐘 30 次（滑動窗口，記憶體版）→ 429 | `test_burst_limited_429` |
| 端點暴露範圍 | 僅 `/health` `/metadata` `/forecast` `/agent/query`＋靜態網頁；無管理端點、無 shell、無任意 URL 工具 | 路由表 |
| 代理人工具邊界 | 工具僅 2 個（行情查詢、預測）；每次查詢最多 3 次工具呼叫；Qwen 只做解釋層、不決定工具參數 | `tests/agent/` |
| 查詢長度 | `/agent/query` 文字 1–2000 字 | `test_api_agent_query_validation` |
| 日誌 | 不記錄請求 body（僅路徑/狀態）；速率桶只存 IP 與時間戳 | 代碼審查 |

## 私人資料保護

- 店價原始紀錄只在 `private/store_quotes/`、預測紀錄在 `private/predictions/`（均 git 忽略）。
- 匿名匯出（`export_anonymous_summary`）不含價格輸入與店家識別。
- `store_id` 只接受 `^[A-Za-z0-9_-]+$`（schema 強制），不收真名地址。
- 模型包僅含公開市場資料；部署 SERVER 不需任何私人檔案。
- Qwen 後端連線資訊只由環境變數提供（`AIOT_QWEN_BASE_URL`/`AIOT_QWEN_MODEL`/`AIOT_QWEN_API_KEY`），不入庫。

## 待 SERVER 部署時補強（T29 前更新）

1. 對外連線方案確認後：TLS、反向代理層的真正速率限制（跨進程）、請求超時。
2. Qwen 推論端口**不直接對外**（僅本機/內部網路可達）；外部提示注入防護已在 prompt 層（agent_prompt.md 規則＋工具結果只作資料）。
3. 服務以非管理帳號執行、檔案權限最小化。
4. 日誌輪替與留存期間依實際環境定。

## 已知限制

- 記憶體速率限制僅單進程有效（uvicorn 單實例部署足夠；多實例需反向代理層）。
- 本機綁 127.0.0.1 時网络層威脅面極小；上述限制為 SERVER 對外情境預置。
