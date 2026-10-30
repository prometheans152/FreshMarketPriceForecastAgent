# 滾動公開行情歷史（D48）

日期：2026-10-30。狀態：本機實作與測試完成，經使用者核准後已於 2026-10-30 17:13 UTC 部署到 Oracle（見第 7 節）。

## 1. 要解決的問題

線上 ForecastEngine 的兩組模型都只用「查詢日前一天以前的公開市場行情」做特徵：最近價格與它的天數、7／14／28 天平均、14 天波動與高低、7／14 天變化。使用者輸入的店價只用來把結果換算成店價。

但線上的公開行情停在 2026-10-02 的快照：

- 原 3 品項（甘藍、青江白菜、絲瓜）的 RF/HGB 特徵卡在 9 月底。
- 57 品項 HGB 的視窗從 t−1 往回算，大多已經沒有資料。
- `forecast_baseline` 遇到最新行情超過 45 天的品項會拒絕預測（`CUTOFF_AGE_MAX_DAYS`）。約 2026-11-16 起，網頁與 ChatGPT 的大多數品項會停止服務。

目標：每天改用台中最新的公開行情，**不重訓、不改任何凍結檔案或已報告的數字**。

## 2. 來源查核（2026-10-30）

- 來源：臺中市公有零售市場每日蔬果價格（data.gov.tw/84539），網址同 `configs/data_sources.yaml`。
- 2026-10-30 23:03（台北）下載：HTTP 200，5,349,735 bytes，SHA-256 `f9be9aa0…`。
- 內容：4,472 列，14 個市場（含停用的建國市場），欄位仍是 63 個且順序不變。日期 2025-10-31～**2026-10-29**，共 364 天。
- 來源是一年滾動視窗，舊日期會被移除。所以新資料只能**接在凍結快照後面**，不能拿來取代快照。
- 與凍結快照重疊的日期，比對 251,442 個值，**0 個不同**。
- 2026-10-03 之後有 340 列，其中 314 列屬於 13 個支援市場。另有 9 列是快照當時還沒公布的舊日期市場日。
- 最後一天常常只公布部分市場（10-29 只有 7 列），之後才補齊。

證據：`outputs/quality_runs/rolling_history_d48_20261030/download/`（outputs 已被 gitignore）。

## 3. 為什麼不能直接換檔

映像裡有三道刻意把模型綁在 2026-10-02 快照的檢查，任何直接換檔都會讓所有預測拒絕：

| 檢查 | 位置 | 綁住的東西 |
| --- | --- | --- |
| `FROZEN_SHA256`／`verified_release_snapshot` | `src/aiot_price/integrations/chatgpt_adapter.py` | release 0.1.0 的 5 個檔案，包含 `public_history.parquet`；3 品項每次請求都檢查 |
| `data_bundle()` | `deploy/oracle-forecastengine/full_catalog_runtime.py` | 61 品項目錄與歷史檔對 manifest 的 hash |
| `ml_release()` | `deploy/oracle-forecastengine/pooled_ml_runtime.py` | 57 品項模型的 `source_sha256`、`source_cutoff` 必須等於目錄 manifest |

這三道檢查保護的是「模型＋它的訓練資料」，本設計**全部保留，照舊執行**。

## 4. 設計：凍結快照與滾動推論歷史分開

```
台中來源 ──► rolling-updater（一次性容器，每天 2 次）
              下載 → 驗證 → 與上一個好版本合併 → 驗證 → 寫入新版本 → 換 CURRENT.json
                                                         │
forecast 容器（唯讀掛載滾動資料夾）◄────────────────────────┘
  1. 照舊驗證凍結 release 與目錄（三道檢查都跑）
  2. 再改用「最新且驗證通過」的滾動版本當模型輸入
```

### 4.1 一個版本裡有什麼

主機資料夾 `/opt/fresh-market-price-agent-docker/rolling-history/`（在 stack 外，換 stack 也不會遺失）：

| 檔案 | 內容 |
| --- | --- |
| `CURRENT.json` | 目前版本 ID、它的 manifest SHA-256、以及較舊的好版本清單（退回用） |
| `versions/<日期>-<12碼hash>/manifest.json` | 版本、截止日、凍結快照身分、來源下載資訊、筆數、合併統計、每個檔的 SHA-256 |
| `source_rows.json.gz` | 2026-10-02 之後的來源原始列，排序後的標準內容，版本 ID 由它的 hash 而來 |
| `download.json.gz` | 這個版本所用的原始下載，可稽核與重建 |
| `public_history.parquet` | 3 品項，和 release 0.1.0 相同格式：凍結內容原封不動在前，新列接在後面 |
| `catalog.json`、`public_history.json.gz` | 61 品項，和映像目錄相同格式，只更新截止日與各市場統計 |
| `status.json`、`runs.jsonl` | 每次執行的結果（成功切換／沒有新資料／拒絕／下載失敗） |

