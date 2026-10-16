## 最新 TW01 私人連線驗證（2026-10-14T04:54:46.111969+08:00；本節優先）

本人專用「TW01 菜價查詢與 A 預測」已建立、已連線，且已取得真正 ChatGPT 原始 application 工具呼叫與結果；目前是 SELF_CHECK_ACCOUNT_CANDIDATE，正式 EXTERNAL_PASS 仍 HOLD。此節以下較早的 DE10／DE11 HOLD 是歷史狀態，原文完整保留。

一般網頁：http://127.0.0.1:8766/ ，收尾 health=ready、manual/chat_disabled、PID80052。私人插件：https://chatgpt.com/plugins/plugin_asdk_app_6ace7f59fe488191af7942bee81bb93f 。正常專用 client PID89804，loopback readyz200；人工重連後的新行情已恢復。驗收 observer 已停止，日常連線不持續捕獲對話。

網頁：manual_web → /forecast(A/B、台斤/公斤、t+7/t+14)及本機 /records → 凍結 ForecastEngine(RF7/HGB14)。ChatGPT：專用私人 Tunnel → 官方 client → SDK stdio／入站界限與 watchdog → 獨立 worker Job → 原 AgentTools／同一凍結 Engine；恰兩工具 get_market_quote、post_forecast(匿名A)，不提供 B、保存、私人紀錄、任意 URL、檔案或程式。

真實案例、原始參數／structuredContent、完整獨立 Engine JSON、原回答與檢查結果：C:\Users\prometheans\Documents\AIOT_FinishProject\outputs\quality_runs\chatgpt_dual_entry_account_followup_20261014014708_Windows5800X\DE11\cases；逐案及全部限制見 C:\Users\prometheans\Documents\AIOT_FinishProject\outputs\quality_runs\chatgpt_dual_entry_account_followup_20261014014708_Windows5800X\DE12\acceptance_matrix.md。檢查器只驗支援的文字格式；未支援或缺說明的原回答保留非零，不改寫成 PASS。行情原案價格／日期污染副本各 exit1。

原19/19 SHA256/size、ML原104行 freeze不變。原整合120、產品564、repo593(--ignore=outputs)回歸 exit0/skip0；裸repo22 collection errors/exit2保留。帳號續作沒有再改產品source/tests、模型或公開資料。離線雲端請求等待逾60秒後人工取消，該體驗仍HOLD；Windows不是硬即時系統，原公開模型未勝相應簡單基線，真店A/B仍未驗證，公開歷史截至2026-10-02。

正常啟動只用本輪已核實的 C:\Users\prometheans\Documents\AIOT_FinishProject\outputs\quality_runs\chatgpt_dual_entry_account_followup_20261014014708_Windows5800X\DE10\tw01_tunnel.ps1 -Action Run（PowerShell7；已有profile時不要再Init）。用file:key參照，agent沒有讀取／印出／hash runtime key。沒有 commit/push、重訓、公开部署、Qwen／3090／Ubuntu操作或借用舊 COS 通道。證據、恢復步驟、checksum正反驗證與独立審查入口：C:\Users\prometheans\Documents\AIOT_FinishProject\outputs\quality_runs\chatgpt_dual_entry_account_followup_20261014014708_Windows5800X\DE12\handoff.md。

---

## 最新 Codex 候選（2026-10-14；本節優先）

# TW01 本輪候選交付

更新：2026-10-14T00:52:48.571008+08:00；主機 Windows 5800X；HEAD `9e29cddce8687489dcd07bc2f8d673d2e0a72ce3`。

**SELF_CHECK_LOCAL_CANDIDATE。獨立代理人：INDEPENDENT_AGENT_PASS；正式 EXTERNAL_PASS：HOLD。本人ChatGPT插件尚未接通，DE10/DE11 HOLD。**

本輪交付補充（2026-10-14）：私人通道 helper 的繼承環境與 profile 漂移缺口，以及交付 checker 的缺件／虛假獨立 PASS 缺口，均已有原始 RED、最小修補及另一上下文的親自重跑。追加原文：`C:\Users\prometheans\Documents\AIOT_FinishProject\outputs\quality_runs\chatgpt_dual_entry_codex_20261013_235947_Windows5800X\DE08\independent\delivery_addendum.md`；原核心 46 檔審查身份不变。helper 作者假 client 最終 16 passed/exit 0，關掉環境清理的隔離副本 exit 1；獨立 reviewer 自己的假 client 與真空設定拒絕分開記錄。**真 tunnel-client Init/Doctor/Run、帳號權限、ChatGPT E2E 仍 NOT_RUN/HOLD。**

