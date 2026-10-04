# Tasks

## P1 研究動機與研究問題
- [x] 1.1 完成問題證據表與至少 3 項可查客觀證據
- [x] 1.2 完成 RESEARCH_MOTIVATION.md 與 RQ1–RQ3

## P2 相關研究與差異
- [x] 2.1 重組 10 件關鍵前作（5 件 2021–2026）為固定欄位矩陣
- [x] 2.2 新增 RESEARCH_GAP.md 與 REFERENCES.md（[R01…] 編號）

## P3 三項貢獻與研究稿
- [x] 3.1 完成 CONTRIBUTIONS.md（C1–C3）
- [x] 3.2 完成 PROPOSAL_REPORT.md（A–Z）

## P4 設計藍圖
- [x] 4.1 重整 design.md（現況藍圖置頂＋歷史附錄保留）

## P5 OpenSpec 管理
- [x] 5.1 初始化 openspec（局部 CLI 1.14.0，`tools/openspec/`；init --tools none --language zh-TW）
- [x] 5.2 P3/P4 完成後同步 specs 並執行 validate --strict（通過；證據 openspec_cli_evidence.txt）

## P6 正式投影片
- [x] 6.1 產出 PPTX（主講15頁＋附錄4頁）與 PDF（各19頁；render_meta.json）
- [x] 6.2 SLIDE_NOTES.md 逐頁講稿＋渲染逐頁檢查（render_review.md：rev2 19/19 PASS）

## 邊界（不變項）
- 不重訓、不調參、不改封存評估與 fixtures、不修改 src/tests/web/contracts。
- 代理人/Hermes/GLM/SERVER 相關修復不在本 change 範圍。
