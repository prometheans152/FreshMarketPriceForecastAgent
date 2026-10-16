# Proposal v5 r3（第三輪獨立複審通過；本機正式提案主版本）

本版依教授最新 Proposal 要求（AI Agent＋Domain Knowledge＋Data Analytics＋Real-World Application）在 v4 簡潔研究版基礎上擴充：Deep Research（五思維／三爭論／十問題）、教授八欄 Article Summary Table、Research Gap、Domain Agent 設計三種表示（五群組架構①–⑤＋虛線 PROPOSED 區、D1–D9 決策流程圖、Algorithm 1 主講 10 步＋附錄完整 41 行）。**Agent 邊界如實標注：CURRENT（規則式：parse_query＋get_market_quote/post_forecast 兩工具＋驗證器僅 Qwen 路徑）／PARTIAL（/records 保存 API 未工具化、到期機制無真值、資料過期僅警告）／PROPOSED（LLM Planner、save_record 工具化、嚴格過期 hard gate）。** 題目、資料、模型與封存結果不變；v1–v4 與試片原樣保留。

**r3（2026-10-09）**：依 ChatGPT 第二輪複審 REVIEW_R2 §3–5 定點返修——p3/p4 表格欄寬總和修正為滿寬 11.93 吋、p5/p24–26 Year 欄 0.46→0.76 吋、生成器新增 `validate_table_geometry()` fail-fast＋check.py PPTX 欄寬實讀＋`test_table_guard.py` 故意造錯 negative control（7 項）、六項 CURRENT/PARTIAL/PROPOSED 語意收斂（ToolCallLimiter 僅計數、驗證器僅 Qwen 路徑、DATA_FRESH 僅警告、get_market_quote 欄位、D1 today 預填、移除 32/32 殘留字串）。

## 開啟檔案

- `FMPA_Proposal_v5.pptx`：可編輯投影片，**23 頁主講＋10 頁附錄**（附錄 A5＝Algorithm 1 完整 41 行）。
- 同名 `.pdf`：由 PowerPoint 匯出（安全匯出器：唯讀未命名副本、不 Quit 共享實例）。
- `SLIDE_NOTES_v5.md`：逐頁講稿、補充與引用索引（與 PPT 內嵌備註同源 `notes_v5.json`）。
- `SOURCES.md`：24 個來源條目與查核層級。

主講設計估時 10 分 40 秒（非實測配音長度）。組員、組長與正式發表日期待填。**r3 已於 2026-10-09 通過 ChatGPT/COS 第三輪獨立複審（EXTERNAL_PASS，限 Proposal 交付範圍）**；[審查原文](../../outputs/audits/proposal_v5_r3_independent_20261009_01/REVIEW_R3.md)。PPT/PDF 保持驗收時的原始快照，封面的「候選」文字記錄的是當時受審狀態，不等於現在仍待審。

## 重建（在專案根目錄，使用全新的輸出目錄）

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONDONTWRITEBYTECODE='1'
$run="outputs/proposal_delivery/v5_rebuild_$(Get-Date -Format yyyyMMdd_HHmmss)"
$out="$run/package"
.venv\Scripts\python.exe -B slides/source/proposal_v5/build.py --root . --out $out --evidence "$run/build"
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
$ppt=Get-ChildItem -LiteralPath $out -Filter *.pptx | Select-Object -First 1
$pdf=[IO.Path]::ChangeExtension($ppt.FullName,'.pdf')
.venv\Scripts\python.exe -B slides/source/proposal_v5/export_safe.py --pptx $ppt.FullName --pdf $pdf --render "$run/render"
if ($LASTEXITCODE -ne 0) { throw 'Export failed' }
.venv\Scripts\python.exe -B slides/source/proposal_v5/check.py --root . --package $out --render "$run/render" --out "$run/check.json"
```

來源程式：`slides/source/proposal_v5/`（build/check/export_safe，參數化防覆寫）。使用專案既有 python-pptx、Pillow、pypdf、pywin32 與 Windows PowerPoint；無新安裝套件。凍結來源（評估 JSON SHA 2d28acd2…、stats_master、UI 截圖）在建置時以斷言核對。

檢查紀錄：`outputs/proposal_delivery/proposal_v5_20261008_01/CHECK.md`（含 r3 返修摘要、author automated checks 74/74、33/33 逐頁目視（p21 附註）、negative control 7/7、pytest 227、保護檔 14/14）；r3 品質紀錄 `outputs/quality_runs/proposal_v5_r3_20261009/`；渲染 `render10/`＋`sheets10/`。
