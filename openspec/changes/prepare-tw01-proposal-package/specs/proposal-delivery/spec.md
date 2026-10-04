# proposal-delivery Specification

## ADDED Requirements

### Requirement: 跨文件一致
本能力要求所有交付物 SHALL 引用一致的數字與主張狀態。
#### Scenario: 數字一致性
- **WHEN** 同一主張出現在 PROPOSAL_REPORT、design.md 與投影片
- **THEN** 三處數值、單位與狀態一致（對照 claims_evidence.csv）

### Requirement: 正式投影片成品
本能力要求交付 SHALL 包含可編輯 PPTX、同名 PDF 與逐頁檢查證據。
#### Scenario: 可編輯交付
- **WHEN** 交付簡報
- **THEN** 提供 .pptx（可編輯文字/表格）與同名 .pdf
- **AND** 頁數相等、逐頁渲染檢查通過（無遮擋/裁切/亂碼）

#### Scenario: 講者備註
- **WHEN** 每頁投影片
- **THEN** SLIDE_NOTES.md 與 PPT 講者備註含講稿、來源與預估秒數

### Requirement: 範圍誠實
本能力要求交付 SHALL 如實標示暫緩與未驗證範圍。
#### Scenario: 代理人整合暫緩
- **WHEN** 描述代理人
- **THEN** 以現有介面原型呈現，未驗證能力列「未來擴充」，不宣稱已通過課程全部要求
