# TW01 Oracle HTTPS 網頁 — 使用與回滾

> **新版正式架構提醒（2026-10-15）：Oracle 網頁與模型運算已安全切換到 Docker Compose，以下是切換前的歷史 systemd/網站資料，不再代表目前運作路由。** 新版維運、Nginx upstream、回滾、Cloudflare MCP 6/6 驗收與正式目錄見 deploy/docker-tw01/oracle/ORACLE_DOCKER_OPERATIONS.md。原 systemd 目前 disabled/inactive，但完整保留；不可直接照下面舊操作撤回整個網頁。

最新：2026-10-15 已部署官方價格欄完整品項 61 項的公開雲端網頁。直接輸入 http://161.33.19.220 會跳轉 HTTPS。**原 3 種 v0.1.0 模型不變，另外 57 種有行情品項已另行訓練出 7／14 天兩個真正的 HGB 監督式 ML 模型。留出測試 MAE 未勝不變價基準，須如實標示。**

## 網址與登入

- HTTP 首頁：http://161.33.19.220 → 301 → HTTPS 網頁。
- HTTPS 首頁：https://161.33.19.220 → /web/。
- 實際網頁：https://161.33.19.220/web/。
- **網頁已改為不用帳密**，任何人可直接開啟和使用網頁 A/B 功能；只允許透過 HTTPS 的同源請求，公開預測 Nginx 每來源 IP 12 次／分鐘（burst 6），API 層另有總共 30 次／分鐘及同時一個推論工作上限。
- **MCP Origin API 仍需 Bearer Token**；網頁的免登入不會取消 /v1/forecast 或 /v1/market-quote 的保護。

原先產生的網站 Basic-Auth 資料仍留在 Oracle root-only 檔中僅供舊版回滾，但目前網站路由完全不引用此認證檔。請勿因為網頁免登入而把真正 Origin API Token 寫到前端。

## 原功能與隱私

- 保留原介面操作：品項、市場、元/台斤、元/公斤、日期、今日價、上週價、A/B 對照、7／14 天、公開資料截止和限制；新增**61 品項分類與搜尋**。
- 官方臺中資料集 84539 有 **15 種蔬菜、27 種水果、7 種魚海鮮、10 種肉類、2 種蛋類**價格欄，合計 61；60 種曾有正價格，牛心柿歷史全為 0（缺測），網頁顯示但停用其預測。官方資料截止 2026-10-02，不代表全臺所有菜都有收錄。
- **原 RF（7 天）／HGB（14 天）凍結正式模型只用於高麗菜、青江白菜、絲瓜三種**，所有權重與版本均保持 0.1.0。
- 其他 57 個有價格的品項：已使用 Windows 5800X 對真實公開日價訓練一組**跨 57 品項的 HGB 7 天模型＋獨立 HGB 14 天模型（multi-crop-ml/1.0.0）**，而非將原 RF/HGB 硬套到未知品項。歷史趨勢只留作基線比較與資料足夠性檢查，不再做新版網頁的最終 A 推論；留出測試 7／14 天 ML MAE 0.02124/0.03130，大於不變價 MAE 0.01163/0.02085。缺價、過期或歷史點不足時明確拒絕。B α=0.3 仍是實驗規則，**不是重新訓練的 B 模型**，全部未經真店到期驗證。
- 此雲端網頁的「保存／查看／匯出／刪除」僅使用當前瀏覽器的 localStorage，不會寫入 Oracle 伺服器；清除瀏覽器紀錄、換手機都可能失去這些資料，請自行匯出。
- 原本 Windows 網頁 http://127.0.0.1:8766 的 A/B 預測與私人紀錄 API 保留原樣；不把私人紀錄複製到 Oracle。
- 雲端網頁的匿名店號僅存在當前瀏覽器，不會送到 Oracle。當天與上週價格會經 HTTPS 傳到 Oracle 進行預測，但不會保存到 Oracle 的私人紀錄。
- Oracle 的 MCP Origin API 仍使用另一把專用 Bearer Token，POST /v1/forecast、POST /v1/market-quote、GET /healthz 契約不改；新增 58 種品項**不會**被 MCP 原版當成 RF/HGB 模型結果。

## 本輪 Oracle 變更

新網頁靜態資源：/var/www/tw01-website/。
正式最新 ML 網頁覆層：/opt/tw01-forecastengine-web/site_overlays/pooled-20261015_013634_ml_v1/。
新版獨立兩個 ML 模型：/opt/tw01-forecastengine-web/ml_releases/pooled-20261015_013634_ml_v1/。
前一版歷史趨勢基準 Web 覆層保留在 /opt/tw01-forecastengine-web/site_overlays/catalog-20261015_003810_r2/（僅供回滾與比對）。
獨立完整公開來源資料：/opt/tw01-forecastengine-web/full_catalog-20261015_003810_r2/。
Systemd 獨立 drop-in：/etc/systemd/system/tw01-forecastengine.service.d/20-web-frontend.conf。
原版 Oracle FastAPI 仍僅綁定 127.0.0.1:8767，受 TLS Nginx 代理；公開頁面另開 /web/forecast 與 /web/catalog.json，原 /v1 API 認證維持不變。
HTTP 80 只讓根目錄 GET/HEAD 轉 HTTPS 與 ACME 驗證可用，其他 HTTP API 仍 404。

