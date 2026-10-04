# GLM執行進度與交接紀錄

## 最新排程：D44-R01–R06 修訂輪自驗完成（2026-10-04）

獨立審查（`outputs/audits/d44_independent_6eb4adf/`＋`d44_resume_6eb4adf_20261004_01/`）對 D44 首輪結論 Request changes 後，GLM 依 `docs/GLM_D44_R01_R06_REVISION_20261004.md` 完成六項修訂並**自驗**（不等於 ChatGPT 複審通過）；逐項證據見 [D44_REVISION_REPORT.md](D44_REVISION_REPORT.md)：

- **R01**：公視報導實為 **2025-08-13 楊柳颱風**（原稿 2026-09-14 誤）；農業部 219 期＝王鎬杰 2010／2004–2009 批發週均價（加適用範圍）；自由/UDN 2026-07 兩則七管道未尋得原文→撤回；「機率」→歷史配對比例；45→85 逐格複核且成因不主張。
- **R02**：R01 陳泯宏（摘要全文實讀：RMSE/MAD/MAPE/方向正確率已知）、R02 李岱鑫（正式題名/66週/下週批發/私有資料有價值）、R05 白菜即時官網（中長期趨勢預測+零售換算→撤回「都只看今天」）、R06 商店頁實讀；R08/R09 降待查線索、新增 R11 廖啜翔 2021 書目；矩陣拆歷史回測/前瞻到期欄；移除「無人」「已建立並開放」。
- **R03**：`run2/stats_master.json`（唯讀重算與補驗交叉核對一致）＋`claims_master.csv`（27 列）作單一數據源；正式值合併 10.5%/16.6%、絲瓜 12.7%/18.3%；浮點 abs>0.05 多 21 列邊界如實註記；364/905 母體標示；12特徵+品項one-hot；候選 DummyMajority/HGBClassifier；`=7天` 標籤修正。
- **R04**：PROPOSAL_REPORT 重寫為可獨立閱讀（摘要/導論/三類前作+比較表/PA–PM 含教學計算例/評估/結論）；T=參數分析（未執行）、U=主要結果對照修正；−0.1% 接近 0 非門檻；混淆矩陣頁碼=17。
- **R05**：design.md 架構①–⑤分組+`/forecast` `/agent/query` `/records` 端點+請求/回傳連線；成熟清除真實兩段（695+691=1,386 列/30 日）；錨定命題改 [p(1+r̂)−p]/p=r̂（sign 負≠down）；S01–S09 定位為第五輪自驗、暫緩不修不驗。
- **R06**：三支製作腳本參數化+防覆寫；`notes_v2.json` 單一底稿同源生成 PPT 備註與 SLIDE_NOTES.md；**v2 PPTX/PDF 各 19 頁**（pypdf 實讀核對；兩輪視覺驗收 19/19 PASS）；製作工具測試 15/15；README 重整為提案入口；AGENTS 同步；OpenSpec 17/17 tasks＋`validate --strict` exit 0（未 archive）。

保護：11 檔 SHA256 前後一致；src/tests/web/contracts/產品 configs 零修改；v1/run1/舊審查未覆寫。未做（如實）：影片未錄、GitHub/YouTube/發布待授權、組員與正式日期待填、乾淨環境重建未驗證。

## D44 首輪（歷史，2026-10-04）

使用者暫緩代理人，先以現有介面作展示。ChatGPT本次用COS讀完L4-1 A–Z可取得正文並檢視圖，重新對照逐字稿，寫入 [來源核對](PROPOSAL_SOURCE_AUDIT_20261004.md)、[執行計畫](PROPOSAL_DELIVERY_PLAN.md)、[GLM提示詞](GLM_PROPOSAL_HANDOFF.md)。