衍生檔案的轉換規則與原始建置程式完全相同，0 和空白都當缺測：

- 3 品項：沿用 `load_taichung_long`，同 `models/package.py`。
- 61 品項：同 `build_full_market_catalog.py`。

測試已證明用這套規則從凍結原始 JSON 重建，結果和凍結檔逐值相同（第 6 節）。

### 4.2 切換前的驗證

**下載本身**（任何一項不符就整批拒絕）：

- 大小 1 byte～50 MB；必須是 UTF-8 JSON 陣列。
- 每列恰好是原本的 63 個欄位，名稱與順序都相同。
- 市場只能是 13 個支援市場或「(停)」開頭的停用市場。
- 日期是有效的 YYYYMMDD，不在未來，年份不早於 2020。
- 價格只能是非負數字字串，且不超過 100,000 元／台斤（擋單位錯誤）。
- 同一市場同一天出現兩列且內容不同時拒絕。

**和上一個好版本比較：**

- 支援市場的列數不得少於上次下載的 90%，用來擋被截斷的下載。來源真的縮短視窗時，要人工加 `--accept-shorter-download` 一次，manifest 會記下。
- 最新日期不得早於目前版本的截止日。
- 重新公布的舊值和已接受的值不同者，不得超過 1%，用來擋欄位對調或改定義。凍結期間的值只比對，**永遠不改**。
- 只有最近 7 天的修正會套用；更舊的修正只計數，不套用。
- 新值相對該序列最近 28 筆的中位數變動超過 5 倍者，若超過 5%，視為單位改變而拒絕。零星的離群值照樣收，與原本的訓練資料處理一致。
- 合併後的列數不得比上一版少，已接受的列不會消失。

**寫入的版本**（更新器寫完後，與伺服器載入時都會再跑一次）：

- manifest 的 SHA-256 必須等於 `CURRENT.json` 所記錄的值，每個檔的 hash 也必須等於 manifest。
- manifest 的凍結快照身分必須和映像裡的凍結檔一致，包含訓練來源 `172dffc7…`、截止日，以及凍結 parquet 與目錄的 hash。
- **凍結前綴不變**：
  - 61 品項歷史截到 2026-10-02 後，標準序列化的 hash 必須等於凍結歷史。
  - 3 品項 parquet 的前 12,288 列必須與凍結 parquet 完全相同。
  - 這項是在「hash 全部重算過也能抓到」的竄改測試裡被證明需要的。
- 日期遞增、價格為正，目錄統計必須與歷史一致，三處截止日必須相同。

### 4.3 原子切換、保留版本、自動退回

- 新版本先寫在 `versions/.tmp-*`，fsync 後改名，**再用伺服器同一套檢查驗一次**。通過後才用「寫暫存檔＋`os.replace`」原子更新 `CURRENT.json`。
- 最多保留 20 個版本（每版約 0.5 MB），`CURRENT.json` 沒列到的才刪。
- 退回順序：`CURRENT` → 清單裡較舊的好版本 → 都不行就回到**2026-10-02 凍結快照**，也就是 D48 之前的線上行為。
- 執行中如果 `CURRENT` 指到壞版本，會繼續服務記憶體裡最後一個好版本。
- 下一次更新會以最後一個好版本為基礎重建，並取代壞掉的版本。

### 4.4 服務端怎麼接（不重建映像）

和 D47 一樣，用 compose override 唯讀掛入模組。`rolling_runtime.py` 只替換三個入口，其他程式不動：

1. `verified_release_snapshot`（3 品項）
   - 先照舊把 5 個凍結檔複製到私人暫存資料夾並逐一驗 hash。
   - 通過後，只在這個暫存資料夾裡把 parquet 換成滾動版本。
   - ForecastEngine 照舊驗模型 hash、照舊讀 parquet。
2. `data_bundle()`（57 品項與目錄）
   - 回傳滾動目錄與歷史，但 manifest 仍是凍結目錄的。
   - 因此 `ml_release()` 的相容檢查照舊比對訓練快照，`data_version` 也仍是訓練來源 `172dffc76e82`。
3. `/healthz`
   - 照舊驗凍結 release；`public_data_cutoff` 改報滾動截止日。
   - 另外多一個 `public_history` 欄位，記錄版本、截止日、待切換版本與略過的錯誤。
   - `/healthz` 經 web nginx 對外公開，所以錯誤訊息只寫版本 ID 和錯誤代碼，不寫主機路徑。

