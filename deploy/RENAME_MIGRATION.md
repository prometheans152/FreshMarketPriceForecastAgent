# 改名上線遷移手冊（第 3 步：PR 合併後執行）

> **執行進度（2026-10-17 01:25 台灣時間）：Oracle 主機完成，Cloudflare／TLS／ChatGPT 未做。**
> - **已完成：**
>   - 3.3：7 個目錄搬到新名，舊路徑留 symlink；Compose 專案改為 `fresh-market-price-agent-oracle`。
>   - 3.4：Nginx 檔名全部改名；新版回滾腳本 `--check-only` 為 READY。
>   - 3.5：forecastengine（disabled）、origin-firewall（只剩 `fmpa_` 規則）、cloudflared（4 條連線）都已改用新名稱。
>   - 驗證：舊 Worker 6/6 E2E 在搬遷後與全部改完後各跑一次，都 PASS；外部 HTTPS 200；ACME 路徑經 symlink 驗證正常。
>   - 舊檔備份在主機 `/root/fmpa-rename-backup-20261017/`。
> - **未做：**
>   - 第 2 節新 Worker：wrangler 目前登入 publicai416 的 Cloudflare 帳號，服務在 Prometheans152 帳號。
>   - 第 4 節 certbot timer：等憑證續期後再改，`tw01-certbot-renew.*` 仍是舊名，經 symlink 正常運作。
>   - 第 5 節 ChatGPT 插件。
> - 3.5 第 3 點的實際做法：cloudflared 切換的就緒檢查請用 `journalctl --since "@<epoch>"`；ISO 時間加 `Z` 會被 journalctl 拒絕。
>
> 以下第 2、4、5 節仍是計畫。
> 執行者需在 Windows 本機（有 `~\.ssh\oracle_amd_ed25519` 與 wrangler 登入）逐步操作、逐步驗證並記錄。
> Oracle 已遷移：日常維運照 `deploy/docker/oracle/ORACLE_DOCKER_OPERATIONS.md`；回滾用新版 `/opt/fresh-market-price-agent-docker/ops/rollback_oracle.py`（舊路徑經 symlink 同一檔）。

## 0. 原則

- **先並存、後切換、再清理。** 新資源驗證通過才停舊資源；舊路徑一律留 symlink。
- **順序固定：** Cloudflare → Oracle → TLS（最後）→ ChatGPT 私人插件。
- **不印出任何秘密：** `FORECASTENGINE_API_TOKEN`、`origin.env`、tunnel token、runtime key 都不可出現在終端、聊天或紀錄。
- **TLS 憑證 2026-10-20 22:25 UTC 到期。** 確認續期成功、到期日往後延之前，不動 certbot timer。
- 實際主機狀態若與下表不同，**先停下來更新本手冊**，不要硬套指令。

## 1. 名稱對照表

| 類別 | 舊名（目前線上） | 新名 |
| --- | --- | --- |
| Worker | `tw01-forecast-mcp` | `fresh-market-price-agent` |
| MCP 網址 | `https://tw01-forecast-mcp.prometheans152.workers.dev/mcp` | `https://fresh-market-price-agent.prometheans152.workers.dev/mcp` |
| MCP serverInfo.name | `tw01-forecastengine-remote` | `fresh-market-price-agent-forecastengine-remote` |
| Compose 專案／容器 | `tw01-oracle`（`tw01-oracle-{web,forecast,mcp}-1`） | `fresh-market-price-agent-oracle`（`…-oracle-{web,forecast,mcp}-1`） |
| systemd | `tw01-forecastengine.service`（含 `.service.d/20-web-frontend.conf`） | `fresh-market-price-agent-forecastengine.service` |
| systemd | `tw01-cloudflared.service` | `fresh-market-price-agent-cloudflared.service` |
| systemd | `tw01-origin-firewall.service` | `fresh-market-price-agent-origin-firewall.service` |
| systemd（最後） | `tw01-certbot-renew.service`／`.timer` | `fresh-market-price-agent-certbot-renew.service`／`.timer` |
| 腳本 | `/usr/local/sbin/tw01-origin-firewall.sh` | `/usr/local/sbin/fresh-market-price-agent-origin-firewall.sh` |
| 目錄（舊路徑留 symlink） | `/etc/tw01-forecastengine/` | `/etc/fresh-market-price-agent-forecastengine/` |
| 〃 | `/etc/tw01-cloudflared/` | `/etc/fresh-market-price-agent-cloudflared/` |
| 〃 | `/opt/tw01-forecastengine/` | `/opt/fresh-market-price-agent-forecastengine/` |
| 〃 | `/opt/tw01-forecastengine-web/` | `/opt/fresh-market-price-agent-forecastengine-web/` |
| 〃 | `/opt/tw01-docker/` | `/opt/fresh-market-price-agent-docker/` |
| 〃 | `/var/www/tw01-website/` | `/var/www/fresh-market-price-agent-website/` |
| 〃 | `/var/www/tw01-acme/`（ACME webroot） | `/var/www/fresh-market-price-agent-acme/` |
| Nginx | `sites-available/tw01-tls.conf`（含 `.pre-docker-20261015_120629`、`.backup-c44b7d` 備份） | `sites-available/fresh-market-price-agent-tls.conf`（備份同步改名） |
| Nginx | `sites-available/tw01-acme.conf`、`conf.d/tw01-public-web-rate-limit.conf`、`snippets/tw01-web-auth.conf`、`/etc/nginx/.tw01-web.htpasswd` | 前綴改成 `fresh-market-price-agent-` |
| iptables 註記 | `tw01_forecastengine_origin_v1` | `fmpa_forecastengine_origin_v1`（新腳本 `remove` 會一併清掉舊註記） |
| 環境變數 | `TW01_*` | `FMPA_*`（程式先讀新名，新名不存在才讀舊名） |
| 瀏覽器 localStorage | `tw01_ui_prefs_v1`、`tw01_web_browser_only_records_v1` | `fmpa_*`（新版網頁載入時自動複製一次，舊鍵保留） |