**2026-10-04 GLM 完成六包並通過驗收（[PROPOSAL_ACCEPTANCE.md](PROPOSAL_ACCEPTANCE.md)）**：
- P1 動機：[RESEARCH_MOTIVATION.md](RESEARCH_MOTIVATION.md)（5 項可查證據＋RQ1–RQ3）。
- P2 前作：[RELATED_WORK_MATRIX.md](RELATED_WORK_MATRIX.md)（10 件、UNKNOWN 12 處如實標）＋[RESEARCH_GAP.md](RESEARCH_GAP.md)＋[REFERENCES.md](REFERENCES.md)（[R01–R10]）。
- P3 貢獻：[CONTRIBUTIONS.md](CONTRIBUTIONS.md)（C1 已驗證／C2 待驗證／C3 初步）＋[PROPOSAL_REPORT.md](PROPOSAL_REPORT.md)（A–Z 完整稿，基線並列、負向保留）。
- P4 設計：根目錄 [design.md](../design.md) 重整為 §0–§5 現況藍圖＋歷史附錄。
- P5 OpenSpec：CLI 1.14.0 局部安裝（`tools/openspec/`）、change `prepare-tw01-proposal-package` 4/4 artifacts、11/11 tasks、`validate --strict` exit 0（[OPENSPEC_WORKFLOW.md](OPENSPEC_WORKFLOW.md)；證據 `outputs/proposal_delivery/run1_20261004/openspec_cli_evidence.txt`）。
- P6 投影片：`slides/TW01_菜價預測_研究提案與初步成果_v1.pptx`＋同名 PDF（各 19 頁＝主講 15＋附錄 4）；逐頁 PNG 渲染＋兩輪獨立視覺驗收，rev2 19/19 PASS（`slides_render/render_review.md`）；[SLIDE_NOTES.md](SLIDE_NOTES.md) 講稿主講約 11:15＋10 分鐘快版；6 張圖表由凍結 JSON 生成並標來源。
- 保護核對：6 個凍結工件 SHA256 不變；`public_test_results.json` 重算 = `2d28acd2…74b8`；`src/`、`tests/`、`web/`、`contracts/`、正式 configs 無修改；`claims_evidence.csv` 15 列回填文稿段落與頁碼。
- 本批未做（維持原狀態）：真店 T16、代理人後端（GLM API／Qwen／SERVER）、影片、發布、遠端推送。第五輪自報不代替 [第五輪獨立審查](../outputs/audits/round5_independent_2f7199e/REVIEW_2f7199e.md)，相關缺陷暫緩而非關閉。

更新日期：2026-10-04（GLM第五輪完成：S01–S09 全修＋Hermes 真介面；詳[第五輪報告](ROUND5_REPAIR_REPORT.md)）。

- **第五輪完成**：Hermes 0.19.0 真建構/真 dispatch/真工具追蹤（tool_complete_callback；無事後補算）；輸入忠實（TrustedContext 防改價/改日期/無中生有）；輸出事實 (mode,horizon,field,unit) 分離；保存不可變 ID＋simulated 隔離；隔離於 import 前生效；227 測試（乾淨環境同數）；凍結工件不變。**真 GLM 仍待金鑰設定。**

## 當前狀態

- **第四輪完成（2026-10-04）：** R01–R08 全修（192 項測試全過）；代理人三層就緒——`rule`（預設）／`glm_zai`/`glm_bigmodel`（OpenAI 相容真 tool-calling）／`qwen_local`（本機 Qwen3.8-27B，不自動切雲端）；框架可選官方 `hermes`（hermes-agent 0.19.0 已裝、白名單隔離、輸出同過真值驗證器）。GLM 金鑰未配置：待使用者提供平台/model ID/金鑰（AIOT_GLM_API_KEY）；真 GLM 呼叫與 Hermes chat 端到端待此。模型與封存評估未動（hash 見第四輪報告 §9）。
- **D41 方向（歷史，2026-10-04 早）：** 本機模型已確定 Qwen3.8-27B，新增 GLM API 可替換且先行使用；Hermes Agent 暫定（HARMES 的拼寫對應為助理解讀）。詳見 [代理人方向](AGENT_RUNTIME_DIRECTION.md)。本次只更新文件／需求設定，未接 API、未安裝 Hermes。
- **第三輪獨立審查結論仍為 Request changes：** `44dabe3` 原環境 134 項測試通過，但 R01–R08 尚未修復；[報告](../outputs/audits/2026-10-04_round3_independent/REVIEW_44dabe3.md)與重現證據保留。GLM 原「F01–F10 全數完成」只能當自報，不能当已通過審查。權重與封存評估未變，但 release fixtures 曾重生成，不能稱全部工件位元組不變。
- **第三輪 GLM 自報（歷史）：** 依[第二輪審查](reviews/ROUND2_7fdb43b_REVIEW.md)增加 36 項測試，98→134 項通過；原自報完成範圍以後續 R01–R08 審查修正為準。
- T26 依審查 F08 改 **DOING**（本機規則層完成；架構為規則調度＋Qwen 解釋，Qwen 實機與 tool_calls 生成架構待 T24/T25）；T22 補前端保存流程（/records＋UI，瀏覽器實測）；T16/T23 維持 HOLD。

