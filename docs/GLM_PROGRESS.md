# GLM執行進度與交接紀錄

更新日期：2026-10-03（GLM第一輪執行）。

## 當前狀態

- **GLM第一輪完成 T01–T15、T17–T22 共21項（PASS），T16/T23 HOLD，T24–T36 依SERVER/到期資料等待。** 全部63項自動化測試通過（`.venv/Scripts/python.exe -m pytest tests/ -q` → 63 passed）。
- 主機分工不變：TRAIN_LOCAL（本機 Ryzen 7 5800X/32GB，有RTX 3080 ti但無CUDA toolkit、訓練用CPU）已完成資料、訓練、打包、本機API與網頁；SERVER_3090 缺連線資訊（見[SERVER_INVENTORY](SERVER_INVENTORY.md)）。
- 公開模型成績（封存測試，凍結清單SHA256 `4e136574…` 校驗通過）：h=7 rf_reg 方向 macro-F1 **0.422**（持平基線0.309）、h=14 hgb_reg **0.417**（基線0.295）；點回歸MAE **未優於**不變價基線（0.066 vs 0.044；0.098 vs 0.075）——已如實寫入所有輸出警示，不作點預測宣稱。
- 同店A/B（T16）HOLD：缺真實店價與到期真值；B模式為明示實驗性規則（α=0.3，未訓練未驗證）。機率/區間未校準一律不輸出（null）。
- 本輪5個subagent並行（T03環境、T05資料、T04查重、T10協議、T21網頁），產出由主對話核對後採用。

## 啟動時處理

GLM先查TASKS與本紀錄，再從第一個依賴已滿足的TODO開始。**下一輪可執行項**：T26代理人工具（可用本機API先行開發，SERVER實測後補T25基準）、T33報告準備（T15/T17結果已齊）。SERVER資訊到位後依序T23→T24/T25→T26→T27→T28→T29→T30/T31→T32→T33–T36。

## 執行紀錄

| 時間／TASK | 主機及輸入版本 | 實際操作、產出、hash與驗收證據 | 結果／限制 | 下一步 |
| --- | --- | --- | --- | --- |
| 2026-10-03 T01 | TRAIN_LOCAL | 逐字稿1710–1718等7段抽驗與COURSE_REQUIREMENTS一致；Notion再試仍JS空殼；建DELIVERY_CHECKLIST | PASS；當屆細則未確認 | 期末公告出現後補核 |
| 2026-10-03 T23 | — | SERVER_INVENTORY.md（已知/所缺/待使用者複製填寫清單） | HOLD：缺OS/位址/連線/目錄/端口/外網方案 | 使用者提供後續T24起 |
| 2026-10-03 T02 | TRAIN_LOCAL | project.yaml（品項/持平±5%/單位/B 7±2天）、forecast.schema.json、design §2.1、DECISIONS D34 | PASS；sanity值由T06補 | — |
| 2026-10-03 T03（subagent） | Win10 19045、Python 3.12.10 venv | 硬體查核（5800X/32GB/3080 ti 12GB但無CUDA toolkit→CPU訓練）；pyproject、requirements-lock、.env.example；venv＋乾淨環境重現安裝，import/讀檔/煙霧測試過；證據outputs/local_env/13檔 | PASS | — |
| 2026-10-03 T05（subagent） | 臺中官方API | 重新下載HTTP200、5,323,185B、SHA256 `172dffc76e82…`（與同日舊快照逐位元組相同＝當日未更新）；fetch_public.py（urllib免依賴、不覆蓋）、data_sources.yaml、DATA_CARD、provenance×2 | PASS；更多年度僅近一年滾動視窗 | 發布延遲實測待追蹤 |
| 2026-10-03 T04（subagent） | WebSearch/GitHub/商店頁 | 19作品實查：農產分析App（輸入現價比對當日行情）、農業大數據平台（29億筆電子發票零售預測，品項重疊）、白菜即時等；RELATED_WORK_MATRIX＋recheck補查段 | PASS；「現場輸入+t+7/14同店漲跌+到期驗證A/B」組合查核範圍內未見相同；單元件均有前作 | 期末報告引用 |
| 2026-10-03 T06 | venv | quality.py：0值905→缺測、無重複鍵、364日連續、(停)建國市場沿用價176 run密集→排除（凍結於prepare_data.py）；DATA_QUALITY_REPORT＋outputs/data_quality/ | PASS | — |
| 2026-10-03 T07–T09 | venv | labels/splits/features/schema＋LABEL_CONTRACT/splits.yaml＋tests 24項全過（手算例一致、防洩漏擾動測試、單位攔截）；prepare_data.py實跑→features_labels.parquet：train 13,009/val 3,855/test 4,680、凍結sha256 `4e136574…`、train成熟日2026-05-09<val起點斷言通過 | PASS；發布延遲假設1日未實測 | — |
| 2026-10-03 T10（subagent） | jsonschema 4.26 | STORE_DATA_PROTOCOL、store_record_schema.json＋範例（simulated標記）；20項負向測試正確拒絕 | PASS；採集負擔待使用者確認 | 使用者開始記錄時啟用 |
| 2026-10-03 T11–T13 | venv CPU、seed42 | 3基線＋Ridge/HGB/RF/分類候選實訓練（outputs/training/training_results.json、models/candidates/）；選型標準看測試前凍結：h=7 rf_reg（val F1 0.4334）、h=14 hgb_reg（0.4591）；MODEL_SELECTION | PASS；點MAE未優於基線如實記；up召回低 | — |
| 2026-10-03 T14 | venv | store_adapter：B可比性檢查（7±2天/單位換算/規格一致）＋實驗規則α=0.3；STORE_ADAPTATION_METHOD；test_store_adapter 10項過 | PASS；B未訓練未驗證（輸出明示） | T16真值到期後驗證 |
| 2026-10-03 T15 | venv | evaluate.py一次性封存測試（凍結hash校驗過）：h=7 acc 0.766/F1 0.422、h=14 0.711/0.417 vs 持平基線0.309/0.295；分品項表＋逐列test_predictions.csv可重算 | PASS；僅公開市場均價目標 | T17/T18引用 |
| 2026-10-03 T17 | venv | test_prediction_limits：來源舊不退回起點、歷史as-of特徵、B降級保A、sanity超界警示不拒絕、機率/區間null；ERROR_ANALYSIS | PASS；up召回≈10%列最大限制 | — |
| 2026-10-03 T18 | venv | package.py→models/releases/0.1.0（manifest：模型hash/切分/能力邊界/價格sanity；public_history.parquet；fixtures）；model-manifest.schema.json、MODEL_CARD；--check-fixtures 3/3 | PASS | T24 SERVER parity用 |
| 2026-10-03 T19–T20 | venv | predict.py（別名解析/單位換算/A/B/降級/警示；~200ms）＋predict_local.py；FastAPI /health /metadata /forecast（重用引擎）；tests/api 12項真模型包測試過 | PASS；僅綁127.0.0.1 | T28對外防護、T24跨主機 |
| 2026-10-03 T21（subagent＋主對話實測） | 瀏覽器390×844＋本機API:8010 | web/三檔（無CDN）＋UI_FLOW；實測：A模式7/14渲染、開上週（28元/09-26）→A/B並排含實驗性警示與資料截止天數、南屯市場→stale_data_unusable錯誤正確顯示、恢復查詢；截圖outputs/e2e/ui_ab_mobile_390x844.png | PASS；空值/鍵盤細節屬代碼審查 | T32真手機外網補 |
| 2026-10-03 T22 | venv | prediction_records.py（凍結預測供T16到期核對、模擬拒收、匿名匯出）；PREDICTION_RECORDS；tests 4項過 | PASS | 使用者保存預測時啟用 |
| 2026-10-03 T16 | — | 機制就緒（T10協議/T14路徑/T22凍結），缺真實同店報價與7/14天到期真值 | HOLD，不因公開模型完成而PASS | 使用者記錄店價 |

