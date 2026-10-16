# TW01 雙入口分階段任務卡（DE00–DE12）

日期：2026-10-13。這份文件是後續實作與驗收計畫；本輪只建立文件交接，**產品改碼、套件安裝、程序重啟、個人帳號、私人通道與 ChatGPT 實測全部 `NOT_RUN`**。DE10／DE11 初始 `HOLD`，原因是本人帳號權限尚未確認，其餘初始 `TODO`。

> 未來執行者是 **ChatGPT＋Windows COS**。使用者本包指示覆蓋 `AGENTS.md` 的舊 GLM 作者角色；原品質、證據、範圍與獨立審查要求保留。ChatGPT 實作者自驗只能記 `SELF_CHECK`，不能替自己簽正式外部驗收。

**目標：** 保留無語言模型的網頁表單 A／B 與本機紀錄，新增個人 ChatGPT 的兩個唯讀 MCP 工具，兩個程序各載入同一份凍結 RF 7 天／HGB 14 天 release。

**架構：** 網頁走原 `/forecast` 與自己的 `/records`；MCP adapter 直接走原 `AgentTools`／`ForecastEngine`，不走 `/agent/query`、HTTP 保存暫存或私人紀錄。MCP 為 stdio，個人 ChatGPT 透過 Windows 私人通道連線。

**技術：** 原 Python／FastAPI／Web／RF／HGB，官方 Python MCP SDK；SDK 的當時版本在 DE04 查證後才 pin。本文件不猜版本，不授權升級既有模型執行依賴。

**必讀原始規範與最新方向：** `AGENTS.md`、`docs/chatgpt_dual_entry/20261013_01/CONCLUSION.md`、`outputs/audits/proposal_v5_r3_independent_20261009_01/REVIEW_R3.md`。`outputs/quality_runs/chatgpt_dual_entry_design_20261013_02/DESIGN.md` 是歷史設計參考，其「等待設計確認」停點已被後續人類的動手授權取代。Proposal 的 `EXTERNAL_PASS` 只涵蓋 v5 r3，不能移用到本包產品。

## 依賴、狀態與執行規則

| 階段 | 任務 | 前置依賴 | 初始狀態 | 產品驗證 |
| --- | --- | --- | --- | --- |
| DE00 | 環境、範圍與保護基準 | 無 | TODO | NOT_RUN |
| DE01 | 實作契約與驗收案例 | DE00 | TODO | NOT_RUN |
| DE02 | manual 後端與紀錄目錄隔離 | DE01 | TODO | NOT_RUN |
| DE03 | 表單 UI 與紀錄功能保留 | DE02 | TODO | NOT_RUN |
| DE04 | MCP SDK 查證與依賴隔離 | DE01 | TODO | NOT_RUN |
| DE05 | 兩工具 adapter 與結果契約 | DE04 | TODO | NOT_RUN |
| DE06 | 原生 MCP、硬超時與人工恢復 | DE05 | TODO | NOT_RUN |
| DE07 | 回歸、反向控制與保護 hash | DE03＋DE06 | TODO | NOT_RUN |
| DE08 | 獨立實作複核與交接 | DE07 | TODO | NOT_RUN |
| DE09 | 隔離本機網頁實測 | DE08，限制見下文 | TODO | NOT_RUN |
| DE10 | 個人帳號權限與私人通道 | DE08 | HOLD | NOT_RUN |
| DE11 | 真 ChatGPT 端到端實測 | DE10 通過 | HOLD | NOT_RUN |
| DE12 | 收尾與分層交付 | DE09＋DE11 通過，或 DE10／DE11 HOLD | TODO | NOT_RUN |

執行順序為 `DE00 → DE01`，再分 `DE01 → DE02 → DE03` 與 `DE01 → DE04 → DE05 → DE06`；兩支完成後 `DE03＋DE06 → DE07 → DE08`。DE08 後可分別做 DE09 與 DE10；DE10 通過才做 DE11。DE09 與 DE11 通過，或帳號層 DE10／DE11 保持 HOLD，均可做 DE12 的文件與候選交付。

- 有實質程式改動的階段先寫能抓到指定缺陷的測試，保留第一次失敗，再做最小實作及重測；其餘階段按任務卡做唯讀／既有檢查，不硬造 TDD 失敗。不得刪測試、削弱斷言或使用固定測試數當通過標準。
- 狀態分為工作狀態 `TODO／DOING／FAIL／HOLD／BLOCKED`、作者自驗 `SELF_CHECK`、獨立代理人複核，以及正式外部驗收。各層另記 `PASS／FAIL／NOT_RUN`；不能把一層 PASS 寫成全案完成。
- DE08 若沒有真正獨立新上下文 reviewer，獨立複核不能 PASS，正式外審維持 HOLD。仍可做已授權的 DE09 隔離本機候選測試與 DE12 交付；DE10／DE11 保持 HOLD 待實作審查。候選不得升格 final。
- 任一重要缺陷退回最早源頭階段，重跑受影響範圍；同原因連續兩次修復失敗即停止盲試，查上游根因，留下原始錯誤與 BLOCKED 證據。
- 本包不自動 commit／push，不公開插件、不部署 SERVER、不買訂閱、不切帳號、不接 GLM／Claude KEY、不恢復 Qwen／Hermes。帳號缺權限只 HOLD 該層，不能因此放棄已授權的本機工作或文件交付。

## 共用檔案邊界與證據格式

工作目錄固定 `C:\Users\prometheans\Documents\AIOT_FinishProject`。以下為使用者先前「動手」已授權、交由下一輪 ChatGPT／Windows COS 執行的範圍；**本輪 Codex 只寫文件，沒有執行程式操作**，接手者無須重問方向。本人登入／權限及正式外審以實際證據判定。

