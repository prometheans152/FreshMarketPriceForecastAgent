# Design: prepare-tw01-proposal-package

## Context
本批是文件／規格／簡報變更，不動產品程式。資料與數字來自凍結工件（manifest、training_results、public_test_results），不重訓。

## Goals / Non-Goals
- Goals：P1–P6 六包可交付；主張可追溯；PPTX/PDF 可用。
- Non-Goals：代理人修復、SERVER 部署、真店實驗、模型重訓、fixtures 重生成。

## Planned Changes
1. 新增 docs/ 下五份研究文檔（見 tasks 2.x/3.x）。
2. 重整根目錄 design.md（保留歷史段、新增現況分層）。
3. slides/ 目錄：製作程式（source/）、匿名圖表（assets/）、成品 PPTX/PDF。
4. 證據：outputs/proposal_delivery/run1_20261004/（claims_evidence、渲染檢查、CLI 紀錄）。

## Migration Plan
- 舊 FINAL_REPORT/FINAL_SLIDES 保留為歷史稿，檔首加入口指向 PROPOSAL_REPORT；不刪不改內容。
- design.md 重整以「現況（2026-10-04）」段落置頂，舊草案降為歷史附錄。

## Open Questions
- 組員名單／日期／當屆期末格式：投影片對應欄位標「待填」。
