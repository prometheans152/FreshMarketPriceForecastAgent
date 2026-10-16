# 菜市場現場價格預測 — Portable Docker（Fresh Market Price Forecast Agent）

**完整可複製版：網頁 + 已訓練的 7／14 天模型 + A/B 比較 + 兩工具 MCP Server。**

這份 ZIP **不包含** Oracle/Cloudflare 的真實 Token、個人金鑰、私人店家紀錄、帳號或 DNS。各台電腦安裝後都會自行產生新密碼，不會共用你目前 Oracle 的權限。

## 一、快速安裝

需求：Docker Engine + Docker Compose v2+、x86_64 Linux 或 Windows Docker Desktop（Linux containers）。推薦至少 2GB 可用 RAM、足夠磁碟與首次安裝的網路（下載公開套件）。

Windows PowerShell：

~~~powershell
Expand-Archive .\FMPA_Docker_Portable_v1.1.0.zip -DestinationPath .\
cd .\FMPA_Docker_Portable_v1.1.0
python setup.py
docker compose up -d --build
docker compose ps
~~~

Linux/macOS：

~~~bash
unzip FMPA_Docker_Portable_v1.1.0.zip
cd FMPA_Docker_Portable_v1.1.0
python3 setup.py
docker compose up -d --build
docker compose ps
~~~

如果 Windows 沒安裝 Python，也可使用 Docker 執行內附的 Python 標準庫設定工具：

~~~powershell
docker run --rm -v "$($PWD.Path):/work" -w /work python:3.12-slim python setup.py
~~~

如果 Windows PowerShell 找不到 docker 指令，但電腦的 WSL Linux 已安裝 Docker Engine（如 Windows 5800X 的 Ubuntu-24.04），可直接使用 WSL 內的 Compose：

~~~powershell
$linuxPath = (wsl --distribution Ubuntu-24.04 --exec wslpath -a $PWD.Path).Trim()
wsl --distribution Ubuntu-24.04 --exec sh -lc "cd '$linuxPath' && python3 setup.py && docker compose up -d --build"
~~~

這不是安裝到另一台 Ubuntu Server；只是從 Windows 呼叫**這台電腦 WSL 本機**的 Docker。其他 WSL 發行版請自行改成實際安裝 Docker 的名稱。

setup.py 第一次執行會產生兩個不同的安全 Token，僅顯示 CREATED，不會輸出 Token 本文。注意**不要把安裝後的 .secrets、.env 打包給別人**。

開啟 **http://localhost:8080/web/**（免登入；完整 61 項）或 http://localhost:8080/（自動進入首頁）。驗收：python tests/smoke.py。

停止：docker compose down。重新啟動：docker compose up -d。保留 .secrets 以維持原 MCP 認證。

## 二、Docker 服務分工

| 容器 | 功能 | 對外網路 |
| --- | --- | --- |
| forecast | FastAPI + 原 RF 7天/HGB 14天 v0.1.0 + 新兩個 pooled HGB 1.0.0；匿名 A 與網頁 A/B | 只有 Docker 內網 8767，不開外部 port |
| web | Nginx 61 品項網頁、品項搜尋、A/B、/v1 API 與 /mcp 反向代理 | 預設只在 127.0.0.1:8080 |
| mcp | 自架標準 Streamable HTTP MCP；兩項工具 get_market_quote、post_forecast | 只有 Docker 內網 9000，通過 web 代理 |
| https（選填） | Caddy 自動管理公網 DNS 網域的 HTTPS 憑證 | 啟用 https profile 才會開 80/443 |

網頁紀錄保存/查詢/刪除/匯出只在使用者自己的**瀏覽器 localStorage**，不會儲存個別店家私人紀錄在 Docker/VPS；換電腦或網址需自行匯出資料。

## 三、真實 ML 與限制

公開資料來源：臺中市公有零售市場每日蔬果價格（data.gov.tw/dataset/84539），來源快照截止 **2026-10-02**，**不是當日即時店價**。61 個官方價格欄包含蔬菜 15、水果 27、魚海鮮 7、肉 10、蛋 2；其中 60 項有歷史正價，牛心柿全缺測不得預測。61 欄**不是全部臺灣蔬菜**。

原三種高麗菜、青江白菜、絲瓜仍使用凍結 v0.1.0 RF/HGB；新增有價 57 項使用**確實已訓練、時間序列切分並測試的 2 個 HGB 回歸模型（7天／14天各一個）**，不是只靠歷史動量規則。B 仍是固定係數 0.3 的實驗性調整，**不是另外訓練的 B 模型**。

獨立時間留出測試的相對變化 MAE：

