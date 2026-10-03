# 第四輪報告：R01–R08 修復＋供應商可切換代理人（GLM API 先行）

執行：GLM（開發執行者），2026-10-04。基準提交：`44dabe3`（第三輪）＋工作區 D41 需求更新（保留）。本輪本地提交見文末。程式碼證據目錄：`outputs/audits/round4_glm_api/`。

## 1. R01–R08 修復對照（原缺陷 → 修後證據）

| 項 | 原缺陷（審查重現） | 修復 | 證據 |
| --- | --- | --- | --- |
| R01 | 工具錯誤（南屯 stale）＋模擬捏造回答以 `backend_used=qwen` 放行；缺輸入亦放行 | 主流程短路：`parsed.missing`／`unit_non_comparable`／無有效工具結果時**不送 LLM**，直接規則層回「補充／無法預測」；驗證器移除 `forecast.error → return True` 短路，改為「無結果時任何期限預測主張一律拒」 | `tests/agent/test_review_round4.py::TestR01ToolFailure` 3 項（含審查原文案例） |
| R02 | 數字只查「出現過」：7/14 交換通過、中文期限繞過、`content=null` 變 `"None"`、A/B 混用 | 驗證器重寫為**期限×模式×單位綁定**：期限詞辨識（含一週/兩週中文）；各期限句的百分比/價格必須屬於該期限的 A 事實（B 數字需句內 B 標示）；公斤/台斤標示與工具單位一致；`content` 非 str 一律降級 | `TestR02NumberBinding` 6 項（交換/跨模式/中文期限/null/單位/正確回答不誤擋） |
| R03 | 跨品項當同品項、無效日期補 t-7、9/1 不識別、負號消失、兩斤32當單價 | 每筆報價綁定品項/數量/單位/金額/日期/解析狀態：跨品項拒 B、`invalid_date` 標記（≠未提供）、月日寫法解析（9/1→2026-09-01）、負數過濾、數量>1 換算單價（兩斤32→16） | `TestR03ParserIntegrity` 5 項（審查五案例） |
| R04 | 偽造/simulated 完整結果可保存；`results=[null]` 入庫拖垮清單；頂層 `[]` 500；saved_at 用報價時間 | **保存改 request_id 綁定**：伺服器記憶體暫存（LRU 500）真推論結果；`POST /records` 只收 `{"request_id"}`，客戶端完整結果一律 422；結構驗證（results 元素須 dict）；壞紀錄跳過不拖垮不刪除；`saved_at` 為真實保存時間（POST/GET/匯出一致；重啟後暫存清空→404 請重新查詢） | `TestR04RecordsIntegrity` 5 項 |
| R05 | 有 previous_observed_at 缺 price → 500；store_id 物件/非匿名通過 | 「只有日期缺價」受控降級 B；`to_taiwan_jin` 包 TypeError；store_id 後端驗證（str、`^[A-Za-z0-9_-]+$`、≤32）→ 400 | `TestR05OptionalFieldCombos` 9 項（組合矩陣） |
| R06 | 代理人查詢不設 lastRun、保存列對應舊表單結果 | 代理人成功且附有效預測→設定 `lastRun{source:'agent'}`＋`resetSaveBar()`＋提示「保存的是代理人結果」；表單同理標 source；兩入口交錯時保存永遠=最後成功查詢 | **真瀏覽器**（390×844）四情境實測：代理人單獨→保存成功（真實時間戳）、表單→標表單、代理人60→標代理人、清單顯示正確 |
| R07 | `--config` 不存在裸拋無報告；reload 失敗回 failed 但資料已新 | （subagent）config 載入入受控區（exit 1＋報告）；提交邊界=快照+原子替換核對通過；reload 失敗→`data_updated_reload_failed`（exit 5）＋重啟指引＋備份位置；退出碼表 0-5 四處同步 | `outputs/audits/round4_glm_api/r07_update/`（含 5 組情境無回歸＋正式工件 hash 不變） |
| R08 | 「所有工件未動」過度概括、乾淨環境只有 98、文檔舊狀態 | 見 §9 hash 對照（fixtures 第三輪已變更之事實保留說明）；乾淨環境重跑**192**（進行中，見 clean_env_final）；文檔同步見 §10 清單 | 本報告＋ clean_env_final.md |

