# 營運操作手冊（T30）

建立：2026-10-04（本機時間 00:02–00:04 實測）；同日 01:08–01:13 依第二輪獨立審查（F04／F05）重構更新流程後補第二輪實測（見 §3.5）。適用範圍：TRAIN_LOCAL（本 Windows 工作區）的公開行情更新。策略聲明見 [configs/update_policy.yaml](../configs/update_policy.yaml)（policy_version 0.2.0）；實測報告 JSON 在 `outputs/update_tests/`（Git 忽略目錄）。

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

# 同時刷新模型包推論歷史（備份→暫存→逐列核對→os.replace 原子替換→驗證；
# 任一步失敗自動保護／還原為舊內容，exit 4）
PYTHONPATH=src .venv/Scripts/python.exe scripts/update_public_data.py --refresh-release-history

# 加上重載檢查：刷新前後各建一個全新 ForecastEngine 並印出 public_cutoff，
# 證明「重啟／重建引擎」後讀到新日期（見 §6：已啟動的服務不會自動生效）
PYTHONPATH=src .venv/Scripts/python.exe scripts/update_public_data.py \
    --refresh-release-history --reload-check
```

### 步驟 3：核對報告要點

- HTTP 狀態 2xx、SHA256 已記錄；
- `snapshot_comparison.new_dates`：新增觀測日期清單（0 日＝無新資料，依策略不動任何檔案）；
- 有用 `--refresh-release-history` 時：`release_history.history_rows_before → after`、`new_dates_beyond_cutoff`、`backup_path`、`post_replace_verified`（逐列核對＋原子替換後驗證）；
- 有用 `--reload-check` 時：`reload_check.cutoff_after` 必須等於新日期才算「重啟後生效」（§6）；
- `date_semantics`：快照截止日／特徵實際可見日／資料版本三個概念對照（§7）。

離開代碼（2026-10-04 第二輪審查後重新編號，與 update_policy.yaml 0.2.0 同步）：

| exit | 意義 | 保留狀態 |
| --- | --- | --- |
| `0` | 成功（含無新資料） | — |
| `1` | 參數／設定錯誤，或其他未預期但受控回報的失敗 | 舊檔全部保留 |
| `2` | schema 驗證失敗（壞 JSON／缺欄／壞日期／Infinity／負值／重複鍵／空檔） | 該檔不落地 |
| `3` | 下載失敗（連線／HTTP／逾時） | 舊檔全部保留 |
| `4` | 寫入／核對失敗（暫存寫入、逐列核對、原子替換、備份還原、reload-check） | 快照已保存者保留（partial_state 註明歷史未刷新）；release parquet 保護為舊內容 |

> 注意：0.1.0 版舊文件中「1＝下載失敗、3＝release 刷新失敗」的編號已停用；接到 exit 3／4 的自動化或文件引用需對照上表。

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

### 3.5 第二輪修復實測（2026-10-04 01:08–01:13 +08:00，修 F04／F05）

第二輪獨立審查（[ROUND2_7fdb43b_REVIEW.md](reviews/ROUND2_7fdb43b_REVIEW.md)）重現四個更新流程缺陷後，`scripts/update_public_data.py` 已重構（退出碼重新編號、原子替換、schema 加強、`--reload-check`），並以 `outputs/update_tests/_round3_repair_tests.py` 重新實測。**以下 t1–t5 的「下載」全部是模擬傳輸（本地暫存 JSON＋monkeypatch `download_file` 回假 HTTP200），故障注入靠 monkeypatch 薄包裝函式；沒有任何真實網路請求，也不是真實官方新行情。** 所有寫入（快照、release、報告）都只落在系統暫存目錄的副本上；正式 `models/releases/0.1.0/`、`data/raw/`、`outputs/splits/` 只被讀取。完整證據：`outputs/update_tests/round3_repair_scenarios.json`。

| # | 情境（全部模擬） | 結果 | 關鍵證據 |
| --- | --- | --- | --- |
| t1 | **F04 主路徑**：模擬下載新日期（20261004）→ 非 dry-run → 保存快照（搬移路徑）→ 刷新 release parquet（原子替換） | exit **0**、全 PASS | 快照與 provenance 落地、`12288 → 12309` 列（追加 21 列）、舊區段逐列相同、新區段全為 2026-10-04、無暫存檔殘留、備份存在、`date_semantics` 區段產出 |
| t2 | 寫入中斷（monkeypatch `_atomic_replace` 拋 OSError，模擬替換前中斷） | exit **4**、全 PASS | 目標 parquet hash 不變且完整可讀（12288 列）、備份存在、報告記錄「原子替換失敗」與 `target_is_old_content: true`、快照保留並以 `partial_state` 註明歷史未刷新 |
| t3 | 核對失敗（monkeypatch `_write_parquet` 故意少寫一列） | exit **4**、全 PASS | 錯誤訊息「列數不符：預期 12288(舊)+21(新)=12309，實為 12308」；目標 hash 不變、備份存在、無暫存檔殘留 |
| t4a | 壞 JSON（截斷檔） | exit **2**、全 PASS | 「JSON 無法解析：JSONDecodeError…」受控回報，不落地 |
| t4b | 缺甘藍欄（審查重現案例：移除「甘藍（平地高麗菜）」） | exit **2**、全 PASS | 錯誤指名「缺少必要欄位：甘藍（平地高麗菜）（第 0 列起共 4450 列缺欄…）」——0.1.0 版此案例回 `errors=[]` 的漏洞已補 |
| t4c | 絲瓜欄含字串 `"Infinity"` | exit **2**、全 PASS | 「絲瓜：非有限值（Infinity）」——0.1.0 版 Infinity 可進歷史的漏洞已補 |
| t4z | 對照：絲瓜＝0（無價格） | schema 通過 | 0 依契約＝無價→缺測，不被誤擋 |
| t5 | `--reload-check` 於副本 release（模擬下載＋`--refresh-release-history`） | exit **0**、全 PASS | 引擎 `public_cutoff`：刷新前 `2026-10-02` → 刷新後 `2026-10-04`；**同一個已啟動引擎實例刷新後仍回 2026-10-02**（實渉證明需重啟，見 §6）；四個權重／manifest／fixtures 檔 hash 不變 |

**正式工件保護核對（5f）**：本輪測試前後 11 個正式工件（release 5 檔＋data/raw 4 檔＋splits 2 檔）hash 對照見 `outputs/update_tests/round3_formal_hashes_check.json` 與 `hashes_round3_before.txt`／`hashes_round3_after.txt`：10 個完全一致。唯一差異 `models/releases/0.1.0/fixtures.json`（mtime 2026-10-04 01:05:34）判定為**同一時間主對話（F01–F08 修復、src/ 變更中）重新生成的並行變更，非本更新流程測試所為**——本案測試腳本只以 `copytree` 讀取正式 release 當複製來源，所有寫入均在系統暫存與 `outputs/update_tests/`。

**真實 CLI 冒煙（非 in-process）**：重構後亦以子程序實跑兩次驗證退出碼——`--input data/raw/taichung/retail_prices_20261003.json --dry-run`（真實本地快照、無網路）→ exit 0／`no_new_data`（`round3_cli_smoke_dryrun.json`）；`--url http://127.0.0.1:9/`（本機拒絕連線埠，未對外部發請求）→ exit 3、報告 `status=failed`＋`old_files_kept=true`（`round3_cli_dead_source.json`）。

