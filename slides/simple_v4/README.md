# 簡潔研究版 v4

本版依使用者指示，參考已下載的歷屆作品，直接重寫簡報內容與版面。題目、模型、資料與封存結果不變；v1–v3與兩頁影片試片原樣保留。

## 開啟檔案

- `菜價預測_研究提案_簡潔版_v4.pptx`：可編輯投影片，16頁主講＋6頁附錄。
- 同名 `.pdf`：由PowerPoint匯出。
- `SLIDE_NOTES_v4.md`：逐頁講稿、補充與引用索引。
- `notes_v4.json`：與PPT備註相同的講稿資料。
- `SOURCES.md`：完整來源與讀取層級。

主講設計估時為10分15秒，不是實測配音長度。本版尚未製作動畫或影片；組員、組長與正式發表日期待填。這是ChatGPT本次作者改寫及自查，不是另一次獨立複審或全案驗收。

## 閱讀順序

主講：動機 → 兩頁相關研究 → 三項亮點 → 編號架構 → 資料／目標 → A／B分頁計算 → 選型與評估 → 兩頁結果 → 原型畫面 → 驗證計畫與結論。

附錄：成熟清除 → 完整A／B公式 → 分品項結果 → 混淆矩陣 → 引用 → 實作索引。

主要改寫是將觀眾需要的研究敘事，與實作者／審查者使用的細節分開。負向結果、同店未驗證及市場均價限制仍在主講；不複製Team17的模型、食譜或研究分數。

## 重建（在專案根目錄，使用全新的輸出目錄）

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONDONTWRITEBYTECODE='1'
$run="outputs/proposal_delivery/v4_rebuild_$(Get-Date -Format yyyyMMdd_HHmmss)"
$out="$run/package"
.venv\Scripts\python.exe -B slides/source/simple_v4/build.py --root . --out $out --evidence "$run/build"
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
$ppt=Get-ChildItem -LiteralPath $out -Filter *.pptx | Select-Object -First 1
$pdf=[IO.Path]::ChangeExtension($ppt.FullName,'.pdf')
.venv\Scripts\python.exe -B slides/source/simple_v4/export_safe.py --pptx $ppt.FullName --pdf $pdf --render "$run/render"
if ($LASTEXITCODE -ne 0) { throw 'Export failed' }
.venv\Scripts\python.exe -B slides/source/simple_v4/check.py --root . --package $out --render "$run/render" --out "$run/check.json"
```

來源程式：`slides/source/simple_v4/`。使用目前專案既有python-pptx、Pillow、pypdf、pywin32及Windows PowerPoint。沒有安裝新套件或改產品環境。匯出器開啟唯讀、未命名副本，只關該副本，從不呼叫共享PowerPoint的Quit。

本次製作與檢查紀錄：`outputs/proposal_delivery/style_v4_20261004_01/`。舊草稿與初次渲染保留在該目錄，不放在正式交付資料夾。
