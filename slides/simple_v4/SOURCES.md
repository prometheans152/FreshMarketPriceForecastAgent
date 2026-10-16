# TW01 v4 來源定位

## [D1]
臺中市政府公有零售市場每日蔬果價格表，data.gov.tw資料集84539；https://data.gov.tw/dataset/84539 。使用既有2026-10-03快照，不重新下載。

## [D2]
outputs/proposal_delivery/run3_20261004_01/stats_master.json: descriptive；data/processed/features_labels.parquet的既存direction。含各時間區的歷史市場×品項×起算日配對；排除insufficient_data，正式±5%邊界含eps=1e-9。

## [E1]
outputs/evaluation/public/public_test_results.json: horizons.h=7 / horizons.h=14；SHA256 2d28acd2f2c3e5ce566b9095c6a85477db8faf858d9ce29e974caaedc25674b8。固定測試列，未重算模型輸出、未重訓。

## [E2]
outputs/evaluation/public/public_test_results.json: by_crop；同一封存測試的分品項描述。

## [M1]
docs/LABEL_CONTRACT.md；src/aiot_price/data/labels.py；docs/PROPOSAL_REPORT.md。h=7/14個日曆日；t為本次可信報價基準日；缺到期正價格者無標籤。

## [M2]
src/aiot_price/models/store_adapter.py: ALPHA_EXPERIMENTAL=0.3；docs/STORE_DATA_PROTOCOL.md；docs/PROPOSAL_REPORT.md。A為乘法錨定；B為固定規則，不是學得的增益。

## [M3]
outputs/training/training_results.json；models/releases/0.1.0/manifest.json；src/aiot_price/models/train.py。候選Ridge、RFRegressor、HGBRegressor、DummyMajority、HGBClassifier；12個數值特徵＋crop_id one-hot，無市場one-hot。

## [S1]
outputs/proposal_delivery/run3_20261004_01/stats_master.json: splits, purge.segments；outputs/splits/split_list.csv。成熟日=t+h+1。图示日期为保留樣本涵蓋期，不表示每一天每個期限都保留。

## [A1]
src/aiot_price/api/app.py: /forecast, /agent/query, /records；src/aiot_price/models/predict.py: ForecastEngine；src/aiot_price/api/prediction_records.py: private/predictions。依既有原型整理的功能關係圖，不是完整系統驗收宣稱。

## [U1]
outputs/e2e/ui_ab_mobile_390x844.png，2026-10-03本機原型截圖。本版只裁出上方7天A/B結果區並明示裁切，未改內部數字、未偽造新查詢。

## [P1]
docs/PROPOSAL_REPORT.md: RQ1–RQ3、C1–C3及後續工作；docs/CONTRIBUTIONS.md；TASKS.md。使用者2026-10-04指示產品代理人整合與SERVER暫緩。

## [R01]
陳泯宏（2024），《國產大宗蔬菜價格預測模型之比較》，臺灣大學統計碩士學位學程。DOI 10.6342/NTU202400875；https://tdr.lib.ntu.edu.tw/handle/123456789/92775 。沿用既有摘要查核，未讀全文。

## [R02]
李岱鑫（2015），《高雄果菜運銷公司高麗菜批發價格預測之研究—蒐集私有資料的價值》，清華大學。https://etd.lib.nycu.edu.tw/cgi-bin/gs32/hugsweb.cgi?o=dnthucdr&s=id%3D%22GH02102077503%22.&searchmode=basic 。沿用書目與摘要查核；實際評估指標仍UNKNOWN。

## [R05]
flux6lab，白菜即時官方頁 https://cabbagelive.com/ 。沿用已讀產品文案：趨勢預測／零售換算。未安裝實測，不把文案當成效果證據，未載明功能保持未知。

## [R06]
鹿中創客，農產分析Google Play頁 https://play.google.com/store/apps/details?id=com.bvc_dev_team.androidapp&hl=zh-TW 。沿用已讀文案：輸入購買價、換算及當日行情比對；未安裝實測，其餘功能不作不存在的斷言。

## [H17]
同課程Team17，《蔬果價格預測：LightGBM的最佳採購指南》（2025），本機歷屆/AIoT_歷屆期末簡報/regular_ii/Team17_蔬果價格預測_LightGBM採購指南.pdf，第7–12頁；原頁 https://app.notion.com/p/Team-17-2d3c4752981180e7985ed1361620f46a 。只依作者簡報，不是已獨立重現的研究結果。

## [C1]
會議錄音 10.txt:535–573、787–899、1738–1764、2080–2097；教授L4-1 https://app.notion.com/p/AIoT-DA-L4-1-Proposal-1-3ebc4752981180d8842fd7e253962c4e 。沿用已讀正文與逐字稿；A–Z為內容對照，不是全部需放主畫面的逐字標題。

## [STYLE]
本版參考：LSTM澆水第4/14/22頁的簡圖與實物展示；蜜蜂健康第5–14頁的背景/動機/前作論述；GUARD節錄第4/5張的總覽與局部解釋；Team17第7–10頁的資料與結果安排。不複製他組數據、圖片、成果或新功能。