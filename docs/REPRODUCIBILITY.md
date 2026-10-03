# 本機重現指引（T34 初版）

建立：2026-10-04。目的：在乾淨的 TRAIN_LOCAL（Windows）環境，從零重現「資料 → 特徵 → 訓練 → 評估 → 模型包 → 推論 → API」全流程。標示「（2026-10-04 實測）」的步驟是本文件撰寫時真的重跑過並貼出輸出；其餘步驟引用既有執行證據（`outputs/` 目錄與各任務文件），命令本身可重跑。

> **SERVER 部署重現：待 T24。** SERVER（RTX 3090 主機）的位址、OS 與部署目錄尚未取得（T23 HOLD）；跨主機模型包一致性驗證（同包同輸入 fixtures 比對）會在 T24 執行後補進本文件。

## 0. 前置條件與大型檔案位置（Git 忽略目錄）

以下目錄都是 [.gitignore](../.gitignore) 排除的本機內容，**clone 專案後不存在，需依本文件步驟重建**：

| 路徑 | 內容 | 重現方式 |
| --- | --- | --- |
| `.venv/` | Python 3.12 隔離環境 | §1 |
| `data/raw/taichung/` | 公開行情快照＋provenance（約 5MB/檔） | §2（官方 API 免帳號） |
| `data/processed/` | 特徵＋標籤 parquet | §3 |
| `models/candidates/`、`models/releases/0.1.0/` | 訓練候選與發布模型包（權重 joblib） | §4–§6 |
| `outputs/` | 切分凍結清單、訓練/評估結果、測試證據 | 各步驟產出 |
| `private/` | 私人店價紀錄與預測保存（同店驗證用） | 使用者自行記錄（T10 協議）；本文件流程**不**需要 |

無任何外部模型權重下載需求：本模型是 scikit-learn 表格模型，訓練與推論全在 CPU。Qwen 相關（SERVER 端）不在本文件範圍。

## 1. 環境（Python 3.12 + venv + 鎖版檔）

詳見 [LOCAL_ENVIRONMENT.md](LOCAL_ENVIRONMENT.md)。摘要（專案根目錄執行）：

```bash
python -m venv .venv                                   # Python 3.12.10
.venv/Scripts/python.exe -m pip install -e ".[dev]"     # 開發安裝（含 pytest＋httpx）
# 或精確重現（lock 的 editable 行為 `-e .`，必須從專案根目錄執行）：
.venv/Scripts/python.exe -m pip install -e ".[dev]" -r requirements-lock.txt
```

預期結果：`aiot-price 0.1.0`（editable，指向 `src/aiot_price`）、pandas 2.3.3、numpy 2.5.3、scikit-learn 1.9.1、PyYAML 6.0.3、jsonschema 4.26.0、pytest 8.4.2、httpx 0.28.1，以及 API／parquet 層的 fastapi 0.142.2、uvicorn 0.54.0、starlette 1.7.0、pyarrow 25.0.1（均已列入 lock 與 `pyproject.toml` dependencies／dev extra）。乾淨環境重現：2026-10-03 實測成功（`outputs/local_env/clean_venv_install.txt`）；2026-10-04 於專案外暫存 venv 以可攜 `-e .` 再次驗證成功（安裝、import、真工件載入、API 測試 12 passed、全套 98 passed），完整命令與輸出見 [outputs/audits/2026-10-04_round2/clean_env_check.md](../outputs/audits/2026-10-04_round2/clean_env_check.md)。

## 2. 資料取得（公開行情快照）

```bash
PYTHONPATH=src .venv/Scripts/python.exe -m aiot_price.data.fetch_public \
    --config configs/data_sources.yaml --out-dir data/raw/taichung
```

預期輸出（**2026-10-04 00:06 實測**，輸出導向 temp 避免同日重複快照；正式跑法輸出到 `data/raw/taichung/`）：

```
來源：taichung_retail_daily（臺中市政府公有零售市場每日蔬果價格）
HTTP 200｜5323185 bytes｜0.406s
SHA256：172dffc76e8249026ac2ad89cc1a9f68bcfb686fd64a2820b38e949fe7e2e259
列數 4450｜欄位 63｜市場 14｜日期 20251004~20261002（364 日）
provenance → …provenance_YYYYMMDD.json
```