私人接線準備位置是 `C:\Users\prometheans\Documents\AIOT_FinishProject\private\tw01_chatgpt_tunnel_codex_20261014`：本人只將新專用 ID 寫入 `tunnel-id.txt`、新 runtime key 寫入 `runtime-key.txt`；不要貼金鑰到聊天。本輪兩檔仍為空，ACL 已去繼承。receipt 的原欄位 `acl_inheritance=true` 實際存的是 AreAccessRulesProtected，已保留原件並更名 `inheritance_disabled=true`，沒有改動權限或讀值。

本人完成工作區選擇、專用通道／key 與風險授權後，才用 PowerShell 7 執行下方 future helper；現在不是成功接線證據。它使用清空後的子環境、固定 ID／file:key 參照／loopback、固定 MCP command，Init 不覆寫既有 profile，Doctor/Run 先驗 profile SHA256 與 identity。官方 client version/init/doctor/run help 已親跑；只讀 help 不等於 doctor/run。

```powershell
pwsh -NoProfile -File "C:\Users\prometheans\Documents\AIOT_FinishProject\outputs\quality_runs\chatgpt_dual_entry_codex_20261013_235947_Windows5800X\DE10\tw01_tunnel.ps1" -Action Init
pwsh -NoProfile -File "C:\Users\prometheans\Documents\AIOT_FinishProject\outputs\quality_runs\chatgpt_dual_entry_codex_20261013_235947_Windows5800X\DE10\tw01_tunnel.ps1" -Action Doctor
pwsh -NoProfile -File "C:\Users\prometheans\Documents\AIOT_FinishProject\outputs\quality_runs\chatgpt_dual_entry_codex_20261013_235947_Windows5800X\DE10\tw01_tunnel.ps1" -Action Run
```

剩餘驗收限制：Windows 排程不是硬即時保證；入站 bound 不等於全機 OOM 保證；公開歷史仍封存截至 2026-10-02（封存前 health 親查），原公開測試未勝對應簡單基線，真店到期 A/B 尚未驗證；本輪 Chrome 目視遭工具拒絕；私人通道權限、ChatGPT 最終自由文字與斷線恢復均未驗證。已重現的本機重要缺陷關閉，ChatGPT 入口仍不具正式啟用條件，正式 EXTERNAL_PASS 仍 HOLD。

實際可使用網址：http://127.0.0.1:8766/ ，本輪再次health=ready、manual/chat_disabled；既有PID80052未重啟。另自行啟停隔離candidate跑22個真正HTTP請求。Chrome自動化拒開`ERR_BLOCKED_BY_CLIENT`，本輪無新桌面/手機圖，不將HTTP或舊37checks當新Chrome验收。

架構：manual browser→manual_web→原API /forecast、/records→凍結ForecastEngine（RF7/HGB14，A/B固定alpha0.3）；ChatGPT（未接通）→TW01專用私人Tunnel（未成立）→tunnel-client→官方SDK stdio/Binary ingress guard→兩工具嚴格schema/watchdog→每呼叫suspended worker Job→原ML隔離worker→adapter/AgentTools/同一凍結release。兩入口各自程序，不走/agent/query，不需要模型API。

真回歸：整合 **120 passed/127 warnings**；產品tests **564 passed/6995 warnings**；repository **593 passed/6995 warnings（明示--ignore=outputs）**，各exit0/skip0。三組範圍嵌套，不相加。裸repo本輪exit2/22 collection errors，源於outputs的歷史及本輪可逆backup同名檔，不刪封存或稱裸全repoPASS。

原19項SHA256/size不變（18 unique），ML原104行freeze逐行不變；初始103行源於PYTHONPATH=src的egg-info遮蔽，有獨立親重現。

主安全修復：watchdog不再將4s當額外工作時間；每worker在執行前入獨立Job、正常/取消/超時清整個後代；入站raw line16384 bytes/depth16/全訊息128members/key64bytes；arguments≤5欄且不排序/回顯巨量extra；SDK input schema完整移入已註冊watchdog的handler。

