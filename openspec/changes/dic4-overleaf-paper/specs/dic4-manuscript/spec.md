# dic4-manuscript Specification

## ADDED Requirements

### Requirement: 可追溯修改前後論文草稿
DIC4 工作包 SHALL 具備兩個可編輯 LaTeX 版本，含 `main.tex` 及同目錄 `references.bib`，並提供具體修訂矩陣。修改前版本如於本輪重新建立，SHALL 明確註明並非歷史 Overleaf 修訂。
#### Scenario: 教授比較論文修改
- **WHEN** 查核 `v1_before` 和 `v2_after`
- **THEN** 兩版可分別開啟編輯且能對照 Abstract、Related Work、方法、結果和限制
- **AND** 修訂矩陣說明差異，不誤稱已向期刊投稿。

### Requirement: 報告數據需對封存結果一致
論文 SHALL 依原本 `public_test_results.json` 逐期限報告 test n、direction macro-F1、momentum macro-F1、relative-return MAE、no-change baseline 和上漲 recall；不得隱藏負向比較或以市場均價當店價真值。
#### Scenario: 核對量化結果
- **WHEN** 重新讀取 JSON 並對照論文表格
- **THEN** 7 日 n=2085、F1=0.4218<0.4226、MAE=0.0664>0.0436、up=16/158
- **AND** 14 日 n=1859、F1=0.4169<0.4306、MAE=0.0983>0.0748、up=23/268
- **AND** 所有 MAE 明示為市場相對變化誤差。

### Requirement: 研究狀態與文獻層級分離
論文 SHALL 有研究問題、來源、相關研究、方法、系統／Agent 邊界、公開市場實驗結果、前瞻真店驗證計畫、限制與結論。原研究只讀摘要/索引的文獻不可假稱全文實讀。
#### Scenario: 論文可供校閱
- **WHEN** 檢查修訂稿
- **THEN** RQ1 已有公開測試、RQ2 尚無店價到期、RQ3 尚缺全面 Agent 驗證分明
- **AND** B 的 alpha=0.3 為固定未訓練規則。