**刻意不改**（改了會破壞線上狀態或凍結證據）：

- Linux 帳號 `tw01forecast`、`tw01tunnel`；網頁 Basic Auth 帳號 `tw01web`。
- Cloudflare Tunnel `tw01-oraclevpc-20261014`（VPC Service 綁在它上面）。
- 凍結 bundle 的 `bundle_type: TW01_FROZEN_ORACLE_A_ONLY`（`provision_service.sh` 以 hash 鎖定）。
- 已上線的 v1.0.0 release：`TW01_Docker_Portable_v1.0.0.zip`、`tw01_verified_linux_amd64_images.tar.gz`、映像 `tw01-portable-*:1.0.0`，以及該 stack `.env` 內的 `TW01_*`（`prepare_oracle_stack.py` 以 hash 鎖定）。新命名的 v1.1.0 需另行建置與驗證。
- `/etc/…/origin.env` 內容：保留 `TW01_ORIGIN_API_TOKEN=` 那一行，新舊程式都讀得到。
- 線上 Nginx 設定**內容**裡的舊路徑與 zone 名稱：經 symlink 仍有效，內容改寫列為選做（見 3.6）。

## 2. Cloudflare（新 Worker 並存，驗證後才切 ChatGPT）

在 `deploy/cloudflare-workers-mcp/`（已合併的 main）：

1. 先跑本機測試：`npm test`，須 45/45 以上全過。
2. 部署新 Worker：`npx wrangler deploy`。`wrangler.jsonc` 的 `name` 已是 `fresh-market-price-agent`；VPC binding（`service_id`）與四個限流設定照抄自舊 Worker。限流 `namespace_id` 與舊 Worker 相同，並存期間共用計數。
3. 設定 secret（**不可印出值**）：`npx wrangler secret put FORECASTENGINE_API_TOKEN --name fresh-market-price-agent`。值與舊 Worker 相同（即 Oracle `origin.env` 的 origin token）。用輸入隱藏的互動模式或不落地的管線；若用管線，注意尾端換行。
4. 確認只看名稱：`npx wrangler secret list --name fresh-market-price-agent`。
5. 跑 6/6 真實 E2E：`node test/real-remote-acceptance.mjs <私人輸出 JSON 路徑>`（腳本已指向新網址）。token 錯誤會在這一步以 401 失敗。
6. **6/6 通過後**才把 ChatGPT connector 改連 `https://fresh-market-price-agent.prometheans152.workers.dev/mcp`。Gemini 設定同理。
7. 舊 Worker `tw01-forecast-mcp` 先保留；用 Cloudflare 儀表板或 `npx wrangler tail tw01-forecast-mcp` 確認一段時間沒有流量後再刪除（需使用者另外同意）。

回滾：ChatGPT connector 改回舊網址即可；舊 Worker 期間完全未動。

## 3. Oracle

### 3.1 先唯讀盤點（不改任何東西）

```bash
ssh -i ~/.ssh/oracle_amd_ed25519 ubuntu@161.33.19.220
sudo systemctl list-unit-files 'tw01-*'
sudo systemctl list-units --all 'tw01-*'
sudo docker compose ls
ls -ld /etc/tw01-* /opt/tw01-* /var/www/tw01-*
ls -l /etc/nginx/sites-available /etc/nginx/sites-enabled /etc/nginx/conf.d /etc/nginx/snippets | grep tw01
sudo grep -rn tw01 /etc/letsencrypt/renewal/
sudo iptables -S INPUT | grep forecastengine_origin
sudo python3 /opt/tw01-docker/ops/rollback_oracle.py --tag 20261015_120629 --check-only
```