15秒從自訂call_tool dispatch計，包含lock等待、輸入/輸出schema及worker decode。bounded ingress framing/SDK JSON-RPC解析先於它。真同步阻塞首次OS停止約15.000–15.016s；最多4s僅清理/確認。這是實測容差，不是硬即時Windows排程保證。拒收ingress的Windows launcher曾exit0，仍有固定診斷、無attack response及實際關閉；negative checker另有exit1。

原始數值限制不變：公開均價非店家真值、正式公開測試未勝對應簡單基線、同店到期A/B尚無證據、機率/區間null。沒有重訓/修改正式模型與資料，不接Qwen/3090/Ubuntu，不改/借既有Tunnel，不讀私人record/key，不commit/push/公開部署/購買。

本輪證據絕對路徑：`C:\Users\prometheans\Documents\AIOT_FinishProject\outputs\quality_runs\chatgpt_dual_entry_codex_20261013_235947_Windows5800X`。原始使用者規格及舊各輪失敗均保留。精確重跑看下方handoff；回滾依backup前後hash逐檔，不reset/clean。

本節原始証據：`outputs/quality_runs/chatgpt_dual_entry_codex_20261013_235947_Windows5800X/DE12/`，獨立原文`outputs/quality_runs/chatgpt_dual_entry_codex_20261013_235947_Windows5800X/DE08/independent/independent_review.md`。
新版完整重跑與短TEMP操作看`outputs/quality_runs/chatgpt_dual_entry_codex_20261013_235947_Windows5800X/DE12/handoff.md`。以下各輪敘述保留作歷史紀錄；舊測試數/未閉合狀態/15+4工作敘述不能替代本輪實測。

---

# TW01 個人 ChatGPT 插件 — Windows MCP 試用候選

**日期：2026-10-13；執行者：本輪 ChatGPT + Windows COS；驗收層級：SELF_CHECK（非獨立或本人 ChatGPT E2E）。**

## 現狀（不可混淆）

1. **已在 Windows 上實作並用原生 MCP SDK 驗證**兩項唯讀工具：`get_market_quote`（公開臺中市場均價）和 `post_forecast`（使用者當日店價 A 模式 t+7/t+14）。正式數字只來自凍結 `ForecastEngine` + `AgentTools`。
2. **未完成** 私人 tunnel、本人 ChatGPT plugin 安裝、ChatGPT 模型選工具／回覆驗收。不能將本機 `initialize/tools/list/tools/call` 稱為 ChatGPT 真接通。DE10/DE11 HOLD；無獨立審查，DE08 HOLD。
3. 網頁手動入口是完全**另一條路**，在 Windows 回圈位址 `http://127.0.0.1:8766/` 使用原模型，保留 A/B 與經使用者按鈕確認的本機隔離 records；它不需要 GLM、Qwen、OpenAI 帳號或 MCP，不與 MCP 交換紀錄。

## 架構／兩個 Python 環境

```text
Windows loopback browser (manual only, not a ChatGPT app)
  -> web/{index.html,app.js,style.css}
  -> manual_web.py -> api/app.py /forecast + /records
                      -> ForecastEngine(release 0.1.0) [original .venv]
                      -> DE09/records (voluntary save only)

Future personal ChatGPT (NOT CONNECTED; no active tunnel)
  -> OpenAI Secure MCP Tunnel [HOLD: user rights, tunnel_id, runtime key]
  -> chatgpt_mcp.py (separate transport venv; official mcp==1.30.0)
      stdio JSON-RPC; tools/list advertises only two read-only schemas
      serial async lock; fixed 15s numeric-work budget, separately bounded cleanup
      Windows Job Object kill-on-close + independent OS-thread watchdog
  -> subprocess mcp_worker.py (original numeric .venv, allowlisted env)
  -> chatgpt_adapter.py -> AgentTools(ForecastEngine(frozen release 0.1.0))
      -> quote or A only -> structuredContent + controlled Chinese fact_text
      (no network/provider calls, no private records path, no B/save tool)
```

## 本機啟動（僅 Windows，PowerShell，在專案根）

以下為已使用/驗證的程式入口；`<RUN>` 替換成本輪完整相對目錄 `outputs/quality_runs/chatgpt_dual_entry_impl_20261013_1349_Windows5800X`。不要複製範例中的帳號、密碼、API key；本文件完全不需要秘密。

