# Oracle Docker — 正式維運與回滾

> **改名（2026-10-16）：** 本文已改用新名稱 `fresh-market-price-agent-*`／`FMPA_*`。線上 Oracle 主機與 Worker 在完成 [RENAME_MIGRATION.md](../../RENAME_MIGRATION.md) 之前仍是舊名 `tw01-*`；遷移前若需維運或回滾，請照 `main@1062818` 版本的本文件操作。

日期：2026-10-15。**原 Oracle VPS 已正式切到 Docker Compose。** IP、HTTPS Nginx、Cloudflare Tunnel、Let's Encrypt IP SAN 憑證均保留。

## 網址與系統

公開網頁：https://161.33.19.220/web/ （免帳密；61 品項、A/B、7/14 天）。

原 Cloudflare Workers MCP：https://fresh-market-price-agent.prometheans152.workers.dev/mcp （真實 6/6 E2E PASS）。

ForecastEngine 原 API 路徑 /v1/forecast、/v1/market-quote 仍需原 Bearer Token，只有原三品項、匿名 A；網頁可用新 57 品項 HGB，但 MCP 契約不擴充。Oracle 直連 /mcp 不公開，仍 404；Docker 自架的 MCP 是另外一個容器內服務。

主機 Nginx 負責 80 HTTP 轉址/ACME 驗證及 443 TLS，轉發全部本專案網頁/預測/API 到主機 localhost:8080 的 Docker web Nginx。其下在同一個 Docker private network 有：

- fresh-market-price-agent-oracle-forecast-1：FastAPI + 原三品項 v0.1.0 RF/HGB + 57 品項 v1.0.0 HGB，最多 650 MB。
- fresh-market-price-agent-oracle-mcp-1：可自架 Streamable HTTP MCP 兩工具，容器內 port 9000，最多 180 MB。
- fresh-market-price-agent-oracle-web-1：網頁、61 品項目錄及反向代理，主機只綁 127.0.0.1:8080，最多 80 MB。

正式目錄：/opt/fresh-market-price-agent-docker/stacks/20261015_120629

此版本不是在 1 GB Oracle 上重訓 ML：映像在 Windows 5800X WSL Docker 真正建置，並於 Oracle 使用來源 SHA256 已核對的 docker load 安裝；保存原始模型 hash，無任何私人紀錄上傳。

原 API Token 由 Oracle 原本的 root-only /etc/fresh-market-price-agent-forecastengine/origin.env 於 VM 本機轉交 Docker 0600 Secret，沒有出現在命令參數、公開原始碼、ZIP、聊天或日誌。Cloudflare Worker 的原 Secret 因此不用變更。新的自架 MCP Client Token 與 Origin Token 相異，同樣只有 root 可以讀取。

## 維運指令

在 Oracle 執行：

    cd /opt/fresh-market-price-agent-docker/stacks/20261015_120629
    sudo docker compose -p fresh-market-price-agent-oracle -f compose.yaml -f compose.oracle.yaml ps
    sudo docker compose -p fresh-market-price-agent-oracle -f compose.yaml -f compose.oracle.yaml logs --tail=50
    sudo docker compose -p fresh-market-price-agent-oracle -f compose.yaml -f compose.oracle.yaml up -d --no-build --pull never
    sudo systemctl status docker.service nginx.service fresh-market-price-agent-cloudflared.service fresh-market-price-agent-certbot-renew.timer

Docker daemon 開機自動啟動；三個專案容器設定 restart:unless-stopped。**舊** fresh-market-price-agent-forecastengine.service 現在 inactive、disabled，但原 service unit、模型及私人資料沒有刪除。

不使用 Compose 的 https/Caddy profile：Oracle 現有 Nginx 已合法占用 80/443 和自動續期，啟用 Caddy 會撞 port。

## 安全回滾（已通過 check-only 預檢）