**何時切換：**

- Docker 每 30 秒呼叫一次 `/healthz`，此時檢查 `CURRENT.json` 有沒有變。
- 新版本會在請求路徑之外先完整驗證。
- 只有在拿得到既有的單一推論鎖 `_busy` 時（也就是沒有推論正在進行）才換參照，所以同一個回答不會混用兩個版本。
- **每天更新不需要重啟容器。**

**不變的東西：**

- 模型檔、release 0.1.0、57 品項模型與評估檔都不動。
- 公開測試數字不變：macro-F1 0.4218／0.4169、MAE 未勝不變價等。
- `data_version`、`model_version`、警告文字，以及 Worker 的 `/v1` 契約都不變。
- 受保護基準（`protected_before.json` 的 14 個檔）前後比對相同，沒有重新抓 hash。

### 4.5 限制

- 模型仍是用 2025-10～2026-10 的資料訓練。新資料只更新輸入特徵，不代表模型對 11 月以後已驗證；負向結果照舊揭露。
- 晚於快照才公布的 2026-10-02 以前市場日（目前 9 列）不加入，以維持凍結前綴不變。
- 網頁 `app.js` 內嵌的「最近行情」說明文字仍是 10-02 的靜態資料，預測結果本身已用新資料，見第 8 節。
- 來源若長期沒有更新，45 天規則照舊生效，只是起算日往後移。
- 信任邊界和既有設計相同：hash 防的是損壞與半寫入，不防同一主機上能寫滾動資料夾的人。forecast 容器只能唯讀；只有更新器能寫入，以 UID 10001 執行，網路與 forecast/mcp/web 分開。

## 5. 檔案

`deploy/oracle-forecastengine/rolling_history/`：

| 檔案 | 用途 |
| --- | --- |
| `rolling_store.py` | 驗證、合併、建置、原子發布、載入驗證、退回選擇（更新器與伺服器共用） |
| `rolling_update.py` | 更新器 CLI；exit 0 已切換或沒有新資料、2 驗證拒絕、3 下載失敗、1 其他 |
| `rolling_runtime.py` | 服務端：替換三個入口，再匯入 D47 的 `v1_full_catalog` |
| `engine_entrypoint_rolling.py` | 和 D47 入口相同，只是改跑 `rolling_runtime:app` |
| `compose.rolling.yaml` | forecast 的唯讀掛載，以及 `rolling-updater` 一次性服務 |
| `fresh-market-price-agent-rolling-history.service`／`.timer` | 主機排程：每天 07:20 與 19:20（台北） |
| `test_rolling_history.py`、`rolling_probe.py` | 測試；服務端測試是在部署映像的原始碼上跑 |

## 6. 本機驗證（2026-10-30）

命令：`PYTHONUTF8=1 .venv\Scripts\python.exe -m pytest deploy/oracle-forecastengine/rolling_history/test_rolling_history.py deploy/oracle-forecastengine/v1_full_catalog/test_v1_full_catalog.py -q`

結果：**73 passed**，exit 0。其中 47 項是新測試，26 項是 D47 原有測試。

- **與凍結檔一致：**
  - 從凍結原始 JSON（`172dffc7…`）重建，61 品項歷史與 3 品項 parquet 都和凍結檔逐值相同。
  - 目錄沒有新列時，和凍結目錄相同。
- **反向測試：** 16 種壞下載都被拒絕，而且滾動資料夾的每個檔案前後逐位元組相同。這 16 種是：
  - 截斷、切掉一半位元組、空檔、不是陣列；
  - 欄位改名、未知市場、負價、文字價、超大價；
  - 未來日期、不存在的日期；
  - 同日衝突、比目前舊的下載；
  - 欄位對調、單位乘 10、改寫舊日期。
- **竄改測試**（hash 全部重算過）：
  - 改快照期間的一個值會被前綴檢查拒絕，61 品項歷史與 3 品項 parquet 都測過。
  - 換成別的凍結快照、版本 ID 想跳出資料夾，也都被拒絕。
- **退回：**
  - 最新版本損壞時退回上一版；兩版都損壞時退回凍結快照，預測仍是 200。
  - 下一次更新會以最後的好版本為基礎，重建並取代壞版本。
- **服務端**（部署映像的原始碼）：
  - **t=2026-10-03 時**，滾動與凍結的 7／14 天結果完全相同，因為特徵只看 t−1 以前。共測 5 個案例：`/v1` 3 個、網頁 2 個。
  - **t=2026-10-30 時**，`public_data_cutoff` 是 2026-10-29，報價日期在 10-02 之後，第三市場的結果確實改變。
  - `data_version`、`model_version` 不變。
