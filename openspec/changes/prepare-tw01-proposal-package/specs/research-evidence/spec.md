# research-evidence Specification

## ADDED Requirements

### Requirement: 主張可追溯
每個研究主張附數字時，系統「文件與投影片」SHALL 提供：來源路徑（或 URL/DOI）、JSON key／CSV 欄／頁次、數值與單位、主張狀態。

#### Scenario: 引用模型成績
- **WHEN** 文稿引用模型 macro-F1
- **THEN** 該數值可在 outputs/evaluation/public/public_test_results.json 對應 key 重算核對
- **AND** 同時並列 flat 與 momentum 基線

#### Scenario: 前作僅讀摘要
- **WHEN** 某前作只取得摘要層級
- **THEN** 比較欄標 UNKNOWN，不得寫成「該文獻無此功能」

### Requirement: 負向結果保留
本能力要求文件與投影片 SHALL 在主講內容並列負向結果。
#### Scenario: 點估計未勝基線
- **WHEN** 呈現報酬 MAE
- **THEN** 明示「未優於不變價基線」於主講頁，不得只藏附錄

### Requirement: 未驗證能力標示
本能力要求未驗證主張 SHALL 明示狀態與待驗證條件。
#### Scenario: B 同店增益
- **WHEN** 描述 B 模式（上週價輸入）
- **THEN** 標示「α=0.3 固定規則、未經真店到期價驗證」