原 Nginx 443 服務設定備份在：

    /etc/nginx/sites-available/fresh-market-price-agent-tls.conf.pre-docker-20261015_120629

獨立 root-only 範圍內回滾工具：

    /opt/fresh-market-price-agent-docker/ops/rollback_oracle.py

無副作用檢查：

    sudo python3 /opt/fresh-market-price-agent-docker/ops/rollback_oracle.py --tag 20261015_120629 --check-only

實際回滾：

    sudo python3 /opt/fresh-market-price-agent-docker/ops/rollback_oracle.py --tag 20261015_120629

先啟用原 systemd 8767，驗證服務能啟動後，才將 Nginx 路由切回原始設定並測試 nginx -t、reload。腳本不動憑證、Cloudflare Tunnel、原模型、任何私人店家紀錄或其他容器。回滾後可再手動停掉僅 fresh-market-price-agent-oracle 三容器釋放記憶體，勿執行全機 Docker prune、刪除模型或私有 Token。

## 已驗收

- Oracle Compose forecast、mcp、web 三容器均 healthy/running。
- Docker 平行期新/舊模型、A/B、61 品項、API 未授權 401 全通過。
- Nginx HTTPS 正式切換及舊服務停用後健康檢查 PASS。
- Windows 外網全部 ML/網頁回歸 **14/14 PASS**，新模型結果與 Windows 完全一致。
- 原 Cloudflare Workers MCP 經公網重新呼叫 **6/6 PASS**（含兩次匿名 A 和行情真值，未使用模擬資料）。
- 外網 HTTPS web、JS、catalog、health HTTP 200、TLS verify 0；root HTTP 301；原 /records 和 Oracle /mcp 都是 404。
- 舊版 RF/HGB、最新版兩個 HGB 模型 SHA256 均與原 Windows 封存完全一致。
- root-only Secret 權限 0600、原 VM 只有 Docker Web 埠 8080 綁 127.0.0.1；原 Python 8767 不再對 host 監聽。
- Nginx、docker、containerd、cloudflared、certbot renewal timer active；原 fresh-market-price-agent-forecastengine systemd inactive/disabled。
- 回滾備份與 live 路由比對無副作用預檢 PASS。未真的執行回滾。

Oracle 最後資源：實測停舊行程後 MemAvailable 約 454 MB，Swap 4095 MB，硬碟尚可用約 27 GB（45 GB 總量）；容器 CPU/記憶體仍應持續監看。

## 憑證與資料限制

原短效 Let's Encrypt IP SAN 憑證目前到期日為 **2026-10-20 22:25:53 UTC**。fresh-market-price-agent-certbot-renew.timer 維持 active，並未因切 Docker 而更改；務必監控實際續期成功，Docker 本身不會替現有 Nginx 自動更新憑證。

行情資料仍截止 2026-10-02，不是即時單店價格。原三品項 RF/HGB 與新 57 品項 HGB 皆未經同店到期驗證；新 HGB 7/14 天測試 MAE 未勝不變價基準。B 是固定 α=0.3 的實驗性規則。

## 證據

Windows 5800X 的原工作根目錄：

    C:\Users\prometheans\Documents\AIOT_FinishProject

本輪品質驗收：

    outputs\quality_runs\oracle_docker_migration_20261015_120629_Windows5800X

主要檔案：prepare_stack.log、docker_image_load.log、oracle_compose_start.log、docker_pre_cutover_public_smoke.log、nginx_docker_cutover.log、cloudflare_mcp_after_docker_cutover.json、oracle_docker_external_ml_14cases.json、oracle_docker_postcutover_resources.log、rollback_dry_run.log、oracle_docker_final_security_and_hashes.log。

可提供其他人複製的原始公開 ZIP 仍位於專案根目錄 TW01_Docker_Portable_v1.0.0.zip；切勿將 Oracle 的 .secrets、origin.env、私人紀錄或現機目錄一起分享。