變更前備份：
- 最新 ML 切換前的 systemd 專用檔：/etc/systemd/system/tw01-forecastengine.service.d/20-web-frontend.conf.pre-pooled-ml-20261015_013634_ml_v1。
- 最新 ML 切換前的四個靜態網站檔：/var/www/tw01-website/index.html.pre-pooled-ml-20261015_013634_ml_v1、app.js.pre-pooled-ml-20261015_013634_ml_v1、style.css.pre-pooled-ml-20261015_013634_ml_v1、catalog.json.pre-pooled-ml-20261015_013634_ml_v1。
- 61 品項切換前的 Nginx TLS：/etc/nginx/sites-available/tw01-tls.conf.pre-catalog-20261015_003810_r2
- 61 品項切換前的 systemd：/etc/systemd/system/tw01-forecastengine.service.d/20-web-frontend.conf.pre-catalog-20261015_003810_r2
- 61 品項切換前的靜態資源：/var/www/tw01-website/index.html.pre-catalog-20261015_003810_r2，app.js.pre-catalog-20261015_003810_r2，style.css.pre-catalog-20261015_003810_r2
- /etc/nginx/sites-available/tw01-tls.conf.pre-web-20261014_182628
- /etc/nginx/sites-available/tw01-acme.conf.pre-web-20261014_182628
- 首頁 Nginx alias 第一次修復前快照 /etc/nginx/sites-available/tw01-tls.conf.pre-web-html-fix-c1

## 回滾方法

只回滾本輪網頁，不停止其他 Oracle 服務、不刪除任何資料、不重新部署模型：

1. **只撤回新 HGB、保留前一版 61 項網站**：將 .pre-pooled-ml-20261015_013634_ml_v1 的 20-web-frontend.conf 及四個靜態檔分別還原，systemctl daemon-reload、restart tw01-forecastengine.service，檢查 /healthz、/web/forecast 和原 /v1 Bearer API。原 Nginx 路由未變，不需要回滾 TLS 或重建 VPS。新模型資料夾保留作分析，不任意遞迴刪除。
2. **退回更早三品項版網站**：依原 .pre-catalog-20261015_003810_r2 的 TLS、systemd 與靜態網站備份分別還原，先 nginx -t，再 daemon-reload、restart/reload 專用服務，最後驗證 /v1 仍受 Token 保護。
3. **退回純 API（連舊網站也撤回）**：須明確授權，才還原原 .pre-web-20261014_182628 TLS/ACME、移除本網站 drop-in，保護原版 MCP Token 與模型不變。
4. 不要對 /opt、models、private、iptables、nginx 其他站點或既有 Windows 專案執行 blanket delete/reset。

## 驗收

- Windows 原 Web、原 API、Oracle 網頁候選本機測試：50/50 PASS。
- Oracle 正式 HTTPS 網頁認證、靜態檔、A/B、CSRF 與反向測試：17/17 PASS。
- 加入網頁後 Oracle 正式 MCP Origin API：16/16 PASS。
- 原 Windows 127.0.0.1:8766 仍然 ready，原模型權重與公開資料不變。
- 完整 61 欄來源 SHA256 驗證通過，新的 57 個額外有資料品項在至少一個市場有可計算的 7／14 日基準。新版本 Windows 回歸 71/71 PASS，Oracle 正式 HTTPS 分類/A/B/空資料處理 15/15 PASS；切換後原 MCP HTTPS API 16/16 PASS。
- **再新增正式監督式 ML**：57/57 新品項都有 train labels，兩個 HGB 模型完成 Windows 監督式訓練、時間留出測試和 9/9 ML 端點單元測試；Oracle 上線後 HTTPS 14/14 PASS 且 5 個新類別輸出與 Windows 同模型逐欄一致；原 MCP 有效 Bearer 接口複驗 16/16 PASS。**ML 不保證勝過不變價，這是明示的結果。**

本輪驗收紀錄位置：
C:\Users\prometheans\Documents\AIOT_FinishProject\outputs\quality_runs\oracle_web_preservation_20261014_182628_Windows5800X

新版完整品項驗收紀錄：C:\Users\prometheans\Documents\AIOT_FinishProject\outputs\quality_runs\oracle_full_catalog_20261015_003810_Windows5800X

最新 ML 訓練、模型 manifest、逐品項 test 指標與 Oracle 實機證據：C:\Users\prometheans\Documents\AIOT_FinishProject\outputs\quality_runs\tw01_pooled_ml_training_20261015_013634_Windows5800X

最新 ML 模型卡：docs/deployment/POOLED_ML_MODEL_CARD_V1.md