| 類型 | 允許檔案／操作 | 限制 |
| --- | --- | --- |
| 新整合 | `src/aiot_price/integrations/__init__.py`、`manual_web.py`、`chatgpt_contracts.py`、`chatgpt_adapter.py`、`chatgpt_mcp.py`、`mcp_worker.py`，及必要的新整合 helper | 不搬動或重寫舊 provider／Hermes／Qwen／model source |
| API | `src/aiot_price/api/app.py` | 僅 manual 入口守衛、延後 agent import、server-only 紀錄目錄注入；原表單／紀錄契約不擴權 |
| Web | `web/index.html`、`web/app.js`、`web/style.css` | 局部移除聊天區與初始化，保留 A／B、單位、日期、保存／載入／匯出／刪除 |
| 測試 | `tests/integrations/` 新測試；受影響 Web／API 測試的局部調整 | 舊 UI 斷言因選定新 UI 而失效時，改成新的明確行為斷言；不能跳過整組或弱化其他功能。測試 HOME fixture 如須修正，只改隔離位置／啟動時序 |
| 依賴 | `pyproject.toml` 的獨立 MCP optional extra；`requirements/chatgpt-mcp.lock` | 查官方當時 release 後 pin，保留原 ML 依賴；相容性衝突用獨立 transport 環境＋原 `.venv` worker |
| 文件 | `docs/CHATGPT_PLUGIN.md`、本包文件／RUNBOOK、root `TASKS.md` 本包入口 | 不改其他舊任務狀態；明列實跑與 NOT_RUN |
| 證據 | `outputs/quality_runs/chatgpt_dual_entry_impl_<actual_run_id>/DE##/` | `<actual_run_id>` 由真正執行開始時間產生；每輪新目錄，不覆寫舊封存 |

禁止修改 `models/`、`data/`、訓練／更新公開資料腳本、封存評估、舊 provider／Hermes／Qwen source 與設定、任何 KEY／帳號檔、正式 Proposal／簡報／影片；不得清理既有未追蹤目錄或用 `git reset --hard`／`git clean`／`git add -A`。

每階段證據目錄至少放 `state.yaml`、`evidence.md`、`commands.log`、`diff_scope.txt`；有 UI 才另放 `visual_review.md`。矩陣欄位為 `要求／原始來源／實際檔案與行號／驗證方式／實際命令與退出碼／結果／限制／審查者`。原始 stdout／stderr、失敗 traceback、測試收集數與環境一併保存；不保存秘密或完整私人聊天。未執行欄填 `NOT_RUN`，不可預填 exit 0。

DE00 啟動時明定 `$taskRun` 為新證據目錄的**絕對路徑** `C:\Users\prometheans\Documents\AIOT_FinishProject\outputs\quality_runs\chatgpt_dual_entry_impl_<actual_run_id>`，替換真正 run ID 後記入 state；各 checker 用 `Join-Path $taskRun 'DE##\...'` 定位，不更改 root cwd，也不把 `DE00\...` 當 root 相對路徑。

每個有實質變更的階段保留六個分離檢查點；可用獨立新 context 時交由不同 reviewer，否則明記同一作者 SELF_CHECK，不能虛構第三方核准。

| 檢查點 | 責任 | 最小證據 |
| --- | --- | --- |
| 輸入 | 主執行者列要求／授權／來源／不動清單 | 原要求、scope、基準 manifest |
| 輸入查核 | 查核者自己讀來源與原碼，確認沒有摘要誤讀 | source_map、UNKNOWN、範圍差異 |
| 實作 | ChatGPT＋Windows COS 依本卡做最小候選 | 實際 diff、變更原因、可逆備份 |
| 實作查核 | 以原規範＋真 diff 核對語意、邊界與測試抓錯能力 | code review、正反測試與缺陷定位 |
| 產出 | 實際產生可重建程式／測試／wire result／必要畫面 | 原生 artifacts、命令與退出碼 |
| 輸出查核 | 不採信作者 PASS，自開輸出與重跑關鍵正反案例 | 原輸出對照、checker 非零、review 原文 |

與原管線對照：DE00／DE01 對應 S00 的範圍／輸入檢核；DE07 對應 S60；DE08 對應 S80 的獨立審查要求；DE02–DE11 為最新授權下的 S90 本包產品範圍，DE12 對應收尾。這份映射不重開 S20 研究／Proposal，不擴張到真店、3090／SERVER 或公開提交。

### 測試程序的共用前置

在**首次 Python 程序啟動及任何產品 import 前**設定測試用 `HOME／USERPROFILE／APPDATA／LOCALAPPDATA／XDG_CONFIG_HOME／XDG_DATA_HOME／XDG_CACHE_HOME／HERMES_HOME／AIOT_HERMES_HOME` 指向該階段的隔離目錄；另設 `AIOT_RUNTIME_ISOLATED=1`、`PYTHONUTF8=1`、`PYTHONIOENCODING=utf-8`、`PYTHONPATH=src`。使用 `$taskHome` 等任務變數，不重用 PowerShell 的 `$HOME`。不要等 `monkeypatch` fixture 才處理 import 副作用。

manual／模型 worker 子程序還要清除繼承的 provider、模型 URL／模型 ID、GLM／Qwen／Hermes 設定與憑證；清除過程只記名稱／動作，不讀取或印出秘密值。ChatGPT tunnel-client 的 runtime key 只屬通道程序，不能轉給模型 worker。全測試禁止 live 模型 API；舊 provider 測試只可用原有 mock／stub。背景啟動 helper 必須隱藏視窗並記錄自己的 PID。

本文件下列命令全部是**預定命令，現在 `NOT_RUN`**。新模組／測試／驗收腳本尚未建立時，命令不代表它們已存在；執行者須在其所屬階段建立並記錄實際完整命令、時間、環境與退出碼。

## DE00 — 環境、範圍與保護基準

**前置：** 無。**初始：** TODO；驗證 NOT_RUN。

**執行內容：**

