# 營運操作手冊（T30 初版）

建立：2026-10-04（本機時間 00:02–00:04 實測）。適用範圍：TRAIN_LOCAL（本 Windows 工作區）的公開行情更新。策略聲明見 [configs/update_policy.yaml](../configs/update_policy.yaml)；實測報告 JSON 在 `outputs/update_tests/`（Git 忽略目錄）。

> **SERVER 端（推論/API/Qwen 的行情刷新與版本管理）：待 T24／T29 補。** 本文件目前只涵蓋本機側；SERVER 位址與部署方式尚未取得（T23 HOLD）。取得後需補：SERVER 上模型包的更新／hash 校驗、服務重啟與 fixture 重播、以及手機端可用性確認。

## 1. 三種操作的區別（先讀這節）

| 操作 | 做什麼 | 不做什麼 | 需要重訓模型？ | 需要動 SERVER？ |
| --- | --- | --- | --- | --- |
| **行情刷新**（本手冊） | 下載新 JSON、驗證、存快照；`--refresh-release-history` 把新觀測日期「只追加」到 `models/releases/0.1.0/public_history.parquet` | 不改模型權重（`model_h7/h14.joblib`）、不改 `manifest.json`／`fixtures.json` | 否 | 否（SERVER 部署後另補傳檔步驟，見上方說明） |
| **模型重訓／發布** | 只在 TRAIN_LOCAL：`prepare_data.py` → `train.py` → `select.py` → `evaluate.py` → `package.py` 產生**新版** `models/releases/<版本>/`，再傳 SERVER 驗 hash＋fixtures（T08–T18、T24） | 不因行情刷新自動觸發；不偷改舊版模型包的權重 | 是（本身就是） | 是（新版要傳檔＋重啟） |
| **Qwen 載入** | SERVER 端把 Qwen 模型載入記憶體／重啟推論服務（T25、T29） | 與菜價行情無關；行情更新後**不需要**重載 Qwen | 否 | 是 |

一句話：**行情刷新讓推論讀到較新的歷史；模型重訓換掉模型本身；Qwen 載入是另一個服務的生命週期。** 菜價模型失敗時不能拿 LLM 編答案，Qwen 失敗時手機仍應顯示直接模型結果（design.md §8）。

## 2. 更新流程操作步驟

工具：`scripts/update_public_data.py`（註：重用 T05 的 `fetch_public` 下載／hash／不覆蓋邏輯，未改任何 `src/` 檔）。以下命令均在專案根目錄（Git Bash）執行。

### 步驟 1：先看會發生什麼（dry-run，不寫入任何檔案）

```bash
PYTHONPATH=src .venv/Scripts/python.exe scripts/update_public_data.py --dry-run \
    --report outputs/update_tests/<名稱>.json
```

### 步驟 2：確認報告無誤後實際執行

```bash
# 只更新快照（data/raw/taichung/，永不覆蓋舊檔）
PYTHONPATH=src .venv/Scripts/python.exe scripts/update_public_data.py

# 同時刷新模型包推論歷史（寫入前自動備份原 parquet）
PYTHONPATH=src .venv/Scripts/python.exe scripts/update_public_data.py --refresh-release-history
```

### 步驟 3：核對報告要點

- HTTP 狀態 2xx、SHA256 已記錄；
- `snapshot_comparison.new_dates`：新增觀測日期清單（0 日＝無新資料，依策略不動任何檔案）；
- 有用 `--refresh-release-history` 時：`release_history.history_rows_before → after`、`new_dates_beyond_cutoff`、`backup_path`、`old_rows_unchanged: true`。

離開代碼：`0`＝成功（含無新資料）；`1`＝下載失敗；`2`＝schema 驗證失敗；`3`＝release 刷新失敗。失敗一律保留舊檔。

## 3. 實測輸出摘要（2026-10-04 00:02–00:04 +08:00）

四個必要情境＋兩個補充情境全部實測；報告 JSON 存 `outputs/update_tests/`。**a1 是真實下載；a2／b／c／d 均為本地模擬**（c 用本機拒絕連線的埠號模擬失效來源，未對任何外部服務發請求）。

### 情境 a｜無新資料（兩種做法都測）

**(a1) 真實下載**（官方 URL，同日內容未更新）：

```bash
PYTHONPATH=src .venv/Scripts/python.exe scripts/update_public_data.py --dry-run \
    --report outputs/update_tests/scenario_a1_real_download.json
```

輸出：

```
下載：HTTP 200｜5323185 bytes｜0.5s
SHA256：172dffc76e8249026ac2ad89cc1a9f68bcfb686fd64a2820b38e949fe7e2e259
schema 檢查通過：列數 4450｜欄位 63｜日期 20251004~20261002（364 日）｜市場 14
比較基準：retail_prices_20261003_232854.json（觀測至 20261002，SHA256 相同）
新增觀測日期：0 日
快照未存：dry-run
狀態：no_new_data
```

**(a2) 本地現有快照當輸入**：`--input data/raw/taichung/retail_prices_20261003.json --dry-run` → 同樣 `新增觀測日期：0 日`、`狀態：no_new_data`（報告：`scenario_a2_local_no_new.json`）。

### 情境 b｜有新資料（本地模擬假日期）

做法：把正式快照最後一天（20261002）的 7 列複製成假日期 20261003（產生器：`outputs/update_tests/_make_fixtures.py`，暫存於系統 temp，**非真實行情**）。

**(b1) dry-run 正確抓到新日期**（`--refresh-release-history` 指向真實 `models/releases/0.1.0`，驗證 dry-run 不寫入）：

