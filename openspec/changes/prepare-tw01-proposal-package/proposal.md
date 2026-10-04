# Proposal: prepare-tw01-proposal-package（TW01 研究提案、設計與正式投影片）

## Why

本 change 對應 D44 工作包：完成菜價題目的研究動機、相關研究與差異、三項主要貢獻、根目錄 design.md、OpenSpec 管理與正式投影片（P1–P6）。代理人整合暫緩，不作為本批前置。

## What Changes

- 新增研究文稿：RESEARCH_MOTIVATION、RESEARCH_GAP、REFERENCES、CONTRIBUTIONS、PROPOSAL_REPORT（A–Z 結構）。
- 重整根目錄 design.md 為現況／本輪／未來分層的設計藍圖。
- 建立 openspec/ 管理與本 change 的 specs/tasks。
- 產出 slides/ 下正式可編輯 PPTX、PDF、講者備註與渲染檢查證據。

## Capabilities

### Capability: research-evidence
研究主張與數字須可追溯到來源（封存評估 JSON/CSV、官方統計或原文文獻），並標示狀態（已驗證／初步／待驗證／暫緩）。

### Capability: proposal-delivery
提案交付（文檔與投影片）須一致引用同一組主張與數字，負向結果保留在主講內容，未完成能力不得寫成已驗收。
