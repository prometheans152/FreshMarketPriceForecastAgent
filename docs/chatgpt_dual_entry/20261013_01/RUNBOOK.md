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

# TW01 DE00–DE12：2026-10-13 Windows COS 本機執行記錄

**注意：本文件記錄本輪真正執行後的現況；原 `TASKS.md` 與 `COS_HANDOFF_PROMPT.md` 作為未修改的原始規格。**

- 工作根：`C:\Users\prometheans\Documents\AIOT_FinishProject`
- 本輪執行證據：`outputs/quality_runs/chatgpt_dual_entry_impl_20261013_1349_Windows5800X/`，所有 DE00–DE12 原始 log、自驗/負向控制、Chrome 截圖及工具 JSON 均在其下。
- 實測表單：`http://127.0.0.1:8766/`（Windows **同一台電腦**，不對外公開）。由 `manual_web.py` 提供，獨立 `DE09/records/` 合成資料；不是 GLM 或 MCP Web UI。
- MCP：僅 **本機原生 SDK initialize/list/call** 成功，tools/list 嚴格兩項；未連本人 ChatGPT。若無帳號權限不能用真 MCP 工具回覆 ChatGPT。
- SDK: Python 官方 `mcp==1.30.0`，獨立 transport Python + Windows tzdata；ML `.venv` 原套件未修改、frozen release 五檔 SHA 與受保護 14 檔均未更動。
- 不使用 Qwen／3090／Ubuntu Server，不重訓、不 commit/push/公開部署。

## 開發增量及檢查

本輪新增 `src/aiot_price/integrations/` 六個 Python 模組，修改 `src/aiot_price/api/app.py` 以無模型入口配置隔離聊天，以及 `web/` 三個檔案移除 GLM 聊天段（原檔保存在 run/backups 及 legacy test fixture）；原有 `/forecast` 模型算法與封存 release 未修改。隔離 manual 模式加了未來日驗證，舊非 manual API 保持原樣。預測保存只接受 request_id，由 server 端取暫存原回應。

正式本機測試是以 Windows 執行的真瀏覽器 Chrome（含 390px 與 1280px）、原始 ForecastEngine 和最終輸入／輸出測試。合成值 32 元／台斤、28 元／台斤上週價、65 元／公斤，非真實顧客／店家資料。Chrome 37/37 與截圖、request trace 見 `DE09/browser_e2e_success.json` 以及對應 PNG。後續實查 390px **B** 原左右欄各174px 過密，已留原樣於 `mobile_AB_before_responsive_fix.png`，改為上下358px單欄後重開真 Chrome 驗 `mobile_AB_followup.json` 及圖片；再次跑全 Chrome 37/37，原成功畫面另封存在 `DE09/pre_responsive_e2e/`。

## 實驗負例與返修

1. 原生 MCP 初次 initialize 在 Windows 缺 `tzdata` 而失敗：`DE06/native_stderr_first.log`；改隔離傳輸環境加 pin，`native_session_after_fix.json` 真實 initialize/兩工具/六呼叫成功。
2. 第一次完整 `tests/`：`DE07/product_full_first.log`，473 pass、16 fail。13 類歷史聊天前端斷言和無聊天表單互斥，故保留原網頁測試的精確前版 fixture（不刪其測試），另用現行表單專屬整合測試驗證無 agent。既有記錄函式相容和 legacy .env 測試隔離條件亦做限定修復；`repair_retest.log` 72 pass，`product_full_after_repair.log` 489 pass。
3. 裸 repo-wide `pytest -q` 收集 `outputs/` 下歷史同名 test_run_live_offline.py 發生 import mismatch，原 traceback 在 `DE07/repo_wide_first.log`；不刪既有 outputs，另依原工作單 `--ignore=outputs` 測指定源碼範圍，見 `DE07/repo_wide_ignore_outputs.log`。兩個結果不能合併假稱裸 repo 全綠。
4. Chrome 初次完整 E2E 在未來日期負例失敗：`DE09/browser_e2e_stderr.log`；只修 web＋manual API（伺服端 422），同一實測 Chrome 完整 37/37 通過。出錯僅用合成資料。
5. 值對照 checker 初版把每次都不同的 `request_id` 誤判資料漂移：`DE05/checker_positive.log`；依原引擎性質僅對動態 request_id 核格式，對剩餘所有確定性欄位完整深度比較；`checker_positive_retest.log` 通過，故意污染價格的 `checker_negative.log` 非零。
6. 凍結 SHA 19/19 正向；篡改基準**副本**反向 18/19、程式非零（`DE07/protected_negative_result.json`），未改動本機任何受保護檔。
7. 最終回歸重測先因 PowerShell 傳遞 `--junitxml` 的字串格式錯誤 exit4/未執行測試，`DE07/final_repo_stderr.log` 保留；改成單一字串參數，`DE07/final_repo_retest_stdout.log` 518 passed。最終保護 checker 首版假設有空 records 初始 JSON 檔而 FileNotFound（`DE12/protection_precheck_failure.md`）；改讀先前實際 PID 收據所載檔數0，重新驗 SHA/size19/19 與 ML freeze。

以上均屬 **作者自驗**。沒有獨立 reviewer／正式 ChatGPT 個人 plugin 實證，DE08、DE10、DE11 **HOLD**。讀者請勿把先前 Proposal v5 r3 的 `EXTERNAL_PASS` 解讀成當前 TW01 雙入口產品驗收。

