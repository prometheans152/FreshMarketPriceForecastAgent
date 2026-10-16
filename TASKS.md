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

# TW01 本輪候選交付

更新：2026-10-14T00:52:48.571008+08:00；主機 Windows 5800X；HEAD `9e29cddce8687489dcd07bc2f8d673d2e0a72ce3`。

**SELF_CHECK_LOCAL_CANDIDATE。獨立代理人：INDEPENDENT_AGENT_PASS；正式 EXTERNAL_PASS：HOLD。本人ChatGPT插件尚未接通，DE10/DE11 HOLD。**

實際可使用網址：http://127.0.0.1:8766/ ，本輪再次health=ready、manual/chat_disabled；既有PID80052未重啟。另自行啟停隔離candidate跑22個真正HTTP請求。Chrome自動化拒開`ERR_BLOCKED_BY_CLIENT`，本輪無新桌面/手機圖，不將HTTP或舊37checks當新Chrome验收。

架構：manual browser→manual_web→原API /forecast、/records→凍結ForecastEngine（RF7/HGB14，A/B固定alpha0.3）；ChatGPT（未接通）→TW01專用私人Tunnel（未成立）→tunnel-client→官方SDK stdio/Binary ingress guard→兩工具嚴格schema/watchdog→每呼叫suspended worker Job→原ML隔離worker→adapter/AgentTools/同一凍結release。兩入口各自程序，不走/agent/query，不需要模型API。

真回歸：整合 **120 passed/127 warnings**；產品tests **564 passed/6995 warnings**；repository **593 passed/6995 warnings（明示--ignore=outputs）**，各exit0/skip0。三組範圍嵌套，不相加。裸repo本輪exit2/22 collection errors，源於outputs的歷史及本輪可逆backup同名檔，不刪封存或稱裸全repoPASS。

原19項SHA256/size不變（18 unique），ML原104行freeze逐行不變；初始103行源於PYTHONPATH=src的egg-info遮蔽，有獨立親重現。

主安全修復：watchdog不再將4s當額外工作時間；每worker在執行前入獨立Job、正常/取消/超時清整個後代；入站raw line16384 bytes/depth16/全訊息128members/key64bytes；arguments≤5欄且不排序/回顯巨量extra；SDK input schema完整移入已註冊watchdog的handler。

15秒從自訂call_tool dispatch計，包含lock等待、輸入/輸出schema及worker decode。bounded ingress framing/SDK JSON-RPC解析先於它。真同步阻塞首次OS停止約15.000–15.016s；最多4s僅清理/確認。這是實測容差，不是硬即時Windows排程保證。拒收ingress的Windows launcher曾exit0，仍有固定診斷、無attack response及實際關閉；negative checker另有exit1。

原始數值限制不變：公開均價非店家真值、正式公開測試未勝對應簡單基線、同店到期A/B尚無證據、機率/區間null。沒有重訓/修改正式模型與資料，不接Qwen/3090/Ubuntu，不改/借既有Tunnel，不讀私人record/key，不commit/push/公開部署/購買。

本輪證據絕對路徑：`C:\Users\prometheans\Documents\AIOT_FinishProject\outputs\quality_runs\chatgpt_dual_entry_codex_20261013_235947_Windows5800X`。原始使用者規格及舊各輪失敗均保留。精確重跑看下方handoff；回滾依backup前後hash逐檔，不reset/clean。

