# 代理人評估（T27）

日期：2026-10-03。狀態：**本機層（規則後端＋工具層）完成；Qwen 端忠實性待 SERVER 實測**（T25/T24 後補測，屆時更新本文件）。

## 架構分層（忠實性設計）

- **提取層（確定性規則）**：菜名別名、價格（「一斤32」「32元」「一公斤80」）、單位、市場、上週價由 `parse_query` 正則解析——可單測、不隨機、不猜。
- **工具層（有限）**：僅 `get_market_quote` 與 `post_forecast`（與 HTTP API 同源）；每查詢最多 3 次呼叫。
- **解釋層（可插）**：本機 RuleBackend（模板逐字引用工具數字）；SERVER 上 QwenBackend（OpenAI 相容 API，系統提示 `configs/agent_prompt.md` 禁止編造數字/機率/原因）。Qwen 失敗自動降級規則回答——手機仍顯示真實模型結果。

## 本機測試結果（tests/agent/，2026-10-03 實跑）

- test_tools.py：12 項（解析確定性、別名、公斤/台斤/不可比單位、上週價、缺項要求補充、不猜價、工具行為、呼叫上限）全過。
- test_faithfulness.py：14 項全過，涵蓋 TASKS T27 指定情境的可行本機子集：

| 情境 | 結果 |
| --- | --- |
| 菜名歧義（高麗菜/青江菜/絲瓜別名） | ✓ 正確映射 crop_id |
| 單位（台斤/公斤/一顆不可比） | ✓ 公斤正確、一顆引導改單位不換算 |
| 無上週價 | ✓ 走 A 模式，回答不提 B |
| 有上週價 | ✓ both 模式，回答標「實驗性、未經同店驗證」 |
| 工具回傳不漲 | ✓ 回答與工具方向一致（模板逐字引用） |
| 缺必要資料 | ✓ 要求補充，不呼叫預測、不發明價格 |
| 來源過期/無資料市場（南屯） | ✓「無法提供」不給假結論 |
| Qwen 不可用/網路錯誤 | ✓ 降級規則回答，真模型結果仍顯示 |
| 機率/可信度字眼 | ✓ 不出現（未校準不輸出） |

- 端點整合：`POST /agent/query` 亂碼查詢→要求補充（實測 curl 2026-10-03）。

## 第三輪補強（2026-10-04，審查 F02/F03/F07；tests/agent/test_review_f02_f08.py）

- **輸出真值對照驗證器上線**：Qwen 文字經 `validate_qwen_answer()` 對照工具真值——誇大詞（必定/機率/已驗證/可信度）、未驗證百分比/日期/價格、方向衝突、空回覆全部拒絕並降級規則回答（審查重現的「7天後必定上漲99%，售價999元」實測被擋）。系統提示不再是唯一防線。
- **提示檔定位修復**：`src/configs/` 錯路徑改為專案根 `configs/agent_prompt.md`（641 字元實載）；缺檔時 Qwen 後端不上線（`strict` 載入），不默空提示。
- **併發**：`/agent/query` 經 `run_in_threadpool` 執行；模擬 0.5s 延遲後端下 health 未被阻塞（審查重現的阻塞情境修正）。
- **降級透明**：回應含 `backend_used`／`degraded`／`degraded_reason`／`forecast`（結構化真值）；規則結果不標 Qwen；前端顯示「Qwen 失敗→規則模式（原因）」。

## 第四輪補強（2026-10-04；R01–R08；tests/agent/test_review_round4.py＋test_providers.py＋test_hermes.py）

- **R01 短路**：缺輸入／工具錯誤不送任何 LLM（零請求實測）；驗證器不再對工具錯誤 return True。
- **R02 綁定**：期限×模式×單位（含中文期限詞、null content、公斤/台斤標示）；期限交換/跨模式/誇大詞全拒，正確回答不誤擋。
- **真 tool-calling 迴圈**（providers.py，19 項離線協議測試）：白名單 2 工具、參數鍵白名單、共用語意驗證、role:"tool" 回送、max_turns/max_tool_calls、provider 失敗保留真值不切雲端。
- **Hermes 0.19.0 整合**（5 項離線測試）：官方 registry 註冊、enabled_toolsets 白名單（31 內建→2）、HERMES_HOME 隔離與環境 scrub、輸出同過真值驗證器。
- R04 保存防偽：request_id 綁定伺服器暫存真推論（偽造/simulated/壞結構全拒）。

## 待 SERVER 補測（HOLD 項）

1. 真 Qwen 載入後：中文品項理解變體（口語/錯字）、工具參數正確率、回答延遲與顯存（T25 基準）。
2. 惡意指示（prompt injection）對 Qwen 解釋層的實測（規則層已不受影響：提取不經 LLM）。
3. API 超時情境（本機同步引擎 <1s；SERVER 加 Qwen 後量測）。

## 輸出

- 本機層案例結果彙整：`outputs/agent_evaluation/local_results.json`（由測試套件產生）。
