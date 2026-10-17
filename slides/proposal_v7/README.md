# 期中提案 v7（20 頁版；Fresh Market Price Forecast Agent）

**r4（2026-10-17）：** 第 5 頁標題「主講精選5件」改為「精選4件」，講稿「挑五件」改為「挑四件」。表格本來就只有 R01、R02、R06、H17 四列，這個錯從 v5 起就存在。check.py 67/67：新增「標題件數＝表格列數」「講稿件數＝表格列數」兩項（反向測試：r3 版在這兩項失敗，65/67）。與 r3 逐像素比對，只有第 5 頁標題那個字不同。

**r3（2026-10-17）：** 依使用者指示改成「現在真的在運作的系統」。第 10 頁架構圖重畫：瀏覽器 → Oracle 雲端網頁；ChatGPT／Gemini → Cloudflare MCP → Oracle ForecastEngine。第 11、12 頁的現況標註、第 18 頁頁尾、第 19 頁結論、第 20 頁實作狀態一起更新，不再列 Qwen、GLM、Hermes。其餘 14 頁與 r2 逐像素相同。check.py 65/65：新增「無 Qwen」「投影片無已退役後端」「架構頁如實標註限制」。

**r2：** 第 10–12 頁把 Qwen3.8-27B 標為封存（D46）。

依教授「20 頁以內」的要求，由 [期中提案 v6](../proposal_v6/README.md) 濃縮而成。v6 的內容與通過獨立複審的 Proposal v5 r3 相同。**所有數字、圖表與結論都不變**，只做刪頁、合併與附錄精簡。v7 沒有另做外部審查。

## 頁序（19 主講＋1 引用索引）

講稿標註的「設計估時」合計 9 分 15 秒，但這是以每分鐘近 400 字估算。講稿共約 3,700 字，以正常語速（每分鐘約 240 字）唸要 15 分鐘左右，所以現場報告或錄影需要另外精簡。

1 封面｜2 研究動機｜3 相關研究｜4 相關服務與研究缺口｜5 文獻摘要表（八欄）｜6 研究問題與三項貢獻｜7–9 深研究：五思維／三爭論／十問題｜10 系統架構｜11 查詢流程圖｜12 演算法一（行號虛擬碼）｜13 資料與評估設計｜14 預測目標與漲跌定義｜15 A 模式｜16 B 模式｜17 初步結果｜18 介面示例｜19 結論｜20 引用與實作索引

## 與 v6（33 頁）的差異

| 處理 | v6 頁 | 理由 |
| --- | --- | --- |
| 刪除 | 10 Agent 設計原則 | 分工與安全要點已在第 10 頁架構圖與第 12 頁演算法頁腳（ForecastEngine、白名單、227 測試、LLM 不算菜價） |
| 刪除 | 22 下一步 | 與結論的「下一步」重複；其中「服務暫緩、SERVER 未提供」已過時 |
| 合併 | 14 資料來源＋18 模型選擇 → 13 資料與評估設計 | 來源、期間、品項、單位、時間切分、模型、防洩漏（1,386 列）集中在一張表 |
| 合併 | 19 方向結果＋20 誤差與召回 → 17 初步結果 | 兩張表數值與 v6 相同；負向結果全部保留 |
| 精簡 | 附錄 A1–A9 | 完整文獻表、十題解答、41 行虛擬碼、公式、分品項、混淆矩陣仍在 `docs/proposal_v5/`；內文對附錄的引用改為指向這些文件 |

封面的「組員／組長、正式發表日期：待填」請在 PowerPoint 裡自行填寫。

## 驗證（2026-10-17）

| 項目 | 結果 |
| --- | --- |
| 頁數 | PPTX＝PDF＝PNG＝備註＝20（≤20） |
| 自動檢查 | `check.py` 62/62：頁數上限、數值對封存 JSON、八欄表、架構／流程圖元素、表格欄寬實讀、不得殘留 TW01、不得引用已刪附錄（反向測試：v6 命中 27 處，v7 為 0） |
| 表格欄寬反向測試 | 7/7 |
| 與 v6 逐頁比對（遮掉頁碼） | 8 頁完全相同；5 頁只有頁尾字樣不同；第 2–4 頁文字相同，只有幾百點的匯出反鋸齒差異；第 13、17 頁是新的合併頁 |
| 目視 | 第 13、17、20 頁、有差異的頁面與所有新頁尾，皆以原始解析度檢查 |

目視曾發現並修正一個問題：第 13 頁初版有兩列文字換行，把表格撐高，壓到下方重點句的裝飾線。自動檢查沒有抓到，因為它讀的是設定列高。修正方式是刪掉與第 14 頁重複的「整理方式」列，並讓兩列長文字預留兩行高度。

## 重建（在專案根目錄，使用新的輸出目錄）

```powershell
$env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'; $env:PYTHONDONTWRITEBYTECODE='1'
$run="outputs/proposal_delivery/v7_rebuild_$(Get-Date -Format yyyyMMdd_HHmmss)"; $out="$run/package"
.venv\Scripts\python.exe -B slides/source/proposal_v7/build.py --root . --out $out --evidence "$run/build"
$ppt=(Get-ChildItem -LiteralPath $out -Filter *.pptx | Select-Object -First 1).FullName
.venv\Scripts\python.exe -B slides/source/proposal_v7/export_safe.py --pptx $ppt --pdf ([IO.Path]::ChangeExtension($ppt,'.pdf')) --render "$run/render"
.venv\Scripts\python.exe -B slides/source/proposal_v7/check.py --root . --package $out --render "$run/render" --out "$run/check.json"
```