| 階段 | 狀態 | 實際驗證/限制 | 證據 |
|---|---|---|---|
| DE00 | SELF_CHECK + 獨立輸入查核 | 原14+5=19/19（18 unique）、104行freeze、入場60/60checksum | DE00/evidence.md；DE12/final_baseline_check.json |
| DE01 | SELF_CHECK + 獨立代理人複核 | 两工具契約、非法輸入/欄數與欄名限制 | src/aiot_price/integrations/chatgpt_contracts.py；DE05/ingress |
| DE02 | SELF_CHECK + 獨立代理人複核 | manual首次import隔離、agent拒絕、records伺服器路徑 | tests/integrations/test_manual_web.py；DE08/independent/manual_isolation_stdout.log |
| DE03 | SELF_CHECK；本輪UI渲染BLOCKED | Web無改碼；本輪真HTTP A/B/fallback/units/records；Chrome拒開 | DE09/http_results.json；DE09/visual_review.md |
| DE04 | SELF_CHECK + 獨立代理人複核 | 官方MCP1.30.0獨立transport；原ML freeze不變 | requirements/chatgpt-mcp.lock；DE00/freeze診斷；DE12/final_baseline_check.json |
| DE05 | SELF_CHECK + 獨立代理人複核 | 真engine/adapter完整JSON、非法schema、污染價格/方向拒收 | DE05/engine_results；DE08/independent/independent_original.json |
| DE06 | SELF_CHECK + 獨立代理人複核 | 15s工作期限、每worker Job完整後代、SDK驗證移入watchdog、入站bound、人工native重開 | DE06/lifecycle_evidence.md；DE06/schemavalidation；DE08/independent/independent_review.md |
| DE07 | SELF_CHECK | integration/product/repo ignore outputs全過；裸repo22collection errors保留 | DE07/*verified.*；DE07/bare_repository.* |
| DE08 | INDEPENDENT_AGENT_PASS；正式外審HOLD | 全新fork_turns=none reviewer親讀原檔、真重跑、兩缺口紅綠與closure | DE08/independent/independent_review.md；review_input_manifest.json；commands.jsonl |
| DE09 | SELF_CHECK_HTTP；Chrome BLOCKED/NOT_RUN | 22個真TCP/HTTP請求，isolated synthetic records；原8766仍live | DE09/http_results.json；process_cleanup.json；visual_review.md |
| DE10 | HOLD | 本人登入/工作區/權限、TW01專用ID/runtime key/風險授權、doctor/run未成立 | DE10/permissions_matrix.md；official_sources.md |
| DE11 | HOLD/NOT_RUN | 没有TW01真ChatGPT tool-call/structuredContent/自由文字/斷線恢复驗收 | DE11/status.md |
| DE12 | SELF_CHECK_LOCAL_CANDIDATE | 本輪候選封存、精確scope、完整失敗史、checksum正反控制；非final | DE12/delivery_manifest.json；handoff.md；failure_history.md |

---

# TW01 最新工作包：網頁表單＋個人 ChatGPT 插件（2026-10-13）

**2026-10-13 23:12 Windows COS 再續作／最新且優先的本機候選版本：** 新 Codex 原碼實讀及執行被安全政策 `BLOCKED`；另以新上下文文本快照完成 `STATIC_ONLY_REQUEST_CHANGES`，**不能取代 DE08 獨立親讀＋負例重跑**。審查指出 A 預測 ±5% 分類邊界未檢查非法方向，作者已在獨立 DE05 紅測得到 **5 failed、4 passed**，修改僅限 `chatgpt_adapter.py` 的方向輸出驗證與 `test_chatgpt_mcp.py` 新負例，綠測 **21 passed**。最新版 **整合 86 passed、產品 tests 530 passed、repo `--ignore=outputs` 559 passed**，均 exit0；歷史裸 repo collection errors 不抹掉。原始保護 **19/19**、ML `.venv` freeze **104/104** 不變，實查網頁仍 `http://127.0.0.1:8766/` ready/manual/chat_disabled。Platform 個人組織現有四條通道均非 TW01，ChatGPT Plugins 頁面顯示新增入口，但**TW01 專用 tunnel、runtime key、doctor/run、真人 ChatGPT tool-call 仍無實證，DE08／DE10／DE11 均 HOLD**，沒有繞過審查 gate。最新原始測試及完整審查停點在 `outputs/quality_runs/chatgpt_dual_entry_continuation_20261013_2251_Windows5800X/`。本輪仍是 `SELF_CHECK／本機候選`，不 commit/push、不動 Ubuntu／RTX3090／Qwen／原模型。

**2026-10-13 深夜 Windows COS 最新續作（覆蓋下方舊測試數，但不改歷史狀態）：** 專用 MCP transport 的 Windows Job Object、異步 worker/pipe、獨立 OS-thread watchdog 及 unregister 競態最小返修已落地，最新 **MCP 整合 77 passed、產品 `tests/` 521 passed、repo `--ignore=outputs` 550 passed**（三者皆 exit 0）。原 14+5 模型／資料保護基準 SHA/size 一致，`.venv` pip freeze 104 行無變更。15 秒僅為 dispatch 起算的工作預算，另有最多 4 秒 bounded cleanup，不宣稱總 wall-clock 嚴格 15 秒。網頁 `http://127.0.0.1:8766/` 健康、manual `chat_disabled`。**目前仍是 SELF_CHECK／本機候選；DE08 獨立 reviewer 未完整執行，DE10 私用 tunnel／本人權限、DE11 ChatGPT 真接線仍 HOLD，不是 EXTERNAL_PASS。** 交付證據 `outputs/quality_runs/chatgpt_dual_entry_continuation_20261013_2125_Windows5800X/DE12/`。不動 Qwen／3090／Ubuntu／原 release，不 commit/push。

**最新方向：保留不依賴 GLM 的表單網頁，保留網頁 A／B 與本機紀錄；新增本人 ChatGPT 的 MCP 兩工具，第一版查行情＋A 預測。Qwen／3090 暫緩，不重訓、不改凍結模型／資料。**

**2026-10-13 Windows COS 執行更新：** 原工作單已在本輪實作雙入口的本機候選，包含無 GLM 表單 A/B/紀錄、本機原生 stdio MCP 兩工具與真 Windows Chrome 介面驗證。執行者為 ChatGPT，結果僅 **SELF_CHECK**；並非本人 ChatGPT 私人插件接通／正式外部驗收。獨立 DE08、權限／通道 DE10、真 ChatGPT DE11 仍 **HOLD**。本段只更新當輪狀態，保留先前規劃及全部歷史任務記錄。

**2026-10-13 15:16 後續實做結果（不覆寫前輪）：** 修正原生 MCP 佇列等待未計入15秒、取消時子程序未確保終止的缺陷；另跑完整真 SDK session、4項取消/排隊負向控制、整合49 PASS及明示 `--ignore=outputs` 的 repo 522 PASS。本人 Platform 已實見個人 Tunnels 清單及 Create/Edit UI，但沒有建立/借用既有 tunnel。Windows 官方 `tunnel-client v0.0.16` 已離線下載、SHA256核對、執行版本說明，不曾連線；AGY reviewer 因 429、Claude Code reviewer 因 OAuth 逾期皆未審到原碼，所以**DE08、DE10、DE11繼續 HOLD**。這是同一作者 SELF_CHECK，**正式外部驗收仍未完成**。新增證據：`outputs/quality_runs/chatgpt_dual_entry_followup_20261013_1516_Windows5800X/DE12/continuation_summary.md`。

- [最新結論與雙入口架構](docs/chatgpt_dual_entry/20261013_01/CONCLUSION.md)
- [完整 DE00–DE12 任務卡與驗收條件](docs/chatgpt_dual_entry/20261013_01/TASKS.md)
- [給 ChatGPT 的 COS 執行工作單](docs/chatgpt_dual_entry/20261013_01/COS_HANDOFF_PROMPT.md)
- [本輪已實作的 Windows MCP 操作與限制](docs/CHATGPT_PLUGIN.md)
- [DE00–DE12 實作後 runbook](docs/chatgpt_dual_entry/20261013_01/RUNBOOK.md)
- [本輪原生 log、失敗與返修證據](outputs/quality_runs/chatgpt_dual_entry_impl_20261013_1349_Windows5800X/DE12/acceptance_matrix.md)

| 任務 | 項目 | 前置依賴 | 產品執行狀態 |
| --- | --- | --- | --- |
| DE00 | Windows／範圍／保護基準 | 原始要求與原檔 | **SELF_CHECK：原14/14、凍結5/5一致** |
| DE01 | 原碼對照與實作契約 | DE00 | **SELF_CHECK：兩工具嚴格 schema，故意造錯非零** |
| DE02 | 無 GLM 的 manual 後端 | DE01 | **SELF_CHECK：隔離 import，A/B/紀錄真 API** |
| DE03 | 保留表單 A／B 與紀錄，移除聊天 | DE02 | **SELF_CHECK：現行表單 Chrome 介面驗證** |
| DE04 | 官方 MCP SDK 與依賴隔離 | DE01 | **SELF_CHECK：SDK 1.30.0 獨立 venv，ML 依賴未動** |
| DE05 | 兩工具 MCP adapter | DE04 | **SELF_CHECK：原 engine 完整值比較，偽值拒收** |
| DE06 | 原生 MCP／15秒終止／人工恢復 | DE05 | **SELF_CHECK：native 6 calls；15.015s 真 PID 終止** |
| DE07 | 回歸、反向控制、保護核對 | DE03＋DE06 | **SELF_CHECK：tests 489 pass，--ignore=outputs 518 pass；裸跑6 collection errors 均留證** |
| DE08 | 獨立實作與輸出複審 | DE07 | **HOLD：未取得另一個獨立 reviewer** |
| DE09 | 本機網頁實測與試用網址 | DE08；無獨立審查只測隔離候選 | **SELF_CHECK／隔離候選：Chrome 37 checks，http://127.0.0.1:8766/** |
| DE10 | 本人權限與私人通道 | DE08通過；帳號條件 | **HOLD：workspace/Tunnels 權限與 runtime key 未核實、client 不在 PATH** |
| DE11 | 真 ChatGPT 工具與文字驗收 | DE10 | **HOLD：本人插件未接通，未執行真 ChatGPT 對話** |
| DE12 | 報告、操作文件與完整交付 | DE09＋DE11；或接線層如實HOLD | **SELF_CHECK：已交付 runbook、狀態與可重現原始證據；非正式終驗** |

DE02／DE03 與 DE04–DE06 可依契約分支進行。帳號缺項只 HOLD DE10／DE11；缺獨立複審時不升格 final，仍完成候選本機驗證與 DE12。工具或 Windows 路徑不可讀則保存原錯並 BLOCKED，不切換 Ubuntu／3090 替代。

本工作包覆蓋下方歷史「GLM先行→3090」的當前執行安排，不改 T01–T36 的既有文字或 Proposal v5 r3 的限定 EXTERNAL_PASS。真店到期 A／B、Qwen／3090、外網多人、影片、GitHub／YouTube／課程發布、插件 B／保存均未納入本輪實作授權。

---

以下保留本輪開始前的 TASKS 原文，作為歷史任務與驗收記錄。

# TW01 菜價預測專題執行任務

## 最新階段：Proposal v5 r3 已通過 S80（2026-10-09）

[ChatGPT 獨立第三輪複審](outputs/audits/proposal_v5_r3_independent_20261009_01/REVIEW_R3.md) 判定 **EXTERNAL_PASS（限 Proposal v5 r3 文件、33頁簡報及其來源一致性）**；[主文](docs/proposal_v5/PROPOSAL.md) 與 [v5 文件包](docs/proposal_v5/STATUS.md) 為當前工作區正式提案入口。D44/v1-v4 的狀態與工作單以下保留為歷史，不可蓋掉這一輪已通過之結論。

| 任務／交付 | 目前狀態 | 證據與依賴 |
| --- | --- | --- |
| Proposal／Deep Research／八欄文獻表（T33） | **EXTERNAL_PASS** | v5 r3 五份文件；REVIEW_R3 |
| v5 簡報／PDF／講稿（T33/T34） | **EXTERNAL_PASS** | 23主講＋10附錄、74/74檢查、7/7 guard、33頁獨立目視；UTF-8 全repo 256 passed |
| README／TASKS／design／AGENTS 主入口 | **工作區已同步（未提交Git）** | 2026-10-09文件升格；不改封存模型和已驗收 PPTX/PDF |
| T16 真店 A/B 到期價 | **HOLD** | 缺同店同規格之7/14日真價；不能拿市場測試冒充 |
| T26/T27 真 LLM Planner／自主工具調度 | **PROPOSED／暫緩** | 目前是規則式兩工具、固定序列；/records獨立保存API |
| SERVER_3090／外網手機 T23–T25/T32 | **HOLD** | 未部署或未驗收 |
| 最終影片、GitHub、YouTube、課程交件 | **未完成／待明確授權** | Final 的>10分鐘影片與>20頁PPT不等於 Proposal 達標 |
| 封面組員／日期 | **待填** | 不猜測 |

**注意：** 提案驗收不等於真正的 Domain Agent 或最終期末成品驗收。本輪不建立 Git commit／remote、不推送或發布，也不重訓。

---


## D44-R01–R06 修訂輪（歷史：2026-10-04）

依 `outputs/audits/d44_independent_6eb4adf/REVIEW_6eb4adf.md` 之 Request changes 完成**研究內容與交付校正**，全部由 GLM 自驗通過，待 ChatGPT 獨立複審；詳 [D44_REVISION_REPORT.md](docs/D44_REVISION_REPORT.md)（原問題／改檔／證據／驗證／剩餘限制逐項）。工作單 [GLM_D44_R01_R06_REVISION_20261004.md](docs/GLM_D44_R01_R06_REVISION_20261004.md)；證據 `outputs/proposal_delivery/run2_20261004_01/`（stats_master＋claims_master 27 列＋r01/r02 查核卡＋v2 渲染 19/19＋openspec CLI）。

| 修訂項 | 內容 | 狀態 |
|---|---|---|
| R01 | 公視日期（實為 2025-08-13 楊柳）、王鎬杰 2010/2004–2009 批發範圍、2026-07 兩則撤回、機率→歷史比例、45→85 成因不主張 | 自驗完成 |
| R02 | R01 摘要全文/R02/R04/R05 官網/R06 商店頁實讀；R08/R09 降線索；回測/前瞻分欄；移除無範圍否定；新增 R11 書目 | 自驗完成 |
| R03 | stats_master 同源（10.5%/16.6% 正式值、21 列邊界註記）；364/905 母體標示；12特徵+one-hot；HGBClassifier；`=7天` 修正 | 自驗完成 |
| R04 | PROPOSAL_REPORT 重寫為可獨立閱讀敘事；T/U/Y/Z 對照修正；前作比較表入主稿；A/B 例標教學；−0.1% 接近 0 | 自驗完成 |
| R05 | 架構①–⑤＋端點＋連線；真實清除帶（695+691=1,386 列）；錨定命題 [p(1+r)−p]/p=r；S01–S09＝自驗暫緩 | 自驗完成 |
| R06 | 三腳本參數化防覆寫；notes_v2 同源講稿；v2 PPTX/PDF 19 頁（視覺 19/19 PASS）；測試 15/15；README 重整；OpenSpec 17/17 tasks＋strict validate exit 0 | 自驗完成 |

影片未錄、GitHub/YouTube/課程提交未發布（待授權）；組員/組長/正式日期待填；真店 T16、代理人後端、SERVER 維持暫緩。

## D44 本輪工作包：研究／設計／OpenSpec／正式投影片（首輪，歷史）

**2026-10-04 最新排程覆蓋：** 使用者先擱置代理人問題，保留現有介面。T25–T28 的代理人整合與相關修復暫緩，不是 PASS，也不阻塞下表。T16 真店、SERVER、影片與發布維持原各自狀態。本輪不執行產品程式修復、重訓、外部部署或其他課堂作業。

詳細任務：[PROPOSAL_DELIVERY_PLAN.md](docs/PROPOSAL_DELIVERY_PLAN.md)；已讀教授來源：[SOURCE_AUDIT](docs/PROPOSAL_SOURCE_AUDIT_20261004.md)；GLM直接入口：[HANDOFF](docs/GLM_PROPOSAL_HANDOFF.md)。本表為本輪狀態索引，P1–P6只是既有T任務的子工作包，不取代T01–T36。

| 工作包 | 對應原TASK | 產物與完成標準 | 狀態 |
|---|---|---|---|
| 來源核對／安排 | T01 | COS實讀L4-1 A–Z、逐字稿補充及六包計畫；只證明本批來源／規劃已完成 | PASS（2026-10-04） |
| P1 研究動機 | T04/T33 | 有證據的問題、研究問題、正式稿與簡報版摘要 | PASS（2026-10-04；RESEARCH_MOTIVATION.md：5項可查證據＋RQ1–RQ3＋169字摘要） |
| P2 前作與差異 | T04 | 重查矩陣、REFERENCES、RESEARCH_GAP；未知不當沒有 | PASS（10件關鍵作品、UNKNOWN 12處如實標、[R01–R10]編號、三組缺口；僅摘要閱讀者主張已縮小） |
| P3 三貢獻／研究稿 | T33 | C1–C3各自可追溯；A–Z提案與初步成果稿 | PASS（CONTRIBUTIONS.md＋PROPOSAL_REPORT.md A–Z；基線並列、負向保留、無顯著/首次用語） |
| P4 設計藍圖 | T02 | 根目錄design.md、架構／資料流／時間軸與具體公式例子 | PASS（§0–§5現況藍圖置頂＋歷史附錄；錨定不變向與0.3來源明示） |
| P5 OpenSpec管理 | T02/T34 | 真CLI初始化、規格情境、change與任務、版本及validate輸出 | PASS（CLI 1.14.0局部安裝；change 4/4 artifacts、11/11 tasks；validate --strict exit 0；openspec_cli_evidence.txt） |
| P6 正式投影片 | T33/T34 | 可編輯PPTX＋對應PDF＋講者備註＋逐頁渲染驗收 | PASS（PPTX=PDF=19頁；兩輪視覺驗收rev2 19/19 PASS（render_review.md）；SLIDE_NOTES.md主講11:15＋10分鐘快版） |
| 本批交付檢查 | T34 | PROPOSAL_ACCEPTANCE、來源／數字／文件一致性與保護證據 | PASS（PROPOSAL_ACCEPTANCE.md六包全過；保護檔6/6 SHA256不變；claims_evidence 15列回填文稿段落與頁碼；eval JSON重算=2d28acd2…74b8） |

先來源／數字核對及P5a管理初始化，再P1/P2平行→P3→P4→P5b→P6→交付檢查。**T33本批提案／簡報不再以T27/T32全部完成為前置条件**；未完成實驗照實標示。**2026-10-04 本批P1–P6與交付檢查全數PASS，驗收見 [PROPOSAL_ACCEPTANCE.md](docs/PROPOSAL_ACCEPTANCE.md)；真店T16、代理人後端、SERVER、影片與發布維持各自狀態，不因本批PASS升格。**原條目以下保留歷史，衝突以D44為準。

> 給 GLM：先讀 [AGENTS.md](AGENTS.md)、[design.md](design.md)、[GLM_HANDOFF.md](docs/GLM_HANDOFF.md)及[MODEL_VALIDATION_PLAN.md](docs/MODEL_VALIDATION_PLAN.md)，按依賴逐項執行。依執行環境採用 Superpowers 的 executing-plans 或 subagent-driven-development；技能不可用時，保留相同的逐項驗證與獨立審查流程。不要把寫好任務、下載資料或產生圖表當成模型已驗證。

**Goal（D41）:** 保留本機已訓練菜價模型與封存評估，先用可替換的 GLM API 後端完成代理人工具整合，再在另一台 RTX 3090 SERVER 自架 Qwen3.8-27B 並以同一介面切換重驗。使用者以手機輸入今天店價及選填上週同店價，取得 7／14 天預測與有根據的解釋。Hermes Agent 暫定（使用者原文 HARMES），詳見 [代理人方向](docs/AGENT_RUNTIME_DIRECTION.md)。

**Architecture:** 訓練端負責資料、時間切分、訓練、評估與可攜模型包；SERVER 負責菜價推論 API、Qwen 代理人及手機網頁。公開市場零售均價模型與同店價格適配分開驗證；有上週紀錄時比較兩種輸入，沒有時仍可使用公開歷史與今天報價。兩台主機不是同一台，3090 SERVER 的作業系統、連線與服務入口尚待取得。

**Tech Stack:** 已有 Python 資料／模型程式、HTTP API 與手機 Web 原型；D41 新增 Hermes Agent 暫定、GLM API 先行與本機 Qwen3.8-27B 可切換。Qwen 型號已確定，但量化／推論引擎及 Hermes 整合未驗證；GLM 平台／模型 ID／金鑰位置未配置，不宣稱已連通。歷史「不預設雲端 API」已由使用者此次明確需求取代。

**Spec:** [design.md](design.md)；研究依據：[課程要求](docs/COURSE_REQUIREMENTS.md)、[公開零售資料](docs/research/TW01_PUBLIC_RETAIL_DATA.md)、[既有作品](docs/research/TW01_RELATED_WORK_RECHECK.md)、[TW01 歷史與現行討論](docs/ideas/TW01_VEGETABLE_BASKET.md)。當前使用者的雙主機安排優先於歷史方案。

## Global Constraints

- 訓練在目前 Windows 工作區進行；另一台 RTX 3090 是 SERVER，接收模型包並執行推論與代理人。
- 無上週紀錄模式：今天同店報價＋公開歷史；有上週紀錄模式：再加上週同店、同規格、同單位報價及實際日期。上週價格可留空，不以 0 或公開均價代填。
- 兩模式都從使用者的今日日期預測 7／14 天後相較今天的變化；公開來源日期較舊時，仍不能把起點改成最新訪價日再另算7／14天。正式標籤口徑在 T02、T07 固定，不能混用日曆日與交易日、某日價與週均價。
- 臺中公開資料是市場平均價格、元／斤，0 代表無價格，沒有個店 ID。2026-10-03 已取得的 4,450 列、14 市場、近一年資料是研究快照，仍需品質及發布時間查核。
- 公開市場成績不能冒充同店成績；同份公開歷史的 t−7 欄位不能冒充新增私人資訊。單純現價乘市場預測倍率不是「現價改善漲跌方向」的證據。
- 不預設有上週紀錄較準，不杜撰機率、區間、準確率門檻或已完成的訓練；負向結果也應如實呈現。
- 不恢復買菜清單、預計整籃重量及菜籃預算。OCR、RAG、多代理人、Qwen 微調、天氣特徵、硬體感測器都不是必需功能。
- 個人原始報價、店家識別、錄音、金鑰、權重及大型資料放在忽略目錄；外部報告使用彙總及匿名例子。
- 一般本機實作、驗證與文件依 GLM 接手指示推進；尚未提供的 SERVER 存取資訊只阻擋依賴它的任務。外部帳號、公開儲存庫／服務目標及提交方式未提供時，不虛構目標或擅自發布。
- 以真實命令、版本、時間、輸出路徑及摘要保存證據；不把歷史快照說成本次重新實測。不要求每項任務都建立無意義測試或 Git 提交。

## Review Focus

1. 單位未知、整顆／整把未提供重量、品種或促銷不同：不得默默換成元／斤並當成同商品；T09、T17、T20、T21 驗證。
2. 上週欄位空白、日期不是整整七天、換店或換規格：維持無上週模式，或明確指出資料不可比，不偽造歷史；T10、T14、T20、T21 驗證。
3. 資料未發布、標籤未到期、相鄰時間跨切分與未來補值：不能進入當時可用特徵或訓練標籤；T07–T09、T15 驗證。
4. 資料過期、未支援城市／品項、模型或 Qwen 失敗：保留來源日期與能力邊界，提供直接模型結果或資料不足，不生成假的店價結論；T17、T27、T30、T32 驗證。
5. 手機外部查詢、模型包不一致、私價誤入 Git、惡意文字或重複呼叫：守住存取、版本、隱私與工具呼叫範圍；T18、T24、T26、T28、T29、T34 驗證。

## 任務狀態與產出規則

**2026-10-04 D41 覆蓋更新：** `44dabe3` 的 134 項測試通過不代表第三輪全數验收；[第三輪獨立審查](outputs/audits/2026-10-04_round3_independent/REVIEW_44dabe3.md)R01–R08 仍開放。下方較早 PASS／修復完成紀錄保留歷史，受影響項不得據此對外宣稱驗收。T26/T27 的本機 GLM 路徑可先行；只有真 Qwen／SERVER 子項依賴 T23–T25。本輪是需求更新，未關閉任何缺陷或完成新執行測試。

本檔是任務狀態主要來源。**2026-10-04 第三輪後現況：T01–T15、T17–T22、T26 前 22 項 PASS／DOING（T26 本機規則層完成、Qwen 實機待 SERVER）；T16（真店到期價）、T23（SERVER 資訊）HOLD；T24–T36 依 SERVER／公告等待。** 各項實際狀態與證據見下方逐項記錄；產出已存在者以其驗收證據為準。根目錄 `design.md`、本檔與接手／驗證文件的初稿，不能代替下列任務的實測證據。

每項狀態使用 `TODO`、`DOING`、`PASS`、`FAIL`、`HOLD` 或 `BLOCKED`，通過後勾選核對項並填日期與證據。`HOLD` 是真價、公告、標籤成熟或必要主機資訊等外部依賴未成立；`BLOCKED` 是當前執行路徑受阻且無法在該任務內續做。兩者都須寫出具體原因、影響的任務及仍可並行完成的工作；資料不足的同店驗證保持 `HOLD`，不能因公開模型完成而勾成 PASS。每次接手維護 `docs/GLM_PROGRESS.md`，記錄本次完成、失敗、下一項與待使用者提供資訊；原始大量執行紀錄放 `outputs/`。

建議模組邊界：`src/aiot_price/data/` 資料取得與處理、`src/aiot_price/features/` 訓練／推論共用特徵、`src/aiot_price/models/` 訓練／推論、`src/aiot_price/api/` HTTP 服務、`src/aiot_price/agent/` 代理人工具、`contracts/` 版本化輸入／輸出與模型包schema、`web/` 手機介面、`configs/` 非秘密設定、`tests/` 重要行為驗證、`deploy/` SERVER 啟停與部署。T02／T03 若選用其他結構，要先同步本檔與設計，使後續路徑保持一致。

## 前期收斂與資料

### T01 核對當屆課程交付與時程

**狀態：PASS（2026-10-03）｜依賴：無｜產出：** 更新 `docs/COURSE_REQUIREMENTS.md`；新增 `docs/DELIVERY_CHECKLIST.md`。

- [x] 重新核對逐字稿相關段落、當屆 Notion 公告與可讀子頁，分開期中提案與期末實作的格式、期限、組員及代理人要求；無法取得的項目明列未確認。（2026-10-03 GLM抽驗1710–1718、1746–1764、1770–1789、1890–1916、2024–2046、2830–2844、4616–4626與文件判讀一致；Notion Proposal再次無法讀取（JS空殼），期末細則維持未確認）
- [x] 將模型、領域分析、量化評估、代理人、網路成果與正式交付逐一映射到任務，不擅自補成全部框架模組皆必需。（DELIVERY_CHECKLIST.md映射表）

**驗收證據：** [COURSE_REQUIREMENTS.md](docs/COURSE_REQUIREMENTS.md) GLM T01核對紀錄段、[DELIVERY_CHECKLIST.md](docs/DELIVERY_CHECKLIST.md)；Notion未讀取已記錄嘗試，未宣稱已核對最終規則。

### T02 收斂正式設計與最小成果

**狀態：PASS（2026-10-03）｜依賴：T01 的已取得資訊｜產出：** 更新 `design.md`、`docs/DECISIONS.md`；建立 `configs/project.yaml`、`contracts/forecast.schema.json` 初版。

- [x] 固定首版品項、資料地域、兩種輸入、7／14 天目標、允許單位、持平門檻、缺貨／促銷／日期容許範圍與不能支援時的回覆；先以最小可展示範圍收斂，不任意擴充。（project.yaml：甘藍/青江白菜/絲瓜、臺中、元/台斤與元/公斤、持平±5%、B日期7±2天；品項與sanity值待T06覆核後凍結）
- [x] 分開「公開市場預測」與「套用店價的估計」，寫出同店 A／B 要檢驗的假說與可接受負向結果；未有同店證據時顯示未驗證。（schema強制target_scope/validation_scope分離；forecast.schema.json）
- [x] 將design.md的 `ForecastRequest`／`ForecastResponse` 欄位、模式、資料截止時間與今日預測起點寫入版本化schema；T19、T20、T26共用，後續必要調整同步所有使用者。
- [x] 確認設計與目前使用者方向一致。一般工程選擇由資料／實測決定；新的採集負擔、對外公開或必要未知條件才提出具體待確認項，完成設計收斂後再實作依賴它的部分。

**驗收證據：** [configs/project.yaml](configs/project.yaml)、[contracts/forecast.schema.json](contracts/forecast.schema.json)、design.md §2.1、DECISIONS.md D34；設計與設定無相反定義，無虛構準確率目標。

### T03 確認訓練電腦並建立可重現環境

**狀態：PASS（2026-10-03）｜依賴：T02｜產出：** `docs/LOCAL_ENVIRONMENT.md`、`pyproject.toml`、選定工具的鎖版檔（`requirements-lock.txt`）、`.env.example`。

- [x] 記錄目前 Windows 的 CPU、RAM、可用磁碟、Python／套件與可用 GPU，評估資料量和訓練成本，不把 SERVER 的3090當成本機硬體。
- [x] 建立專案隔離環境與最小套件，依選定框架寫安裝／執行方式；秘密只用環境變數，不寫進範例。

**驗收證據：** 在本機完成 import／版本與最小讀檔檢查，保存環境輸出；另一個乾淨隔離環境可按文件安裝，不能只保存未跑過的套件清單。

### T04 補齊本案既有作品與差異查核

**狀態：PASS（2026-10-03）｜依賴：T02｜產出：** 更新 `docs/research/TW01_RELATED_WORK_RECHECK.md`；新增 `docs/RELATED_WORK_MATRIX.md`。
2026-10-03 實際證據：[RELATED_WORK_MATRIX.md](docs/RELATED_WORK_MATRIX.md)（前輪7件＋本輪19作品實查）與[重查補查段](docs/research/TW01_RELATED_WORK_RECHECK.md)；查核範圍內未見相同組合，差異主張收縮後維持（B增益仍待測）。

- [x] 延續已查的台灣批發、零售、私人資料與 AI 行情作品，補查可取得的開源、產品、課程範例與歷屆作品實際方法，不重列全部50題。
- [x] 列出相同與不同處、只讀摘要／完整內容的界線；將差異表述為「今天／上週同店輸入是否有用及其負擔」，不能宣稱全球首次。

**驗收證據：** 每個比較連到具體作品，能指出本案另測什麼；若查到完全相同做法且無差異，記錄並縮小／修正設計，不以換名字補差異。

### T05 取得正式資料快照、授權與來源紀錄

**狀態：PASS（2026-10-03）｜依賴：T02、T03｜產出：** `src/aiot_price/data/fetch_public.py`、`configs/data_sources.yaml`、`docs/DATA_CARD.md`；實檔在 `data/raw/`。
2026-10-03 實際證據：[data/raw/taichung/](data/raw/taichung/)正式快照（HTTP200、5,323,185B、SHA256 `172dffc76e82…`，與舊快照逐位元組相同＝同日未更新）＋provenance JSON×2；[fetch_public.py](src/aiot_price/data/fetch_public.py)、[data_sources.yaml](configs/data_sources.yaml)、[DATA_CARD.md](docs/DATA_CARD.md)。更多年度：官方API僅近一年滾動視窗（DATA_CARD記錄）。

- [x] 從官方來源重取／封存選中資料，保存取得時間、URL、授權、SHA-256、檔案長度、觀測日期與發布日期資訊；已有2026-10-03實檔可作快照，不假裝多年全集已取得。
- [x] 查更多年度資料是否真能下載；外加批發／天氣等來源只在有實檔、合法取得與獨立增益需求時採用，失效來源不能列為訓練輸入。

**驗收證據：** 可重現取得與解析所選快照；資料卡說明元／斤、0無價、市場均價、地域及授權，不能把臺北月表當每日標籤。

### T06 資料品質與可用範圍分析

**狀態：PASS（2026-10-03）｜依賴：T05｜產出：** `src/aiot_price/data/quality.py`、`docs/DATA_QUALITY_REPORT.md`、`outputs/data_quality/`。
2026-10-03 實際證據：[DATA_QUALITY_REPORT.md](docs/DATA_QUALITY_REPORT.md)＋outputs/data_quality/quality_report.json；0值905格轉缺測、無重複鍵、364日無斷點、(停)建國市場沿用價176 run中密集→排除凍結於prepare_data.py；南屯甘藍0%覆蓋由insufficient路徑處理。

- [x] 檢查市場＋日期重複、價格缺測、0值、日期斷點、品項覆蓋、異常值、連續沿用價格、停用市場、更新延遲及單位不一致。
- [x] 依品項／市場／月份列可用樣本與季節限制，選定首版可支援範圍；不能把多市場同日的相關列當成大量獨立觀測。

**驗收證據：** 報告包含實際計數、排除理由及抽樣原始列；不能只靠圖表判定品質合格。未知發布時間有保守使用規則。

### T07 建立7／14天標籤與資料契約

**狀態：PASS（2026-10-03）｜依賴：T02、T06｜產出：** `src/aiot_price/data/labels.py`、`docs/LABEL_CONTRACT.md`、`tests/data/test_labels.py`。
2026-10-03 實際證據：[labels.py](src/aiot_price/data/labels.py)、[LABEL_CONTRACT.md](docs/LABEL_CONTRACT.md)、[test_labels.py](tests/data/test_labels.py)全過（手算E1–E5與程式一致、浮點邊界±5%含）；實資料標籤輸出於 features_labels.parquet。

- [x] 以設定建立起點、到期日、當日／到期價、方向及目標類型，兩個期限分開；明定是否精確日曆日，缺到期價就是缺標籤，不能當作未漲。
- [x] 將市場均價標籤與同店實價標籤分開；標籤成熟時間含發布延遲，微幅持平門檻先固定於訓練／驗證，不由測試調整。

**驗收證據：** 手算例子與程式一致，涵蓋7／14天、日期缺漏、0／空值、持平邊界、促銷與未到期；輸出保留真實來源及標籤成熟時間。

### T08 設計時間切分與防洩漏

**狀態：PASS（2026-10-03）｜依賴：T07｜產出：** `src/aiot_price/data/splits.py`、更新 `docs/MODEL_VALIDATION_PLAN.md`、`configs/splits.yaml`、`tests/data/test_splits.py`。
2026-10-03 實際證據：[splits.py](src/aiot_price/data/splits.py)、[splits.yaml](configs/splits.yaml)、[test_splits.py](tests/data/test_splits.py)全過；凍結清單 SHA256 `4e136574…`（train 13,009／val 3,855／test 4,680；train成熟日2026-05-09<val起點斷言通過）。

- [x] 固定訓練、驗證、最終測試及滾動回測日期；同日多市場放同一區，必要時另測未見市場，不做隨機逐列切分。
- [x] 每次預測只能用當時已公布資料與已成熟訓練標籤；按最大14天期限及實際發布延遲做清除／間隔，避免未到期或重疊標籤跨界影響評估。
- [x] 最終測試封存；調參、選品項、補值、持平門檻及機率／區間校正只用訓練與驗證。資料不足則縮小結論，不偷用測試補。

**驗收證據：** 每個切分有起訖、筆數、成熟時間斷言與排除清單；針對分界日期及未來資訊提供實際檢查輸出。

### T09 實作資料標準化與特徵流水線

**狀態：PASS（2026-10-03）｜依賴：T03、T07、T08｜產出：** `src/aiot_price/data/schema.py`、`src/aiot_price/features/build.py`、`tests/data/test_features.py`、`data/processed/`。
2026-10-03 實際證據：[schema.py](src/aiot_price/data/schema.py)、[features/build.py](src/aiot_price/features/build.py)、[test_features.py](tests/data/test_features.py)全過（未來資料擾動不改過去特徵、t日價t日不可見、單位攔截）；data/processed/features_labels.parquet。

- [x] 定義品項／規格映射、元／斤的標準價格、日期、可用公開歷史與當下可知特徵；斤／公斤可明確換算，未知重量的顆／把不能自行推定。
- [x] 所有補值、編碼、標準化只在訓練區擬合；缺測與缺上週價格有明確狀態，禁止未來回填、以0代價或默默合併不同規格。

**驗收證據：** 同一筆原始輸入轉換可重現；單位／品種錯配被攔截；對未來資料做擾動不改變過去特徵，訓練與推論共享同一轉換。

### T10 規劃低負擔同店報價與預測紀錄

**狀態：PASS（2026-10-03）｜依賴：T02、T07｜產出：** `docs/STORE_DATA_PROTOCOL.md`、`configs/store_record_schema.json`；原始紀錄在 `private/store_quotes/`。
2026-10-03 實際證據：[STORE_DATA_PROTOCOL.md](docs/STORE_DATA_PROTOCOL.md)、[store_record_schema.json](configs/store_record_schema.json)＋[範例](configs/store_record_example.json)；20項負向測試正確拒絕（jsonschema 4.26實測）。

- [x] 定義匿名店家代號、品項／規格、實際日期、單位、價、促銷與報價／實付來源；使用者只在有紀錄時提供上週價，不要求固定大量日記或整籃重量。
- [x] 設計需核對的未來同店到期價、缺貨／換規格／未到期處理及採集投入統計；明列人要提供的資料，不偽造上週紀錄。
- [x] 區分訓練／校正紀錄與未來獨立測試；採集方式及負擔須符合使用者已接受範圍，未確認部分提出可選的最小方案。

**驗收證據：** schema與匿名範例可檢查；有同店可比性的核對表與資料不足狀態；市場模擬資料明標「模擬」，不能轉成私人真值。

## 模型、評估與模型包

### T11 建立可比較基線

**狀態：PASS（2026-10-03）｜依賴：T08、T09｜產出：** `src/aiot_price/models/baselines.py`、`outputs/baselines/`、`docs/BASELINE_REPORT.md`。
2026-10-03 實際證據：[baselines.py](src/aiot_price/models/baselines.py)、[BASELINE_REPORT.md](docs/BASELINE_REPORT.md)、outputs/training/training_results.json；三基線與候選同列比較，錨定假設註記。

- [x] 建立價格不變／一律不漲、僅歷史平均或近期簡單趨勢基線；全部使用與候選相同的可用資料、切分及7／14天口徑。
- [x] 如採現場價乘市場預測比率，單獨列為錨定假設；驗證其方向不因正價格錨定而自動改善，不能當作已學會店家行為。

**驗收證據：** 每個基線有7／14天樣本數與指標，手算例子正確；比較使用完全相同測試列，而非不同可用資料。

### T12 訓練公開市場模型候選

**狀態：PASS（2026-10-03）｜依賴：T03、T08、T09、T11｜產出：** `src/aiot_price/models/train.py`、`configs/training.yaml`、`outputs/training/`、`models/candidates/`。
2026-10-03 實際證據：[train.py](src/aiot_price/models/train.py)實際訓練（CPU、seed42、6,377/6,134訓練列）、outputs/training/training_results.json、models/candidates/*.joblib； Ridge/HGB/RF/分類候選與指標全記錄。

- [x] 先以CPU可行的小型候選與資料量相稱的特徵比較；回歸／方向分類及是否另訓練7／14天由驗證需求決定，不為使用3090強選深度網路。
- [x] 固定種子、版本、資料hash、設定與資源用量，記錄所有正式比較及失敗；訓練僅在目前 Windows 電腦執行。

**驗收證據：** 至少完成一個非基線的真實訓練模型與可重跑紀錄，驗證區結果可對回資料／設定，沒有將最終測試當調參資料。

### T13 選模與輸出可信程度

**狀態：PASS（2026-10-03）｜依賴：T12｜產出：** `src/aiot_price/models/select.py`、必要時 `src/aiot_price/models/calibration.py`、`docs/MODEL_SELECTION.md`。
2026-10-03 實際證據：[select.py](src/aiot_price/models/select.py)、[MODEL_SELECTION.md](docs/MODEL_SELECTION.md)、model_selection.json；標準凍結於看測試前（主指標驗證macro-F1；h=7選rf_reg 0.4334、h=14選hgb_reg 0.4591）；點MAE未優於不變價→限制如實記錄。

- [x] 依預先固定的驗證指標、成本與延遲選型；若複雜模型未改善，保留簡單方案及原因，不挑對測試最好看的模型。
- [x] 只有獨立驗證支持時才顯示上漲機率／區間，並評估校正／涵蓋；否則顯示方向、估計與明確限制，不任意輸出「可信度90%」。

**驗收證據：** 選型有可重現比較表；所有輸出字段有計算來源及允許顯示條件；機率或區間如不存在，不影響完成基本模型推論。

### T14 實作有／無上週店價的兩種路徑

**狀態：PASS（2026-10-03）｜依賴：T09、T10、T13｜產出：** `src/aiot_price/models/store_adapter.py`、`tests/model/test_store_adapter.py`、`docs/STORE_ADAPTATION_METHOD.md`。
2026-10-03 實際證據：[store_adapter.py](src/aiot_price/models/store_adapter.py)、[STORE_ADAPTATION_METHOD.md](docs/STORE_ADAPTATION_METHOD.md)、[test_store_adapter.py](tests/model/test_store_adapter.py)全過；B＝實驗性規則（α=0.3）標unvalidated，7±2天/單位/規格檢查，不可比回A。

- [x] 定義兩模式共同使用今天店價及公開歷史，B再使用可比的上週店價與日期；有B輸入時可同時產生A、B結果，無B資料時正常走A。
- [x] 選擇有證據支持的店價適配方法；缺真私人標籤時B只能是明示假設的實驗原型，不能標成已訓練／已校正的同店模型。不以兩筆價杜撰已學得店家規律，不強訓不可靠個店模型；公開模型與系統可先完成，等真價成熟再驗證。
- [x] 將公共市場模擬的特徵／流程測試與私人增益實驗分開，禁止把同份公開t−7資料重複加入後的改善稱同店增益。

**驗收證據：** 同一案例切換上週欄位的差異可追溯，空值／不同單位／換店／換規格被正確處理；方法卡標出已訓練部分、假設與尚無證據部分。

### T15 完成封存測試的公開模型評估

**狀態：PASS（2026-10-03）｜依賴：T11、T13｜產出：** `src/aiot_price/models/evaluate.py`、`outputs/evaluation/public/`、`docs/PUBLIC_MODEL_EVALUATION.md`。
2026-10-03 實際證據：[evaluate.py](src/aiot_price/models/evaluate.py)一次性執行、[PUBLIC_MODEL_EVALUATION.md](docs/PUBLIC_MODEL_EVALUATION.md)、outputs/evaluation/public/（凍結清單hash校驗通過；test_predictions.csv可重算）；h=7 macro-F1 0.422 vs基線0.309、h=14 0.417 vs 0.295；點MAE未優於基線如實記錄。

- [x] 一次性套用已固定模型與設定到封存測試，7與14天分別報樣本數、基線、誤差與方向結果；價格回歸可報MAE／RMSE，方向可報混淆矩陣、上漲召回／誤報及平衡指標，與正式任務一致。
- [x] 分品項、月份／市場及變動情境檢視；若有機率／區間另報校正或涵蓋，對相鄰時序與多市場相關性採時間分組的比較與不確定性說明。

**驗收證據：** 表格可由預測逐列檔重算，含測試時間、實際價、預測、版本與排除原因；結論只支持公開市場目標，不改稱同店準確率。

### T16 完成真同店的未來A／B對照

**狀態：HOLD（2026-10-03）｜依賴：T10、T14、T19；需真實同店資料與標籤到期｜產出：** `outputs/evaluation/store/`、`docs/STORE_AB_EVALUATION.md`。
2026-10-03 狀態：等待真實同店到期價；A/B配對與凍結預測的機制（T10/T14/T22）已就緒，缺使用者實際店價紀錄與7/14天到期真值。不因公開模型完成而PASS。

- [ ] 保存預測當時已固定的A、B及基線結果，取得可比的7／14天後實價；在同一批具上週紀錄的案例上隱藏／提供該紀錄做配對比較。
- [ ] 分開用於調整與最終未來測試的資料；報差異、錯誤案例、樣本／店家／品項數、時間範圍與輸入負擔，不因B資料可得性不同而偷換比較案例。
- [ ] 若資料不足或標籤尚未成熟，記錄HOLD及可完成的公開模型成果；不能使用公共模擬、人造標籤或回憶價冒充真實同店驗證。

**驗收證據：** 每筆結果有事前預測與到期真值時間；能回答B是否改善及證據強度。結果未改善仍可完成誠實的實驗，但不足證據不能宣稱已完成同店效力驗證。

### T17 錯誤分析與能力邊界

**狀態：PASS（2026-10-03）｜依賴：T15｜產出：** `docs/ERROR_ANALYSIS.md`、`tests/model/test_prediction_limits.py`。
2026-10-03 實際證據：[ERROR_ANALYSIS.md](docs/ERROR_ANALYSIS.md)、[test_prediction_limits.py](tests/model/test_prediction_limits.py)全過（來源舊不退回起點、歷史as-of特徵、B降級、sanity警示、機率null）；up召回率低列為最大限制。

- [x] 檢查價格劇變、停用市場、規格不匹配、單位不明、未支援城市／品項、超出歷史範圍、上週日期偏移與過期來源的行為；來源較舊不能使預測起點悄悄退回來源日。
- [x] 固定拒絕／降級規則及限制文案；不把臺中均價外推全國同店當成已驗證，不由預測漲價直接保證建議囤貨能省錢。
- [x] 先完成公開結果與能力邊界，不等待T16才能打包／推論；T16產生真店結果後再追加錯誤分析及必要修正，重驗受影響工件，不形成互相等待。

**驗收證據：** 對照真實錯誤例與邊界測試，輸出不誇大可用範圍；未完成T16時明示同店A／B效果待驗證。

### T18 封裝可攜模型版本

**狀態：PASS（2026-10-03）｜依賴：T13、T15、T17｜產出：** `src/aiot_price/models/package.py`、`contracts/model-manifest.schema.json`、`docs/MODEL_CARD.md`、`models/releases/<version>/`。
2026-10-03 實際證據：[package.py](src/aiot_price/models/package.py)、[model-manifest.schema.json](contracts/model-manifest.schema.json)、[MODEL_CARD.md](docs/MODEL_CARD.md)、models/releases/0.1.0/（manifest含hash/切分/能力邊界；fixtures 3案例重現3/3通過）。

- [x] 包含模型、轉換器、品項／單位映射、輸出契約、相依版本與設定；manifest記模型版本、資料hash、訓練時間、7／14天支援與已驗證目標。
- [x] 建立固定輸入與預期輸出的跨主機fixture，檢查hash及載入來源；不反序列化來路不明模型，權重與大型資料保持忽略。

**驗收證據：** 一個自足模型包可在新環境載入並通過fixtures；模型卡與測試報告對應同版本，未通過的私價功能不能包裝成已驗證。

## 本機應用與SERVER

### T19 本機推論與重現入口

**狀態：PASS（2026-10-03）｜依賴：T18；T14可用時納入店價兩模式｜產出：** `src/aiot_price/models/predict.py`、`scripts/predict_local.py`、`tests/model/test_inference.py`。
2026-10-03 實際證據：[predict.py](src/aiot_price/models/predict.py)、[scripts/predict_local.py](scripts/predict_local.py)；真模型7/14查詢輸出符合schema（別名解析、A/B/降級、延遲~200ms）；--check-fixtures 3/3。

2026-10-04 第三輪（審查 F01/F06）：規格可比性接入推論入口（specification/previous_specification 不一致→B 拒）；上週欄位（價格/日期/單位）錯誤全部受控降級不丟例外；布林/Infinity/負值價格、缺時區日期受控 422；「上次無日期」的代理人請求正確走 A。

- [x] 實作共享推論入口，使用design.md的 `ForecastRequest`／`ForecastResponse` 定義與 `contracts/forecast.schema.json` 語意；輸入標準化品項／規格、今日報價時間、今日價／單位、可選上週價／日期與公開資料版本，回傳模式、期限、目標類型、資料日期與模型版本。起點為使用者今日，與公開資料截止時間分開。
- [x] 支援A、B、兩模式比較以及資料不足，推論不重新訓練；檢查同輸入可重現、錯誤模型包與缺資料處理。
- [x] T14未完成時先驗收公開核心與直接推論，把店價適配／B支援狀態明列未提供，不因此拖住公開模型。雙模式的最後驗收仍依T14、T16各自的實作與實際證據。

**驗收證據：** 在目前電腦以打包模型真正執行7／14天查詢，與T18 fixtures一致；保存延遲與實際輸出，不只通過mock。

### T20 建立菜價HTTP API與契約

**狀態：PASS（2026-10-03）｜依賴：T19｜產出：** `src/aiot_price/api/app.py`、`contracts/forecast.schema.json`、`docs/API_CONTRACT.md`、`tests/api/test_forecast_api.py`。
2026-10-03 實際證據：[api/app.py](src/aiot_price/api/app.py)、[API_CONTRACT.md](docs/API_CONTRACT.md)、[test_forecast_api.py](tests/api/test_forecast_api.py)12項全過（真模型包：成功/422拒絕/503資料不足/B降級並列）。

2026-10-04 第三輪修正（審查 F06）：8KB 改按實際串流讀取位元組執行（chunked／無 Content-Length 的 9,198B 請求實測回 413，不再只信標頭）；previous_observed_at 格式錯誤受控降級 B（不再 500）；布林／Infinity 價格、缺時區日期皆受控 422。

- [x] 固定 `POST /forecast`：含品項／規格、公開市場對應、今日日期／價／單位、可選上週紀錄；`mode` 使用 `without_last_week`、`with_last_week`、`both`，輸出每個7／14天結果、狀態、目標類型、來源時間、模型版本與限制。`GET /health` 回報就緒與版本，`GET /metadata` 回報可用來源／品項／單位／模式及其支援狀態，皆不含秘密。
- [x] API重用T19推論，不在API另造轉換；驗證正價格、日期、單位、未知品項、過大輸入及缺B資料，錯誤有清楚代碼與使用者可懂訊息。

**驗收證據：** 契約與真實HTTP請求一致，成功／拒絕／資料不足皆有測試；速度以真模型量測，不只測端點存在。

### T21 建立手機操作介面

**狀態：PASS（2026-10-03）｜依賴：T02、T20｜產出：** `web/`、`docs/UI_FLOW.md`。

2026-10-03 實際證據：[web/index.html](web/index.html)＋app.js＋style.css（無CDN依賴）與[UI_FLOW.md](docs/UI_FLOW.md)；node --check 過、http 200 過；本機 API（127.0.0.1:8010）同源整合實測：手機尺寸390×844填入32元/台斤查詢→A模式7/14結果渲染、開上週開關（28元、2026-09-26）→A/B並排對照含實驗性警示與資料截止天數、南屯市場→錯誤訊息正確顯示（stale_data_unusable）、切回中義恢復查詢；截圖 outputs/e2e/ui_ab_mobile_390x844.png。空值/鍵盤細節為前端代碼審查（buildRequest驗證），未逐一實機操作——真手機操作留待SERVER階段（T32）補。

2026-10-04 第三輪修正（審查 F07/F08）：代理人店號改與表單同源（tw01_ui_prefs_v1，廢 vp_store_id）；代理人區塊顯示結構化 7/14 結果卡（含單位）與實際後端標示（規則結果不標 Qwen）；「保存這次預測／已保存紀錄／匯出／刪除」流程上線（瀏覽器端到端實測，截圖 outputs/e2e/ui_agent_structured_round3.png）。

- [x] 提供單品、今天價格／單位、上週價格選填與實際日期；市場／規格盡量可選，匿名店家可記憶於使用者端，避免多填與整籃流程。
- [x] 有上週資料可並排顯示兩模式的7／14天結果；沒有也能查詢。清楚顯示市場來源、店價估計與未驗證部分，單位不可比時先說明而非默默換算。

**驗收證據：** 在實際手機尺寸驗證輸入、鍵盤、空值、錯誤、更正與結果閱讀；使用者不提供上週記錄也能完成查詢，不需要查看技術欄位才能理解。

### T22 保存預測與對照結果

**狀態：PASS（2026-10-03）｜依賴：T10、T20、T21｜產出：** `src/aiot_price/api/prediction_records.py`、`docs/PREDICTION_RECORDS.md`、`private/predictions/`。
2026-10-03 實際證據：[prediction_records.py](src/aiot_price/api/prediction_records.py)、[PREDICTION_RECORDS.md](docs/PREDICTION_RECORDS.md)、[test_prediction_records.py](tests/api/test_prediction_records.py)全過（roundtrip保留版本/單位、模擬拒收、匿名匯出）。

2026-10-04 第三輪補齊（審查 F08：函式層→一般使用者完整流程）：API `/records` 四端點（POST 保存/GET 摘要清單/GET export 完整匯出/DELETE 單筆刪除，ID 防注入）＋網頁「保存這次預測」「已保存紀錄（刪除/匯出）」UI；瀏覽器端到端實測（查詢→保存→清單顯示；outputs/e2e/ui_agent_structured_round3.png 同場景）。自願保存、不影響查詢；紀錄在 SERVER 端 private/predictions/（本機測試以暫存目錄替換）。

- [x] 提供由使用者選擇保存／匯出的簡單紀錄，保存當時輸入、A／B、7／14天、資料與模型版本，供日後到期價核對；不強制帳號或上傳店家原始紀錄。
- [x] 保護保存位置、去識別、匯出與刪除流程；同店驗證需事前模型輸出，不許到期後重算冒充原預測。

**驗收證據：** 匯出再讀取不遺失版本／日期／單位；關閉保存仍可用基本查詢；私價資料不進入公開報告或伺服器日誌的敏感內容。

### T23 確認RTX3090 SERVER條件

**狀態：HOLD（2026-10-03）｜依賴：無；需要使用者提供可用SERVER資訊｜產出：** `docs/SERVER_INVENTORY.md`。
2026-10-03 狀態：[SERVER_INVENTORY.md](docs/SERVER_INVENTORY.md)已建（已知RTX 3090/24GB；缺OS、位址、連線、目錄、端口、外網方案）。依賴SERVER之T24–T32等待；本機主線不受影響。

- [ ] 確認SERVER作業系統、CPU／RAM／磁碟、3090可用顯存、驅動／CUDA、現有服務與實際連線方式；由使用者安全提供位址與存取方式，不從歷史找密碼。
- [ ] 確認允許的部署目錄、端口、啟停與手機外部連線方法；不預設Linux／SSH、不占用既有服務端口。

**驗收證據：** 真主機只讀檢查輸出與連線證據，秘密不入文件。未取得資訊只HOLD T23及依賴SERVER的任務，繼續本機資料／模型／介面工作。

### T24 跨主機部署菜價模型與一致性驗證

**狀態：TODO｜依賴：T18、T20、T23｜產出：** `deploy/model_service/`、`docs/SERVER_MODEL_DEPLOYMENT.md`、`outputs/server/model_parity/`。

- [ ] 按SERVER實際OS建立相容環境，安全傳模型包並驗hash；菜價推論先評估CPU執行，不假定必須與Qwen搶GPU。
- [ ] 在SERVER跑T18相同fixtures，核對數值容許誤差、7／14天、模式、資料版本與延遲；啟用HTTP服務並測就緒／失敗。

**驗收證據：** 本機與SERVER同包同輸入的對照結果、hash及環境版本；只傳檔不算部署成功，SERVER真API回應才可完成。

### T25 驗證已指定的 Qwen3.8-27B 在 3090 執行

**狀態：DOING（2026-10-03：型號核實完成；3090 實測 HOLD 待 SERVER）｜依賴：T23｜產出：** `docs/QWEN_SERVER_BENCHMARK.md`、`configs/agent_model.yaml`、`outputs/server/qwen_benchmark/`。

**D41：使用者已確認 Qwen3.8-27B，不是 Qwen3-8B。** 下方原「原意待確認／9B首選」保留為歷史，已由 D38 修訂與 D41 取代。此任務只待量化工件、推論引擎、context 及真 3090 測試；不能自動改成較小模型，也不能阻擋 T26/T27 的 GLM 路徑。

2026-10-03 實際證據：官方來源（QwenLM GitHub、HF Qwen org）核實——Qwen3.8 僅 2.4T/27B 兩尺寸，官方權重皆超 24GB 不可行；候選 Qwen3.5-9B（首選，BF16 約 19.3GB、明文支援工具呼叫）/Qwen3.5-4B/Qwen3-8B（皆 Apache-2.0）。產出 [QWEN_SERVER_BENCHMARK.md](docs/QWEN_SERVER_BENCHMARK.md)（核實完成/實測 HOLD 分節）＋[agent_model.yaml](configs/agent_model.yaml)。**待使用者確認 Qwen3.8 原意**（見 DECISIONS D38）；載入/顯存/延遲實測依 T23。

- [ ] 向官方來源確認使用者所稱Qwen3.8的實際可取得名稱、大小、授權與工具呼叫支援；無法確認就記錄，不拿歷史聊天中的型號／連結當證明，也不暗自換模型。
- [ ] 選適合可用24GB顯存與SERVER環境的候選／量化／上下文及推論框架，實際測載入、峰值顯存、延遲、中文品項理解與工具參數正確率。
- [ ] 鎖定能跑的版本與設定；若不可用或速度不足，依測試提出更小官方版本或框架調整，核心菜價模型仍可直接查詢。

**驗收證據：** 真權重載入及實際請求輸出，包含版本、大小、量化、可用顯存、延遲與工具案例；僅官方頁可讀不算3090實測通過。

### T26 實作代理人工具與呼叫流程

**狀態：DOING（2026-10-04 第五輪：S01–S09 修堅——Hermes 真介面（handler JSON 字串/真 callback 追蹤/無事後補算）、TrustedContext 輸入忠實、隔離 import 前生效；227 測試＋乾淨環境同數；真 GLM 待金鑰、真 Qwen 待 SERVER）｜依賴：本機契約與整合依 T20 及共用缺陷修復；真 GLM 請求依本案 API 設定；只有 SERVER Qwen 子項依 T24/T25｜產出：** `src/aiot_price/agent/tools.py`、`src/aiot_price/agent/service.py`、`configs/agent_prompt.md`、`tests/agent/` 及實際 Hermes 整合設定／工具追蹤。

- [ ] **T26 本機／GLM 子項（D41）：** 先修第三輪 R01–R05 共用防線；建立供應商無關的工具契約，按 Hermes 官方介面查驗整合（框架暫定），只暴露本案有限工具。真正模型 tool_calls、工具參數驗證、執行及結果回送需有證據，不能只有 GLM 文字改寫。
- [ ] **T26 切換子項（D41）：** provider／model／Base URL／key_env 集中配置，GLM API 與本機 Qwen3.8-27B 共用工具及前端；如實標示實際 provider／model／降級，模型切換不改菜價工件、封存評估或可信保存。未明確允許時不做本機→雲端自動 fallback。

2026-10-03 實際證據：分層代理人（確定性規則提取＋2 有限工具與API同源＋可插後端：RuleBackend/QwenBackend 降級安全）；`POST /agent/query` 上線（web「問代理人」入口實測截圖 outputs/e2e/ui_agent_mobile.png）；test_tools 12 項過；單次查詢工具呼叫上限 3。

2026-10-04 第三輪修正（審查 F01/F02/F03/F07，證據 tests/agent/test_review_f01_f06.py＋test_review_f02_f08.py 共 36 項行為測試）：子句級價格綁定（單位/日期/店家/規格）、明示日期優先、「昨天」如實、「上次」無日期不補 t-7、另一店/換規格拒 B、Qwen 輸出真值對照驗證器（誇大詞/未驗證數字日期價格/方向衝突全擋）、提示檔缺失不上線、`/agent/query` 丟執行緒池（慢後端不阻塞 health）、回應含 backend_used/degraded/degraded_reason/forecast 結構化真值。**架構差異明示（未冒充）**：本設計 Qwen 只做解釋層，工具參數由確定性規則產生；若採 Qwen 自行生成 tool_calls 的架構需在 SERVER 實測後另驗（T25）。

- [ ] 定義取得可用公開行情、呼叫 `POST /forecast` 的有限工具及參數schema，建立 `POST /agent/query` 接收自然語言查詢；代理人提取菜名、價格與日期，缺必要資料先要求補充，不自行發明店價。
- [ ] 真正執行工具再回答；限制工具名、端點、呼叫次數與超時，不給代理人任意shell、任意URL或修改模型的權限。

**驗收證據：** 保存匿名的「使用者輸入→工具參數→真API結果→回答」追蹤，含兩模式與7／14天；不能用模板假裝呼叫模型。

### T27 檢查代理人回答忠實與失敗降級

**狀態：DOING（2026-10-04 第四輪：離線防線 48 項新測試過；真 GLM／真 Qwen 忠實性分開待金鑰／SERVER）｜依賴：T17、T26；GLM 子項不依賴 T23–T25｜產出：** `tests/agent/test_faithfulness.py`、`docs/AGENT_EVALUATION.md`、`outputs/agent_evaluation/`。

- [ ] **T27 分後端驗收（D41）：** 同一案例集先做離線協議／錯誤防線測試，再以真 GLM API 記工具參數正確性、真值忠實性與延遲；日後切 Qwen3.8-27B 重測。數字必須綁期限／模式／單位；工具失敗、缺資料、空 content、不同比較商品、保存來源及雲端降級均須覆蓋。GLM 通過不代表 Qwen 通過，聊天成功不代表工具整合完成。

2026-10-03 實際證據：本機層覆蓋菜名歧義/單位/無上週/有上週標實驗性/不漲忠實呈現/缺資料要求補充/無資料市場不給假結論/Qwen失敗降級/無機率字眼——test_faithfulness 14 項＋[AGENT_EVALUATION.md](docs/AGENT_EVALUATION.md)＋outputs/agent_evaluation/local_results.json（8 案例）。真 Qwen 載入、prompt injection 實測與延遲量測依 T24/T25。

- [ ] 用固定中文案例測菜名歧義、單位、無上週價、日期不比、工具回傳不漲、來源過期、Qwen／API超時與惡意指示；核對參數、結果與最終回答。
- [ ] 回答不能改變工具方向／數字、捏造原因／機率或將均價說成同店真值；Qwen不可用時手機仍能顯示直接模型結果與說明。

**驗收證據：** 有案例數、工具成功／參數正確／回答忠實與延遲結果、失敗例；所有核心錯誤有處理，不能只挑成功對話展示。

### T28 完成安全、隱私與資源限制

**狀態：DOING（2026-10-03：本機層完成；對外部署補強於 T29）｜依賴：T20、T22、T26｜產出：** `docs/SECURITY_PRIVACY.md`、相關服務設定與 `tests/api/test_access_limits.py`。

2026-10-03 實際證據：body>8KB→413、每IP每分鐘30次→429（滑動窗口）、日誌不記 body、/health與/metadata無秘密實測（test_access_limits 6 項過）；[SECURITY_PRIVACY.md](docs/SECURITY_PRIVACY.md) 列 SERVER 部署待補項（TLS/反向代理限流/Qwen端口不對外/服務帳號）。

- [ ] 按實際使用範圍設存取控制、請求大小／頻率／超時、允許來源、敏感紀錄保護與日誌遮罩；Qwen與內部模型端點不無限制暴露。
- [ ] 核對私價留存、匯出／刪除、店家匿名、金鑰環境設定及依賴；保護模型載入與外部資料文字，避免被當操作指令。

**驗收證據：** 未授權、超量、惡意參數與日誌抽查實測；正常手機使用仍可完成，秘密與原始店價沒有進入提交候選檔。

### T29 部署SERVER完整服務與手機網路入口

**狀態：TODO｜依賴：T21、T24、T27、T28；需具體網路入口｜產出：** `deploy/`、`docs/DEPLOYMENT.md`、`outputs/server/deployment/`。

- [ ] 按實際OS設定Web、API、Qwen服務的啟停／健康檢查與相依順序；選已允許的私人或公開連線方式，保持內部端點隔離。
- [ ] 完成手機在SERVER外的真查詢，核對來源、版本、代理人工具與7／14天結果；需要外部帳號／網域／公開服務卻尚無目標時只提出具體依賴，不臆造發布。

**驗收證據：** 實際手機外部網路端到端紀錄、可用入口與SERVER日誌對得上，電腦／服務離線時有清楚狀態；本機畫面或內網API不能當成蔬果行可用證明。

### T30 建立資料更新、監控與模型更新流程

**狀態：DOING（2026-10-03：本機手動更新流程四情境實測通過；SERVER 自動化/排程待 T24/T29）｜依賴：T05、T24、T29｜產出：** `scripts/update_public_data.py`、`docs/OPERATIONS.md`、`configs/update_policy.yaml`。

2026-10-03 實際證據：[update_public_data.py](scripts/update_public_data.py)（schema驗證/快照比較/--dry-run/--refresh-release-history 備份＋只追加＋寫後核對）＋[update_policy.yaml](configs/update_policy.yaml)＋[OPERATIONS.md](docs/OPERATIONS.md)；四情境實測（真實下載無新資料、模擬新資料、失效來源、schema變動）通過，報告 outputs/update_tests/；追加機制在暫存副本真實執行（12,288→12,309列、自動備份、append-only 核對），0.1.0 原檔 hash 前後不變。

- [ ] 先提供手動可驗證更新流程，檢查來源hash／日期／schema，避免重複與壞檔覆蓋；舊資料及更新失敗有日期提示與降級。
- [ ] 明確區分「刷新公開行情／特徵」與「重訓並升級模型」；重訓仍在Windows經T08–T18再傳SERVER，不每次查詢就重訓。
- [ ] 自動排程如確實需要，依部署環境及使用者已接受的執行方式設定；不因本任務建立Codex提醒或未被要求的長期自動化。

**驗收證據：** 新資料、無更新、失效來源、schema變動各實測一次，模型版本不因資料刷新偷偷更換；運維文件列資料／模型版本與故障查法。

### T31 建立回滾與恢復

**狀態：TODO｜依賴：T18、T29、T30｜產出：** `deploy/rollback/`、`docs/ROLLBACK_RUNBOOK.md`。

- [ ] 保留上一個可用模型包、配置與服務版本，描述升級、失敗回退、停止與恢復步驟；備份私價遵循留存與訪問範圍。
- [ ] 在不影響既有SERVER服務的測試窗口驗證模型版本退回與服務重啟；不移除未知資料或以重設主機解決配置問題。

**驗收證據：** 實際回滾前／後版本、health與fixture結果；文檔有安全的操作範圍與復原點，不只有未執行指令。

## 整合、報告與正式交付

### T32 完整端到端與行動使用驗收

**狀態：TODO｜依賴：T22、T27、T29、T31｜產出：** `docs/E2E_ACCEPTANCE.md`、`outputs/e2e/`。

- [ ] 真手機輸入今日價，分別無／有上週價，取7／14天結果並保存；確認代理人真實工具調用、API／模型版本、UI與匯出一致。
- [ ] 驗證單位錯誤、資料不足、換規格、網路中斷、SERVER／Qwen關閉、來源過期、重啟與回滾；模型／代理人功能與手機可用性分開報告。

**驗收證據：** 每個場景有時間、輸入、結果與問題狀態；不能用mock、靜態網站或本機錄影冒充SERVER外部使用。

### T33 完成研究報告、投影片與課程對照

**狀態：DOING（2026-10-03：初稿完成；期末細則/組員/最終數據齊後定稿）｜依賴：T01、T04、T15、T17、T27、T32；T16結果如有則納入｜產出：** `docs/FINAL_REPORT.md`、`docs/FINAL_SLIDES.md`及當屆要求的實際投影片格式。

2026-10-03 實際證據：[FINAL_REPORT.md](docs/FINAL_REPORT.md)（10章＋數字來源對照表）與[FINAL_SLIDES.md](docs/FINAL_SLIDES.md)（15頁）初稿；數字與 outputs JSON 逐項核對（含 momentum 基線與選定模型相當的負向並列）；組員/期末格式標待補。

- [ ] 整理動機、具體前作、資料／授權、雙主機架構、代理人工具、方法、時間切分、7／14天量化、A／B私價結果與限制；圖表使用實際評估輸出。
- [ ] 映射當屆每項交付；私價驗證未完成則明列資料／到期缺口，公開市場成績不填入同店欄，也不稱符合全部評分細則。

**驗收證據：** 報告數字可重算並對應版本；投影片可讀，期中與期末要求分開，所有引用、匿名例與未完成事項清楚。

### T34 完成README、重現包與公開前檢查

**狀態：DOING（2026-10-03：REPRODUCIBILITY 初版完成含 2026-10-04 實測；PUBLICATION_REVIEW 與最終 README 待 T32 後）｜依賴：T18、T30、T32、T33｜產出：** 更新 `README.md`、`.gitignore`；新增 `docs/REPRODUCIBILITY.md`、`docs/PUBLICATION_REVIEW.md`。

2026-10-03 實際證據：[REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md)（環境/資料/管線/訓練/評估/打包/fixtures/API/pytest 全流程＋hash 對照；實測 fixtures 3/3、pytest 98 passed）；requirements-lock.txt 已補 fastapi/uvicorn/pyarrow/httpx 鎖版；SERVER 重現標待 T24。

- [ ] 寫出本機訓練、SERVER啟動、API／手機使用、版本、資料取得、重現評估與限制；將大型權重／資料的取得方式寫清，不把忽略文件不存在說成可直接重現。
- [ ] 檢查提交候選中的秘密、原始私價／店家識別／錄音、資料授權、檔案大小、連結與輸出；只準備可審閱內容，不擅自建立公開遠端或提交課程。

**驗收證據：** 乾淨環境依README完成核心推論／指定評估，連結與依賴可用；公開檔案清單及敏感掃描結果經人工覆核。

### T35 製作展示影片與完成指定外部交付

**狀態：TODO｜依賴：T01、T32–T34；需真實交付目標與發布範圍｜產出：** `docs/DEMO_SCRIPT.md`、`recordings/final_demo/`、`docs/DELIVERY_RECORD.md`。

- [ ] 依當屆規格準備並錄製真流程、雙模式、7／14天、SERVER代理人工具、量化成果與限制，遮罩個人資料；未確認時不把期中約10分鐘當期末硬規則。
- [ ] 取得GitHub／影片／課程提交的實際目標與已授權範圍，再發布已審閱內容；若目標或授權未提供，完成可審閱檔案後HOLD發布部分。
- [ ] 交付後驗證可開啟網址、實際版本、影片可看及系統可操作，保存提交／更新證據；不能把本機檔或登入完成說成外部交付已完成。

**驗收證據：** 實際成品、目標與確認記錄；公開內容無秘密或原始私價，交付狀態與可用網路成果一致。

### T36 獨立總驗收與最後交接

**狀態：TODO｜依賴：T01–T35的產出／缺口紀錄｜產出：** `docs/FINAL_ACCEPTANCE.md`、更新 `docs/GLM_PROGRESS.md`、`docs/DELIVERY_CHECKLIST.md`及本檔。

- [ ] 由未撰寫該部分的審查者核對資料、時間洩漏、真實訓練、公開／同店分界、A／B公平性、跨主機一致性、代理人工具、手機網路、隱私及正式交付；GLM自述完成不是唯一證據。
- [ ] 修正可處理問題，再核對變更影響的必要項目；保存剩餘HOLD與責任／下一步，不為結案把未知改PASS。
- [ ] 交接目前電腦的重訓步驟、SERVER啟停／更新／回滾、模型與資料版本、驗收報告、備份／秘密位置的安全說明，以及實際外部連結。

**驗收證據：** 總驗收逐项指向已跑證據及尚缺項；可以分別判斷公開模型、同店A／B、代理人、部署與課程交付是否完成，而不是只有「全部成功」。

## 依賴與可並行順序

- 第一批：T01、T23可同時查；T02完成收斂後，T03–T04及T10可並行。SERVER資訊未到不阻擋本機主線。
- 資料主線：T05 → T06 → T07 → T08 → T09 → T11 → T12 → T13 → T15 → T17 → T18 → T19；T14是並行的店價適配支線，不阻擋公開模型評估。
- 店價主線：T10 → T14 → T19／T22 → T16。真同店測試需等待到期，應早規劃採集；成熟前不把同店效果列完成。
- 應用主線：T19 → T20 → T21 → T22。SERVER主線：T23 → T24／T25 → T26 → T27 → T28 → T29 → T30 → T31 → T32；T24與T25可獨立進行，依賴本機模型與UI的條件仍依各項所列。
- 交付主線：已取得的模型／部署結果 → T33 → T34 → T35 → T36。最終課程規則與外部目標只阻擋相應交付，不阻擋準備可審閱檔案。

每輪GLM回報用「完成的任務與證據、仍HOLD的具體原因、下一輪任務」三部分。開始訓練、部署與發布前，均以當時的設計、已授權範圍及實際環境為準。
