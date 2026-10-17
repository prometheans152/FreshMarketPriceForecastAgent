# 期中提案 v7 來源定位

## [D1]
臺中市政府公有零售市場每日蔬果價格表，data.gov.tw資料集84539；https://data.gov.tw/dataset/84539 。使用既有2026-10-03快照，不重新下載。

## [D2]
outputs/proposal_delivery/run3_20261004_01/stats_master.json: descriptive/splits/purge；2026-10-08本輪唯讀重核一致。

## [E1]
outputs/evaluation/public/public_test_results.json: horizons.h=7 / h=14；SHA256 2d28acd2f2c3e5ce566b9095c6a85477db8faf858d9ce29e974caaedc25674b8。固定測試列，未重算模型輸出、未重訓。

## [E2]
outputs/evaluation/public/public_test_results.json: by_crop；同一封存測試的分品項描述。

## [M1]
docs/LABEL_CONTRACT.md；src/aiot_price/data/labels.py；docs/proposal_v5/PROPOSAL.md。h=7/14個日曆日；t為本次可信報價基準日；缺到期正價格者無標籤。

## [M2]
src/aiot_price/models/store_adapter.py: ALPHA_EXPERIMENTAL=0.3；docs/STORE_DATA_PROTOCOL.md。A為乘法錨定；B為固定規則，不是學得的增益。

## [M3]
outputs/training/training_results.json；models/releases/0.1.0/manifest.json；src/aiot_price/models/train.py。候選Ridge、RFRegressor、HGBRegressor、DummyMajority、HGBClassifier；12個數值特徵＋crop_id one-hot，無市場one-hot。

## [S1]
outputs/proposal_delivery/run3_20261004_01/stats_master.json: purge.segments。成熟日=t+h+1；7天清除帶8日、14天15日。

## [A1]
src/aiot_price/api/app.py: /forecast, /agent/query, /records；src/aiot_price/agent/tools.py: AgentTools（get_market_quote、post_forecast 兩工具）＋ToolCallLimiter＋parse_query；src/aiot_price/models/predict.py: ForecastEngine；prediction_records: private/predictions。依既有原型整理；save_record 尚未封裝為 AgentTool（/records 由 Web 另呼）。

## [DEP1]
deploy/docker/oracle/ORACLE_DOCKER_OPERATIONS.md（Oracle Docker：網頁＋ForecastEngine，61品項）；deploy/cloudflare-workers-mcp/MCP_TOOL_CONTRACT.md 與 src/contracts.js（2工具、格式檢查、限流、回傳核對）；docs/deployment/POOLED_ML_MODEL_CARD_V1.md（57品項HGB，測試MAE未勝不變價）；2026-10-17 新Worker real-remote-acceptance 6/6 PASS。

## [U1]
outputs/e2e/ui_ab_mobile_390x844.png，2026-10-03本機原型截圖。只裁出上方7天A/B結果區並明示裁切，未改內部數字、未偽造新查詢。

## [P1]
docs/proposal_v5/PROPOSAL.md；docs/CONTRIBUTIONS.md；TASKS.md。使用者2026-10-04指示產品代理人整合與SERVER暫緩；2026-10-08指示Proposal v5第一階段（文件與簡報，不改產品程式）。

## [R01]
陳泯宏（2024），《國產大宗蔬菜價格預測模型之比較》，臺灣大學統計碩士學位學程。DOI 10.6342/NTU202400875；https://tdr.lib.ntu.edu.tw/handle/123456789/92775 。沿用既有摘要全文查核，未讀全文。

## [R02]
李岱鑫（2015），《高雄果菜運銷公司高麗菜批發價格預測之研究—蒐集私有資料的價值》，清華大學。https://etd.lib.nycu.edu.tw/cgi-bin/gs32/hugsweb.cgi?o=dnthucdr&s=id%3D%22GH02102077503%22.&searchmode=basic 。沿用書目與摘要查核；實際評估指標仍UNKNOWN。

