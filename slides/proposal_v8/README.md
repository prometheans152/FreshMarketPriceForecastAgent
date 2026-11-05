# AIoT 期中提案：使用者原生 V8 固定版交付

狀態：**EXTERNAL_PASS（另一COS reviewer2 獨立審查，嚴格限定本報固定 SHA 的期中 V8 PPTX／PDF／20頁PNG／Notes／MP4／SRT）**；作者的 SELF_CHECK 仍是另一份歷史證據，沒有將整體設計藍圖、模型／產品、AI真實對話或對外發布升格。仍未上傳YouTube、推送GitHub或提交課程，正式發表日期待填。

外審鎖定 SHA256：PPTX `b863486b038aaf34175c9dc81d4c86d6ce27c5d51fe5a1dc10d941b62ce6c8d0`；PDF `eb0aefb27a46c91dfadd0aec09e90ddd5411f7c277bb2af5cdfc4869136f2175`；MP4 `210697d669e25ac1644b7f6f0d4ffcfbf9fd8c574723d8ac1a874d63179b47f0`；SRT `fedcf281dbdd1b77fa2d07af01de74552a232b9c40dbbb5b1bbed0bee0d157c3`，並包含已核對同源的20頁內容。外審原文與檢查記錄連結按**接回主專案後**的 `outputs/quality_runs/v8_cos_20261105_01/` 位置編寫。

## 當前交付

| 檔案 | 用途 |
| --- | --- |
| [FMPA_Proposal_v8_updated.pptx](FMPA_Proposal_v8_updated.pptx) | 20 頁可編輯原生投影片，使用者原 V8 為唯一底稿 |
| [FMPA_Proposal_v8_updated.pdf](FMPA_Proposal_v8_updated.pdf) | Office 從上述 PPTX 實際輸出的 20 頁 PDF |
| [png/](png/) | 20 張 1600×900 PNG，檔名 slide_01.png 至 slide_20.png |
| [SLIDE_NOTES_v8.json](SLIDE_NOTES_v8.json) | 20 頁已驗證旁白與補充來源／界線 |
| [SLIDE_NOTES_v8.md](SLIDE_NOTES_v8.md) | 與 JSON 同源的完整 Markdown 講稿 |
| 最終逐頁像素比較（本機 `outputs/v8_final/visual/pixel_comparison.json`，不入 Git）・[全頁縮圖](contact_sheet.png) | 1、5、10、19、20頁改動；其餘15頁與原V8像素完全相同 |
| 作者最終檢查（本機 `outputs/quality_runs/v8_cos_20261105_01/author/v8_final_check.json`，不入 Git） | 作者61/61；同機最小來源重建56/56（本機 `outputs/quality_runs/v8_cos_20261105_01/author/repro_sandbox/repro_check.json`，不入 Git）、作者反向控制3/3（本機 `outputs/quality_runs/v8_cos_20261105_01/author/v8_final_negative_tests.json`，不入 Git） |
| 獨立複審原文（本機 `outputs/quality_runs/v8_cos_20261105_01/independent_review/OUTPUT_REVIEW.md`，不入 Git）・20頁目視紀錄（本機 `outputs/quality_runs/v8_cos_20261105_01/independent_review/visual_review.md`，不入 Git） | 另一COS獨立實看20/20 PNG、PDF文字20/20，獨立56/56與61/61、3項反向拒絕、影片13/13 |
| [整檔 SHA 同源匯出證據](export_reuse_evidence.json) | 最終PPTX與先前Office實際匯出來源整檔SHA一致，PDF與20PNG逐檔核對 |
| [可攜重建來源](../source/proposal_v8/README.md) | `input_contract.json`、20頁旁白、封存數值與預期hash均隨來源提供 |
| 作者自驗原文（本機 `outputs/quality_runs/v8_cos_20261105_01/author/AUTHOR_REPORT.md`，不入 Git） | 作者當時僅逐張實看第1、5、10、19、20頁；原文保留當時SELF_CHECK狀態，不覆寫後續外審結論 |

影片：MP4（本機 `recordings/midterm_v8_cos_20261105/FMPA_Midterm_v8_updated.mp4`，不入 Git） 與同步 SRT（本機 `recordings/midterm_v8_cos_20261105/FMPA_Midterm_v8_updated.srt`，不入 Git）；20段已驗證音檔原hash不變，長度 **585.933333秒（9:45.93＜期中10分鐘上限）**，另一COS獨立技術驗證 **13/13**，174字幕與20頁旁白一致。**真人尚未逐字聽校人名／專有名詞發音**。期中20頁／9:45.93**不代表期末「超過20頁／超過10分鐘」已達標**。

## 變更邊界