- [ ] 自己讀必讀原始規範及本包文件；確認 Windows COS 工具能讀寫此工作區。記錄 cwd、HEAD、tracked diff、ignored 狀態與既有 untracked 清單，不能把前輪未提交內容歸成本包新改動。
- [ ] 以原 `outputs/proposal_delivery/run3_20261004_01/protected_before.json` 的 14 組 path／SHA256／size 逐檔比對。**不改原 manifest，不重新抓基準掩蓋不符。**
- [ ] 原 14 組只涵蓋 release 的 manifest，沒有 `model_h7.joblib`、`model_h14.joblib`、`public_history.parquet`。另存完整 `models/releases/0.1.0/` 五檔 baseline：`manifest.json`、`fixtures.json`、兩個 joblib、`public_history.parquet`；與原 14 份基準並行，不能替換它。
- [ ] 對允許修改檔留下 task-start hash／size、可逆候選備份與原 diff；另記原 `.venv` Python／已安裝 ML 套件版本。只列憑證／帳號「未碰」，不讀內容。

**允許改檔：** 本階段證據目錄；只讀原 source／模型／資料／審查／基準。新增只讀比對腳本 `DE00/verify_baselines.py`，不得寫回受保護檔。

**驗證與反向控制：** 複製一份測試用 baseline／受保護檔到 `DE00/negative/`，只改副本一個 byte 或 hash，checker 必須非零退出並指出檔案；原正式檔前後不變。基準缺檔、hash 或 size 不符不得忽略。

**預定命令（NOT_RUN）：** `git rev-parse HEAD`、`git status --short --untracked-files=all`、`git diff --name-only`；隔離 HOME 後 `& .venv\Scripts\python.exe -X utf8 (Join-Path $taskRun 'DE00\verify_baselines.py') --legacy-manifest <原14基準絕對路徑> --release-baseline (Join-Path $taskRun 'DE00\release5_before.json')`。原14參數替換正式 manifest 的絕對路徑，實跑以本階段建立的真正 script／參數為準。

**證據：** `DE00/scope_before.*`、`protected14_check.json`、`release5_before.json`、`source_before.json`、`environment_before.json`、原 diff、比對及 negative log。

**完成／退回／停點：** 兩份基準皆可讀且一致、範圍與既有變更已分辨，才進 DE01。任一保護不符標 FAIL 並停產品寫入；保留原錯誤，不自動修正模型／封存。只可繼續整理缺口與交付證據。

## DE01 — 實作契約與驗收案例

**前置：** DE00 通過。**初始：** TODO；驗證 NOT_RUN。

**執行內容：**

- [ ] 讀真呼叫路徑：`api/app.py`、`agent/tools.py`、`models/predict.py`、`api/prediction_records.py`、`contracts/forecast.schema.json`、Web init／表單／紀錄。固定兩入口差異與 A／B 邊界，不把既有文件宣稱當程式事實。
- [ ] 在 `chatgpt_contracts.py` 定義兩工具 input／output schema：輸入 object 均 `additionalProperties=false`；annotations 均 `readOnlyHint=true`、`destructiveHint=false`、`openWorldHint=false`。工具清單與 dispatch 白名單都只能有 `get_market_quote`、`post_forecast`。
- [ ] `get_market_quote` 必填 `crop_id`、`market_id`；品項只 `cabbage／bok_choy／sponge_gourd`，市場使用原 `KNOWN_MARKETS`。`post_forecast` 再必填有限正數、非 bool 的 `current_price` 及 `NTD_per_taiwan_jin／NTD_per_kg`；`observed_on` 選填但有填必須嚴格 `YYYY-MM-DD` 且為真日曆日，未填取 Asia/Taipei 今日。
- [ ] 日期轉成該日 `T12:00:00+08:00`；拒未來日；固定 `mode=without_last_week`、horizons 7／14、`store_id=null`。拒收 B／上週價／自製 mode／保存／URL／路徑／程式碼／額外欄位。MCP caller 不能指定 release_dir、worker interpreter 或 records-dir。
- [ ] 輸出 schema 定義 `input_echo`、實際 normalized engine request、台北 `query_date`、原結果與資料／模型版本。行情保留 `observed_date／public_data_cutoff／price_age_days_at_cutoff`，另附 `price_age_days_at_query`，兩種 age 不混用。預測保留原值、單位、精確 t+7／t+14、warnings、`unvalidated`，機率／區間為 null。
- [ ] 鎖定 manual CLI：`manual_web --host --port --release-dir --records-dir --home`；host 只 loopback。新旗標 `AIOT_MANUAL_WEB=1`，server-only `AIOT_RECORDS_DIR` 由 launcher 的 `--records-dir` 注入；預設仍為 `private/predictions`。鎖定 MCP CLI：`chatgpt_mcp --release-dir --worker-python --home`，stdio、固定單工具 15 秒，不提供 caller 可改 timeout。
- [ ] 列每項驗收的 owning stage／正反案例／expected result；回顯參數只能供核對，不宣稱原聊天逐字忠實或真人確認，`confirmed=true` 也不是確認證據。

**允許改檔：** 新 `chatgpt_contracts.py`、`tests/integrations/test_chatgpt_contracts.py`、本包契約／案例文件及 DE01 證據；不改 engine 或舊 JSON 契約。

**驗證與反向控制：** 缺 crop／market、不支援 enum、bool／0／負數／NaN／Infinity、非兩種單位、`2026-2-03`／非法日／未來日、B／save／path／extra 都須受控拒絕；schema 與 dispatch 兩層都要驗。故意把 schema 副本改成允許 extra，契約 checker 必須非零。

**預定命令（NOT_RUN）：** `& .venv\Scripts\python.exe -m pytest tests/integrations/test_chatgpt_contracts.py -q`；先保留紅測，再實作與綠測。

**證據：** `DE01/contracts.json`、`case_matrix.md`、`source_map.md`、紅／綠測 log、schema 造錯 checker log。

**完成／退回／停點：** 可指向實際 schema、函式與每一反向案例，無模糊的「之後再處理」。若契約違反雙入口差異退 DE01；模型或私人紀錄擴權立即停點，不自行加入第三工具。

## DE02 — manual 後端與紀錄目錄隔離

**前置：** DE01 通過。**初始：** TODO；驗證 NOT_RUN。

**執行內容：**