```powershell
$r=(Resolve-Path 'outputs\quality_runs\chatgpt_dual_entry_impl_20261013_1349_Windows5800X').Path
$root=(Get-Location).Path
$env:PYTHONPATH='src'
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'

# 原本的 ML interpreter，提供 Windows 本機表單及保存到隔離目錄
& .\.venv\Scripts\python.exe -X utf8 -m aiot_price.integrations.manual_web `
  --host 127.0.0.1 --port 8766 `
  --release-dir (Join-Path $root 'models\releases\0.1.0') `
  --records-dir (Join-Path $r 'DE09\records') `
  --home (Join-Path $r 'DE09\runtime_home')

# 在另一個 PowerShell 工作階段，transport venv；只測 stdio，不自行公開
& (Join-Path $r 'DE04\transport_venv\Scripts\python.exe') -X utf8 `
  -m aiot_price.integrations.chatgpt_mcp `
  --release-dir (Join-Path $root 'models\releases\0.1.0') `
  --worker-python (Join-Path $root '.venv\Scripts\python.exe') `
  --home (Join-Path $r 'DE06\native_home')
```

啟動前先確認 8766 未被他人占用；本輪實測程序身分、PID、反向案例見 `DE09/process_identity_after_date_repair.json`。MCP stdio 程序的 stdout 不適合人工操作或一般 HTTP curl；原生 SDK client 實測腳本在 `DE06/native_probe.py`。原生 session log 在 `DE06/native_session_after_fix.json`。

依賴：`pyproject.toml` 的獨立 extra `mcp`，完整解析清單 `requirements/chatgpt-mcp.lock`；切勿直接在原本 `.venv` 安裝或升級 MCP/ML 相依套件。選用官方 Python SDK **v1.30.0 維護分支**的已核 release（不是假稱最新 v2）；此包是穩定的 stdio 小型候選，尚未升級 v2。Windows 上 pin 的 `tzdata==2025.3` 是必需的；未安裝時第一次原生 initialize 會因 Asia/Taipei ZoneInfo 失敗（失敗 log 已保留）。

## 工具語意與限制

- **兩個工具、僅唯讀**：`get_market_quote(crop_id, market_id)`；`post_forecast(crop_id, market_id, current_price, price_unit, observed_on?)`。無 B、previous_price、store_id、save_record、URL／檔案位置、程式執行、使用者定義 timeout。
- 支援三菜（cabbage/bok_choy/sponge_gourd）、13 個臺中市場、元／台斤或元／公斤；今日店價為正有限數，不可 bool。觀測日採台北時區，未填時使用台北今日日期，規定中午時間錨定，目標日期是精確 t+7、t+14。
- 公開行情不是即時店家售價。回傳同時列出行情實際觀測日、資料快照截止日、在截止日的價齡、相對查詢日的價齡；不能以截止日冒稱實際報價日期。
- 未經同店到期配對驗證；公開方向 macro-F1 與相對變化 MAE 均不優於相應基線；不得宣稱實際買菜命中率或模型推估機率/信賴區間。原版 warning/版本/target_scope/validation_scope 在結構化回覆保留。
- 15 秒是固定的 **tool dispatch 起算（包含 serial-lock 排隊）的數值工作預算**，並非任何 Windows 狀況都能保證在 15.000 秒內完成程序清理。必要的 worker 退出確認／失敗關閉另有最多 4 秒容限；watchdog 以獨立 OS thread 監督工作期限加清理容限，並依 Windows Job Object `KILL_ON_JOB_CLOSE` 終止獨立 transport 的子程序。這是 bounded fail-closed 設計，不是嚴格即時 OS 保證。超時後需人工重開 MCP／私人通道；不支援無限重試、背景續跑、未授權連線。

## 正式連接的必要條件（目前 HOLD）

依 2026-10-13 官方文檔核對：<https://developers.openai.com/api/docs/guides/secure-mcp-tunnels>、<https://developers.openai.com/plugins/deploy/connect-chatgpt>。

1. **本人**在 ChatGPT 工作區確認可新增 custom MCP server；本人 Platform personal organization 具備 Tunnels Read+Manage（建立）及 Read+Use（運行/選取），並有可用的 `tunnel_id` 和獨立 runtime API key。登入與秘密由本人在核准介面／受保護配置中提供，執行者不讀、不印、不借舊模型 key。
2. 取得並獨立驗證官方 `tunnel-client`；配置 `--mcp-command` 指向本機上述 stdio 程序，執行 `tunnel-client doctor --profile <個人設定> --explain` 與 `run`，由 `/healthz`、`/readyz` 與控制 UI 實測可用；保持本機無公開入站 listener。
3. 在本人 ChatGPT Plugins 新增 custom MCP server，Connection 選 Tunnel，綁定本人工作區/組織，核對 SDK metadata 與兩工具。使用合成菜價實際 `@` 插件對話測 tool selection、追問缺參數、日期、價齡、結構化值與最終文字。執行證據另立新階段；成功前狀態不得更改。

