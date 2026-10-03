# TRAIN_LOCAL 訓練機環境查核與可重現設置（T03）

查核日期：2026-10-03。狀態：**PASS**——venv 已建立、依賴已安裝、import／版本／最小讀檔與煙霧測試均實際執行通過；原始輸出保存於 `outputs/local_env/`（Git 忽略目錄）。

本機是 TRAIN_LOCAL（訓練機）。GPU 查核結果見下方「已知限制」：本機實際有一張 NVIDIA GeForce RTX 3080 ti，但它不是 SERVER_3090 的 3090，且本案訓練計畫用 CPU 表格模型，不依賴它。

## 硬體與系統摘要

| 項目 | 實測值 | 查核方式 |
| --- | --- | --- |
| OS | Microsoft Windows 10 專業版 64 位元（10.0.19045） | `Get-CimInstance Win32_OperatingSystem` |
| 主機 | ASUS（System Product Name） | `Win32_ComputerSystem` |
| CPU | AMD Ryzen 7 5800X，8 核心／16 執行緒，3.8GHz | `Win32_Processor` |
| RAM | 32GB（33,463,172 KB 可見），查核時可用約 10.4GB | `Win32_OperatingSystem` |
| 磁碟 C: | 總量 1906.4GB，剩餘 822.8GB | `Win32_LogicalDisk` |
| GPU | NVIDIA GeForce RTX 3080 ti 12GB（驅動 596.49，WDDM 模式，查核時約 3.4GB 已被桌面程式占用） | `nvidia-smi` |
| CUDA toolkit | 未安裝（`nvcc` 不存在；驅動支援 CUDA 13.2 執行階段） | `nvcc --version` |
| Node.js | v24.16.0 | `node --version` |

訓練成本評估：本案資料為臺中市場每日零售均價 JSON（約 5.3MB，4450 列 × 63 欄），pandas + scikit-learn 的表格時間序列模型在本機 CPU 與 RAM 下綽綽有餘；不需要 GPU。

## Python 與套件管理

| 項目 | 實測值 |
| --- | --- |
| `python --version` | Python 3.12.10（`C:\Users\prometheans\AppData\Local\Programs\Python\Python312\python.exe`，使用者安裝） |
| `py` 啟動器 | 不在 PATH；完整路徑 `C:\Users\prometheans\AppData\Local\Programs\Python\Launcher\py.exe` 存在，`-0p` 列出 3.12（預設）與 uv 管理的 CPython 3.11.15 |
| pip（系統） | 26.2.1 |
| uv | 0.11.16（本機另有，但本案依計畫使用 stdlib venv + pip） |
| venv 內 pip | 25.0.1（Python 3.12 內建版本，未升級） |

## 專案隔離環境（可重現步驟）

以下命令均在專案根目錄 `C:\Users\prometheans\Documents\AIOT_FinishProject` 執行；不安裝全域套件、不改全域配置。

1. 建立環境：`python -m venv .venv`（Python 3.12.10）
2. 安裝（實際成功指令）：`.venv/Scripts/python.exe -m pip install -e ".[dev]"`
   - 套件定義在 [pyproject.toml](../pyproject.toml)：`aiot-price` 0.1.0、src layout（`src/aiot_price/`）、`requires-python = ">=3.10"`、dev extra 含 pytest。首次安裝一次成功，無需退回逐一套件安裝。
3. Git Bash 啟用：`source .venv/Scripts/activate`；PowerShell：`.venv\Scripts\Activate.ps1`；cmd：`.venv\Scripts\activate.bat`。或直接用完整路徑 `.venv/Scripts/python.exe` 呼叫，不啟用也可。
4. 鎖版：`.venv/Scripts/python.exe -m pip freeze`，去掉 pip 產生的絕對路徑 `-e` 行後在最上方加 `-e .`，存為專案根目錄 [requirements-lock.txt](../requirements-lock.txt)（重現精確版本用；pyproject.toml 的相容範圍與此檔並存）。注意：pip freeze 原始輸出的 `-e c:\users\...` 反斜線路徑會被 pip 跳脫解析而失敗，必須改成 `-e .` 並從專案根目錄安裝。
5. 乾淨環境重現（已實測）：`python -m venv <新路徑>` 後在專案根目錄執行 `<新路徑>\Scripts\python.exe -m pip install -r requirements-lock.txt`；2026-10-03 已以此法另建乾淨 venv 驗證，安裝成功且 8 個套件版本與主環境完全一致（`outputs/local_env/clean_venv_install.txt`、`clean_venv_verify.txt`，驗證後該測試 venv 已刪除）。

`.venv/`、`.env` 已被 [.gitignore](../.gitignore) 排除，`.env.example` 保留為無秘密範本；秘密一律用環境變數，不寫進範例或 Git。

## 實際安裝版本（2026-10-03 實測）