- [ ] 新 `manual_web.py` 在首次 API import 前設 `AIOT_RUNTIME_ISOLATED=1`、`AIOT_MANUAL_WEB=1`、HOME 隔離，清除繼承 provider／Qwen／GLM／Hermes／模型 API 設定與秘密。禁止自動讀 `private/.env` 或 GLM 專用 KEY，不重用 `agent/local_web.py` 的 key loader。
- [ ] 移除 manual 可觸及的 API 頂層 `agent.service`／Qwen import；必要的 legacy agent import 改在非 manual 路徑才發生。原 `profile=rule` 分支仍可能 `QwenBackend()`，單設 rule 不合格。
- [ ] `/agent/query` 在解析 provider／載入 Qwen、Hermes／建立 engine 供 agent 使用之前，回受控 `chat_disabled`；`/agent/status` 回明確聊天停用／manual 狀態，provider 為 null，不能探測模型或讀 provider 設定。
- [ ] `/forecast`、health／metadata、rate／body limits 與原 A／B 保留。新 `AIOT_RECORDS_DIR` 只接受伺服器啟動注入；save／list／export／delete 全部傳入同一設定目錄，預設仍 `private/predictions`。現有 helper 已有 `out_dir`，不用改 `prediction_records.py`。
- [ ] 客戶端不得傳任意目錄控制；HTTP 保存仍只收本 HTTP 程序真推論的 request_id，MCP 程序的結果不得混入 `_RECENT_FORECASTS`。

**允許改檔：** 新 `manual_web.py`／必要整合 helper、`api/app.py` 指定範圍、`tests/integrations/test_manual_web.py`、必要 API 測試局部及 DE02 證據。

**驗證與反向控制：** 在新子程序 import 前裝攔截器，令 provider／service／Qwen／Hermes import、私有 dotenv／KEY 讀取、外部模型 HTTP 任一觸發即 FAIL；以非秘密的繼承設定測試清除。真 ForecastEngine 的 A／可比 B 仍有結果；直接 agent 請求拒絕；records 正向只寫隔離目錄，偽造 request_id／完整結果／注入 out_dir 均拒絕。原 `private/predictions` 不新增／刪除／覆寫。

**預定命令（NOT_RUN）：** `& .venv\Scripts\python.exe -m pytest tests/integrations/test_manual_web.py -q`；`& .venv\Scripts\python.exe -m aiot_price.integrations.manual_web --help`。真正 launcher 及 record-dir 流程在 DE09 再實測。

**證據：** `DE02/import_guard.json`、`provider_call_counts.json`、API 原請求／回應、records 隔離前後清單、原目錄未變證據、紅／綠測與 diff。

**完成／退回／停點：** 不只畫面隱藏，而是首次 import 到直接 agent endpoint 都無 provider／KEY／模型網路路徑，原表單與紀錄可運行。隔離失效退 DE02；契約錯誤退 DE01；不為修 manual 去改舊 provider。

## DE03 — 表單 UI 與紀錄功能保留

**前置：** DE02 通過。**初始：** TODO；驗證 NOT_RUN。

**執行內容：**

- [ ] 移除 GLM 聊天區、送問答行為與 init 的 `bindAgent／loadAgentStatus` 呼叫；初始化不能請求 `/agent/status` 或 `/agent/query`，不只更換顯示名稱。
- [ ] 保留品項、市場、店價、公斤／台斤、日期、選填同店上週價／日期／規格與 A／B 結果；上週資料缺失／不可比仍依原規則回 A，B α=0.3 不變。
- [ ] 保留 `tw01_ui_prefs_v1`、匿名店號、表單 lastRun、保存、清單載入、匯出、刪除與等待／錯誤提示；最後成功表單結果才是保存對象。
- [ ] 僅調整聊天相關版面／CSS／測試；不要重新設計整份頁面或改研究限制。工具／ChatGPT 不在線時，表單仍能操作。

**允許改檔：** 三個 Web 檔局部、`tests/integrations/test_manual_web_ui.py`、受影響舊 UI 測試的指定斷言及 DE03 證據。

**驗證與反向控制：** init 網路攔截紀錄應無 agent 請求；表單 A／B、單位、缺價格、非法／未來日期、保存 disabled／enabled、保存後清單與刪除正常。把隔離 HTML／JS 副本加回 agent init 呼叫，checker 必須 FAIL；不能用 `display:none` 假通過。實際桌面／窄螢幕渲染留待 DE09。

**預定命令（NOT_RUN）：** `& .venv\Scripts\python.exe -m pytest tests/integrations/test_manual_web_ui.py tests/integrations/test_manual_web.py -q`。

**證據：** `DE03/web_contract.md`、init 請求記錄、UI 測試正反 log、變更 diff；未實開瀏覽器項仍 NOT_RUN。

**完成／退回／停點：** 表單與紀錄能力完整保留且無聊天初始化。若 records／A／B 被刪或保存綁定錯誤退 DE03；後端隔離缺陷退 DE02。

## DE04 — MCP SDK 查證與依賴隔離

**前置：** DE01 通過。**初始：** TODO；驗證 NOT_RUN。設計交接記錄 SDK 尚未安裝，執行時仍須現查。

**執行內容：**

- [ ] 記錄目前 Python、pip、installed MCP／ML／API dependencies；用官方 MCP Python SDK repository／release／package metadata 查當時版本及 Python 支援，記查核時間與原文連結後選 exact pin，不能猜 pip 版本。
- [ ] 在隔離候選環境先解析與安裝官方 SDK；產出 `requirements/chatgpt-mcp.lock`（選定版本／transitive 版本／可用 hash），`pyproject.toml` 只加獨立 MCP extra。
- [ ] 比較原 `.venv` 的 numpy／pandas／scikit-learn／joblib／pyarrow 等凍結執行版本；不得順手升級、重訓、轉存 joblib 或更新資料。
- [ ] 若 SDK 與原 API／ML 依賴衝突，採隔離 transport 環境只執行官方 MCP SDK；數值 worker 用原 `.venv\Scripts\python.exe`，透過受控本機程序訊息傳 JSON。transport 不直接載入 joblib，不接受 caller 指定執行檔或路徑。
- [ ] 記 interpreter／env／worker 路徑及一鍵可逆卸除候選方式；不覆寫 working `.venv` 以追求安裝成功。