**第三輪重現器重跑**（複製至 `outputs/audits/round4_glm_api/rerun_round3/`，不覆蓋歷史）：25 項中 23 過；3 個未過項**全部是本輪審查要求的契約演進**（重現器斷言舊契約）：①②客戶端直貼完整結果保存→現被 R04 防偽正確拒 422；③reload 失敗保舊→現為 R07 的 `data_updated_reload_failed` exit 5；④保存 body `forecast_response` →現為 `request_id`。UI 檢查 `agent_uses_form_store_id`、`agent_only_prediction_is_saveable` 通過。

## 2. Hermes Agent 整合（官方 0.19.0，非手刻冒名）

- **套件**：PyPI `hermes-agent==0.19.0`（Nous Research 官方 Trusted Publishing、MIT、Python ≥3.11<3.14）；**import 名 `run_agent`**；已裝入專案 .venv 並鎖版。
- **整合層**：`src/aiot_price/agent/hermes_runner.py`——用官方 `model_tools.registry.register()` 註冊兩個菜價工具到專屬 toolset `aiot_price`；`AIAgent(..., enabled_toolsets=["aiot_price"])` 白名單**只開這兩個工具**，terminal/browser/execute_code 等 28 個內建全部排除（離線實測：31→2）。
- **安全（探測事故教訓）**：`HERMES_HOME` 固定 `private/hermes_home`（隔離全域設定）；環境 scrub（移除 OPENAI/OPENROUTER/ANTHROPIC 等金鑰，僅映射 profile 指定 key）；`quiet_mode`＋`skip_memory`＋`skip_context_files`＋`save_trajectories=False`；不用 `hermes-agent` CLI entry point。
- **GLM/Qwen 切換**：GLM 走官方 `zai` provider（`GLM_API_KEY`）；自架 Qwen3.8-27B 走 OpenAI 相容 `base_url` 直接建構——同一整合層。
- **輸出防線**：Hermes 最終回答同樣過 `validate_qwen_answer` 真值對照（捏造→降級規則），不因框架放寬。
- 探測詳情：`docs/research/HERMES_INTEGRATION_PROBE.md`＋`outputs/audits/round4_glm_api/hermes_probe/`（11 檔）。

## 3. GLM API 配置狀態（不含金鑰值）

- 檢查位置：環境變數（GLM_API_KEY/ZAI_API_KEY/AIOT_GLM_API_KEY/BIGMODEL_API_KEY/ZHIPUAI_API_KEY 等）與專案 `.env`/`.env.local`/`private/*.env`——**全部未配置**。
- **待使用者提供**（見 §10 缺項）：①實際平台（Z.AI 或 BigModel——兩者端點不互換）；②該平台可用的 model ID；③金鑰設定方式（建議 `private/.env` 或系統環境變數 `AIOT_GLM_API_KEY`，設定後寫入 `AIOT_AGENT_PROFILE=glm_zai` 或 `glm_bigmodel`）。
- 附註：Hermes 探測時 CLI 從使用者全域環境偵測到一個 `sk-` 金鑰（來源未查明、值未保存）；若那是你的 GLM key，將它設為 `AIOT_GLM_API_KEY` 即可用（不確定則先確認方案允許本專題使用情境）。
- 依指示：**缺金鑰只阻擋真 GLM 呼叫**——R01–R08、適配層、Hermes 整合、離線協議測試均已完成。

## 4. 真正 tool_calls 流程（離線協議驗證；真 GLM 待金鑰）

