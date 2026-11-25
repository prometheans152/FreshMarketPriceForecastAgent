# DIC4｜任務與驗收

## 1. 來源與範圍
- [x] 1.1 實讀 DIC4 原始白板 JPEG
- [x] 1.2 核對 DIC3 提案、根設計、封存測試數值及 Git 工作區既有變更
- [x] 1.3 制定可編輯的 v1／v2 分離策略及不碰模型／部署邊界

## 2. 論文草稿
- [x] 2.1 建立 v1_before/main.tex 與 references.bib 作本輪工作初稿
- [x] 2.2 建立 v2_after/main.tex、references.bib：研究、方法、負向結果、限制
- [x] 2.3 修訂前後對照與文獻來源層級註記
- [x] 2.4 數字、LaTeX 基本結構、引用與結果分母通過自動核對（`scripts/verify_dic4_paper.py`，exit 0）
- [x] 2.5 產出 ZIP，Overleaf 真正編譯、檢查 PDF 與錯誤（5 頁；逐頁渲染核查，exit 0）

## 3. 工作流程
- [x] 3.1 建立 DIC4 OpenSpec proposal、design、specs、tasks
- [x] 3.2 CLI 嚴格驗證通過、保留原始測試輸出（4/4 artifacts；validate --strict exit 0）
- [x] 3.3 使用隔離 worktree 與精確檔案範圍完成 GitHub commit/push；已開 PR #2，未合併 `main`，原主樹 dirty changes 保留
- [x] 3.4 使用者允許省略非必要 Overleaf MCP；COS Browser 已完成真正匯入／編譯，沒有虛報 MCP 連線

## 4. 交付
- [x] 4.1 Overleaf 專案已建立、可見並能產出 PDF（`https://www.overleaf.com/project/6b06bd77157dbfcfac3cf914`）
- [x] 4.2 最新證據／待辦／本機實體路徑與環境差異報告（`docs/dic4/ACCEPTANCE_REPORT.md`）
