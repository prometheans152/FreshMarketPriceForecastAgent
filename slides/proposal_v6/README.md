# 期中提案 v6（Fresh Market Price Forecast Agent）

期中繳交版。**內容與 [Proposal v5 r3](../proposal_v5/README.md) 相同**；v5 r3 已於 2026-10-09 通過 ChatGPT/COS 獨立複審。本版只做兩件事：

- **改名：** 把 TW01 換成「本案」或新名稱 Fresh Market Price Forecast Agent。虛擬碼的 `TW01_AGENT` 改為 `PRICE_AGENT`。
- **清掉過期字樣：** 封面的「候選版，待獨立複審」，以及講者備註中的「作者自驗候選，待複審」。

題目、數據、模型、圖表、講稿內容都沒有改。封面的「組員／組長、正式發表日期」仍是「待填」，請在 PowerPoint 裡自行填寫。v6 沒有另做外部審查。

## 檔案

- `FMPA_Proposal_v6.pptx`：可編輯投影片，23 頁主講＋10 頁附錄。
- `FMPA_Proposal_v6.pdf`：由 PowerPoint 匯出，33 頁。
- `SLIDE_NOTES_v6.md`：逐頁講稿，與 PPT 內嵌備註同源（`notes_v6.json`）。主講設計估時 10 分 40 秒，這是估計值，不是實際錄音長度。
- `SOURCES.md`：來源條目與查核層級，與 v5 相同。

## 驗證（2026-10-17）

| 項目 | 結果 |
| --- | --- |
| 頁數 | PPTX＝PDF＝PNG＝備註＝33 |
| 自動檢查 | `check.py` 75/75 通過：v5 原有 74 項，加上「內文與備註不得出現 TW01／候選版／待獨立複審」 |
| 表格欄寬反向測試 | `test_table_guard.py` 7/7 |
| 舊字樣反向測試 | 同一檢查在 v5 命中 15 處（第 1、4、7、8、13、23、26、28 頁），在 v6 為 0 |
| 與 v5 逐頁像素比對 | 25 頁完全相同；8 頁有差異，都是預期的改名處，皆已逐張以原始解析度目視，無溢出或重疊 |
| 匯出安全 | 唯讀未命名副本，原始 PPTX 雜湊不變，未關閉共用 PowerPoint |

建置與比對紀錄放在本機 `outputs/proposal_delivery/v6_midterm_20261017_123447/`（不進版控）。

## 重建（在專案根目錄，使用新的輸出目錄）

```powershell
$env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'; $env:PYTHONDONTWRITEBYTECODE='1'
$run="outputs/proposal_delivery/v6_rebuild_$(Get-Date -Format yyyyMMdd_HHmmss)"; $out="$run/package"
.venv\Scripts\python.exe -B slides/source/proposal_v6/build.py --root . --out $out --evidence "$run/build"
$ppt=(Get-ChildItem -LiteralPath $out -Filter *.pptx | Select-Object -First 1).FullName
.venv\Scripts\python.exe -B slides/source/proposal_v6/export_safe.py --pptx $ppt --pdf ([IO.Path]::ChangeExtension($ppt,'.pdf')) --render "$run/render"
.venv\Scripts\python.exe -B slides/source/proposal_v6/check.py --root . --package $out --render "$run/render" --out "$run/check.json"
```