| 套件 | 版本 | pyproject 範圍 |
| --- | --- | --- |
| aiot-price（本專案，editable） | 0.1.0 | — |
| pandas | 2.3.3 | >=2.0,<3 |
| numpy | 2.5.3 | >=1.24,<3 |
| scikit-learn | 1.9.1 | >=1.3,<2 |
| PyYAML | 6.0.3 | >=6,<7 |
| requests | 2.34.2 | >=2.31,<3 |
| jsonschema | 4.26.0 | >=4.18,<5 |
| pytest | 8.4.2 | >=7,<9 |

其他傳遞依賴（scipy 1.18.1、joblib 1.6.0 等）完整清單見 `requirements-lock.txt` 與 `outputs/local_env/requirements-lock.txt`。

## 驗證輸出摘要（已執行）

- import／版本檢查（`outputs/local_env/verify_final.txt`）：`aiot_price 0.1.0` 可 import 且指向 `src\aiot_price\__init__.py`；上表 7 個套件版本全部可查，輸出尾行 `ALL_CHECKS_OK`。
- 最小讀檔檢查（同檔）：以 json + `pandas.json_normalize` 讀 `data/retail_recheck/taichung/retail_prices_20261003.json`，得 4450 列 × 63 欄，首列 `市場名稱=中義市場`、`訪價日期=20251004`，280,350 格全非空。
- 煙霧測試（`outputs/local_env/pytest_smoke.txt`）：`.venv/Scripts/python.exe -m pytest tests/test_smoke.py -v` → 4 passed。
- 完整測試現況（`outputs/local_env/pytest_run.txt`）：全專案 pytest 為 19 passed / 1 failed；失敗的 `tests/data/test_labels.py::test_hand_e2_flat_boundary_inclusive` 屬 T07 標籤邊界語意（並行進行中），不屬 T03 環境問題，環境相關測試全部通過。
- 乾淨環境重現（`outputs/local_env/clean_venv_install.txt`、`clean_venv_verify.txt`）：另建全新 venv 用 `pip install -r requirements-lock.txt` 安裝，8 個套件版本與主環境完全一致，editable 指向 `src\aiot_price\__init__.py`，輸出尾行 `CLEAN_VENV_OK`。

## 已知限制

1. **GPU 不在訓練計畫內**：本機有 RTX 3080 ti（12GB），但無 CUDA toolkit（`nvcc` 不存在），且本案用 CPU 表格模型；不把本機 GPU 當 SERVER_3090 的 3090，也不在此機跑 Qwen 大模型推論。
2. **numpy 2.5.3 + pandas 2.3.3 出現 DeprecationWarning**：`The 'generic' unit for NumPy timedelta is deprecated`（見 pytest_run.txt 警告統計）。目前僅警告、不影響執行；若未來 pandas 升級把它變錯誤，可將 numpy 上限收到 `<2.5`。
3. **`py` 啟動器不在 PATH**：Git Bash 內 `py -0` 失敗；需用完整路徑或直接 `python`（3.12.10）。
4. **Windows 命令列編碼**：`python -c "..."` 內嵌中文字串（如欄名）可能因主控台編碼出錯，讀檢查改用位置索引（見 verify_data_read.txt 的對照紀錄）；後續腳本一律從 UTF-8 檔案讀中文欄名，不放進命令列參數。
5. **並行工作共存**：T03 執行期間，同工作區有其他 TASK（資料載入、標籤、切分等）的 `src/aiot_price/data/`、`tests/data/` 檔案陸續建立（時間戳 2026-10-03 23:26–23:29）。T03 只建立 `src/aiot_price/__init__.py` 最小骨架與 [tests/test_smoke.py](../tests/test_smoke.py)，未改其他 src 檔；editable 安裝可自動吃到後續新增的子套件（已由 pytest 實際 import 驗證）。

## 證據檔清單（outputs/local_env/，Git 忽略）

| 檔案 | 內容 |
| --- | --- |
| `cpu.txt` | CPU 型號／核心數原始輸出 |
| `ram_os.txt` | RAM 總量／可用、OS 版本原始輸出 |
| `disk.txt` | 各磁碟總量／剩餘原始輸出 |
| `python_check.txt` | Python／py／pip／uv 查核原始輸出 |
| `gpu_node_check.txt` | nvidia-smi、nvcc、node 查核原始輸出 |
| `pip_install.txt` | `pip install -e ".[dev]"` 完整安裝日誌 |
| `verify_final.txt` | import／版本／最小讀檔整合驗證（ALL_CHECKS_OK） |
| `verify_data_read.txt` | 讀檔檢查（含中文欄位編碼問題對照） |
| `pytest_smoke.txt` | T03 煙霧測試 4 passed |
| `pytest_run.txt` | 全專案 pytest 輸出（19 passed / 1 failed，失敗屬 T07 範圍） |
| `clean_venv_install.txt` | 乾淨 venv 依鎖版檔安裝日誌 |
| `clean_venv_verify.txt` | 乾淨 venv import／版本驗證（CLEAN_VENV_OK） |
| `requirements-lock.txt` | pip freeze 鎖版副本（`-e` 行已改為 `-e .`） |
