# 交接給 Claude Code（2026-10-16）

這份是 claude.ai 對話的交接。完整 review 存在 claude.ai 專案「AIOT_FinishProject」的 `claude/REVIEW_20261016.md`；下面節錄這次要用到的部分。

## 已經決定的事
- **英文名稱**：Fresh Market Price Forecast Agent
- **短名**：`fresh-market-price-agent`（資料夾、服務、Worker 都用這個）
- **環境變數前綴**：`FMPA_`（原本是 `TW01_`）
- **GitHub**：`https://github.com/prometheans152/FreshMarketPriceForecastAgent`（private，**目前還是空的**）
- **中文題目**：保留，只拿掉 TW01。
- **Python 套件名**：`aiot_price` 不改。
- **改名範圍**：第 1～3 層全部改（見下面），第 4 層歷史紀錄不動。
- **做法**：在分支 `rename/fresh-market-price-agent` 上改，開 PR 給使用者審。

## 已經做好的事
`.gitignore` 已補上 `/歷屆/`、`/*.zip`、`.wrangler/`、`.dev.vars`、`.build-check/`、`.secrets/`。

## 步驟 1：把目前的成果推上 GitHub（改名之前）
最後一次 commit 是 10/4（`9e29cdd`），10/5～10/15 的工作都還沒進版控。

```powershell
git check-ignore -v 歷屆 TW01_Docker_Portable_v1.0.0.zip .wrangler private outputs data models deploy/cloudflare-workers-mcp/.dev.vars
git add -A
git status --short   # 確認沒有 歷屆/、zip、private/、.secrets、.dev.vars
git commit -m "Snapshot 10/5-10/15: MCP integrations, Oracle/Docker/Workers deploy, pooled ML, tests"
git remote add origin https://github.com/prometheans152/FreshMarketPriceForecastAgent.git
git push -u origin main
```

- **只推 `main`**：不要用 `--all` 或 `--mirror`。`refs/codex/turn-diffs/*` 這些快照裡存著 `歷屆` 的 ZIP。
- **用 `-v` 跑 check-ignore**：上面每個路徑都要印出它命中的規則，有任何一個沒印就先別推。

## 步驟 2：改名，第 1、2 層
1. **對外文字**
   - README、docs 標題、design.md、AGENTS.md、TASKS.md 拿掉 TW01。
   - 網頁標題（`web/` 和 Oracle 網頁產生器 `deploy/oracle-forecastengine/build_*web_assets.py`）。
   - MCP server 的顯示名稱與描述。
   - pyproject 的 description。
   - 簡報檔名：`slides/**/TW01_*` 用 `git mv` 改名，簡報內容不重新產生。
2. **程式裡的名字**
   - 環境變數 `TW01_*` 改成 `FMPA_*`。**過渡期要同時能讀舊名**：新名不存在時退回讀 `TW01_*`，否則還沒切換的線上服務會壞掉。
   - `deploy/docker-tw01/` 改成 `deploy/docker/`，用 `git mv`。
   - nginx 的限流 zone 名稱和錯誤碼字串。
   - 瀏覽器存設定的鍵 `tw01_ui_prefs_v1`：改新鍵時**要加一次性搬移**，先讀舊鍵、寫進新鍵，舊鍵保留。Oracle 網頁的紀錄也存在 localStorage，一樣要搬，不然使用者存的東西會不見。
   - 寫死 TW01 字串的測試（大約在 `tests/integrations/` 有 6 個檔、`tests/fixtures/`）一起改。

**驗收條件**
- `pytest tests` 全過。建議在 pyproject 加 `[tool.pytest.ini_options] testpaths = ["tests"]`，這樣直接跑 pytest 就不會撿到 `outputs/` 裡的同名測試。
- `deploy/cloudflare-workers-mcp` 的 Node 測試 45/45 全過。
- `outputs/proposal_delivery/run3_20261004_01/protected_before.json` 列的保護檔，hash 和大小都不能變（模型與資料檔一律不動）。
- `git grep -i tw01` 只剩第 4 層和刻意保留的過渡相容碼，要在 PR 說明裡列出來。

## 步驟 3：已上線服務（PR 合併後，在 Windows 本機執行）
Oracle 的 SSH 金鑰（`~\.ssh\oracle_amd_ed25519`）和 Cloudflare 的 wrangler 登入都在這台電腦上。

1. **Cloudflare**
   - 用 `wrangler.jsonc` 的 `name: fresh-market-price-agent` 部署一個**新的** Worker。
   - 重新設定 secret `FORECASTENGINE_API_TOKEN`（**不要印出值**）。VPC binding 和限流設定照抄。
   - 跑 6/6 的 E2E 測試，通過後才把 ChatGPT connector 改連新網址 `https://fresh-market-price-agent.prometheans152.workers.dev/mcp`。
   - 舊的 `tw01-forecast-mcp` 確認沒人在用之後再刪。
2. **Oracle**
   - Docker Compose 專案和容器：`tw01-oracle-*` 改成新名。
   - systemd：`tw01-cloudflared`、`tw01-origin-firewall` 和 web override 改名。
   - `/etc/tw01-forecastengine/` 和 `/opt/tw01-docker/` 改到新路徑，舊路徑先留 symlink。
   - 照 `deploy/docker-tw01/oracle/ORACLE_DOCKER_OPERATIONS.md` 的回滾步驟準備好再動手。
3. **TLS 憑證（最後才做）**
   - `tw01-certbot-renew.timer` 最後才改名。
   - 憑證 **2026-10-20 22:25 UTC 到期**，先確認已經續期成功、到期日往後延了，再改 timer 名稱並確認新 timer 是 active。
4. **ChatGPT 私人插件**
   - 改顯示名稱。
   - `private/tw01_chatgpt_tunnel_codex_20261014/` 和 `tw01_tunnel.ps1` 裡的路徑要一起改；不改的話先保留原樣。
   - 不要讀取或印出 runtime key。

## 第 4 層：不要動
- `outputs/` 的審查證據資料夾名稱與內容。
- `private/` 裡的歷史資料。
- 選題歷史目錄裡的 TW01：那是當初 TW01～TWxx 候選題的編號。
- 凍結的模型和資料。

## 改名之後的優先事項（review 結論）
1. **Oracle 每天自動更新行情**：只刷新 `public_history`、不重訓；網頁要顯示資料日期；同時每天保存原始快照。來源可能只保留一年。
   - 模擬結果：資料舊 14 天，F1 會從 0.42 掉到約 0.40；舊 60 天掉到約 0.29～0.32，已經接近全持平基線。
2. **前瞻測試**：先寫好腳本並 commit。10/3 以後的資料模型從沒看過。
3. **README 改寫成期末報告入口**：要把 Oracle 網址和現況寫進去。`FINAL_REPORT.md:176`、`PUBLIC_MODEL_EVALUATION.md:18` 的「顯著」改用 bootstrap 信賴區間。
   - 模型減全持平：7 天 [+0.055, +0.169]、14 天 [+0.067, +0.172]。
   - 模型減動量：7 天 [−0.088, +0.088]、14 天 [−0.104, +0.084]。
4. **MCP 代理人加 1～2 個唯讀分析工具**：歷史走勢、跨市場比較。
5. **期末交付**：簡報、10 分鐘 YouTube、組員名單。
