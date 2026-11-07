# 期中精簡版簡報

- [可編輯 PowerPoint](FMPA_Midterm_Minimal.pptx)
- [20 頁 PDF](FMPA_Midterm_Minimal.pdf)
- [20 張 PNG 預覽](png/slide_01.png)
- [逐頁講稿 Markdown](SLIDE_NOTES.md)／[JSON](SLIDE_NOTES.json)

第 11 頁原生流程圖與第 12 頁 12 行偽碼，
與專案根目錄 `design.md` 第 6 節同步。

## 採用後重新產生（在正式專案根目錄執行）

下列指令只在新的 `outputs/quality_runs/` 子目錄產生候選檔，
不覆寫正式 DESIGN 或現有 PPT；原正式 PPT 輸入經固定 SHA-256 驗證。

```powershell
.\.venv\Scripts\python.exe slides/source/midterm_minimal/build_midterm_minimal.py --source slides/midterm/FMPA_Midterm.pptx --design-source design.md --proposal-source docs/midterm/PROPOSAL.md --notes-source slides/midterm/SLIDE_NOTES.json --out outputs/quality_runs/minimum_sync_rebuild_check_20261107_02/slides/midterm_minimal/FMPA_Midterm_Minimal.pptx --audit outputs/quality_runs/minimum_sync_rebuild_check_20261107_02/build_meta.json
```

預設路徑由專案根目錄計算；已有目標檔時會拒絕覆寫。
PDF／PNG 需以隔離的 Office DispatchEx 另行安全匯出；
只開候選（ReadOnly／Untitled），不可 Quit 共用 PowerPoint。

研究證據以公開市場均價為主；真店 A/B 效益需另行配對驗證。