## 4. 故障查法

| 症狀 | 診斷 | 處理 |
| --- | --- | --- |
| **來源失效**（exit 3；`URLError`／HTTP 錯誤／逾時） | 看 `--report` JSON 的 `error` 欄；先用瀏覽器/curl 開 `configs/data_sources.yaml` 的 `download_url` 確認是來源問題還是本機網路 | 舊檔全部保留，系統照常用最後一次成功快照。來源持續失效時在 DATA_CARD 記錄；**不得**把失敗當「價格不變」回給使用者（API 有 stale 資料邊界，見 ERROR_ANALYSIS） |
| **schema 變動**（exit 2；壞 JSON／缺欄／壞日期格式） | 錯誤訊息會指名缺什麼、壞幾格（例：`缺少必要欄位：甘藍（平地高麗菜）`、`絲瓜：非有限值（Infinity）`）；用報告 `schema_check.errors` 逐項看 | 該檔不落地、release 不動。官方改欄位時：先人工比對新舊欄位語意，更新 `src/aiot_price/data/schema.py` 的映射與 data_sources.yaml 的 `expected`，同步 DATA_CARD／DECISIONS 後才可放行——本腳本不自動適配新 schema |
| **品項值不合法**（exit 2；Infinity／負值／無法轉數字／(市場,日期) 鍵重複） | 0.2.0 起三個支援品項欄逐格檢查：空值／NaN＝缺測、0＝無價（依契約轉缺測）可通過；其餘拒絕 | 同上：不落地。若官方真開始供應負值或非數字內容，視為 schema 變動處理 |
| **無新資料**（exit 0，`no_new_data`） | 不是故障：官方 API 是近一年滾動視窗，同日重複下載回相同內容（DATA_CARD 已記錄）；報告會顯示 `same_hash_as_baseline: true` 或新增日期 0 | 不需處理。想確認來源活著就看 HTTP 200 與 SHA256 有沒有寫進報告 |
| **寫入／核對失敗**（exit 4；暫存寫入中斷／逐列核對不符／原子替換失敗／替換後驗證失敗／備份還原失敗） | `release_history.error` 會寫明失敗在哪一步；`target_is_old_content`／`restored_from_backup` 說明目標現況 | 0.2.0 起自動保護：目標 parquet 保持完整可讀的舊內容（必要時已自動從備份還原）。仍失敗（`target_is_old_content: false`）時用報告 `backup_path` 的備份手動覆蓋回 `public_history.parquet`，再重跑一次；不可手動編 parquet。快照若已保存屬合法取得內容，保留不回滾（報告 `partial_state` 有註明歷史未刷新） |
| **reload-check 失敗**（exit 4；引擎建不起來或 hash 不符） | 報告 `reload_check.error`；常見原因是 release 目錄不完整或模型檔 hash 與 manifest 不符 | 先確認 release 目錄五檔齊全；權重不符代表模型包被動過，回到 T18 package.py 重新打包，不要就地修 |
| **快照目錄出現多個同日檔**（`_HHMMSS` 後綴） | 正常：不覆蓋舊檔的設計；同日多次成功取得**新內容**才會發生 | 保留全部並讓 provenance 對得上即可，不刪檔 |