工具及日後連線條件、套件安裝、回滾和可用命令：請讀 `docs/CHATGPT_PLUGIN.md`。總表、原始狀態與交付 checksum 置於本輪 `DE12/` 目錄。

## 後續（15:16）補正索引

原 `chatgpt_dual_entry_impl_20261013_1349_Windows5800X/DE12/delivery_manifest.json` **只屬當時版本快照**。後續另立新目錄 `outputs/quality_runs/chatgpt_dual_entry_followup_20261013_1516_Windows5800X/`，嚴禁引用前輪 checksum 冒稱新 source 不變。新增真缺陷：worker 等待 lock 沒有計15秒、MCP取消 call 可能在同步 to_thread 留下執行中的子程序。原始實作透過新的 async process executor 把 15 秒算到 dispatch 起始、取消時實 kill/reap；新的整合49 PASS，全 repo `--ignore=outputs` 522 PASS，新 SDK initialize/list/call 2工具6次通過。詳細新紅/綠測與 Windows PID checker 返修在 `followup.../DE09/test_results.md`。

同輪從本人 Platform 實見 Tunnels 列表和按鈕，但未新建 TW01 專用 tunnel，既有 3090/COS 路徑不動。官方 Windows `tunnel-client v0.0.16` 已離線驗 SHA/執行 `--version`，缺本人 runtime key/新 tunnel，因此未執行 doctor/run；AGY 新 reviewer 因429、Claude Code 新 reviewer 因 OAuth 過期都未完成實作複核。DE08/DE10/DE11 仍 **HOLD**；不是正式 EXTERNAL_PASS。

## 最新 21:25 續作：Windows Job Object、watchdog 與分層狀態

新證據根 `outputs/quality_runs/chatgpt_dual_entry_continuation_20261013_2125_Windows5800X/`。已加入專用 transport 的 Windows Job Object `KILL_ON_JOB_CLOSE`、pending spawn 故障時 `os._exit` fail-closed、同步阻塞 event-loop 仍生效的獨立 OS-thread watchdog；最新 watchdog unregister/stop 與超時的競態已作最小返修。工作預算是從 MCP dispatch 開始的 **15 秒**，必要清理另允許 **最多 4 秒**；不保證作業系統硬即時 15 秒 wall-clock 內終止。正常流程以真 worker kill/reap；必要時由專用 transport job kernel 清理；pytest 與 COS host 不能直接加入此 job。

最新 source 版整合 77 passed、產品 `tests/` 521 passed、repository `--ignore=outputs` 550 passed，退出碼均為 0；凍結 19 項 SHA/size 完全一致、原 ML freeze 104 行完全一致。真 MCP SDK wire 的兩工具與 6 calls 包括在最新定點測試；此為本機 SELF_CHECK，原生成功不是 ChatGPT 私用插件接通。其他原始正／負向和歷史失敗均不覆寫。

沒有獨立 reviewer 完成原程式親讀＋重跑，因此 DE08 仍 `HOLD`；DE10 缺獲授權私用通道與本人授權，僅驗證隔離候選 `tunnel-client v0.0.16 --version`，`doctor`／`run` 未執行；DE11 ChatGPT tool-call/最終回答驗收未執行。當前實際測過的 Web URL 仍為 `http://127.0.0.1:8766/`（manual、`/health ready`、`/agent/status chat_disabled`）。詳見新 `DE12/` 的交付清單、返修史及層級表。

## 23:12 新一輪安全審查返修與最終本機回歸

**新 run：** `outputs/quality_runs/chatgpt_dual_entry_continuation_20261013_2251_Windows5800X/`。Windows COS 顯示 Host 5800X、原 HEAD 仍 `9e29cddce8687489dcd07bc2f8d673d2e0a72ce3`，manual site PID 80052、`/health ready`、`/agent/status manual/chat_disabled`。Platform 個人 Tunnels UI 及 ChatGPT Plugins 增加入口已真實唯讀檢查，但只看到既有四條非 TW01 通道，DE10/DE11 不接線（詳 `DE10/permissions_observed.md`）。

本輪 Codex CLI `0.162.1` 的真正新上下文原碼讀取命令遭工具政策封鎖，沒有新獨立 source/tests runtime 結論。改供 11 份作者擷取的編號原始碼文字與 SHA256，Codex text-only verdict `STATIC_ONLY_REQUEST_CHANGES`；其中 ±5% 分類邊界原可接受非法方向已真紅／綠修復（原紅 5 fail、4 pass；綠完整檔21 pass）。最新真正回歸：**86 integration／530 product／559 repo `--ignore=outputs`，全部 exit0**，原14＋release5 **19/19** 雜湊一致，ML freeze 104 行完全一致。以前各輪測試數只是當時紀錄，不替代這次最新結果，也不把嵌套範圍數目相加。

其餘 Codex 提醒 **15s work+至多4s cleanup 不等於總 15s**、直接 worker PID 非整個 descendant tree 的確認、進入 SDK handler 前 inbound JSON 無尺寸證明等，尚無足以授予 DE08 通過的獨立完整證據；`DE08/static_review_disposition.md` 梳理每項。**DE08／DE10／DE11 繼續 HOLD**，本輪交付是可試用的本機候選，不是已連上的 ChatGPT 個人插件、也不是 EXTERNAL_PASS。相關 DE05 紅/綠、DE07 原始 log、DE12 本輪 checksum／返修史必須隨同保留。
