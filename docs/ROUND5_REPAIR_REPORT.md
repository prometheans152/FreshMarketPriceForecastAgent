# 第五輪修復報告：S01–S09

執行：GLM，2026-10-04。基準：受審 HEAD `f146b97`（第四輪）；本輪程式提交見 Git log。證據目錄：`outputs/audits/round5_repair_run1/`。歷史審查目錄未覆寫。

## 逐項狀態（S01–S09）

| 項 | 狀態 | 修復內容 | 證據 |
| --- | --- | --- | --- |
| S01 Hermes 真介面 | **已修** | 依安裝版 0.19.0 原始碼重寫：建構參數改實際支援集（`ephemeral_system_prompt`/`max_iterations`/`max_tokens`/`tool_complete_callback`；無 `system_prompt`/`_env`）；handler 改 registry 慣例 `handler(args, **kwargs)` 且**回傳 JSON 字串**（dict 回傳被 normalize 拒——審查未發現的深層根因）；追蹤以 `tool_complete_callback` 權威記錄（tool_call_id/args/result），**移除事後重算**；無工具執行→`no_tool_execution_observed` 降級，不得產生成功狀態；每請求 override 重註冊（不綁舊引擎） | test_hermes 5 項（含真 AIAgent＋真 openai SDK 型別 mock＋真 dispatch 完整往返） |
| S02 隔離/平台/rule | **已修** | 隔離在 **import run_agent 之前**執行（模組載入一次）：映射 GLM_API_KEY→AIOT_GLM_API_KEY 後移除 Hermes 備援金鑰鏈（GLM/ZAI/OPENAI/OPENROUTER/…）、HERMES_HOME 固定專案隔離目錄；Hermes 一律顯式 `base_url`（zai 有 key 會 probe 兩平台——顯式 base_url 防之）；`/agent/query` rule 分支不再建 QwenBackend（rule=永遠零 LLM）；glm_zai/glm_bigmodel 各用自己 base_url | test_hermes 隔離測試（產品本身 scrub，非測試 wrapper）＋test_providers 端點分流 |
| S03 輸入忠實 | **已修** | `TrustedContext`（可信規則解析→品項/市場/價格(台斤)/報價日/允許模式/上週值/店號）；工具執行前 `validate_args_against_context`：改價/改日期/換品項/換市場/無中生有上週價/未允許模式全拒（等價單位換算接受）；店號一律呼叫端值；system 注入後端提供之可信日期（Asia/Taipei） | test_providers `TestS03`（審查五案例：999 元、補 28 元、絲瓜復活 B、店號 b、10/1 日期） |
| S04 輸出事實分離 | **已修** | 驗證器重構：事實以 (mode,horizon,field,unit) 分離——百分比/價格不同集合、A/B 不聯集（B 段只准 B 值、A/B 對照段聯集）；期限詞**定位分段**（一句多期限按位置切，逗號連句不誤拒）；日期配就近期限（交換目標日→拒）；「下週」等口語期限入表；非目標日（起點/行情日）排除配對 | test_round5_s04 8 項（4 審查案例拒＋正向不誤擋） |
| S05 保存完整性 | **已修** | request_id **伺服器生成**（客戶端值→`client_ref`；同 ID 不同輸入不再覆蓋）；simulated 沿全流程（請求/回應/保存/清單）；合法 JSON 壞結構（results=[null]）讀取受控跳過＋`skipped_bad_records` 計數（原檔保留）；代理人保存附標準化輸入＋provider/backend_used/runtime；saved_at=真實保存時間 | test_round5_s05 7 項 |
| S06 秘密遮罩 | **已修** | 上游錯誤 body 只遮罩後進內部 stderr（`mask_secrets`：sk-/Bearer/api_key= 模式）；對外例外只有穩定碼（`provider_http_error:401`）；degraded_reason/answer 不含 body | test_providers 錯誤路徑（合成 canary 不外流） |
| S07 資源上限 | **已修** | 工具總數真上限（`remaining<=0` 不再 `max(1,…)` 多執行）；每個宣告的 tool_call_id 都有回覆（超預算回 `tool_budget_exceeded` 協議訊息，不留懸空 ID）；總時間上限（total_timeout）；Hermes `max_iterations`/`max_tokens` 由 profile 映射 | test_providers 迴圈測試 |
| S08 解析器 | **已修**（subagent） | 2公斤80→40、0.5斤16→32（小數數量）、當次非法日期→要求澄清（不改今天）、「每斤32共買兩斤」不誤除、上週公斤數量換算、12/25 遠未來月日要求澄清、全域年份移除（參數傳遞）；防回歸 47 項 | test_s08_parser 20 項（先紅 8） |
| S09 假通過 | **已修** | 配置完整驗證（model/base_url 缺→明確 503＋具體建議）；`_load_private_env()` 實作（private/.env 只載 AIOT_ 前綴、既有環境優先、冪等、不借 Hermes dotenv）；FakeAgent 測試改真 AIAgent＋SDK 型別 mock；saved_at 測試先 assert 200 | test_round5_s05 環境載入測試＋test_hermes 重寫 |