## 5. 版本與聯繫

- 目前唯一模型包：`models/releases/0.1.0`（manifest：訓練快照截止 2026-10-02、來源 JSON SHA256 `172dffc76e82…`、凍結切分清單 `4e136574…`）。
- 行情刷新**不改** manifest：`observation_end` 恆為訓練當時快照截止日；parquet 的最後日期可能較新，兩者差異可在報告 `release_history` 區段對照（`release_cutoff_date` vs `manifest_observation_end`）。
- 自動排程：**無**。依 AGENTS/T30，不建立未被要求的長期自動化；需要時依部署環境另案評估。
- 更新流程變更時同步：`configs/update_policy.yaml`（策略）與本文件（操作）。

## 6. 行情更新後如何讓推論服務生效（重載步驟，F05c）

**事實**：`ForecastEngine` 只在初始化時讀 `public_history.parquet`；行情更新只改「磁碟檔」，**已啟動的引擎／API 服務不會自動看到新行情**。本輪已實測：刷新副本 release 後，同一個已啟動的引擎實例仍回舊截止日 `2026-10-02`，重建的新引擎才回 `2026-10-04`（`round3_repair_scenarios.json` t5）。

刷新完成後的明確步驟：

1. 確認刷新本身成功：exit 0、報告 `release_history.changed: true`、`post_replace_verified` 有逐列核對訊息。
2. **重建／重啟推論端**（依部署形態擇一）：
   - 本機 CLI／腳本：下次執行本來就會新建 `ForecastEngine`，無需額外動作；
   - 本機 API（`src/aiot_price/api/app.py`，長駐行程快取引擎實例）：**重啟 Uvicorn 行程**（停止後重新啟動；不要只重載路由）；
   - SERVER 部署後（T24／T29）：先依部署流程把刷新後的模型包同步到 SERVER，再**重啟推論服務行程**。
3. 驗證生效：跑 `--reload-check`（或直接以新引擎查一次）確認 `public_cutoff` 已是刷新後日期：
   ```bash
   PYTHONPATH=src .venv/Scripts/python.exe scripts/update_public_data.py \
       --input <最新快照> --refresh-release-history --reload-check --dry-run
   ```
   報告 `reload_check.cutoff_after` 必須等於新日期；不等於＝沒生效（多半是服務沒重啟或讀到別的目錄）。
4. Qwen **不需要**重載（與菜價行情無關，見 §1）；模型權重與 manifest 不因刷新改變，不需重新訓練或重新打包。

## 7. 「快照截止日」≠「特徵實際可見日」≠「資料版本」（F05d）

對使用者或報告解釋行情日期時，三個概念必須分開，不得把全域快照截止日當成「該市場品項最新可見價格日」：

| 概念 | 定義 | 在哪看 |
| --- | --- | --- |
| **快照截止日** | 本次 JSON／parquet 的**全域**最大觀測日（跨所有市場／品項） | 報告 `snapshot_comparison.baseline_max_date`、`schema_check.stats.max_date`、`release_history.release_cutoff_date` |
| **特徵實際可見日** | 預測特徵經 `visible_delay_days`（目前 1）回看後，**該市場／該品項**實際用到的最新價格日；因市場／品項而異，可能早於快照截止日 | 由推論端（`build_features`＋`price_last_age`）計算；例：10/2 查詢某市場某品項特徵可能只用 10/1 價 |
| **資料版本** | manifest 的訓練快照 SHA256／`observation_end`；行情刷新**不改變**資料版本 | 報告 `release_history.manifest_observation_end`、回應的 `data_version` |

腳本報告的 `date_semantics` 區段自 0.2.0 起自動附上三者的對照與說明。例：刷新含 2026-10-04 的快照後，`snapshot_max_date=20261004`、`release_history_last_date=2026-10-04`，但 `manifest_observation_end=2026-10-02`（資料版本不變）；而個別預測的「最新可見價格日」要看推論端計算的特徵可見日，不是 10-04。
