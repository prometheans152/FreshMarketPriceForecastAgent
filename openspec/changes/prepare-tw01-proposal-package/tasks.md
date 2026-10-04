# Tasks

## P1 研究動機與研究問題（原 D44 首輪）
- [x] 1.1 完成問題證據表與至少 3 項可查客觀證據
- [x] 1.2 完成 RESEARCH_MOTIVATION.md 與 RQ1–RQ3

## P2 相關研究與差異（原 D44 首輪）
- [x] 2.1 重組關鍵前作為固定欄位矩陣（首輪：依 2026-10-03 查核重組，未新增檢索——已如實記錄）
- [x] 2.2 新增 RESEARCH_GAP.md 與 REFERENCES.md（[R01…] 編號）

## P3 三項貢獻與研究稿（原 D44 首輪）
- [x] 3.1 完成 CONTRIBUTIONS.md（C1–C3）
- [x] 3.2 完成 PROPOSAL_REPORT.md（A–Z）

## P4 設計藍圖（原 D44 首輪）
- [x] 4.1 重整 design.md（現況藍圖置頂＋歷史附錄保留）

## P5 OpenSpec 管理（原 D44 首輪）
- [x] 5.1 初始化 openspec（局部 CLI 1.14.0，`tools/openspec/`；init --tools none --language zh-TW）
- [x] 5.2 同步 specs 並執行 validate --strict（通過）

## P6 正式投影片（原 D44 首輪）
- [x] 6.1 產出 PPTX（主講15頁＋附錄4頁）與 PDF（各19頁；v1）
- [x] 6.2 SLIDE_NOTES.md 逐頁講稿＋渲染逐頁檢查（v1 render_review：rev2 19/19 PASS）

## D44-R01–R06 修訂輪（2026-10-04；依 d44_independent_6eb4adf 審查）
- [x] R01 校正新聞日期與證據範圍（公視實為 2025-08-13 楊柳颱風；王鎬杰 2010/2004–2009 批發；2026-07 兩則撤回；機率→歷史比例；45→85 成因不作主張）
- [x] R02 前作實查（R01 摘要全文/R02 書目摘要/R04/R05 官網/R06 商店頁實讀；R08/R09 降待查線索；回測/前瞻分欄；移除無範圍否定與「已建立並開放」）
- [x] R03 統一數字口徑（stats_master.json＋claims_master.csv 27 列；10.5%/16.6% 正式值；364/905 母體標示；12特徵+one-hot；HGBClassifier 候選；`=7天` 標籤修正）
- [x] R04 PROPOSAL_REPORT 補完整敘事（T=參數分析/U=主要結果對照修正；前作比較表入主稿；A/B 例標教學計算；−0.1% 接近 0 非門檻；混淆矩陣頁碼 17）
- [x] R05 design.md 修正（架構①–⑤分組編號＋端點＋連線；真實清除帶兩段 695+691=1,386 列；錨定命題 [p(1+r)−p]/p=r；S01–S09 定位為自驗暫緩）
- [x] R06 同源交付（三腳本參數化防覆寫；notes_v2.json 單一底稿→PPT 備註+SLIDE_NOTES.md；v2 PPTX/PDF 19 頁；渲染＋視覺驗收；製作工具測試 15/15；CLI 重跑存證）

## 邊界（不變項）
- 不重訓、不調參、不改封存評估與 fixtures、不修改 src/tests/web/contracts。
- 代理人/Hermes/GLM/SERVER 相關修復不在本 change 範圍。
- 本 change 之 R01–R06 勾選為 GLM 執行者自驗；ChatGPT 獨立複審另計，格式驗證通過≠內容驗收。