每完成／失敗／阻塞一項，新增紀錄並同步TASKS狀態。詳細機器資訊與日誌放忽略目錄`outputs/`，此處引用必要摘要，不貼金鑰或私人明細。

## 全案完成核對

- [x] 公開資料與授權已重查、資料流程可重現（T05/T06，2026-10-03）。
- [x] TRAIN_LOCAL訓練與獨立測試已執行，有7／14日與基線結果（T12/T15）。
- [x] A／B的實作、訓練狀態與真同店效果分開，缺證據如實標示（T14 PASS、T16 HOLD）。
- [ ] 工件及前處理完整，TRAIN_LOCAL與SERVER版本／固定輸入輸出相符（本機fixtures 3/3；SERVER端待T24）。
- [ ] Qwen實際呼叫工具，回答忠於結果；錯誤與資料不足情境通過（T25–T27待SERVER）。
- [ ] SERVER實際運行，手機外網可用，服務重啟／回退已驗證（T29–T32待SERVER）。
- [ ] 私人資料／憑證沒有進入公開交付（private/、data/、models/、outputs/、recordings/均在.gitignore；提交前再掃描）。
- [ ] 當屆課程交付已核對並完成（T01完成核對；期末細則未確認；T33–T35待）。
- [ ] 最終獨立審查通過（T36待）。

## 待使用者提供

1. SERVER_3090：OS、位址、連線方式、專案目錄、已用端口、nvidia-smi/nvcc輸出、手機外網連線方案（[SERVER_INVENTORY](SERVER_INVENTORY.md)待填清單，可直接複製回覆）。
2. 真店驗證（T16）：是否願意依[STORE_DATA_PROTOCOL](STORE_DATA_PROTOCOL.md)記錄同店報價（店家數/品項/頻率），7/14天後回填到期價。
3. 組員、期末交付期限與格式（當屆Notion無法讀取，僅有逐字稿快照）。
4. GitHub／影片發布目標與授權範圍（T35）。
