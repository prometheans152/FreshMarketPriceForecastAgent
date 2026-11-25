# dic4-workflow Specification

## ADDED Requirements

### Requirement: Overleaf 可重現匯入與編譯
交付 SHALL 具可匯入 Overleaf 的 ZIP，且不含私鑰、私人店家資料或模型；若實際雲端編譯完成，SHALL 保留其實際 PDF 和核驗紀錄，不得用本機文字檢查冒稱雲端成功。
#### Scenario: 使用者已登入 Overleaf
- **WHEN** Agent 匯入論文 ZIP 並觸發重新編譯
- **THEN** 專案名稱、可見 LaTeX 原始碼、BibTeX 來源、PDF 產出與錯誤狀態分別列出
- **AND** 未編譯成功時標示阻擋原因。

### Requirement: 工程流程以 OpenSpec 管理
DIC4 change SHALL 同時有 proposal、design、specs、tasks，並執行 CLI strict validate；結果 SHALL 保留真實退出碼。
#### Scenario: GitHub 工作流程檢查
- **WHEN** 查核本地 change
- **THEN** CLI 可解析本 change 並檢查需求情境
- **AND** Git 變更範圍局限 DIC4，不將其他既有 dirty 檔案混入提交。

### Requirement: MCP 工具與登入權限誠實
只有實際成功的 Overleaf MCP 連線才能標示 Connected；若僅以瀏覽器操作 Overleaf，SHALL 明示 Browser-based 而非 MCP。使用者登入或授權由本人完成，秘密不得記錄。
#### Scenario: MCP 連線尚未驗證
- **WHEN** 查不到官方 MCP 或現有第三方工具未授權
- **THEN** 可以完成 LaTeX、瀏覽器匯入與 OpenSpec 文件
- **AND** 將 MCP 接線記為待確認，不偽造工具測試。
