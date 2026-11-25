# DIC4 完成紀錄與未完成事項

驗收日期：2026-11-25（Asia/Taipei）
範圍：教授白板 `C:\Users\prometheans\Desktop\課程\AIOT\DIC4\429406.jpg`、原 `AIOT_FinishProject` 的現有 FMPA 期中提案與封存模型結果。本次不重訓、不重部署、不更改產品源碼與歷史 DIC3 檔。

## 狀態與雲端成果

| 項目 | 狀態 | 可查證依據 |
| --- | --- | --- |
| 本輪修改前草稿 | 完成 | `paper/dic4/v1_before/main.tex` 與 `references.bib` |
| 修改後論文草稿 | 完成 | `paper/dic4/v2_after/main.tex` 與 `references.bib` |
| 修訂差異 | 完成 | `docs/dic4/REVISION_COMPARISON.md` |
| Overleaf 真正匯入與編譯 | 通過 | `https://www.overleaf.com/project/6b06bd77157dbfcfac3cf914`；專案檔樹含 `main.tex`、`references.bib`、`before/`，UI 顯示 Compile finished |
| 編譯 PDF 本機副本 | 通過 | `paper/dic4/v2_after/FMPA_DIC4_Overleaf.pdf`，實際 5 頁，238258 bytes，SHA256 `71A872F86BE2F4288AB7C5707626700DCFAB4604F27D9E999E3910A11F200B61` |
| OpenSpec 四件規格 | 通過 | `openspec/changes/dic4-overleaf-paper`（proposal / design / specs / tasks） |
| GitHub push / PR | **已完成獨立分支上傳；PR 開啟** | GitHub 登入 `prometheans152`；推送分支 `dic4/overleaf-paper-20261125`；審查請求 `https://github.com/prometheans152/FreshMarketPriceForecastAgent/pull/2`，尚未合併 `main` |
| Overleaf 編輯器 MCP | **依使用者指示省略（非必要）** | 2026-11-25 使用者確認可以不用 MCP；本輪 COS 瀏覽器實際匯入／編譯已成功，不冒稱 MCP 連線 |

**版本定義**：`v1_before` 是 2026-11-25 本輪依既有提案重建的精簡對照稿，不是以前投稿或前次 Overleaf 的真正歷史版本；`v2_after` 是本輪英語學術草稿。論文未提交期刊、未經同行評審。正式投稿格式、真實作者英譯姓名／單位以及文獻書目仍需由團隊確認。

## 核驗記錄

1. `PYTHONUTF8=1 .venv\Scripts\python.exe scripts\verify_dic4_paper.py`（PowerShell 預先設定 `$env:PYTHONUTF8='1'`）：**exit 0／STATIC_CHECK_PASS**。核對引用 keys、LaTeX 基本結構、章節與封存 7/14 日數值。原始紀錄：`outputs/dic4_20261125/static_check.log`。
2. `tools\openspec\node_modules\.bin\openspec.cmd status --change dic4-overleaf-paper`：**exit 0／4/4 artifacts**。原始紀錄：`outputs/dic4_20261125/openspec_status.log`。
3. `tools\openspec\node_modules\.bin\openspec.cmd validate dic4-overleaf-paper --strict --no-interactive`：**exit 0／Change is valid**。原始紀錄：`outputs/dic4_20261125/openspec_validate.log`。
4. 在本人已登入 Overleaf 的 Chrome 執行 ZIP upload，專案生成並編譯後確認 `Compile finished`，PDF 視圖顯示 `1/5` 至 `5/5`。實際取得 PDF（`%PDF-`，HTTP 200、application/pdf），複製到上列實體路徑。
5. 以本機 `python outputs\dic4_20261125\render_inspect_pdf.py`：**exit 0／5 頁**。各頁 426 / 415 / 413 / 435 / 129 個文字單詞；無文字座標超出頁面。每頁輸出 `outputs/dic4_20261125/pdf_pages/page_1.png` 至 `page_5.png`，已逐張實際目視。結果：未見超界、裁切、主要內容重疊；第 5 頁僅含 References，頁面留白多，但完整可讀。紀錄：`outputs/dic4_20261125/pdf_inspect.log`。
6. LaTeX 匯入 ZIP：`paper/dic4/v2_after_overleaf.zip`，僅 `main.tex`、`references.bib`、`before/draft_before.tex`、`before/references.bib` 四個檔案，排除密鑰與私有資料。

## 摘要數據與限制

| horizon | public test n | model macro-F1 | momentum macro-F1 | model return MAE | no-change return MAE | rising recall |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 7 天 | 2,085 | 0.4218 | **0.4226** | 0.0664 | **0.0436** | 16/158 |
| 14 天 | 1,859 | 0.4169 | **0.4306** | 0.0983 | **0.0748** | 23/268 |

以上都是封存公有市場實驗，不是個別店家的準確率，並未證明 ML 較簡單法有效或省錢。真店同品項同規格配對 A/B 評估尚未做；B 規則權重 0.3 為固定假設，不是訓練結果。沒有另外重跑模型。篇章引用來源中 R01–R03 仍限原本摘要／索引級別；英語書目有工作譯名，投稿前再逐項核對。

## 帳號／登入與待辦

- **Overleaf 登入已完成**，不必再註冊。雲端編輯器連結：`https://www.overleaf.com/project/6b06bd77157dbfcfac3cf914`。
- **GitHub 登入與推送已完成**：使用者於 Chrome 登入 `prometheans152`，本機 Git 透過已設定的 Credential Manager 將 DIC4 17 個檔案推送至獨立分支，並建立 PR #2。PR 保留為 OPEN，未合併 `main`；主工作目錄的 unrelated dirty changes 保留。
- **Overleaf MCP 不需要**：依使用者明確回覆不再另接 MCP；COS 瀏覽器的實際上傳與編譯足以滿足此輪可操作需求，無須第三方存取登入憑證。
- 課堂 iLearning/正式投稿（若有）**未提交**；白板無足夠證據確認當屆精確上傳期限／投稿期刊。

## Git 工作區保護

作業前基準：HEAD `d15384f`、branch `main`，既有 README / TASKS / design / rolling history 等多筆 dirty 和 untracked 檔。**主工作樹未進行 commit、push、reset 或 clean，也沒有切換 `main`；保留原本 dirty 檔。**為避免混入其他改動，另於忽略輸出區建立獨立 Git worktree，僅對本次 DIC4 17 個檔案提交（初始 commit `33ad04d0fcc43b5d31de02aca78cf05b9b92fb5b`）並推送新分支，PR #2 留待審查。所有本輪交付內容位於 `paper/dic4/`、`docs/dic4/`、`openspec/changes/dic4-overleaf-paper/`、`scripts/verify_dic4_paper.py`，渲染及診斷在忽略的 `outputs/dic4_20261125/`。未改模型／部署／資料，也未將 DIC3 未追蹤工作混入 PR。