- **第二輪（2026-10-03夜～10-04凌晨）新增：T26 PASS（代理人本機層）、T25/T27/T28/T30/T33/T34 DOING（本機/核實部分完成）、T16/T23 維持 HOLD。** 累計 98 項自動化測試全過。
- **代理人已可用**：`POST /agent/query`（確定性提取＋2有限工具＋可插後端；本機規則模式、SERVER 插 Qwen、Qwen 失敗自動降級）；網頁新增「用問的也可以」入口（實測截圖 outputs/e2e/ui_agent_mobile.png）。
- **Qwen 型號（T25／D41）：** 使用者已指定 Qwen3.8-27B；原「跑不動／9B首選／原意待確認」已被 D38 修訂及 D41 取代。量化檔、推論引擎與真 3090 測試仍待環境；先推進 GLM API 路徑。
- 第一輪完成 T01–T15、T17–T22 共21項（PASS），詳見下方紀錄。
- 主機分工不變：TRAIN_LOCAL（本機 Ryzen 7 5800X/32GB，有RTX 3080 ti但無CUDA toolkit、訓練用CPU）已完成資料、訓練、打包、本機API與網頁；SERVER_3090 缺連線資訊（見[SERVER_INVENTORY](SERVER_INVENTORY.md)）。
- 公開模型成績（封存測試，凍結清單SHA256 `4e136574…` 校驗通過）：h=7 rf_reg 方向 macro-F1 **0.422**（持平基線0.309）、h=14 hgb_reg **0.417**（基線0.295）；點回歸MAE **未優於**不變價基線（0.066 vs 0.044；0.098 vs 0.075）——已如實寫入所有輸出警示，不作點預測宣稱。
- 同店A/B（T16）HOLD：缺真實店價與到期真值；B模式為明示實驗性規則（α=0.3，未訓練未驗證）。機率/區間未校準一律不輸出（null）。
- 本輪5個subagent並行（T03環境、T05資料、T04查重、T10協議、T21網頁），產出由主對話核對後採用。

## 啟動時處理

GLM 開發執行者先查 TASKS、D41、[代理人方向](AGENT_RUNTIME_DIRECTION.md)及第三輪 R01–R08。先修共用本機缺陷，接 Hermes 暫定框架／GLM API 路徑並驗收 T26/T27 本機子項；缺 API 只阻真 GLM 呼叫，不阻協議測試。SERVER 到位後再做 T23→T24/T25 與 Qwen 後端重驗，不把 GLM 全部工作串在其後。T16／T32／正式交付依各自真實條件處理。

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

| 2026-10-04 T26 | venv＋瀏覽器實測 | agent/tools.py（確定性解析＋get_market_quote/post_forecast＋呼叫上限3）＋service.py（RuleBackend/QwenBackend降級）＋agent_prompt.md＋`POST /agent/query`；test_tools 12項過；網頁「問代理人」實測（截圖ui_agent_mobile.png） | PASS（本機層；SERVER Qwen 整合待T24） | T25/T24後補Qwen實測 |
| 2026-10-04 T27（本機層） | venv | test_faithfulness 14項過（菜名歧義/單位/無上週/B標實驗性/忠實方向/缺資料要求補充/無資料不假結論/Qwen降級/無機率字眼）；AGENT_EVALUATION.md＋outputs/agent_evaluation/local_results.json（8案例） | DOING：Qwen端忠實性待SERVER | T24/T25後補 |
| 2026-10-04 T28（本機層） | venv | body>8KB→413、每IP每分鐘30→429、日誌不記body、/health無秘密；test_access_limits 6項過；SECURITY_PRIVACY.md（SERVER補強清單） | DOING：對外補強於T29 | T29前更新 |
| 2026-10-04 T25（subagent） | 官方來源實查 | Qwen3.8核實：僅2.4T/27B、官方權重超24GB；候選Qwen3.5-9B（首選）/Qwen3.5-4B/Qwen3-8B（Apache-2.0、官方證據齊）；QWEN_SERVER_BENCHMARK.md＋agent_model.yaml | DOING：3090實測HOLD待SERVER；**待使用者確認型號原意** | 使用者回覆或T23後 |
| 2026-10-04 T33（subagent） | outputs JSON核對 | FINAL_REPORT.md（10章＋數字來源對照；含momentum基線與選定模型相當的負向並列）＋FINAL_SLIDES.md（15頁）；組員/期末格式標待補 | DOING：期末細則/組員/最終數據後定稿 | 公告後定稿 |
| 2026-10-04 T30（subagent） | 真實下載＋本地模擬 | update_public_data.py（驗證/dry-run/refresh備份＋只追加＋寫後核對）＋update_policy.yaml＋OPERATIONS.md；四情境實測過（真實下載無新資料/模擬新資料/失效來源/schema變動），refresh在副本真實執行（12,288→12,309、原檔hash不變） | DOING：SERVER端流程待T24/T29 | T24後補 |
| 2026-10-04 T34（subagent） | venv | REPRODUCIBILITY.md（全流程重現＋hash對照；實測fixtures 3/3、pytest 98過）；requirements-lock補fastapi/uvicorn/pyarrow/httpx | DOING：PUBLICATION_REVIEW與最終README待T32 | T32後收尾 |