## Hermes 實際版本與真建構/dispatch

- 版本：`hermes-agent==0.19.0`（Nous Research；import 名 `run_agent`）。
- **真建構**：`AIAgent(model, provider=None, api_key, base_url, ephemeral_system_prompt, enabled_toolsets=["aiot_price"], quiet_mode, skip_memory, skip_context_files, save_trajectories=False, max_iterations, max_tokens, tool_delay=0, tool_complete_callback=recorder)`——離線實測成功（test_hermes 全程真物件）。
- **真 dispatch**：`model_tools.registry.register(name, toolset, schema, handler, override=True)`；handler `def handler(args, **kwargs)` 回傳 **JSON 字串**（dict 會被 `_normalize_handler_result` 拒——本輪發現的深層根因，審查重現的 TypeError 由此而來）。
- **真工具追蹤**：`tool_complete_callback(tool_call_id, name, display_args, function_result)` 逐事件記錄；**全程無事後補算**——驗證：模擬模型完全不呼叫工具時回 `no_tool_execution_observed`（非成功）。

## 隔離/切換/零雲端證據

- 產品本身（非測試 wrapper）在 import 框架前 scrub 供應商金鑰鏈＋HERMES_HOME 隔離（test 以合成 canary 驗證 OPENAI/OPENROUTER/GLM 鍵被移除、AIOT_* 保留）。
- rule 分支零 LLM 建構；glm_zai/glm_bigmodel 各自 base_url；qwen_local `cloud_fallback=false`。
- 真 GLM **未呼叫**（金鑰仍未配置——待使用者提供平台/model ID/金鑰設定）。

## 驗證結果（本輪自驗；未經新一輪獨立審查）

- **A（Hermes＋模擬傳輸）**：test_hermes 5 項（真建構→真 dispatch→工具回送→捏造拒絕）。
- **B（direct 防改寫）**：test_providers S03 案例全過。
- **C（後端切換/併發）**：rule 零 LLM、503 分流、同 ASGI 併發＋chunked 413（既有 4 項＋分流）。
- **D（真瀏覽器）**：表單45→保存、代理人60→保存（交錯正確指向）、快速連續（代理人後到正確接管）、清單含中繼資料、刪除 2→1、匯出連結存在。
- **E（API/資源）**：併發/串流/上限測試全過。
- **F（安全）**：隔離 scrub、錯誤遮罩、未知工具拒絕測試全過。
- **G（完整回歸）**：**227 passed**（第四輪 192→+35；無刪測試；兩處舊斷言因更嚴格契約更新，已註明）。
- **H（乾淨環境）**：專案外全新 venv → **227 passed**＋hermes 0.19.0 import OK（`outputs/audits/round5_repair_run1/clean_env_round5.md`）。
- **R07 無回歸**：五情境＋round3 回歸全過、正式工件不變（`r07_rerun/summary.json` 全 true）。
- **凍結工件**：評估 JSON（`2d28acd2…` 重算一致）、CSV、雙權重、manifest、public_history、切分清單、逐字稿——**全部不變**。fixtures.json 因 S05 契約（request_id 伺服器化＋simulated 欄位）重生成：舊版備份於 `fixtures_pre_s05_backup.json`，語義差異核對=0（預測數字完全不變）。

## 使用者現在本機可實際操作

```powershell
cd C:\Users\prometheans\Documents\AIOT_FinishProject
$env:PYTHONPATH="src"; .venv\Scripts\python.exe -m uvicorn aiot_price.api.app:app --host 127.0.0.1 --port 8000
# 瀏覽器開 http://127.0.0.1:8000
# - 表單查價／「用問的」代理人（rule 模式，零 LLM）
# - 保存/清單/匯出/刪除（含 provider 與標準化輸入追溯）
# 切換後端：$env:AIOT_AGENT_PROFILE="glm_zai"（需 AIOT_GLM_API_KEY＋configs/agent_model.yaml 填 model）
# 框架切換：$env:AIOT_AGENT_FRAMEWORK="hermes"
# 金鑰檔：private/.env（僅 AIOT_ 前綴；系統環境變數優先）
```

## 未完成（不可用模擬補 PASS）

1. **真 GLM 呼叫**：待使用者提供（平台 Z.AI/BigModel、model ID、金鑰設定為 `AIOT_GLM_API_KEY`）。
2. **真 Qwen3.8-27B/3090**：待 SERVER。
3. T16 真店 A/B、T32 外網手機、T35 發布：各自 HOLD。
4. 模型負向結果完全不變（momentum 未勝、點 MAE 未勝不變價、up 召回低、B 未驗證、機率 null）。