```
schema 檢查通過：列數 4457｜欄位 63｜日期 20251004~20261003（365 日）｜市場 14
新增觀測日期：1 日 20261003
release 歷史未變更：僅報告，未寫入
狀態：ok
```

報告另列：release 截止日 2026-10-02、將追加 21 列（7 市場 × 3 品項）、`(停)` 市場未出現在追加清單。執行後 `models/releases/0.1.0/public_history.parquet` SHA256 仍為 `e53e34c4…`（未變）。

**(b2) 真的執行追加——在 release 副本上測，不動 0.1.0 原檔**（`--release-dir` 指向 temp 內的 parquet＋manifest 副本）：

```
release 歷史已更新：12288 → 12309 列（追加 21 列、新日期 1 日、備份 …\release_copy\public_history.backup_20261004_000321.parquet）
狀態：ok
```

獨立核對（pandas 逐列比較）：副本前 12288 列與 0.1.0 原檔**完全相同**（`old segment identical: True`）、新 21 列全部是 2026-10-03、備份檔存在；真實 0.1.0 parquet hash 前後不變（`e53e34c49098e309544b902dbff29708cde2f969035dd13995e64deed2ba2e3c`）。**亦即：追加與備份機制已真實執行過，但是在暫存副本上；0.1.0 的 parquet 從未被本輪測試修改。**

### 情境 c｜失效來源（本地模擬：不存在的埠）

```bash
PYTHONPATH=src .venv/Scripts/python.exe scripts/update_public_data.py --url http://127.0.0.1:9/ --dry-run \
    --report outputs/update_tests/scenario_c_dead_source.json
```

輸出（exit code 1，無 traceback、不崩潰）：

```
錯誤：下載失敗（URLError: <urlopen error [WinError 10061] 無法連線，因為目標電腦拒絕連線。>）；舊檔全部保留，未寫入任何資料。
```

### 情境 d｜schema 變動（本地模擬：刪掉「市場名稱」欄）

```bash
PYTHONPATH=src .venv/Scripts/python.exe scripts/update_public_data.py \
    --input "$TEMP/aiot_update_scenarios/scenario_d_no_market.json" --dry-run \
    --report outputs/update_tests/scenario_d_schema_change.json
```

輸出（exit code 2，錯誤明確指名缺欄）：

```
錯誤：schema 驗證失敗，不採用此檔；缺少必要欄位：市場名稱（現有欄位數 62）
```

### 測試後環境核對

`data/raw/taichung/` 仍只有原本 4 個檔（2 快照＋2 provenance），`models/releases/0.1.0/` 全部檔案 hash 不變（`outputs/update_tests/hashes_before.txt`／`hashes_after.txt` 可對照）。臨時檔都在系統 temp `aiot_update_scenarios/`。

## 4. 故障查法

| 症狀 | 診斷 | 處理 |
| --- | --- | --- |
| **來源失效**（exit 1；`URLError`／HTTP 錯誤／逾時） | 看 `--report` JSON 的 `error` 欄；先用瀏覽器/curl 開 `configs/data_sources.yaml` 的 `download_url` 確認是來源問題還是本機網路 | 舊檔全部保留，系統照常用最後一次成功快照。來源持續失效時在 DATA_CARD 記錄；**不得**把失敗當「價格不變」回給使用者（API 有 stale 資料邊界，見 ERROR_ANALYSIS） |
| **schema 變動**（exit 2；缺欄／壞日期格式） | 錯誤訊息會指名缺什麼（例：`缺少必要欄位：市場名稱`）；用報告 `schema_check.errors` 逐項看 | 該檔不落地、release 不動。官方改欄位時：先人工比对新舊欄位語意，更新 `src/aiot_price/data/schema.py` 的映射與 data_sources.yaml 的 `expected`，同步 DATA_CARD／DECISIONS 後才可放行——本腳本不自動適配新 schema |
| **無新資料**（exit 0，`no_new_data`） | 不是故障：官方 API 是近一年滾動視窗，同日重複下載回相同內容（DATA_CARD 已記錄）；報告會顯示 `same_hash_as_baseline: true` 或新增日期 0 | 不需處理。想確認來源活著就看 HTTP 200 與 SHA256 有沒有寫進報告 |
| **release 刷新後核對失敗**（exit 3） | `release_history.error` 會寫「列數或舊列內容不一致」 | 用報告內 `backup_path` 的備份還原 parquet（覆蓋回 `public_history.parquet`），再重跑一次；仍失敗則回報，不要手動編 parquet |
| **快照目錄出現多個同日檔**（`_HHMMSS` 後綴） | 正常：不覆蓋舊檔的設計；同日多次成功取得**新內容**才會發生 | 保留全部並讓 provenance 對得上即可，不刪檔 |

## 5. 版本與聯繫

- 目前唯一模型包：`models/releases/0.1.0`（manifest：訓練快照截止 2026-10-02、來源 JSON SHA256 `172dffc76e82…`、凍結切分清單 `4e136574…`）。
- 行情刷新**不改** manifest：`observation_end` 恆為訓練當時快照截止日；parquet 的最後日期可能較新，兩者差異可在報告 `release_history` 區段對照（`release_cutoff_date` vs `manifest_observation_end`）。
- 自動排程：**無**。依 AGENTS/T30，不建立未被要求的長期自動化；需要時依部署環境另案評估。
- 更新流程變更時同步：`configs/update_policy.yaml`（策略）與本文件（操作）。
