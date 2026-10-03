# AIoT 期末專題

本工作區用來完成TW01「現場菜價7／14天預測與分析代理人」期末專題，並保留先前選題與資料查核紀錄。

初始化／交接更新日期：2026-10-03。**目前階段（GLM第一輪完成後）：本機（TRAIN_LOCAL）已完成資料管線、公開市場模型訓練與封存測試、模型包 v0.1.0、本機 HTTP API 與手機網頁原型（63 項測試通過）。** 同店 A/B 驗證（T16）與 SERVER_3090 部署（T23 起）分別等待真店到期價與 SERVER 連線資訊。正式題名及期末交付格式在後續 TASK 收斂。

**主機分工已確認：這台工作機已完成菜價模型訓練；另一台RTX 3090是SERVER，待連線資訊後部署菜價推論、Qwen代理人與手機服務。** Qwen3.8為優先候選，具體大小／量化／框架待SERVER實測。SERVER連線與OS資訊尚缺，不把兩台電腦混為一台。

模型要點（2026-10-03 封存測試，臺中市場均價目標）：7 天方向 macro-F1 0.422、14 天 0.417（全預測持平基線為 0.309/0.295）；點估計 MAE 未優於不變價基線（已如實警示）。見 [MODEL_CARD](docs/MODEL_CARD.md) 與 [PUBLIC_MODEL_EVALUATION](docs/PUBLIC_MODEL_EVALUATION.md)。

原 50 題清單保留作歷史對照。現行篩選要求：以台灣公開訓練資料為主，實際查找既有作品，剔除沒有實質差異的方向。個人／家庭資料優先；公開資料限定也可，但需有可驗證的特色。

## 文件入口

| 文件 | 用途 |
| --- | --- |
| [TASKS.md](TASKS.md) | 完成本案的全套TASK、依賴、產出與驗收；目前執行項全TODO |
| [design.md](design.md) | 使用需求、雙主機分工、模型／代理人界線與工具契約草案 |
| [GLM_HANDOFF.md](docs/GLM_HANDOFF.md) | 可交給GLM的完整啟動提示詞及證據規則 |
| [GLM_PROGRESS.md](docs/GLM_PROGRESS.md) | 實際執行與接手紀錄；尚無訓練／部署紀錄 |
| [MODEL_VALIDATION_PLAN.md](docs/MODEL_VALIDATION_PLAN.md) | 市場模型、同店A／B、時間切分、發布延遲、模型工件與驗證 |
| [AGENTS.md](AGENTS.md) | 工作區代理人的接手規則與證據邊界 |
| [PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md) | 使用者條件、目前進度及尚未提供的資訊 |
| [COURSE_REQUIREMENTS.md](docs/COURSE_REQUIREMENTS.md) | 老師逐字稿與課程網頁的要求、原文位置、確認程度 |
| [ORDINARY50_TOPIC_CATALOG.md](docs/ORDINARY50_TOPIC_CATALOG.md) | 現行一般使用者／一般上班族U01–U50：用途、本人輸入、公開資料、前作與差異 |
| [GENERAL50_TOPIC_CATALOG.md](docs/GENERAL50_TOPIC_CATALOG.md) | 獨立覆核版G01–G50：4題新發想＋46題重驗採用的U題，附備案與淘汰證據 |
| [H16_TOPIC_CATALOG.md](docs/H16_TOPIC_CATALOG.md) | 第三批H01–H16：新發想＋N輪重驗＋TW重驗後僅存16題，含為何不足50的說明 |
| [WORK50_TOPIC_CATALOG.md](docs/WORK50_TOPIC_CATALOG.md) | W01–W50歷史研究：使用者已全數拒絕，不再供挑選 |
| [NEW50_TOPIC_CATALOG.md](docs/NEW50_TOPIC_CATALOG.md) | 上一輪N01–N50：保留編號與證據，使用者保留N18供比較 |
| [TAIWAN_TOPIC_SHORTLIST.md](docs/TAIWAN_TOPIC_SHORTLIST.md) | 前一輪TW01–TW05；保留來源與比較，不代表使用者選定 |
| [TW01需求與歷史](docs/ideas/TW01_VEGETABLE_BASKET.md) | 現行菜價需求、D33後執行方向與歷史討論；原菜籃流程已淘汰 |
| [TW01菜價重查](docs/research/TW01_RELATED_WORK_RECHECK.md) | 一週公共／私人預測、零售趨勢與AI產品的具體證據及現場報價差異限制 |
| [TW01零售公開資料](docs/research/TW01_PUBLIC_RETAIL_DATA.md) | 臺中近一年市場每日均價已下載／讀取，臺北月份CSV與高雄失效來源分開記 |
| [N18保留筆記](docs/ideas/N18_BEDROOM_MIN_TEMPERATURE.md) | 使用者保留的臥室清晨最低溫構想；尚未定題 |
| [G02保留筆記](docs/ideas/G02_TYPHOON_DAY_OFF.md) | 使用者保留紀錄維持；直接前作已查到，一般版推薦撤回，尚未定題 |
| [G41保留筆記](docs/ideas/G41_TRAVEL_BUDGET_RANGE.md) | 使用者保留紀錄維持；基本功能已有，私人校正差異待查核，尚未定題 |
| [G02／G41重查](docs/research/G02_G41_RELATED_WORK_RECHECK.md) | 使用者要求實查後的作品、讀取狀態、重疊判定與原稿勘誤 |
| [TOPIC_CATALOG.md](docs/TOPIC_CATALOG.md) | 原 50 題歷史清單；不是現行推薦 |
| [DECISIONS.md](docs/DECISIONS.md) | 已接受條件、助理建議與尚未定案事項 |
| [選題查核 SKILL.md](.agents/skills/aiot-topic-review/SKILL.md) | 評估選題、資料適配、查重與個人化的專題技能 |