授權：政府資料開放授權條款第1版；單位元/臺斤、0＝無價格等資料契約見 [DATA_CARD.md](DATA_CARD.md)。注意：官方 API 是近一年滾動視窗，**未來重跑時日期範圍會前移、hash 會變**；要比對歷史快照用檔案 hash，不要期望永遠下載到 `172dffc7…`。

## 3. 資料管線（標籤＋特徵＋切分凍結）

```bash
PYTHONPATH=src .venv/Scripts/python.exe scripts/prepare_data.py \
    --json data/raw/taichung/retail_prices_20261003.json
```

預期輸出（2026-10-03 執行證據：`outputs/data_quality/prepare_summary.json`）：排除 `(停)建國市場`；產出 `data/processed/features_labels.parquet`；切分 train 13,009／val 3,855／test 4,680 列；凍結切分清單 `outputs/splits/split_list.csv`，**SHA256 `4e1365746a25275ea81285700cc570358f3537d4d23184ba4e9ada58e1c9cce6`**（2026-10-04 重算核對一致）。重跑注意：此步驟會重寫 `data/processed/` 與 `outputs/splits/`；凍結 hash 應相同（種子與規則固定），不同就是流程被改過，先停下查原因。

## 4. 訓練（TRAIN_LOCAL、CPU、seed 42）

```bash
PYTHONPATH=src .venv/Scripts/python.exe -m aiot_price.models.train \
    --parquet data/processed/features_labels.parquet --out-dir outputs/training --models-dir models/candidates
```

預期輸出（2026-10-03 執行證據：`outputs/training/training_results.json`）：h=7/h=14 各訓練 3 基線＋Ridge／HGB／RF 回歸＋2 分類候選（CPU 數分鐘）；候選 joblib 存 `models/candidates/`。選型（看測試前凍結標準）：h=7 選 `rf_reg`（驗證 macro-F1 0.4334）、h=14 選 `hgb_reg`（0.4591），見 [MODEL_SELECTION.md](MODEL_SELECTION.md)。

## 5. 封存測試評估（一次性）

```bash
PYTHONPATH=src .venv/Scripts/python.exe -m aiot_price.models.evaluate --parquet data/processed/features_labels.parquet
```

預期輸出（2026-10-03 執行證據：`outputs/evaluation/public/public_test_results.json`；凍結清單 hash 校驗先跑）：

```
h=7 rf_reg n= 2085 acc= 0.7655 macroF1= 0.4218 MAE= 0.0664 | flat MAE= 0.0436 flat F1= 0.3092
h=14 hgb_reg n= 1859 acc= 0.7106 macroF1= 0.4169 MAE= 0.0983 | flat MAE= 0.0748 flat F1= 0.2954
```

（2026-10-04 依 `public_test_results.json` 逐項核對修正：h=7 flat MAE 0.0441→0.0436、h=14 flat MAE 0.0745→0.0748、h=14 flat F1 0.2951→0.2954，先前為手抄筆誤。）

解讀：方向 macro-F1 **優於全預測持平基線**，但**未勝過 momentum（簡單趨勢）基線**（測試集 momentum macro-F1：h=7 0.4226、h=14 0.4306，與選定模型相當甚至略高；選定標準是在驗證集凍結的，不挑事後較佳者）；點回歸 MAE **未優於**不變價基線（如實標示的限制，不做點預測宣稱）。重跑前注意：這是封存測試的一次性評估，正式結果只認第一次；重跑僅供核對可重算性（逐列檔 `test_predictions.csv` 可獨立重算）。

## 6. 模型包封裝

```bash
PYTHONPATH=src .venv/Scripts/python.exe -m aiot_price.models.package --version 0.1.0
```

預期輸出（2026-10-03 執行證據）：`models/releases/0.1.0/` 內含 manifest.json、model_h7/h14.joblib、public_history.parquet、fixtures.json。**重跑警告：會重寫 release 目錄（含 manifest 時間戳與 joblib 二進位未必逐位元組相同），重現驗證一律用下面的 hash 表與 fixtures，不要重跑此步來「驗證」。**

## 7. 推論驗證與 API（本機）

**固定輸入輸出重現（跨主機 parity 基準）：**

```bash
PYTHONPATH=src .venv/Scripts/python.exe scripts/predict_local.py --check-fixtures
```

預期輸出（**2026-10-04 實測**）：`fixtures check: 3/3 passed`。

**啟動 HTTP API：**

```bash
PYTHONPATH=src .venv/Scripts/python.exe -m uvicorn aiot_price.api.app:app --host 127.0.0.1 --port 8000
```