最後一行必須印出 `SCOPED_ROLLBACK_READY=YES`，否則先停。

### 3.2 上傳新版部署檔

把合併後 repo 的 `deploy/oracle-forecastengine/fresh-market-price-agent-*`（unit、firewall 腳本、conf）與 `deploy/docker/oracle/rollback_oracle.py` 上傳到 `/home/ubuntu/fresh-market-price-agent-rename-stage-<日期>/`，逐檔比對 SHA256。上傳前確認 `.sh`／`.service`／`.timer`／`.conf` 是 LF 行尾：本 repo 沒有 `.gitattributes`，Windows 簽出可能變成 CRLF，shell 腳本會因此無法執行。

### 3.3 停 Docker → 搬目錄 → 用新專案名啟動（短暫中斷）

```bash
cd /opt/tw01-docker/stacks/20261015_120629
sudo docker compose -p tw01-oracle -f compose.yaml -f compose.oracle.yaml down
for d in /etc/tw01-forecastengine /etc/tw01-cloudflared /opt/tw01-forecastengine \
         /opt/tw01-forecastengine-web /opt/tw01-docker /var/www/tw01-website /var/www/tw01-acme; do
  new="${d/tw01-/fresh-market-price-agent-}"
  sudo mv "$d" "$new" && sudo ln -s "$new" "$d"
done
cd /opt/fresh-market-price-agent-docker/stacks/20261015_120629
sudo docker compose -p fresh-market-price-agent-oracle -f compose.yaml -f compose.oracle.yaml up -d --no-build --pull never
sudo docker compose -p fresh-market-price-agent-oracle -f compose.yaml -f compose.oracle.yaml ps
```

- 這個 stack 是凍結的 v1.0.0，`.env` 仍是 `TW01_*`，正確，不要改。
- **`/opt/tw01-forecastengine` 的 symlink 不可刪：** 裡面的 `venv`、`acme-venv` 腳本 shebang 寫死舊絕對路徑，刪掉會讓 certbot 與回滾服務失效。重建 venv 是另一項工作。
- 驗證：`ps` 三個容器皆 healthy／running；從 Windows 瀏覽器開 `https://161.33.19.220` 完成一次預測；Worker E2E 再跑一次。
- 回滾：`down` 新專案、把目錄搬回並刪 symlink、用 `-p tw01-oracle` `up`。

### 3.4 Nginx 檔名

```bash
cd /etc/nginx/sites-available
for f in tw01-tls.conf* tw01-acme.conf*; do   # 含 .pre-docker-*、.pre-catalog-*、.backup-* 備份
  sudo mv "$f" "${f/tw01-/fresh-market-price-agent-}"
done
sudo ln -s /etc/nginx/sites-available/fresh-market-price-agent-tls.conf /etc/nginx/sites-enabled/
sudo ln -s /etc/nginx/sites-available/fresh-market-price-agent-acme.conf /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/tw01-tls.conf /etc/nginx/sites-enabled/tw01-acme.conf
sudo mv /etc/nginx/conf.d/tw01-public-web-rate-limit.conf /etc/nginx/conf.d/fresh-market-price-agent-public-web-rate-limit.conf
sudo mv /etc/nginx/snippets/tw01-web-auth.conf /etc/nginx/snippets/fresh-market-price-agent-web-auth.conf  # 若存在
sudo mv /etc/nginx/.tw01-web.htpasswd /etc/nginx/.fresh-market-price-agent-web.htpasswd                    # 若存在
sudo nginx -t && sudo systemctl reload nginx
```

- 新舊 site 不可同時在 `sites-enabled`，否則 server block 重複。
- 若某個設定檔 `include` 了改名的 snippet／htpasswd，先改那一行再 `nginx -t`；`nginx -t` 失敗就把檔名改回，不 reload。
- `.pre-docker-20261015_120629` 備份必須是**實體檔案**（新版 `rollback_oracle.py` 拒絕 symlink）。
- 安裝新版回滾腳本並自檢：

```bash
sudo install -m 0755 <stage>/rollback_oracle.py /opt/fresh-market-price-agent-docker/ops/rollback_oracle.py
sudo python3 /opt/fresh-market-price-agent-docker/ops/rollback_oracle.py --tag 20261015_120629 --check-only
```

### 3.5 systemd（除 certbot 外）