`run_agent_loop()`（`providers.py`）實作完整迴圈：LLM 生成 `tool_calls` → **白名單**（僅 2 工具；未知→錯誤訊息回模型不執行）→ **參數鍵白名單**＋語意驗證（走 ForecastEngine 與 API 共用）→ **真菜價工具執行** → 結果以 `role:"tool"` 回送 → 最終回答 → **真值驗證器**。離線測試（mock OpenAI 相容回應＋真 ForecastEngine）19 項：完整 roundtrip（含 tool 訊息回送斷言）、捏造拒絕、缺輸入零請求、provider 失敗保留真值、無工具結果不採用、max_turns 截止、端點分流與 503。

## 5. 啟動方式

```bash
cd C:/Users/prometheans/Documents/AIOT_FinishProject
PYTHONPATH=src .venv/Scripts/python.exe -m uvicorn aiot_price.api.app:app --host 127.0.0.1 --port 8000
# 網頁 http://127.0.0.1:8000（查詢/問代理人/保存/匯出/刪除）
```

## 6. 後端切換（明確配置；不自動切雲端）

| 環境變數 | 值 | 行為 |
| --- | --- | --- |
| `AIOT_AGENT_PROFILE` | `rule`（預設） | 規則解析＋真工具＋模板（無 LLM、無金鑰） |
| | `glm_zai` / `glm_bigmodel` | GLM API（需 `AIOT_GLM_API_KEY`＋configs/agent_model.yaml 填 model ID；缺→503 明確報錯不靜默降級） |
| | `qwen_local` | 本機 Qwen3.8-27B 端點（base_url 佔位待 SERVER；**失敗不切雲端**） |
| `AIOT_AGENT_FRAMEWORK` | `direct`（預設）/ `hermes` | 直達 OpenAI 相容迴圈 / 官方 hermes-agent 框架 |

## 7. 測試命令與結果（本輪程式版本）

- `.venv/Scripts/python.exe -m pytest tests/ -q` → **192 passed**（基準 134 →第四輪 +58：R01-R05 回歸 29、providers 協議 19、hermes 離線 5、併發/串流 4、結構 1；無刪測試無放寬——第三輪舊斷言僅因 R04 契約演進調整為更嚴格形式）。
- 第三輪三重現器重跑：§1 對照（3 未過項均為契約演進，已列差異說明）。

## 8. 乾淨隔離環境（驗證 I）

`outputs/audits/round4_glm_api/clean_env_final.md`（專案外 %TEMP% 全新 venv：安裝→真工件載入→全套 192）——見該檔實測記錄。

## 9. 受保護工件 hash（本輪後實算）

| 工件 | SHA256（前16） | 對照 |
| --- | --- | --- |
| public_test_results.json | `2d28acd2f2c3e5ce` | =審查記錄 `2d28acd2…574b8` ✓ |
| test_predictions.csv | `adf2ca0a246b5489` | 不變 |
| model_h7/h14.joblib | `ea98f31d…`/`d88fd53d…` | 不變 |
| manifest.json | `6f82dac547a72a69` | 不變 |
| split_list.csv | `4e1365746a25275e` | 不變 |
| 會議錄音 10.txt | `46b80ee649fcc11d` | =初始值 ✓ |

fixtures.json：第三輪因 evidence_summary 文字修正重生成（當時已記錄）；本輪未動。模型分數、切分、選型、負向結果全部未變（h7/h14 macro-F1 0.4218/0.4169；momentum 0.4226/0.4306；點 MAE 未勝不變價；up 召回約10%/9%；B=α0.3 實驗性未驗證；機率 null）。

## 10. 未完成與所需資訊

1. **真 GLM 呼叫**（驗證 G）：待使用者提供平台/model ID/金鑰設定（§3）。金鑰就位後執行小批量真請求驗證 tool_calls 與忠實性。
2. **真 Qwen3.8-27B**（3090 顯存/延遲/工具正確率）：待 SERVER（T23/T25）；本機端點適配已用協議測試證明。
3. T16 真店 A/B、T32 外網手機、T35 發布：各自 HOLD（不可用模擬補 PASS）。
4. Hermes `chat()` 端到端（真 LLM）：同 1。
5. 本輪提交：見 Git log（本地 commit，未推送）。