| 2026-10-04 第三輪 F01/F06 | venv | [tools.py](../src/aiot_price/agent/tools.py)解析器重寫為子句級綁定（價格×單位×日期×店家×規格）；[predict.py](../src/aiot_price/models/predict.py)受控驗證（布林/Infinity/缺時區422；上週欄位錯誤降級不500；規格可比接入入口）；app.py 8KB按實際串流位元組（chunked 9,198B實測413）。審查5案例＋多品項/負數/錯誤日期全過（test_review_f01_f06.py 18項） | 修正完成 | — |
| 2026-10-04 第三輪 F02/F03/F07 | venv | prompt路徑修復（parents[3]＋strict載入，缺檔不上線）；Qwen輸出真值對照驗證器（誇大詞/未驗證數字日期價格/方向衝突/空回覆→降級規則）；/agent/query 丟threadpool（0.5s慢後端下health<0.4s）；回應含backend_used/degraded/degraded_reason/forecast（test_review_f02_f08.py 18項） | 修正完成；Qwen實機待T24/T25 | — |
| 2026-10-04 第三輪 F04/F05（subagent） | 暫存副本 | update_public_data.py 0.2.0：下載路徑修復（saved變數）、原子替換＋核對失敗自動保舊檔/還原、schema強化（壞JSON/缺欄/Infinity/鍵唯一，exit 2/3/4區分）、--reload-check證明重啟後讀到新截止（同一實例確實讀舊）；正式工件10/11 hash不變（fixtures為主對話並行重生成）。報告outputs/update_tests/round3_* | 修正完成；真實新行情路徑待新資料日 | — |
| 2026-10-04 第三輪 F07/F08（subagent＋主對話） | 瀏覽器390×844＋API:8013 | web：店號單一來源（tw01_ui_prefs_v1）、代理人結構化結果卡＋後端標示、保存/清單/匯出/刪除UI；後端/records四端點（ID防注入）；端到端實測：查詢→保存→清單、「上次無日期」顯示B拒絕提示＋A結果（截圖outputs/e2e/ui_agent_structured_round3.png） | 修正完成 | T32真手機補 |
| 2026-10-04 第三輪 F09（subagent） | 官方來源複查 | Qwen結論修訂：27B官方BF16/FP8無法全放24GB，但**27B GGUF 4-bit（實作者16.5–17.6GB）列優先實測候選**（使用者候選不排除）；NVFP4需Blackwell不適用3090；實測優先序＋benchmark_plan（revision/量化檔/框架/context/併發/中文工具案例）寫入QWEN_SERVER_BENCHMARK與agent_model.yaml（default=null） | 結論修訂完成；3090實測HOLD | 使用者確認候選 |
| 2026-10-04 第三輪 F10（subagent） | 專案外乾淨venv | lock去絕對路徑改`-e .`；pyproject補fastapi/uvicorn/pyarrow（dev加httpx）；%TEMP%乾淨環境全程驗證（安裝→import→真工件載入→pytest 98過）記錄於clean_env_check.md；README/PROJECT_CONTEXT/design/REPRODUCIBILITY/MODEL_CARD/FINAL_REPORT/FINAL_SLIDES同步（修正3處基線數字：0.0436/0.0748/0.2954）；TASKS開頭過時句修正 | 修正完成 | — |

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