- 第 1 頁補正組長與三名組員（「鄭筑云」不轉寫）、日期仍待填。
- 第 10 頁更新 MCP 60 品項／13 市場、僅 A、不提供 B／保存，歷史遠端原 6/6＋新增 5/5；網頁 61 品項可 A/B，紀錄僅留瀏覽器；AI 真實對話與解釋仍待驗收。
- 第 10、19、20 頁區分「訓練／評估封存至 2026-10-02」與「推論用公開行情自 2026-10-30 每日更新」，模型**沒有重訓**；刪除每日更新未完成的現行說法。
- 第 5 頁 Year 欄擴為 **0.76 吋**，在同一張原生表格內重新分配欄寬；另 10 張表格修復 V8 既有的外框 metadata 3000000 EMU 假尺寸，實際欄／列尺寸與文字均保留。除第 5 頁文字位置改善外，其他表格修復沒有造成任何輸出像素變化。
- 第 17 頁科研分數與負向發現、A/B 教學示例未改；第 1／10／19／20 頁之外沒有更動可見文字。PPT 20頁Notes、JSON、MD與影片的旁白使用 `slides/source/proposal_v8/frozen_inputs/narration.json`；根目錄V8 SRT僅供參考，最終字幕由原音檔 words 時間戳同步生成。

## 隔離重建／檢查

以下命令在 **本隔離工作樹根目錄**執行，使用已安裝 Python 及 PowerPoint。輸出使用全新、**尚不存在**的目錄或檔案；修改器有原 V8 SHA-256 和凍結評估 JSON 的 guard。

```powershell
$python = 'C:\Users\prometheans\Documents\AIOT_FinishProject\.venv\Scripts\python.exe'
& $python slides/source/proposal_v8/rebuild.py --output outputs/v8_candidate/review/FMPA_Proposal_v8_updated.pptx
& $python slides/source/proposal_v8/export_v8.py --pptx outputs/v8_candidate/review/FMPA_Proposal_v8_updated.pptx --pdf outputs/v8_candidate/review/FMPA_Proposal_v8_updated.pdf --render outputs/v8_candidate/review/png
& $python slides/source/proposal_v8/check_v8.py --pptx outputs/v8_candidate/review/FMPA_Proposal_v8_updated.pptx --pdf outputs/v8_candidate/review/FMPA_Proposal_v8_updated.pdf --png outputs/v8_candidate/review/png --out outputs/v8_candidate/review/check.json
& $python slides/source/proposal_v8/visual_compare.py --original outputs/v8_candidate/original/png --updated outputs/v8_candidate/review/png --outdir outputs/v8_candidate/review/visual
```

使用 `slides/source/proposal_v8/negative_test_v8.py` 產生隔離的壞F1／Year欄／封存來源對照，三者都必須被檢查器非零退出拒絕，作者與另一COS均實測成功。作者的同機最小來源樹（本機 `outputs/quality_runs/v8_cos_20261105_01/author/repro_sandbox/repro_check.json`，不入 Git）無COS根資料、重建結果SHA相同；**尚未在全新電腦安裝依賴或驗證其他OS**。`export_v8.py` 支援獨立 PowerPoint COM 程序及原稿唯讀副本；本次完整PPTX SHA相同而沿用較早build6已完成的Office輸出，沒有重新匯出，詳見 `export_reuse_evidence.json`。

影片原始制作指令已留在 `recordings/midterm_v8_cos_20261105/commands.log`，現用版本：

```powershell
& $python recordings/midterm_v8_cos_20261105/make_video.py --run recordings/midterm_v8_cos_20261105/final_run --render outputs/v8_final/png --pptx outputs/v8_final/FMPA_Proposal_v8_updated.pptx --rate '+0%' --name FMPA_Midterm_v8_updated
& $python recordings/midterm_v8_cos_20261105/verify_video.py --run recordings/midterm_v8_cos_20261105/final_run --name FMPA_Midterm_v8_updated
```

上方影片指令僅供在新隔離run內重演；目前 `final_run` 已有成果，勿直接覆寫。`video_input_lock.json` 保存PPTX、20PNG、20MP3與20份words資料在編碼前後的完整SHA，另一COS獨立驗證13/13。**作者只逐張看第1、5、10、19、20頁；獨立reviewer2另逐張看完20/20**，見逐頁目視原文（本機 `outputs/quality_runs/v8_cos_20261105_01/independent_review/visual_review.md`，不入 Git）。隨附 `final_run/timing.json` 仍有原作者暫存絕對PNG路徑；移動到別的工作樹重跑驗證器前，須先核對20張PNG SHA並重新映射該路徑，FFmpeg也須在指定同機路徑。模型14項保護由主協調者owner另行重查，**不屬reviewer2已驗項目**；真店A/B及ChatGPT／Gemini介面內對話未驗收。Qwen3.8-27B封存、GLM／Hermes／SERVER暫緩。