**允許改檔：** `pyproject.toml` 指定 extra、新 lock、DE04 的隔離依賴環境與證據；不改原依賴範圍或模型檔。

**驗證與反向控制：** 官方 SDK import／pin／lock 一致、`pip check` 無衝突、原 ML freeze 前後一致。用隔離 resolver 的刻意不相容 constraint 確認會非零，保存衝突與採取 transport fallback 的理由，不能忽略 resolver 錯誤。

**預定命令（NOT_RUN）：** 原 `.venv` 的 `python -m pip freeze`／`python -m pip show mcp`；候選 interpreter 的 `python -m pip install -r requirements/chatgpt-mcp.lock`／`python -m pip check`。版本與候選 interpreter 在查證後寫入實際命令，這裡不提供未查證版本。

**證據：** `DE04/sdk_sources.md`、`dependency_before.txt`、`dependency_after.txt`、resolver／install／pip-check log、環境選擇與 lock hash。

**完成／退回／停點：** 官方確切版本與隔離策略可重建、原 ML stack 未變。衝突退 DE04 用分離環境；若只能改 ML stack 才能跑，標 BLOCKED 並交付衝突，不越權升級。

## DE05 — 兩工具 adapter 與結果契約

**前置：** DE04 通過，沿用 DE01 契約。**初始：** TODO；驗證 NOT_RUN。

**執行內容：**

- [ ] 新 `chatgpt_adapter.py` 只建立原 `ForecastEngine` 與 `AgentTools`；`get_market_quote`／`post_forecast` 直接呼叫原函式。Web 與 MCP 各載同凍結 release，engine／request_id／records 暫存不跨程序共享。
- [ ] 先 schema 驗證，再 dispatch 白名單與程式型別／有限值驗證；不靠 annotations 當執行防護，不解析自由文字選市場或用預設市場代填缺項。
- [ ] 實作台北 query day、嚴格日期與 noon 轉換、exact t+7／t+14；原 engine 的 `Today／今天／距今` 警告逐字保留在原結果，受控文字加註其「今天」指報價基準日 t，不必然是查詢當日。不能改 engine 來處理措辭。
- [ ] 行情另計 query-age，保留原 cutoff-age；缺測 0／未知日期／無價格回受控錯誤，陳舊資料如實說明，不能把 snapshot cutoff 當實際觀測日或宣稱即時。
- [ ] 回 `structuredContent` 加受控事實文字；原價格、方向、單位、版本、warnings 與限制不得重算替換。`input_echo` 是工具實際提交值，不能寫真人已確認；機率／區間保持 null，公開均價不是個店真值。
- [ ] MCP 永不讀寫 `private/predictions`，不註冊 HTTP 最近推論；B、保存及任何任意執行要求都受控拒絕，不產生偽 B 或第三工具。

**允許改檔：** 新 adapter／必要整合 helper、`tests/integrations/test_chatgpt_mcp.py`、契約局部與 DE05 證據；不改 `agent/tools.py`／`models/predict.py`。

**驗證與反向控制：** 真凍結 engine 原呼叫與 adapter 逐欄對照，涵蓋兩種單位、歷史日、台北／UTC 跨日、閏日、精確到期日；quote 兩種 age 用不同日期驗算。缺項、bool／非有限價、未知單位／日、未來、B／save／confirmed／URL／path／code／extra、未知 tool name 均拒絕。隔離 checker 副本故意改一個價格／方向／目標日必須非零；mock 測試不取代真 engine 對照。

**預定命令（NOT_RUN）：** `& .venv\Scripts\python.exe -m pytest tests/integrations/test_chatgpt_mcp.py tests/integrations/test_chatgpt_contracts.py -q`；正反 tool-result checker 命令由本階段建立並記錄。

**證據：** `DE05/original_engine_results.json`、`adapter_results.json`、`result_comparison.json`、date／unit／age cases、偽值 checker 非零 log、無 provider／records 副作用證據。

**完成／退回／停點：** 模型與資料同源、兩工具無寫入、副作用控制及不合法輸入真正生效。值／日期／echo 錯誤退 DE05；schema 邊界錯誤退 DE01；不能改模型讓比對過關。

## DE06 — 原生 MCP、硬超時與人工恢復

**前置：** DE05 通過。**初始：** TODO；驗證 NOT_RUN。

**執行內容：**

- [ ] 新 `chatgpt_mcp.py` 用已 pin 官方 SDK 實作 stdio initialize／tools/list／tools/call；工具清單、schemas、annotations、structuredContent 與受控文字以實際 wire result 為準。stdout 只有協定，診斷走 stderr，沒有 print／BOM／秘密。
- [ ] 新 `mcp_worker.py` 以明示原 interpreter 及 frozen release 執行數值工作；單 worker 串行。先做 startup／manifest／hash 檢查，tool call 使用單調時鐘從 dispatch 起計固定 15 秒。
- [ ] 超時需有**真正可終止的 worker／process 控制**：停止並確認 worker 已退出、沒有背景推論或延遲回寫；無法確認時退出工具程序。thread timer、future timeout、常數或提前回錯都不足以證明硬超時。
- [ ] 禁止無限重試；第一版人工重開工具／通道程序。依實際 terminal／tunnel-client 行為記復原，不假設自動重建。原生本機 MCP 要先驗人工重開後再次 initialize／list／call。

**允許改檔：** 新 MCP transport／worker／必要 helper、`tests/integrations/test_mcp_native.py`、`test_mcp_timeout.py`、DE06 證據；不新增入站 HTTP listener。

**驗證與反向控制：** 真 SDK client 與 stdio 程序交握，list 僅兩工具，兩工具真 engine call 符合契約。隔離 worker 故意卡住超過 15 秒，記開始／deadline／終止／PID／退出碼，確認無殘留工作；容許的程序清理延遲需記實測，不能把容差改成較長工具預算。人工重開後正向 call 成功；stdout 混入假診斷的副本應讓協定 checker 非零。

