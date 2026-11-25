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
6. GitHub 已以隔離 worktree 對本輪 DIC4 17 個檔案進行 scoped commit/push；PR #2 為獨立審核入口，`main` 沒有因此被合併或改寫。
7. Overleaf MCP 已依使用者意願省略；實際使用 COS Browser 操作，並已驗證 Overleaf 匯入與 PDF 編譯。

## 連結
GitHub PR：`https://github.com/prometheans152/FreshMarketPriceForecastAgent/pull/2`；分支：`dic4/overleaf-paper-20261125`；OpenSpec：`openspec/changes/dic4-overleaf-paper/`；成品：`paper/dic4/`。不把帳號、token 或 Overleaf session 儲存在 GitHub 文件。
