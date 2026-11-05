# V8 原生簡報：可攜重建來源

使用者原版 `FMPA_Proposal_v8.pptx` SHA256：`b0b362c99b079861bc0cc324d7ab6ed5a7f148671ddfff4debfe26597752ebdd`。使用者原稿必須保持原樣；`rebuild.py` 只修改指定文字、20頁原生 Notes 與十張表格的尺寸 metadata（第5頁增寬 Year），不重新繪製整份簡報或更動科學數字。

此目錄包含 `rebuild.py`、`check_v8.py`、`export_v8.py`、`negative_test_v8.py`、`visual_compare.py`、`audit_final.py`、`input_contract.json` 及 `frozen_inputs/`。凍結來源內有已驗證20頁旁白、公開評估 JSON、統計 JSON，並以來源原始 SHA256 對照。完全重建不需要根目錄 `BASELINE_INPUTS.json`、`inputs/verified_current`、`outputs/evaluation`、`outputs/proposal_delivery`，也不須模型或原訓練資料；如完整工作樹有 BASELINE，檢查器會多驗其它受保護原始檔。

把原始 V8 放在一個新專案根目錄，保留此資料夾位於 `slides/source/proposal_v8/`。已安裝 `lxml`、`python-pptx`、`Pillow`、`pypdf` 和 PowerPoint/pywin32 可執行以下示例（先在新目錄執行，輸出路徑必須不存在）：

```powershell
& $python slides/source/proposal_v8/rebuild.py --input FMPA_Proposal_v8.pptx --output outputs/review/FMPA_Proposal_v8_updated.pptx
& $python slides/source/proposal_v8/export_v8.py --pptx outputs/review/FMPA_Proposal_v8_updated.pptx --pdf outputs/review/FMPA_Proposal_v8_updated.pdf --render outputs/review/png
& $python slides/source/proposal_v8/check_v8.py --pptx outputs/review/FMPA_Proposal_v8_updated.pptx --pdf outputs/review/FMPA_Proposal_v8_updated.pdf --png outputs/review/png --out outputs/review/check.json
```

本次最終原生 PPTX SHA256 `b863486b038aaf34175c9dc81d4c86d6ce27c5d51fe5a1dc10d941b62ce6c8d0` 與先前 `outputs/v8_candidate/build6` 已完成 PowerPoint 唯讀匯出之 **整檔 hash 完全相同**，故經 `audit_final.py` 核查後沿用同源 PDF、20張原圖。真實依據 `outputs/v8_final/export_reuse_evidence.json`；不是再次假稱執行Office匯出。

作者在無 `BASELINE_INPUTS.json` 的同機最小來源樹重建同一PPTX SHA，checker 56/56，完整基準61/61；F1、Year欄及封存來源竄改三項反向控制均被拒絕。原結果見作者 SELF_CHECK 報告（本機 `outputs/quality_runs/v8_cos_20261105_01/author/AUTHOR_REPORT.md`，不入 Git）與同機最小來源檢查（本機 `outputs/quality_runs/v8_cos_20261105_01/author/repro_sandbox/repro_check.json`，不入 Git）。**這是使用已安裝依賴的同台Windows重建，不是新電腦安裝或跨OS驗證。**

2026-11-05 另一 COS reviewer2 已對固定 SHA 的 V8 成品完成 **EXTERNAL_PASS**：獨立檢查56/56與61/61、三項反向拒絕、20/20原尺寸PNG目視、PDF逐頁文字20/20、MP4／SRT影音13/13；參閱獨立審查原文（本機 `outputs/quality_runs/v8_cos_20261105_01/independent_review/OUTPUT_REVIEW.md`，不入 Git）和20頁目視紀錄（本機 `outputs/quality_runs/v8_cos_20261105_01/independent_review/visual_review.md`，不入 Git）。外審PPTX鎖定 `b863486b038aaf34175c9dc81d4c86d6ce27c5d51fe5a1dc10d941b62ce6c8d0`，PDF `eb0aefb27a46c91dfadd0aec09e90ddd5411f7c277bb2af5cdfc4869136f2175`，MP4 `210697d669e25ac1644b7f6f0d4ffcfbf9fd8c574723d8ac1a874d63179b47f0`，SRT `fedcf281dbdd1b77fa2d07af01de74552a232b9c40dbbb5b1bbed0bee0d157c3`及同源20頁。**外審限定已產出的簡報與影音包，未審整體設計藍圖、模型14項保護（由主協調者另查）、真店驗證、AI介面內對話、真人發音或期末交付。**所有報告連結使用接回主專案後的 `outputs/quality_runs/v8_cos_20261105_01/` 位置；原作者報告的歷史 SELF_CHECK 記錄保留。