本輪未發現 `tunnel-client` 在 Windows PATH 內，沒有合法可核的 tunnel_id／runtime key／工作區權限；DE10/DE11 依交接規定保持 HOLD，**沒有建立任何對外通道**。

## 測試與回滾

- 新整合測試：`& .\.venv\Scripts\python.exe -X utf8 -m pytest tests/integrations -q`（需 `TW01_MCP_RUN` 和 `TW01_MCP_PYTHON` 指向本輪 SDK 環境，才會執行 native 交握而非跳過）。
- 全產品：`pytest tests -q`；裸 `pytest -q` 會收集多年 output 封存下同名腳本而衝突，保留失敗、再明示 `--ignore=outputs` 重跑。全部 log 在本輪 `DE07`。
- 範例／逆向：`DE01/contract_checker.py` 與 `DE05/result_checker.py`，故意污染 copy 的 schema／價格必須非零；`DE07/protected_positive.json` 19/19 SHA 不變，修改 baseline 副本 checker 非零。
- 不動任何受保護模型/資料；同目錄 `backups` 包含本輪開始前已 dirty 的原始允許改檔版本。回滾先核對 file SHA 和 Git diff，再逐檔手動恢復特定本輪增量，禁止 `git reset --hard` 或 `git clean`。不要以歷史備份覆寫在本輪以後可能由他人再修改的檔案。

視覺補正：390px 手機 B 對照原左右各174px過窄；保留 `DE09/mobile_AB_before_responsive_fix.png`，已改成 A、B 上下兩張完整寬度卡片並以真 Chrome 重新量測／截圖 `DE09/mobile_AB_followup.png`。原模型歷史日警示提到的「今天」，網頁另行解釋為使用者報價基準日，沒有改動引擎原文。

狀態詳見 `outputs/quality_runs/chatgpt_dual_entry_impl_20261013_1349_Windows5800X/DE12/acceptance_matrix.md`；本人 ChatGPT 端測試和獨立外部複審均未完成。

## 2026-10-13 後續程式硬化／私人通道候選（以本節為新狀態）

新的 Windows COS 續作封存：`outputs/quality_runs/chatgpt_dual_entry_followup_20261013_1516_Windows5800X/`，沒有覆寫前輪基準與舊有錯誤。正式 stdio server 仍在 `src/aiot_price/integrations/chatgpt_mcp.py`，但已改用 async worker subprocess，**從接到工具呼叫時起**計算固定15秒，連等待 serial lock 一併計入；在逾時或呼叫取消時確實 kill child/確認退出才回應，避免背景殘留。新增測試 `tests/integrations/test_mcp_dispatch_deadline.py`，4 passed；整合 49 passed、`pytest -q --ignore=outputs` 全庫 522 passed，另有新原生 MCP session 2工具／6呼叫成功。結果與完整首次失敗/返修詳見 `DE09/test_results.md`。

本人 Platform 的 Tunnels 頁 `https://platform.openai.com/settings/organization/tunnels` 已可查看清單，並有建立/編輯操作入口；但未真測 Manage/Use、沒有建立**TW01 專用**通道或碰現有 COS／3090 通道。2026-10-06 公開的官方 Windows `tunnel-client v0.0.16` 已在續作 `DE10/transport_candidate_v0.0.16/extracted/tunnel-client.exe` 隔離放置，下載 ZIP 的 SHA256 與官方 release `SHA256SUMS.txt`、GitHub API digest 相同，`--version` exit0。沒有 runtime key，故 **`init`、`doctor`、`run` 全部 NOT_RUN**，不能用 `--version` 冒稱私人 tunnel 成功。部署前仍需新的獨立 DE08 reviewer 和本人進行帳號私用授權。

## 最新 Windows 5800X 本機安全收尾（2026-10-13 22 時後）

