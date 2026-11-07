# 現場菜價 7／14 天預測與分析代理人

**Fresh Market Price Forecast Agent（FMPA）｜AIoT 應用與資料分析**  
組長：王彥傑｜組員：鄭筑云、許嘉修、游雅婷

使用者在店裡看到蔬菜的**今天價格（元／台斤或元／公斤）**，即可查詢從當天起 **7／14 日曆日**的市場變化參考；同店同規格上週價可選填，用於實驗性 B 模式。原首版三品項模型是 **7 日 Random Forest、14 日 HistGradientBoosting**。封存公有市場測試的方向 macro-F1 為 **0.4218／0.4169**，均未勝動量基線；相對變化 MAE 亦未勝不變價。**公開市場均價不等於個別店家的真價**，真店 A/B 增益尚未驗證。

[完整期中提案（Abstract／Introduction／Related Work／Proposed Scheme）](docs/midterm/PROPOSAL.md) · [系統設計、架構、流程與演算法](design.md) · [研究補充：文獻八欄表／5 思維／3 爭論／10 問題](docs/midterm/RESEARCH_NOTES.md) · [封存公開測試數據](docs/midterm/public_test_results.json)

![研究總覽資訊圖](docs/assets/資訊圖表_20261105.png)

## Installation

Windows PowerShell（需 Python 3.12；尚未在全新環境重測安裝）：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]" "scikit-learn==1.9.1" "pandas==2.3.3" "joblib==1.6.0"
```

本機推論需團隊提供與封存版本一致的 `models/releases/0.1.0/` 模型及公開歷史快照；部分處理後資料工件也未隨 Git 提供。缺少工件可使用下方雲端 Demo。

## How to Run

工件備妥後，在專案根目錄執行（`AIOT_RELEASE_DIR` 必須指向實際存在的封存版本）：

```powershell
$env:AIOT_MANUAL_WEB = "1"
$env:AIOT_RELEASE_DIR = (Resolve-Path ".\models\releases\0.1.0").Path
.\.venv\Scripts\python.exe -m uvicorn --app-dir src aiot_price.api.app:app --host 127.0.0.1 --port 8000
```

開啟 **http://127.0.0.1:8000/**；`/health` 應顯示 `ready`，`/metadata` 提供支援的品項及市場。本機 CLI、API 請求欄位和測試方式見[系統設計](design.md)。

## Demo

在本機 Web 表單選**甘藍／中義市場**，填 **32 元／台斤**、觀察日期 **2026-10-02**，不填上週價，送出 A 模式。這是配合封存行情的**歷史示範**：應看到 **2026-10-09（7 天）與 2026-10-16（14 天）**、方向、參考金額、資料日期及店價未驗證警示；實際金額以模型回傳為準。本機首版封存模型僅涵蓋三品項。

[雲端網頁 Demo](https://161.33.19.220/web/) 提供不同部署範圍（61 個品項欄位、60 個有行情），不能與本機三品項封存模型混為同一測試。AI 助理端提供 `get_market_quote`、`post_forecast` 兩個 MCP 工具（匿名 A）。
