# 投影片製作來源：依賴與重建（D44 收尾輪 v3）

## 依賴（本機 `.venv` 實測版本；2026-10-04 盤點，未做乾淨環境重建驗證）

| 套件 | 版本 | 用途 |
| --- | --- | --- |
| python-pptx | 1.0.2 | 產生可編輯 PPTX（notes、connector、群組框） |
| pandas | 2.3.3 | 讀 parquet/CSV |
| pyarrow | 25.0.1 | parquet 引擎 |
| matplotlib | 3.11.2 | 圖表素材（微軟正黑體） |
| pywin32 | 312 | PowerPoint COM 匯出（含所有權防護，見下） |
| pypdf | 6.19.0 | PDF 頁數核對 |
| pytest | （產品既有） | 製作工具測試 |

系統需求：Windows＋PowerPoint（桌面版）＋微軟正黑體。

## 實際重建範例（Windows；變數統一，可直接貼 PowerShell 執行）

```powershell
# 於專案根目錄 C:\Users\prometheans\Documents\AIOT_FinishProject
$RUN   = "outputs/proposal_delivery/run3_20261004_01"
$VER   = "v3"
$ASSET = "slides/assets_v3"
$PPTX  = "slides/TW01_菜價預測_研究提案與初步成果_v3.pptx"

# 1) 共享數據主檔（唯讀重算＋與複審 descriptive_counts.csv 交叉斷言）
.\.venv\Scripts\python.exe slides/source/build_stats_master.py --out $RUN/stats_master.json

# 2) 六張圖表素材（讀 stats_master＋封存評估 JSON＋parquet 唯讀 purge 分組）
.\.venv\Scripts\python.exe slides/source/make_assets.py --out $ASSET --stats $RUN/stats_master.json

# 3) 講稿 MD（由 notes_v3.json 單一底稿生成；與 PPT 備註同源）
.\.venv\Scripts\python.exe slides/source/make_slide_notes.py --force

# 4) PPTX（notes/數字/素材由參數讀入；第13頁 UI 截圖為必要素材，缺圖 exit 3）
.\.venv\Scripts\python.exe slides/source/make_pptx.py --pptx $PPTX --assets $ASSET --notes slides/source/notes_v3.json --stats $RUN/stats_master.json

# 5) PDF＋逐頁 PNG（COM；所有權防護：開始前偵測既有 PowerPoint，共享時只 Close 本輪簡報、不 Quit 應用）
.\.venv\Scripts\python.exe slides/source/export_and_render.py --pptx $PPTX --render $RUN/slides_render_v3

# 6) 測試（22 項：數值/purge分組/同源/架構語意標籤/防覆寫/缺圖失敗/共享 PowerPoint 不 Quit）
.\.venv\Scripts\python.exe -m pytest slides/source/test_make_tools.py -q
```

## 檔案說明

| 檔案 | 角色 |
| --- | --- |
| `build_stats_master.py` | 唯讀重算 descriptive/eval/**purge 期限別分組**/splits → `stats_master.json`（交叉核對計數動態產生） |
| `make_assets.py` | 6 張圖；time_split 依 purge 分組（h7 8日/h14 15日） |
| `notes_v3.json` | 19 頁講稿**單一底稿**（p8 按五群組編號對照解說） |
| `make_slide_notes.py` | notes_v3.json → `docs/SLIDE_NOTES.md` |
| `make_pptx.py` | v3 PPTX（第8頁五群組架構；第10頁全教學假設；UI 截圖必須存在 `--ui-shot`） |
| `export_and_render.py` | COM 匯出（**所有權防護**：tasklist 前測＋Presentations.Count 檢查，僅獨佔且清空才 Quit） |
| `test_make_tools.py` | 22 項測試（含 `TestExportSafety` 共享實例 mock、缺 UI 截圖受控失敗） |

## 邊界

- 製作鏈只唯讀正式資料；v1/v2、run1/run2、舊審查、配音試片不覆寫。
- 依賴為現有環境盤點；乾淨環境完整重建驗證未執行（如實列未驗）。