## [R04]
農委會×財政資訊中心（2018）農業大數據平台：電子發票農產品零售價格估計。農傳媒報導《從29億張電子發票撈蛛絲馬跡…》https://www.agriharvest.tw/archives/12897 ；報導全文實讀，平台未登入。

## [R03]
林沂臻（2017），《應用希爾伯特-黃變換之菜價預測》，中山醫學大學碩士論文（NDLTD 105CSMU5585004）。沿用索引摘要查核；全文未取得。

## [R07]
YuehChun（2025），NCHU-Data-Mining-Project：氣候×台灣蔬菜價格探勘，GitHub repo（2025-05更新）https://github.com/YuehChun/NCHU-Data-Mining-Project 。repo+README層級。

## [R10]
農糧署（2026），115年度補助計畫公告：結合生成式AI與預測式機器學習於農產品產銷決策支援架構之先導研究（115農科-4.4.1-糧-02）https://www.afa.gov.tw/cht/index.php?act=download&ids=47334 。公告PDF全文實讀；公告非成果。

## [R05]
flux6lab，白菜即時官方頁 https://cabbagelive.com/ 。沿用已讀產品文案：中長期趨勢預測／零售換算。未安裝實測，不把文案當成效果證據，未載明功能保持未知。

## [R06]
鹿中創客，農產分析Google Play頁 https://play.google.com/store/apps/details?id=com.bvc_dev_team.androidapp&hl=zh-TW 。沿用已讀文案：輸入購買價、換算及當日行情比對；未安裝實測。

## [H17]
同課程Team17，《蔬果價格預測：LightGBM的最佳採購指南》（2025），本機歷屆/AIoT_歷屆期末簡報/regular_ii/Team17_蔬果價格預測_LightGBM採購指南.pdf。2026-10-08本輪第一手逐頁影像閱讀11/15頁（第1–4、7–12、15頁）；第5、6、13、14頁主題依同批逐頁筆記補足。只依作者簡報，不是已獨立重現的研究結果。

## [W1]
王鎬杰（2010），《近年颱風、豪雨後批發市場蔬菜交易價量變動分析》，農糧署《農政與農情》第219期；https://www.moa.gov.tw/ws.php?id=22086 。官網全文實讀（2026-10-04）；2004–2009全台批發週均價之歷史統計，非本案期間地區。

## [N1]
公視新聞2025-08-13「豪雨、颱風導致菜價上漲 台北傳統市場1把蔥380元」https://news.pts.org.tw/article/765375 。官網原文實讀；早於本案資料期間（2025-10-04起），僅消費端歷史背景。

## [G1]
docs/proposal_v5/DEEP_RESEARCH.md（五思維／三爭論／十問題，含證據與推理）；docs/proposal_v5/ARTICLE_SUMMARY_TABLE.md（八欄表10件＋來源層級）。

## [AD1]
docs/proposal_v5/AGENT_DESIGN.md：架構五群組①–⑤、工具層CURRENT／PROPOSED對照（get_market_quote/post_forecast現況；save_record工具化屬Proposed）、安全約束11條、D1–D9流程圖（節點標狀態）、Algorithm 1（主講10步＋完整41行）與Pseudocode↔實作映射。

## [C1]
會議錄音 10.txt:1710–1718、1890–1916（模型＋Domain Agent要求）；教授L4-1 https://app.notion.com/p/AIoT-DA-L4-1-Proposal-1-3ebc4752981180d8842fd7e253962c4e 。沿用已讀正文與逐字稿。

## [DD1]
docs/proposal_v5/DESIGN_DELTA.md：v5與根目錄design.md之沿用／新增／待同步／未來分界；本輪不覆寫正式design.md。

## [STYLE]
沿用v4簡潔白底風格（simple_v4），參考Team17第7–10頁資料與結果安排、GUARD總覽與局部說明、LSTM簡潔視覺、蜜蜂健康Related Work論述。不複製他組數據、圖片、成果或新功能。