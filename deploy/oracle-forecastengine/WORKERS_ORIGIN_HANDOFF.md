# Cloudflare Workers → ForecastEngine Origin 交接（2026-10-14）

Oracle ForecastEngine 第二層已完成實際 HTTPS、正式 Bearer API、原模型一致性及錯誤恢復驗收；這不代表 Workers/ChatGPT MCP 端到端已成功。Workers 對話只修改 deploy/cloudflare-workers-mcp，不可改此 Oracle API 契約或模型。

## 可直接接線的正式 HTTPS Origin

Base URL：https://161.33.19.220

- GET /healthz：不必 Token，2026-10-14 從 Windows 公網 TLS 驗證成功（HTTP 200；ssl_verify_result=0），回 status=ready。
- POST /v1/market-quote：需服務端專用 Authorization: Bearer（秘密值不得公開）。
- POST /v1/forecast：同上，僅提供匿名 A 模式。
- Content-Type: application/json；UTF-8。
- Oracle 原始運算 deadline 15 秒；Workers 上游 HTTP fetch timeout 建議 20 秒。
- 嚴格驗證 Let's Encrypt 的 IP SAN TLS，禁止跳過證書驗證、明文 HTTP、任意重導向。
- 認證用的秘密只存在 Oracle root-only、0600 的 /etc/tw01-forecastengine/origin.env。Cloudflare Secret 必須用使用者核准的安全流程填入，不可寫入共用文件／原始碼／輸出紀錄，也不可以沿用舊 COS Tunnel Token；Workers 前端用戶認證應是另一套獨立秘密。
- 受支持品項：cabbage、bok_choy、sponge_gourd；受支持市場以 docs/deployment/FORECASTENGINE_API_V1.md 為準。
- 必須原樣使用 upstream 的 engine_result，包含 request_id、方向、期限、模型／資料版本、warnings、target_scope、validation_scope 及 probability/interval 的 null。Workers 不得重算任何數值。

## 已驗收案例（合成輸入，非真店配對驗證）

GET 市場行情對應的 POST /v1/market-quote 請求：

    {"crop_id":"cabbage","market_id":"中義市場"}

2026-10-14 實測傳回凍結公開市場均價 30.0 元／台斤，行情實際觀測日與資料截止都是 2026-10-02。**不是 2026-10-14 單店真實售價，更非即時現場行情。**

POST /v1/forecast 請求：

    {"crop_id":"cabbage","market_id":"中義市場","current_price":32,"price_unit":"NTD_per_taiwan_jin","observed_on":"2026-10-14"}

實際原生模型結果：

| Horizon | target_date | direction | relative_change_estimate | price_estimate |
| --- | --- | --- | --- | --- |
| 7 | 2026-10-21 | flat | -0.0486 | 30.4 元／台斤 |
| 14 | 2026-10-28 | flat | -0.0417 | 30.7 元／台斤 |

以上為單一合成測例的原版 RF／HGB 模型推估，沒有店家到期真值驗證。若 price_unit 為 NTD_per_kg，價格估計須保持原單位；箱重未知應拒絕。若 observed_on 省略，Oracle 以 Asia/Taipei 當日為 t；明示日期不得覆蓋；預測日嚴格是 t+7 與 t+14 日曆日。

## 本輪 Oracle 驗收證據

- 初始正式 HTTPS 功能：16/16 PASS，退出碼 0。
- 延伸 HTTPS 安全與契約：先 17/18，發現超大 request 的 413 是 HTML；修正專用 Nginx 後 18/18 PASS，退出碼 0，保留失敗原證據。
- HTTPS 真實 engine_result 對 Windows 原版所有欄位逐一比對：5/5 PASS，僅比較時忽略動態 request_id；原始 request_id 仍完整留在證據。
- 強制服務異常退出後 systemd 自動恢復，重新 HTTPS 預測 16/16 PASS、再次結果一致性 5/5 PASS。
- Windows 原生隔離 API 套件 30/30 PASS（含逾時、單工忙碌、未預期例外和恢復注入測試）。
- Windows 既有 Web A/B 相關測試 18/18 PASS，原埠 8766 實際 A/B 合成請求仍可得到兩種模式的 7/14 天結果。
- Nginx 對外有有效憑證，原始 Python 8767 不對外；Token 環境 root-only 0600，模型／資料 SHA256 與封存一致；憑證續期 Dry-run 及 systemd 排程已驗收。

完整獨立驗收位置：
C:\Users\prometheans\Documents\AIOT_FinishProject\outputs\quality_runs\oracle_forecastengine_acceptance_20261014_160405_c44b7d_Windows5800X

## Workers 對話尚需完成

1. 在 deploy/cloudflare-workers-mcp/ 讀取 owner 文件 docs/deployment/FORECASTENGINE_API_V1.md，更新原本的 PENDING origin 為上述 HTTPS Base URL（由 Workers 對話操作）。
2. 核實 Cloudflare Wrangler 登入、部署權限及獨立的 ChatGPT OAuth/其他正式可行的認證流程，不能把目前測試用 Bearer Gate 假稱為完整 ChatGPT OAuth。
3. 經使用者核准的安全 Secret 注入流程，將新 Oracle Token 設為 Cloudflare Workers Secret；絕不在 Markdown、Git 或聊天中透露。
4. 部署 Workers 後，用 MCP initialize、tools/list、tools/call 實際打到 Oracle；逐欄核對完整 upstream engine_result；再以 ChatGPT 本身的新 MCP 工具實際呼叫一次。
5. 真正提供已驗證的 Workers MCP URL，以及 ChatGPT 端到端測試日誌。未完成前一律標示 ORIGIN_PASS / E2E_NOT_VERIFIED。

上述交接不修改另一個對話負責的 Cloudflare Workers 工作目錄。
