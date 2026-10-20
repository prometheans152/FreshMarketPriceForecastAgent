# ForecastEngine Origin — 維運與回滾（內部文件）

> **改名（2026-10-16／17）：** 本文已改用新名稱 `fresh-market-price-agent-*`／`FMPA_*`。Oracle 主機已於 2026-10-17 遷移完成，最後一項 certbot 續期排程也已於 2026-10-20 改成 `fresh-market-price-agent-certbot-renew.*`；新 Worker `fresh-market-price-agent` 已部署並通過 6/6，但 ChatGPT 仍連舊的 `tw01-forecast-mcp`（保留到切換為止）。進度見 [RENAME_MIGRATION.md](../RENAME_MIGRATION.md)。

驗收日：2026-10-14。以下為內部維運資訊，不應出現在對外 PPT；禁止把 API Token、私鑰、完整授權 Header 寫入程式、Git、聊天或日誌。

## 實際運行架構

- Oracle 既有 Instance：instance-20260701-1329，161.33.19.220，大阪，Ubuntu 22.04.5，x86_64，1 OCPU、1GB RAM。
- HTTPS Origin：https://161.33.19.220。Let's Encrypt 正式 IP SAN 憑證到期：2026-10-20 22:25:53 UTC，短效約六日。
- 正式路由：GET /healthz；POST /v1/market-quote；POST /v1/forecast。後兩者需獨立 Bearer Token，僅匿名 A，不暴露 B／records／任意 URL 或 Shell。
- Oracle 凍結程式與模型：/opt/fresh-market-price-agent-forecastengine/releases/20261014_145908_9fe6fa/。
- 目前部署指向：/opt/fresh-market-price-agent-forecastengine/current。
- Python 虛擬環境：/opt/fresh-market-price-agent-forecastengine/venv/。
- 原生 FastAPI 僅監聽 127.0.0.1:8767；外網一律通過 443 Nginx TLS 反向代理。
- systemd：fresh-market-price-agent-forecastengine.service；專用帳號 tw01forecast；Restart=on-failure；CPUQuota=100%；MemoryHigh=550M；MemoryMax=750M；MemorySwapMax=512M。
- 專用金鑰環境檔：/etc/fresh-market-price-agent-forecastengine/origin.env，root:root、0600。已產生本輪唯一新 Token；絕對不可在交接 Markdown 中揭露。
- HTTPS 配置：/etc/nginx/sites-available/fresh-market-price-agent-tls.conf。
- 413 JSON 修復前備份：/etc/nginx/sites-available/fresh-market-price-agent-tls.conf.backup-c44b7d。
- TCP 80 僅提供 ACME HTTP-01 驗證，其餘 404；443 提供合法 HTTPS。iptables 僅新增含 fmpa_forecastengine_origin_v1 註記的兩條允許規則；保留既有 SSH 與其他服務規則。
- TLS 自動續期：fresh-market-price-agent-certbot-renew.service / fresh-market-price-agent-certbot-renew.timer，每日兩次檢查，Dry-run 成功，systemd oneshot 退出碼 0。

## 安全巡檢

先使用 Windows COS Core 既有已授權 OpenSSH 金鑰 oracle_amd_ed25519 及 ubuntu@161.33.19.220 登入；保持 StrictHostKeyChecking=yes。進入 Oracle VPS 後執行：

    systemctl is-active fresh-market-price-agent-forecastengine.service nginx.service fresh-market-price-agent-certbot-renew.timer
    systemctl show fresh-market-price-agent-forecastengine.service -p MainPID -p NRestarts -p MemoryCurrent -p MemoryMax -p CPUQuotaPerSecUSec
    sudo journalctl -u fresh-market-price-agent-forecastengine.service -n 40 --no-pager
    sudo nginx -t
    sudo /opt/fresh-market-price-agent-forecastengine/acme-venv/bin/certbot certificates
    sudo /opt/fresh-market-price-agent-forecastengine/acme-venv/bin/certbot renew --dry-run --cert-name 161.33.19.220
    curl --fail --show-error --silent https://161.33.19.220/healthz

嚴禁使用不安全 TLS 選項、略過證書驗證、降低成明文 HTTP 或將 Token 輸出至終端、筆記或記錄。只在需要時經使用者核准的秘密設定流程同步 Workers Secret。

## 重啟與故障恢復

    sudo systemctl restart fresh-market-price-agent-forecastengine.service
    systemctl is-active fresh-market-price-agent-forecastengine.service
    curl --fail --show-error --silent https://161.33.19.220/healthz

2026-10-14 驗收已分別實測一般重啟與僅對 fresh-market-price-agent-forecastengine.service 主程序發送 SIGKILL；systemd 約四秒後自動重啟，NRestarts=1，健康檢查回 ready，未重啟 VPS 或其他服務。

## 回滾與發布

1. 遇到 Release SHA256、FastAPI 數值一致性、驗證鏈、憑證、服務版本等失敗時，必須 Fail closed，不開放 HTTP 繞過。
2. 若需停止本輪 API，可僅執行 sudo systemctl stop fresh-market-price-agent-forecastengine.service，不影響 Windows 本機 Web A/B。
3. 本輪 Nginx 413 JSON 修復有保留舊版 backup-c44b7d；若新設定故障，將其恢復到 fresh-market-price-agent-tls.conf，先執行 sudo nginx -t 成功再 sudo systemctl reload nginx.service。注意舊版可能重新出現「413 是 HTML」缺陷；正常情況請保留新設定。
4. 未來更新要建立全新、不可覆寫的 releases/<release-id> 目錄，逐檔 SHA256、版本與相同輸入 fixtures 驗證後，才切換 current symlink 和重啟專用服務。保留先前已驗證版本。此為 Oracle **第一個正式部署版本**，沒有更早的 Oracle Release 可以切回：故障時停用服務、用本輪凍結 Bundle 復原，而非臆造可回滾版本。
5. 不得清空全部 iptables 規則或重建 Oracle Instance。停用服務時只能選擇性撤回本專案註記（`fmpa_forecastengine_origin_v1`，遷移前為 `tw01_forecastengine_origin_v1`）的防火牆規則，且需考量 TLS 續期。
6. 不得對模型重新訓練、更新歷史公開資料或轉移私人 records。任何密鑰輪替需要 Workers 端協調；禁止將原始秘密寫到 CLI 參數或 Git。

## 驗收與證據

本輪完整證據目錄：
C:\Users\prometheans\Documents\AIOT_FinishProject\outputs\quality_runs\oracle_forecastengine_acceptance_20261014_160405_c44b7d_Windows5800X

外部 Workers/ChatGPT MCP E2E 仍由另一對話實作驗收，不得因 Origin PASS 宣稱整體 E2E 成功。