- **切換時機：** 推論鎖被占用時，新版本只會進入待切換，鎖釋放後下一次 `/healthz` 才切換。
- **更新器實跑：** 截斷的下載 exit 2，`CURRENT.json` 不變；同一份下載再跑一次是「unchanged」。
- **檢查器本身會抓錯：** 在隔離副本裡拿掉前綴檢查，或把縮短門檻改成 0，對應測試都會失敗（exit 1）。
- **記憶體：** Windows 上服務程序約 244 MB，凍結版約 233 MB。切到滾動版本後會釋放凍結歷史的快取。
- 第五市場有幾個品項好幾個月都是同一個價格（例如青蔥 113），兩天的特徵只差星期幾，模型輸出相同。這是資料本身的性質，所以「結果有改變」的測試只用第三市場。

證據：`outputs/quality_runs/rolling_history_d48_20261030/`（下載、探針輸出、測試 log、變異測試 log）。

## 7. 部署（2026-10-30 使用者核准後執行）

**實際結果（UTC）：**

- **預檢：**
  - 線上 D47 檔案 hash 與文件記錄相同，三個容器 healthy。
  - 可用記憶體 376 MB；主機連得到台中來源（200，5,349,735 bytes）。
- **17:12 第一版：**
  - `20261029-d5f765439920`，與本機建出的 ID 相同。
  - 更新器 32 秒完成，本機量到峰值約 201 MB。
- **17:13 切換：** forecast 37 秒後 healthy，之後重啟 web。
- **驗證：**
  - `/healthz`：`source` 為 `rolling`，截止 10-29。
  - `/v1` 報價觀測日 10-29；以 t=2026-10-03 查詢與凍結版數字逐位相同；四種拒絕的回應碼不變。
  - 外網網頁與 `/v1` 數字一致。
  - Worker 遠端原 6/6＋新品項 5/5。
  - forecast 221 MiB／650 MiB。
- **17:18 啟用 timer：** 經 systemd 手動跑一次，success、`unchanged`。
- 證據：`outputs/quality_runs/rolling_history_d48_deploy_20261031/`。
- **未在線上實際跑過的路徑：** 執行中的熱切換。第一次會發生在來源公布新的一天之後的排程執行，本機測試已涵蓋。

原計畫如下（已照做）。

1. **放檔並核對 SHA-256：**
   - 4 個 Python 檔（store、update、runtime、entrypoint）放到 `stack/rolling/`。
   - `compose.rolling.yaml` 放到 stack 根目錄。
   - 2 個 systemd unit 放到 `/etc/systemd/system/`。
   - 建立主機資料夾：`install -d -o 10001 -g 10001 -m 0755 /opt/fresh-market-price-agent-docker/rolling-history`。
2. **建立第一版**（forecast 尚未讀取，線上不受影響）：
   ```
   docker compose -p fresh-market-price-agent-oracle -f compose.yaml -f compose.oracle.yaml -f compose.v1ext.yaml -f compose.rolling.yaml run --rm --no-deps -T rolling-updater
   ```
   這一步會從 Oracle 直接下載，順便確認 Oracle 能連到台中來源。檢查 `status.json` 是 `switched`。
3. **切換 forecast**（約 30 秒停機），之後要重啟 web：
   ```
   ... -f compose.rolling.yaml up -d --no-build --pull never forecast
   ... restart web
   ```
4. **驗證：**
   - 主機內 `/healthz` 的 `public_history.source` 是 `rolling`。
   - `/v1` 報 3 品項與目錄品項時，截止日都是新的。
   - 外網網頁可用；Worker 遠端原 6/6＋新品項 5/5。
5. **啟用排程：** `systemctl enable --now fresh-market-price-agent-rolling-history.timer`。之後每天 07:20、19:20 執行，不重啟、不停機。
6. **回滾：**
   - 同一個 `up` 指令拿掉 `-f compose.rolling.yaml`，再重啟 web，就回到 D47，也就是凍結資料。
   - 停用 timer。
   - 滾動資料夾保留不刪。

## 8. 後續（本次不做）

- 網頁 `app.js`／`web/catalog.json` 內嵌的各市場「最近行情」文字仍是 10-02。需要另外決定，是否讓 web 也讀滾動目錄。
- 維運手冊和 README 已更新。`docs/PROPOSAL_REPORT.md` 第 121 行與 `design.md` 圖中的「行情只到 2026-10-02」是經過外審的交付文字，本次沒有改。