**預定命令（NOT_RUN）：** 選定 transport interpreter 的 `python -m pytest tests/integrations/test_mcp_native.py tests/integrations/test_mcp_timeout.py -q`，以 server CLI 明示 `--worker-python <原.venv絕對路徑>`；`python -m aiot_price.integrations.chatgpt_mcp --help`。若 SDK 與 ML 分離，不冒稱單一 interpreter 跑完所有層。

**證據：** `DE06/native_session.json`、原 wire messages、stderr、timeout 時間線與 PID／退出紀錄、人工重開前後 session、協定造錯 log。

**完成／退回／停點：** 原生協定、數值、stdout、硬終止與人工恢復各自通過。無法硬終止／恢復標 FAIL 退 DE06，不發布通道候選；不以 REST mock／adapter unit test 代替 native MCP。

## DE07 — 回歸、反向控制與保護 hash

**前置：** DE03＋DE06 自驗完成。**初始：** TODO；驗證 NOT_RUN。

**執行內容：**

- [ ] 重新比對原 14 基準與 DE00 全 release 五檔 baseline；比較 source 增量 diff、既有 dirty／untracked 狀態與原私人 records 目錄不變。不能更新基準消掉變更。
- [ ] 首次 Python／pytest collection 前設定隔離 HOME、`AIOT_RUNTIME_ISOLATED=1` 與 UTF-8；檢查舊 test import 是否自行覆蓋到歷史封存 HOME。必要時僅修隔離 fixture／啟動位置，不能改業務斷言或污染舊證據。
- [ ] 分別跑新 integration、產品 `tests/`、repo-wide 三層。每層保存實際收集數、passed／failed／warnings、退出碼與環境；不引用歷史固定數當本輪通過。
- [ ] 若裸 repo-wide 因 `outputs/` 候選副本重複收集／import mismatch 失敗，保留原命令與 traceback，確認原因後再以 `--ignore=outputs` 做明示範圍重跑；不得刪封存、改斷言、把裸跑失敗抹成全 repo 綠。
- [ ] 重跑受影響反向控制：非法 schema／日期／價格、provider import／KEY／模型網路阻斷、偽 engine 值 checker、隔離 records 保存綁定、native timeout／人工恢復。測試器自身有改動須驗壞輸入非零。

**允許改檔：** 新 integration tests、已授權局部測試 fixture／斷言；修復仍只回 DE01–DE06 允許範圍；DE07 證據。

**驗證與反向控制：** 逐列重現 DE01／02／03／05／06 的失敗案例；五檔基準副本篡改須非零。不得以正常結果通過推論 checker 有抓錯能力。測試若碰原 private／模型／資料立即停止並記污染範圍。

**預定命令（NOT_RUN）：** `& .venv\Scripts\python.exe -m pytest tests/integrations -q`；`& .venv\Scripts\python.exe -m pytest tests -q`；`& .venv\Scripts\python.exe -m pytest -q`；必要的明示重跑 `& .venv\Scripts\python.exe -m pytest -q --ignore=outputs`。SDK 分離時，native tests 透過明示 transport interpreter 的子程序 harness 跑 SDK client，原 pytest 不須 import SDK 或載入 transport 的 ML 依賴；另保存該 interpreter 的 native test 結果。不能為 collection 過關而跳過 native 驗收或升級原 ML stack。

**證據：** `DE07/protected14_after.json`、`release5_after.json`、`diff_scope.txt`、分層原始 pytest log／collection／environment、所有失敗及反向 log、實測總矩陣。

**完成／退回／停點：** 適用回歸與反向控制關閉、保護檔不變，作者可記 SELF_CHECK。既有失敗與本次引入分開；未解重要失敗退 owning stage，不提交 DE08「全部 PASS」；未跑層保持 NOT_RUN。

## DE08 — 獨立實作複核與交接

**前置：** DE07 證據齊備。**初始：** TODO；驗證 NOT_RUN。

**執行內容：**

- [ ] 交給真正新的 reviewer context：原使用者要求／AGENTS／設計、原 source、候選 diff、真 artifacts／命令／原始 log。不要提供作者「已通過」結論或暗示預期 PASS；reviewer 自己查程式、數值與可重現證據。
- [ ] 複核 import 邊界、兩工具白名單、日期／單位／age、no-write、records 注入、frozen release、依賴環境、native 協定／硬超時與錯值 checker。reader 能重跑正反測試並指出行號／退出碼。
- [ ] fresh subagent 可出「獨立代理人複核結論」與實際範圍，不能冒稱使用者驗收或正式 ChatGPT 外部驗收；作者自驗仍 SELF_CHECK，正式外審狀態保持 HOLD，直到確有另一正式審查原文。
- [ ] 若沒有獨立 context，只交自驗矩陣、原始 artifacts 與精確重建指令；DE08 不記 PASS，獨立／外審 HOLD。不要把同一作者重看三次當三 reviewer。

**允許改檔：** DE08 審查／交接文件與本包狀態。若 reviewer request changes，僅回指定源頭修復並重跑受影響範圍；不借複審擴張功能。

**驗證與反向控制：** reviewer 重跑至少一個真 engine 對照、一個非法輸入、一個故意錯值 checker 非零、native timeout／人工恢復。核對 reviewer 身分／context／讀取範圍及限制；沒有證據不能授予獨立複核 PASS。

**預定命令（NOT_RUN）：** reviewer 使用 DE07 的實際測試／baseline 命令獨立重跑；此文件不填假的 reviewer、命令或退出碼。

**證據：** `DE08/review_input_manifest.json`、`independent_review.md` 或 `self_check_only.md`、reviewer 自己的命令／正反 log、request-changes closure。

**完成／退回／停點：** 有真獨立代理人複核且重要缺陷關閉，才通過本包實作審查門檻；這仍不是正式 EXTERNAL_PASS。無 reviewer 時可續 DE09 的隔離本機候選驗證與 DE12 文件交付，DE10／DE11 HOLD；任何未審候選禁止升 final。