## 下一步

1. 使用者將[GLM接手指引](docs/GLM_HANDOFF.md)交给GLM，從TASKS第一個可執行項開始；不再重做全部選題。
2. 核對本機環境、課程當屆規則、資料和方法，收斂design草案；先完成公開核心與本機訓練／測試。
3. 建立A／B流程、API和手機頁面，打包模型後在指定3090 SERVER部署與驗證Qwen工具呼叫。
4. 分開完成真店效果、手機外網、交付與獨立驗收；缺資料的項目保留HOLD／BLOCKED，不能冒充全案完成。

完整順序、依賴及產出以TASKS為準。組員、截止日期、SERVER存取與OS、確切技術版本及自家資料仍需補齊；可先推進不依賴它們的任務。N18／G02／G41保留為歷史備案，其他清單不納入當前實作。

## 原始資料與版本管理

- 原始逐字稿 `會議錄音 10.txt` 保留原位；因為是課堂原始內容，預設不納入 Git。
- 本機 Git 已初始化於 `main`；尚未建立提交或設定遠端。
- `data/`、`private/`、`recordings/`、`models/`、`outputs/` 及環境檔預設忽略；需要時再建立目錄。
- 技能保存在本工作區的 `.agents/skills/`，沒有安裝到全域技能目錄。可要求代理人讀取上方技能文件；若執行環境提供技能選單，可依其實際探索結果使用 `$aiot-topic-review`。

## 課程來源

- [期末 Proposal 指導](https://app.notion.com/p/AIoT-DA-L4-1-Proposal-1-3ebc4752981180d8842fd7e253962c4e)
- [課程首頁與歷屆入口](https://app.notion.com/p/O-AIoT-DA-2026-9-30-67148cb998b3405b91b83cc995dd0588)

文件中的資料集及網頁結果是研究快照；選題進入實作時，應再查核選中來源及可用樣本。

U清單已整理50張研究卡，尚未訓練或驗證效果。U45的深蹲片段、U46的完整延遲未見題標籤、U50的人聲嘴型區間仍待補；其他逐題限制見詳卡與[整合查核](docs/research/ORDINARY50_INTEGRATION_CHECK.md)。

G清單是第二輪獨立發想與覆核（2026-10-03）：21個新發想中4題入選、3題備案、14題淘汰；47個U題重驗後46題入選，留下U10欄位名、U18前作連結、U26計數、U28管道變動、U39前作對照等勘誤，8張深入卡在建議之前。證據見[新發想查核](docs/research/GENERAL50_FRESH_CHECK.md)、[U覆核](docs/research/GENERAL50_U_RECHECK.md)與[深入卡](docs/research/GENERAL50_DEEP_DIVE.md)；未訓練、未採集自家資料、未定題。

H批是第三輪（2026-10-03，回應「再找50個」）：新發想15題＋N輪18題重驗＋TW02/TW03＋開放探勘後，誠實成立的只有16題（H01會考難度最佳）；陣風、雨斷、浪況被官方產品侵蝕，姓名、車牌、收容、素食、寵物名、家庭收支微資料等死於資料閘門。證據見[H批查核](docs/research/H16_CHECK.md)；未以同配方換變數湊數。