`GET /health` 預期輸出（**2026-10-04 實測**，埠 8012）：

```json
{"status":"ready","model_version":"0.1.0","data_version":"172dffc76e82","public_data_cutoff":"2026-10-02","modes":["market_mean","store_price_estimate_A","store_price_estimate_B_experimental"]}
```

`POST /forecast`（甘藍、中義市場、32 元/台斤、無上週價）實測回應摘要：`mode_executed=without_last_week`、`public_data_age_days=1`、h=7 `direction=flat`／`relative_change_estimate=-0.0406`／`price_estimate=30.7`（元/台斤）、含「點估計 MAE 未優於不變價基線」警示與 `probability=null`（未校準不輸出）。完整契約見 [API_CONTRACT.md](API_CONTRACT.md)。

**測試套件：**

```bash
.venv/Scripts/python.exe -m pytest tests/ -q
```

預期輸出（**2026-10-04 實測**）：`98 passed`（含資料、標籤、切分、特徵、推論邊界、store adapter、API、預測紀錄；會出現 numpy/pandas timedelta DeprecationWarning，已知不影響結果，見 LOCAL_ENVIRONMENT 已知限制2）。

## 8. 版本與 hash 對照表（重現驗收基準）

| 工件 | SHA256（2026-10-04 核對） |
| --- | --- |
| 訓練用原始快照 `data/raw/taichung/retail_prices_20261003.json` | `172dffc76e8249026ac2ad89cc1a9f68bcfb686fd64a2820b38e949fe7e2e259` |
| 凍結切分清單 `outputs/splits/split_list.csv` | `4e1365746a25275ea81285700cc570358f3537d4d23184ba4e9ada58e1c9cce6` |
| `models/releases/0.1.0/model_h7.joblib`（rf_reg, h=7） | `ea98f31d91d27e18644c61736534483b443429e940cf474ee8a1adb9f7c5b327` |
| `models/releases/0.1.0/model_h14.joblib`（hgb_reg, h=14） | `d88fd53d25f62e3737444609c2769f1ab9d547783ee2b0ff6a1128aa24dae92a` |
| `models/releases/0.1.0/public_history.parquet` | `e53e34c49098e309544b902dbff29708cde2f969035dd13995e64deed2ba2e3c`（註：T30 行情追加後此 hash 會變，屬預期） |

環境：Windows 10 19045、Python 3.12.10、scikit-learn 1.9.1、pandas 2.3.3、numpy 2.5.3、joblib 1.6.0；訓練 seed 42、CPU。模型能力邊界與未驗證項見 [MODEL_CARD.md](MODEL_CARD.md)（up 召回率低、同店 A/B 未驗證、機率/區間不輸出）。

## 9. 遺留項（初版如實列出）

1. SERVER 端重現（模型包傳輸、hash 校驗、fixtures 重播、服務啟停）：**待 T24/T29**（T23 HOLD：缺 SERVER 連線資訊）。
2. ~~`requirements-lock.txt` 缺 fastapi／uvicorn／starlette~~：**已解決（2026-10-04）**——lock 改為可攜 `-e .`、pyproject 補齊 fastapi／uvicorn／pyarrow（httpx 入 dev），並於專案外乾淨 venv 驗證通過（見 §1 與 [clean_env_check](../outputs/audits/2026-10-04_round2/clean_env_check.md)）。
3. 發布延遲（觀測日 vs 可下載日）未實測：重現者拿到的最新日期可能落後，屬來源特性非流程錯誤（MODEL_VALIDATION_PLAN 3.3）。
4. 同店 A/B（T16 HOLD）與自動排程更新（依 policy 不建）：不影響上述公開模型全流程重現。

## 第四輪補充（2026-10-04）

- 依賴新增：`hermes-agent==0.19.0`（官方 Nous Research；import 名 `run_agent`）、`pytest-asyncio`、`openai==2.24.0`（hermes 依賴）——見 requirements-lock.txt。全套測試 192 passed（歷史：第三輪 134、初驗 98）。
- 代理人啟動與切換：`AIOT_AGENT_PROFILE`（rule/glm_zai/glm_bigmodel/qwen_local）＋`AIOT_AGENT_FRAMEWORK`（direct/hermes）；詳 docs/ROUND4_GLM_API_REPORT.md §5-6。
- 乾淨環境最終驗證：outputs/audits/round4_glm_api/clean_env_final.md。