1. **forecastengine（目前 inactive/disabled，是回滾目標，零中斷）：** 安裝新 unit，把 drop-in 目錄改名，內容不改（舊路徑經 symlink 有效，`TW01_POOLED_ML_DIR` 由舊版程式讀取）。

   ```bash
   sudo install -m 0644 <stage>/fresh-market-price-agent-forecastengine.service /etc/systemd/system/
   sudo mv /etc/systemd/system/tw01-forecastengine.service.d /etc/systemd/system/fresh-market-price-agent-forecastengine.service.d
   sudo systemctl daemon-reload
   systemctl cat fresh-market-price-agent-forecastengine.service   # 確認 drop-in 已套用
   sudo rm /etc/systemd/system/tw01-forecastengine.service && sudo systemctl daemon-reload
   ```

   保持 disabled；3.4 的回滾自檢必須仍是 `SCOPED_ROLLBACK_READY=YES`。

2. **origin-firewall（先加新規則再拆舊規則，無空窗）：**

   ```bash
   sudo install -m 0755 <stage>/fresh-market-price-agent-origin-firewall.sh /usr/local/sbin/
   sudo install -m 0644 <stage>/fresh-market-price-agent-origin-firewall.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now fresh-market-price-agent-origin-firewall.service
   sudo systemctl disable --now tw01-origin-firewall.service   # 舊 ExecStop 只移除舊註記規則
   sudo iptables -S INPUT | grep forecastengine_origin          # 應只剩 2 條 fmpa_ 規則
   ```

3. **cloudflared（數秒中斷，Worker 請求會短暫失敗）：** 帳號 `tw01tunnel` 不改；token 檔已隨 3.3 移到新目錄。

   ```bash
   sudo install -m 0644 <stage>/fresh-market-price-agent-cloudflared.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl disable --now tw01-cloudflared.service
   sudo systemctl enable --now fresh-market-price-agent-cloudflared.service
   systemctl is-active fresh-market-price-agent-cloudflared.service
   ```

   之後再跑 Worker E2E 6/6。回滾：反向停新啟舊。

### 3.6（選做）設定檔內容改寫

線上 Nginx／systemd 檔案內容仍含 `/var/www/tw01-website/`、`tw01_public_web_per_ip` 等舊字串，經 symlink 仍正常。要改寫時一次一檔：先 `cp -a` 備份、改寫、`nginx -t`（或 `systemd-analyze verify`）通過才 reload；zone 名稱必須在 `conf.d` 定義與 `limit_req` 使用處同時改。

## 4. TLS（最後；2026-10-20 22:25 UTC 到期）

1. 先確認已續期：`sudo /opt/fresh-market-price-agent-forecastengine/acme-venv/bin/certbot certificates`，到期日必須晚於 2026-10-20 22:25 UTC；`systemctl list-timers 'tw01-certbot-renew.timer'` 的上次執行成功。
2. 續期 webroot：`/etc/letsencrypt/renewal/` 若寫 `/var/www/tw01-acme`，經 symlink 仍有效，**不要刪該 symlink**。
3. 先啟用新 timer、再停舊 timer，任何時刻至少一個 timer active：

   ```bash
   sudo install -m 0644 <stage>/fresh-market-price-agent-certbot-renew.service <stage>/fresh-market-price-agent-certbot-renew.timer /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now fresh-market-price-agent-certbot-renew.timer
   sudo /opt/fresh-market-price-agent-forecastengine/acme-venv/bin/certbot renew --dry-run --cert-name 161.33.19.220
   sudo systemctl disable --now tw01-certbot-renew.timer
   systemctl is-active fresh-market-price-agent-certbot-renew.timer
   systemctl list-timers 'fresh-market-price-agent-certbot-renew.timer'
   ```

## 5. ChatGPT 私人插件

- 在 ChatGPT 改顯示名稱（目前為「TW01 菜價查詢與 A 預測」）。
- `private/tw01_chatgpt_tunnel_codex_20261014/` 與 `tw01_tunnel.ps1` 內的路徑：要改就兩者一起改並重跑 `-Action Doctor`；不改就保留原樣。
- 不讀取、不印出 runtime key。

## 6. 完成後的清理（需使用者另外同意）

- 舊 Worker `tw01-forecast-mcp` 確認無流量後刪除。
- `/etc/systemd/system/tw01-*` 舊 unit 檔移除（先 `disable`，再刪檔、`daemon-reload`）。
- 舊路徑 symlink：`/opt/tw01-forecastengine` 必須等 venv 重建後才可移除；其餘可在確認沒有任何設定引用舊路徑（`sudo grep -rn tw01 /etc /opt`）後移除。
- repo 端：所有主機完成遷移後，再開 PR 移除 `TW01_*` 環境變數與 localStorage 舊鍵的過渡相容碼。