## DE09 — 隔離本機網頁實測

**前置：** DE08 有審查結論；若缺獨立 reviewer，僅可隔離候選驗證。**初始：** TODO；驗證 NOT_RUN。

**執行內容：**

- [ ] 先用 Windows COS 查 8766 listener 的 PID、executable、實際 cwd 與啟動用途；命令列需遮蔽可能的秘密，不能只看 port／module 名就推定程序歸屬。無可靠 cwd／ownership 證據時，不停止該程序，選另一個空閒 loopback port。
- [ ] 只可逆重啟確認屬本專題且本次允許處理的程序，或啟動自己的候選 port。記新 PID、host、port、cwd、release hash、server records-dir；修改檔案不表示舊 8766 已切 manual。
- [ ] 以真正 manual launcher、原真 engine、**明示合成價格**跑實際瀏覽器表單 A／可比 B／不可比降 A／公斤台斤／日期／錯誤／等待；開桌面與窄螢幕頁，核對卡片、警告、限制與 t+7／t+14。
- [ ] 保存→載入→匯出→刪除走真 API request_id 暫存與 records 全流程，所有檔案只能在 `DE09/records/`。不混入原 `private/predictions`，不收真人店資料；合成輸入及其測試來源寫在 sidecar／報告，不宣稱真店實驗，也不弱化既有 simulated 防護。
- [ ] 瀏覽器 request trace 無 agent status／query；provider／KEY／外部模型 call 攔截數為零，直接 agent endpoint 拒絕。ChatGPT／tunnel 程序完全離線時再跑一次表單，證明入口可獨立使用。

**允許改檔／操作：** DE09 隔離紀錄／截圖／log；自己的已確認候選程序與 loopback port；若發現缺陷，只回 DE02／DE03 範圍修復。不停止他人程序，不讀 KEY，不恢復 GLM／Qwen。

**驗證與反向控制：** 缺價／bool 或無效數／未知單位／非法日期、不可比 B、偽造保存 request_id／客戶端完整結果、非法刪除 ID、records-dir 客戶端注入均受控失敗。真值與原 tool/API JSON 對照；移除 ChatGPT／通道後網頁仍成功。禁止只用 TestClient 或靜態截圖冒充本階段實跑。

**預定命令（NOT_RUN）：** Windows listener／程序 inspector（實際 cwd 核對另附可靠證據）；`& .venv\Scripts\python.exe -m aiot_price.integrations.manual_web --host 127.0.0.1 --port <確認可用port> --release-dir <凍結release絕對路徑> --records-dir <DE09/records絕對路徑> --home <DE09/runtime_home絕對路徑>`；實際 browser 流程由 Windows COS 操作並記錄。

**證據：** `DE09/process_identity.json`、restart／rollback receipt、browser 請求記錄、API 原 JSON、records 流程匯出與原目錄不變、各畫面與 `visual_review.md`、tunnel-off 表單證據。

**完成／退回／停點：** 真網頁／真 engine／隔離 records／無 provider 四項都有本輪證據。無 reviewer 時只寫「隔離本機候選實測」；未審不升 final。程序身分不明則選另一 port；來源保護不符立即 FAIL。

## DE10 — 個人帳號權限與私人通道

**前置：** DE08 實作審查門檻通過。**初始：** HOLD（本人權限未確認）；驗證 NOT_RUN。

**執行內容：**