最新實作與驗證封存：`outputs/quality_runs/chatgpt_dual_entry_continuation_20261013_2125_Windows5800X/`。`chatgpt_mcp.py` 已使用 bounded async pipe、worker spawn 取消後的 Job Object fail-closed、串行鎖等待計時；`windows_job_guard.py` 將 `TransportDeadlineWatchdog` 由獨立 OS thread 驅動，並在同一 condition lock 中對到期中的工具呼叫做關閉決策，避免完成／取消註銷與關閉的競態。只有專用 MCP 程序 `main()` 安裝 Job Object；**共享 COS host、pytest 或 8766 Web 程序不可安裝或終止**。

最新版驗證：`DE06/race_native_target_stdout.log` 的 9 項定點通過，`DE06/integrations_after_race_stdout.log` 的 77 項整合通過，`DE07/after_race_tests_stdout.log` 的 521 項產品測試通過，`DE07/after_race_repo_ignore_outputs_stdout.log` 的 550 項明示排除封存回歸通過；原 14+5 baseline 仍一致，ML `.venv` freeze 104 行前後相同。**這些全部只是作者 SELF_CHECK**，不是獨立正式驗收；早期裸 `pytest -q` 的封存同名測試 collection error 仍保留。

最新獨立 reviewer 無法安全啟動，DE08 仍 `HOLD/REQUEST_CHANGES`；Windows 候選 `tunnel-client v0.0.16 --version` exit0（新紀錄 `DE10/candidate_client_status.json`），但尚無 TW01 專用 tunnel、使用者的 runtime 通道憑證與所需操作權限驗證，**doctor/run 與本人 ChatGPT 真 E2E 均 NOT_RUN**。DE10、DE11 繼續 `HOLD`，沒有公開部署、借用既有 tunnel、或使用模型 API key。最新版分層證據在 `DE12/acceptance_matrix.md`，不可引用舊版 checksum 充當新 source 雜湊。

## 23 時新版方向驗證返修及實際 Platform／ChatGPT 權限觀察

本輪來源與原始證據根：`outputs/quality_runs/chatgpt_dual_entry_continuation_20261013_2251_Windows5800X/`。新上下文 Codex 真正透過自己的 Windows command 讀原碼的嘗試遭 policy `BLOCKED`，未能獨立跑測試；改以**作者擷取、附來源 SHA256／行號的 11 個文字檔片段**交給新 Codex context，得到 `STATIC_ONLY_REQUEST_CHANGES`。**這不是 DE08 獨立實讀＋重跑通過，也不是正式 EXTERNAL_PASS**。

文字審查指出 `chatgpt_adapter.py` 對相對變化靠近 ±5% 四位小數門檻時原先跳過方向驗證。原本 mock 假資料在模型結果中注入 `unknown`、反方向、`insufficient_data` 時會錯誤通過；`DE05/direction_red_stdout.log` 是 **5 failed／4 passed**。只修 adapter 中允許 `flat/up/down`、正常結果僅 `unvalidated`，近門檻只准持平或符合正負號的相鄰方向，原始 RF/HGB 價格和規則完全不動。返修後 `test_chatgpt_mcp.py` **21 passed**；全整合 **86 passed**、產品 `tests/` **530 passed**、指定 `--ignore=outputs` repository **559 passed**（全 exit0）。仍有審查未關閉的工作/清理時間界線、潛在 worker 後代清理證據和 MCP inbound 尺寸證明，見新 `DE08/static_review_disposition.md`；不可擅自宣稱 DE06 形式化嚴格 15 秒總 OS deadline 或完整程序樹無 orphan。

同輪透過 **Windows COS Desktop 真實已登入瀏覽器**，見 Platform `Personal Organization` Tunnels 清單既有 COS Core／Desktop／Antigravity／Ubuntu3090 四條**非 TW01** 通道；ChatGPT Plugins 畫面有 `新增` 入口。顯示建立按鈕並不等於已驗證 Platform Tunnels `Read/Manage/Use`、ChatGPT workspace custom MCP 的最終許可或已完成本人風險授權。官方 2026-10-13 文檔 [Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)／[Connect and test your plugin](https://developers.openai.com/plugins/deploy/connect-chatgpt) 要求本人專用 `tunnel_id`、runtime key、組織／工作區關聯及真正 `doctor/run`、ChatGPT `@` 工具呼叫。**本輪未創建/借用任何通道，doctor/run 和 DE11 真 E2E 都 NOT_RUN；DE10/DE11 仍 HOLD。** 新證據見 `DE10/permissions_observed.md`／`DE11/status.md`。
