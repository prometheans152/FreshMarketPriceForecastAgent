# DIC4｜GitHub + OpenSpec 工作流

## Repository
既有遠端：`origin https://github.com/prometheans152/FreshMarketPriceForecastAgent.git`。
本輪應把新增的 `paper/dic4/`、`docs/dic4/`、`openspec/changes/dic4-overleaf-paper/`（及任何核對腳本）視為獨立審核範圍。

## 目標（Goal）
使用既有 FMPA 作業成果撰寫一份可在 Overleaf 編輯的論文草稿，保留修訂前後的差異，對研究證據與產品狀態採保守表述。

## 設計（Design）
- `paper/dic4/v1_before/` 和 `paper/dic4/v2_after/` 分開保存。
- 經本機審核後僅以 v2 的兩個 LaTeX 原始檔打包 Overleaf ZIP。
- 由 OpenSpec change `dic4-overleaf-paper` 定義需求和可驗收情境。
- LaTeX 源碼可在本機 Git 追溯；Overleaf 專案是同步的編輯副本。
- 本機 dirty main 不可自動 `git add -A`、`reset`、`clean` 或覆寫歷史文件。

## 任務（Tasks）
1. 核對教授白板、DIC3 現有文稿及封存評估。
2. 撰寫 v1 工作基準、v2 修改稿及修訂矩陣。
3. OpenSpec spec-driven change，CLI strict validate。
4. 核對數值、編譯／Overleaf 目視及檔案驗收。
5. 登入本人 Overleaf 後匯入 v2，確認雲端可見與 PDF。
6. 若要 GitHub 留痕，僅對本輪新增的路徑做範圍內 commit/push；未取得使用者明確推送授權前保留本機。
7. Agent／Overleaf MCP 需使用可驗證的授權整合；無官方 MCP 時不可假稱已接通第三方工具。

## 連結
OpenSpec: `openspec/changes/dic4-overleaf-paper/`；成品位置：`paper/dic4/`。不把帳號、token 或 Overleaf session 儲存在 GitHub 文件。