- [ ] 只用 **Windows COS／本機 Windows**；不要調用 Ubuntu COS、RTX 3090 或 SERVER。先重查當時官方 [Secure MCP Tunnels](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels) 與 [Connect ChatGPT](https://developers.openai.com/plugins/deploy/connect-chatgpt)，記查核日、讀取段落與實際 CLI 語法。
- [ ] 分開查本人 ChatGPT 個人工作區的「新增 custom MCP／插件」權限，以及本人 Platform personal organization 的 `Tunnels Read／Manage／Use`，逐項填可用／不可用／UNKNOWN。個人帳號、個人 organization、runtime key 三者不等於權限已具備。
- [ ] 本人自行登入、選本人工作區／organization、完成必要 UI 授權；執行者不切帳號、不恢復憑證、不借 GLM／Claude KEY、不買方案、不推定權限或訂閱可用。
- [ ] 權限齊備才依當時官方方法建立私人 tunnel_id／受保護本機 runtime key 設定，運行 tunnel-client doctor 與 Windows stdio MCP。runtime API key 用於通道控制，**不等於模型 API KEY，也不使本工具呼叫 OpenAI 模型 API**。
- [ ] 秘密由本人填入受保護設定，執行者與報告不讀／不印 key 值，key 不上 source／命令列／log／chat；通道憑證不傳入 engine worker。只建立本人私用連線，不公開入站、防火牆、外網轉送或其他使用者。

**允許改檔／操作：** DE10 遮蔽權限矩陣與通道健康證據、本人成立的私人通道／私用插件設定；不改 source／舊帳號／舊 KEY。憑證設定不是交付檔，不能抄進證據。

**驗證與反向控制：** doctor／tunnel 狀態與 ChatGPT 能辨識本人的兩工具分開驗；用不帶秘密的缺設定／斷通道案例確認受控失敗，不把 doctor 綠當 ChatGPT call 成功。不以變更本人角色／撤銷 key 製造失敗案例。

**預定命令（NOT_RUN）：** 當時官方查證後的 tunnel-client version／doctor／run 命令；目前不虛構安裝版本或 token 參數。全部實際命令去秘密後保存。

**證據：** `DE10/official_sources.md`、`permissions_matrix.md`、client version、doctor／run log、遮蔽 tunnel 關聯／工具可見性證據；本人 login／authorization 步驟及未完成點分列。

**完成／退回／停點：** 權限與私人通道實測成立才進 DE11。任何缺權限／需本人操作時 DE10／DE11 HOLD 並記實際原因；不可轉成公開方案。只停帳號層，已授權本機及 DE12 繼續，沒有重新要求使用者選方向。

## DE11 — 真 ChatGPT 端到端實測

**前置：** DE10 真實通過；DE09 的網頁結果另計。**初始：** HOLD；驗證 NOT_RUN。

**執行內容：**

- [ ] 本人私用 ChatGPT 對話實際選 TW01 插件，用明示合成價格做行情、A 預測、缺價追問、公斤／台斤、歷史日／台北跨日、陳舊公開資料與資料不足案例。
- [ ] 記每案原聊天要求（僅合成必要片段）、tool name／實際 arguments／原 structuredContent 與受控文字、最後回答。將原 JSON 的價格／方向／單位／t+7／t+14／版本／warnings／限制逐項與最後文字核對。
- [ ] 缺品項／市場／價／單位需追問，不能替使用者選市場或猜價；明示「公開均價、非店家真值」「店價推估未同店驗證」「未勝簡單基線」，不用模型文字填空缺數值、機率、因果或省錢。
- [ ] 實際要求 B／上週價／保存／讀全體紀錄／任意 URL／path／code，確認 ChatGPT 說明第一版限制，server schema／dispatch 仍拒絕違規 call。回顯工具參數不是真人確認，最後自由文字不會自動通過原網頁 validator。
- [ ] 做真通道人工斷線／重開後的 initialize／list／call 與 ChatGPT 恢復案例；與 DE06 原生本機恢復分開。沒有實際 ChatGPT tool call 就不宣稱已連上或插件可用。

**允許改檔／操作：** 本人已授權私用對話與 DE11 合成驗收證據；必要 plugin 描述／RUNBOOK 文案局部。錯誤只回相應 DE01／05／06／10 修復，不擴到 B／保存／自訂 UI 卡片。

**驗證與反向控制：** 真 ChatGPT 最後回答核對 checker 的正常 case 應通過；在隔離證據副本故意改一個價格或日期，checker 非零。若模型最後文字錯誤，記 FAIL 並保留原工具 JSON，不能只改提示詞後稱保證正確；受影響案例需重跑。

**預定命令（NOT_RUN）：** Windows COS 的真正 ChatGPT browser/tool-call 操作；本階段 final-answer checker 的正向與偽值副本命令。命令、工具數及退出碼以實際操作為準，現在沒有 E2E 成功 log。

**證據：** `DE11/e2e_case_matrix.md`、各案必要片段／tool input-output／最後文字對照、合成標記、checker 正反 log、通道斷線與人工恢復證據；不記私人真店資料或秘密。

**完成／退回／停點：** 真 ChatGPT＋真私人通道＋真 frozen engine 的完整證據才可說「個人插件已實測」。模型回覆、server 值、通道三層分別判定；沒有權限／未操作則 HOLD／NOT_RUN，不能用 native MCP 或 doctor 代替。

## DE12 — 收尾與分層交付

**前置：** DE09 與 DE11 通過；或 DE10／DE11 HOLD 時，完成可做的本機候選與缺口交付。缺獨立 reviewer 時適用 DE08 的候選限制。**初始：** TODO；驗證 NOT_RUN。

**執行內容：**

- [ ] 再比對原 14 保護與整個 release 五檔 baseline、原 `.venv` ML freeze、增量 diff／untracked 清單；排除憑證／私人資料及越權變更。不得把最後 hash 重新定義為最初基準。
- [ ] 寫 `docs/CHATGPT_PLUGIN.md`／本包 RUNBOOK：兩入口操作、確切 interpreter／SDK pin／release hash、manual CLI、server records-dir、stdio worker、15 秒超時、人工停止／重開、權限缺項與 rollback。
- [ ] root `TASKS.md` 只增本包入口與逐層真實狀態，不擅改 T16／LLM／SERVER／期末發布等舊關卡。候選與 final、作者自驗／獨立代理人複核／正式外部驗收各自標示。
- [ ] 收斂實際檔案／測試／失敗返修史、原始 log／輸出精確路徑與重建指令；新 checksum manifest 最後生成且不含自身，不刪失敗 evidence。
- [ ] 分層列網頁表單、A／B／records、本機原生 MCP、硬超時、本人權限／私人通道、真 ChatGPT 文字核對。真店到期 A／B、Qwen／GLM／Hermes、3090／SERVER、外網多人、公開插件、影片、GitHub／YouTube／課程提交仍不在本包完成聲明內。

**允許改檔：** 本包／RUNBOOK、`docs/CHATGPT_PLUGIN.md`、root `TASKS.md` 本包入口、DE12 證據；不 commit／push／發布，不補做未授權範圍。

**驗證與反向控制：** 交付清單逐項實開，命令與 artifacts 可定位；checker 掃到偽造 PASS／缺證據／秘密占位或故意刪除的一份隔離交付檔副本，須報缺口非零。正向交付清單不得含未生成檔案或虛構 reviewer。

**預定命令（NOT_RUN）：** DE00 只讀 baseline checker、逐檔交付／連結／狀態一致性 checker、`git status --short --untracked-files=all`／`git diff --name-only`；執行者記真正完整命令與退出碼。

**證據：** `DE12/final_scope.*`、`final_baseline_check.json`、`delivery_manifest.json`、checksum、`acceptance_matrix.md`、`failure_history.md`、`handoff.md`、rollback／剩餘 HOLD 清單。

**完成／退回／停點：** 本包可如實交付「本機驗證＋個人插件實測」，或「本機候選＋帳號層 HOLD」；無正式獨立外審就保持外審 HOLD，未審候選不升 final。**文件完成、套件可 import、測試綠、doctor 綠、hash 一致都不能單獨代表產品完成。**

## 本次文件整理的完成界線

這份 TASKS 只記錄可執行工作順序與驗收要求。沒有建立上述新產品模組／測試、沒有安裝 SDK、沒有跑產品測試、沒有重啟 8766、沒有讀 KEY、沒有操作 COS／本人帳號／3090。產品各階段仍如首頁 `TODO／HOLD＋NOT_RUN`；後續執行者須以真正新 run 的原始證據更新，不回填本文件日期的成功紀錄。