| | ML 7天 | ML 14天 |
| --- | ---: | ---: |
| 新 HGB MAE | 0.02124 | 0.03130 |
| 不變價基準 MAE（愈小愈好） | **0.01163** | **0.02085** |

**兩個模型的 MAE 都沒有勝過不變價基準，且尚無同店到期真價驗證**；不能宣稱預測很準、個店準確度已驗證、或機率區間已校準。

## 四、MCP 連線

本機 MCP：**http://localhost:8080/mcp**，預設使用獨立 MCP Client Bearer Token；和後端 Origin API Token 不同。

在安裝電腦自己的終端、只為連線 MCP 用戶端時查看：

~~~powershell
Get-Content .\.secrets\mcp_client_token
~~~

Linux/macOS：cat .secrets/mcp_client_token。MCP 用戶端送 Authorization: Bearer（其後接 MCP Token）。切勿將值貼到 Git、聊天或公開截圖。

若連接的客戶端只支援 No Auth，必須先為自己的部署設定 TLS 與流量配額，再將 .env 中 FMPA_MCP_AUTH_MODE 改成 public_noauth；公開模式所有人都能使用兩項工具。**絕對不能以網頁免登入為由取消 /v1/forecast、/v1/market-quote 的服務端 Bearer**。

MCP 僅提供原版 3 品項、匿名 A 及公開行情，禁止 B、私人紀錄、任意 URL 或程式；新增 57 品項的 HGB 僅供網頁。Cloudflare Workers 的 VPC/Secret 屬原先另一個雲端整合，**不能直接隨 Docker 複製**；這份 ZIP 內的 mcp 服務是可自架替代入口，並非原 Cloudflare 設定。

## 五、公開 HTTPS 網址

**預設僅本機 HTTP**：FMPA_BIND_ADDRESS=127.0.0.1，FMPA_HTTP_PORT=8080。（v1.0.0 舊 .env 的 TW01_* 變數名仍可讀，新名優先；建議改成 FMPA_*。）想開放給其他人，應使用公網 DNS 域名 + TLS；不要將 HTTP 8080 直接改綁 0.0.0.0，否則 API/MCP Token 可能在網路中遭窺探。

在自己的新 Docker VPS 設定 DNS A/AAAA 指向主機，在 .env 中新增：

~~~dotenv
FMPA_PUBLIC_DOMAIN=forecast.yourdomain.example
FMPA_PUBLIC_ORIGIN=https://forecast.yourdomain.example
~~~

在真正的 DNS 指向/防火牆 80、443 可用後執行：

~~~bash
docker compose --profile https up -d --build
~~~

域名是範例，不能直接複製使用。首頁為 https://你的域名/web/、MCP 為 https://你的域名/mcp。IP 位址自動 TLS 是否受支援取決於證書提供方，不應沿用原 Oracle 的 IP-SAN 憑證或跳過 TLS 驗證。

若已有 Cloudflare Tunnel/其他反向代理，也能將其 HTTPS 上游代理到 loopback 8080，並將 FMPA_PUBLIC_ORIGIN 改成使用者瀏覽器看到的真實 HTTPS 原點。**Public Origin 必須精確相符**，否則同源安全驗證會拒絕網頁預測。代理後的 IP 限流可能共用單個代理 IP，公網還應在外層設流量配額與存取政策。

## 六、備份、搬家與安全

- 搬家：只分享尚未使用的 ZIP；每台重新 python3 setup.py，產生新 Token。**不分享已設定的 .secrets、.env、私人記錄、SSH Key。**
- 網頁輸入今日和上週的店價用於推論，但伺服器不保存私人紀錄；所有保存到瀏覽器的資料，需使用網頁「匯出」備份。
- 停止：docker compose down；恢復：docker compose up -d；狀態：docker compose ps；系統紀錄：docker compose logs --tail=50。
- 版本資料均有 SHA256：RELEASE_MANIFEST.json、SHA256SUMS.txt、ML release manifest 及原 RF/HGB manifest。新模型升級應建立**新版本發布包**而不是覆寫凍結的 v0.1.0 模型。
- 這份可攜版**不會修改原主人正在運作的 Oracle systemd/Nginx/TLS 正式服務**。如日後要切換生產環境，須獨立規劃健康檢查、資料備份與回滾，避免中斷。

## 七、驗收

本包附純 Python 標準庫的 tests/smoke.py，可對已啟動的 localhost Compose 進行真正 HTTP/ML/MCP 測試，不需要傳送 Token 到外部服務：

~~~bash
python3 tests/smoke.py
~~~

僅執行 docker compose config 表示 YAML 正確，**不代表容器啟動、ML 計算或 MCP 能實際連線**；分享前應保存真實端到端測試結果。
