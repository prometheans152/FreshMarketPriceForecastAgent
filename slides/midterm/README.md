# 現場菜價 7／14 天預測與分析代理人｜期中提案

本期中提案包含 **20 頁（19 頁主講、1 頁引用附錄）**，使用可編輯的 PowerPoint、PDF 與逐頁講稿呈現研究問題、現有系統、公開測試成果及限制。

| 檔案 | 內容 |
| --- | --- |
| [FMPA_Midterm.pptx](FMPA_Midterm.pptx) | 可編輯投影片，20 頁 |
| [FMPA_Midterm.pdf](FMPA_Midterm.pdf) | PDF 閱讀版，20 頁 |
| [png/](png/) | 20 張 1600 × 900 的投影片圖片 |
| [SLIDE_NOTES.md](SLIDE_NOTES.md)、[SLIDE_NOTES.json](SLIDE_NOTES.json) | 每頁正式旁白、來源與限制 |

研究與資料入口：[研究筆記、文獻與設計說明](../../docs/midterm/RESEARCH_NOTES.md)／[公開測試結果 JSON](../../docs/midterm/public_test_results.json)。論文原作者、研究引用及證據層級以研究筆記的來源索引為準。

**使用方法：** 報告時播放 PPTX 第 1–19 頁，第 20 頁供引用查閱；需要講稿時開啟 Markdown 或 PowerPoint 的備忘稿。PDF 適合分享與閱讀，PNG 供逐頁檢視。重建與匯出可參考 [簡報來源腳本](../source/midterm/build_midterm.py)、[PDF／圖片匯出腳本](../source/midterm/export_midterm.py)。

**科學與使用限制：** 封存公開測試中，7／14 天方向 macro-F1 為 0.4218／0.4169，未勝動量基線；相對變化 MAE 為 0.0664／0.0983，未勝不變價基線。公開市場均價不能代替同店真價；B 模式的 0.3 係數是固定規則。已確認 ChatGPT 匿名 A 的一次真實對話，其他情境、Gemini、同店到期 A/B 增益及人因效果仍待驗證。研究整理、程式與簡報使用 AI 工具協助，數據與引用依來源核對。
