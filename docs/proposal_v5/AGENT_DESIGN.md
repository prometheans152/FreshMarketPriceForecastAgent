# TW01 Domain Price Agent 設計（Proposal v5）

版本：2026-10-08。本文件是**設計文件**：描述目標架構、流程與虛擬碼，並嚴格區分「已實作的規則式原型」與「未來要完成的 LLM Planner／Tool-calling Agent」。本輪**不修改** `src/aiot_price/` 產品程式；GLM API／Qwen3.8-27B／Hermes／SERVER_3090 整合依使用者 2026-10-04 指示暫緩。與根目錄 `design.md` 的同步計畫見 [DESIGN_DELTA.md](DESIGN_DELTA.md)。

**核心原則（一句話）**：Agent 自主選擇合適工具；ForecastEngine 專責菜價預測；程式強制驗證；Agent 根據真實工具結果解釋。

---

## 1. 為什麼需要 Domain Agent（教授要求之對應）

| 教授要求 | 本設計的對應 |
| --- | --- |
| 不是只有 ML Model | 預測引擎只是③號工具；Agent 負責理解需求、補資訊、選工具、組合解釋 |
| 不是 Chatbot | 對話以白名單工具的真實執行為前提；無工具結果不得作答 |
| 不是 LLM 包裝現成模型 | LLM 不產生任何價格數字／方向／日期；結構化真值由程式產生並驗證 |
| Domain Knowledge | 單位換算（台斤/公斤）、可比性五重檢查、±5% 門檻、市場均價 vs 店價分界、發布延遲處理，全部編碼為程式規則（§5） |
| Data Analytics | 工具輸出附資料截止日、樣本範圍與驗證狀態；保存預測供到期量化核對 |

> **現況註記**：上表為**目標（Proposed）**對應。現有規則原型以固定序列執行（不自主選工具）、保存經 Web 另呼 `/records`（非 Agent 工具）；逐項 CURRENT／PARTIAL／PROPOSED 對照見 §4 與 §8。

## 2. 三種角色與現況狀態

| 角色 | 職責 | 現況（2026-10-08，依實際程式核對） |
| --- | --- | --- |
| ForecastEngine（③） | 以封存模型（RF 7天/HGB 14天）計算 r̂、A 錨定、B 調整；維持資料與驗證邊界 | **已實作**（本機；模型包 v0.1.0；fixtures 3/3 重現） |
| Agent 執行層（②內） | 理解請求→檢查必要資訊→缺則追問→LLM 自主提出白名單工具呼叫→受控執行→接收結構化結果→組裝附證據的回答→失敗明示 | **Tool-calling 已實作（2026-10-09）**：`parse_query()` 可信解析＋TrustedContext＋LLM tool_calls 迴圈（direct/Hermes）＋**三個**工具（`get_market_quote`／`post_forecast`／`save_record`）＋`ToolCallLimiter`（單查詢計數上限 3 次）＋忠實性驗證器（**僅掛 Qwen 路徑**）＋模板回答（由工具事實逐字組文、不經驗證器）；`tests/` 227 項測試通過。**注意**：現況的工具呼叫為確定性固定序列，非模型自主選擇；自然語言理解為規則級，非 LLM |
| LLM 後端（暫緩未來區） | 自然語言理解／追問對話／依真值卡生成解釋文字；**不計算、不竄改、不補值** | **未接線**（GLM API 金鑰未配置；Qwen3.8-27B 待 SERVER；Hermes 0.19.0 離線介面驗證過、未接線；`RuleBackend` 模板回答已實作） |

**明確區分**：目前已實作的是**規則式原型**（②的確定性實作）；**未來要完成的 LLM Planner／Tool-calling Agent**（模型自行提出 tool_calls、伺服端驗證執行）屬暫緩未來區，本文件對其只做設計，不寫成已實作成功。兩者共用同一驗證器防線。

## 3. System Architecture（系統架構圖；主要群組①–⑤）

```text
┌─① 使用者與手機介面（web/）────────────────────┐
│  表單入口（品項/今天價/單位/日期；選填上週同店價） │
│  自然語言入口（文字查詢）                          │
└──────┬──────────────────────▲─────────────┘
       │提交查詢 NL/Form          │回傳：7/14 天方向＋點估計＋
       │（結構化請求）            │期限（從今天算）＋資料截止日＋
       │                         │來源與驗證狀態標示
┌─② Agent 查詢處理（api/app.py）▼─────────────────┴──┐
│  端點：POST /forecast（表單） POST /agent/query（NL）  │
│  職責：必要資訊檢查（缺→追問）／單位與可比性驗證／       │
│        依白名單選工具＋參數契約／組裝回答／失敗明示      │
│  （現況：規則式解析；未來：LLM Planner 提出工具呼叫，    │
│   伺服端驗證器把關——虛線區）                            │
└──┬───────────▲───────────────┬──────────────────┘
   │呼叫預測     │回傳 r̂/A/B      │保存當次預測（僅使用者選擇）
┌─▼───────────┴─┐      ┌────▼──────────────────┐
│③ 菜價計算        │      │⑤ 預測紀錄（private/predictions/）│
│ ForecastEngine  │      │ JSON 凍結（請求＋回應）；         │
│ 封存模型推論      │      │ 查閱/匯出/刪除（/records）；      │
│ （RF 7天/HGB14天）│      │ 與④完全分離之獨立私人儲存          │
│ ＋A 錨定/B 調整   │      └────▲──────────────────┘
└──┬──────────────┘           │讀取（查閱/到期核對經②回①）
   │唯讀載入公開歷史
┌──▼──────────────────────────────────────────┐
│④ 公開行情資料（public_history 凍結快照；唯讀；不放私人紀錄）│
└──────────────────────────────────────────────┘
┄┄┄┄┄┄ 暫緩未來區（虛線；未部署、未驗收）┄┄┄┄┄┄
┆ ▸ LLM 後端：GLM API（金鑰未配置）／Qwen3.8-27B 端點（SERVER 未部署）／Hermes 0.19.0 框架（未接線）
┆ ▸ 角色＝理解與解釋（②內的語言層），不是用 LLM 猜菜價（菜價一律由③計算）
┆ ▸ SERVER_3090 部署與外網手機展示（T32）
┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄
```

**正文對照解說（與投影片同編號）**：①接收使用者表單或自然語言查詢，交給②；②檢查必要資訊（品項、今天價、單位、日期；自然語言缺項則追問），驗證單位與上週價可比性，通過後以參數契約呼叫③；③唯讀載入④的公開歷史，以封存模型計算 r̂_7/r̂_14 並做 A（現價錨定）與 B（有可比上週價時的差動量調整），結構化結果回到②；②組裝附期限／資料截止日／來源／驗證狀態的回答回①。只有使用者選擇保存時，②才把當次請求＋回應凍結寫入⑤（與④完全分離的私人儲存）；日後查閱與 7/14 天到期核對亦經②回①。**虛線區**為暫緩未來：LLM 後端只進入②的語言層，不改③④⑤的計算與資料邊界。**箭頭語意**：①→②提交；②→③計算請求；③→④唯讀載入；③→②結果回傳；②→①回答；②→⑤保存（僅自願）／⑤→②查閱。④與⑤之間無直接連線。

**線型圖例**：實線＝現況已實作之資料流；虛線（┄）＝暫緩未來、未部署未驗收。**數字①–⑤為功能群組索引，不是執行順序。**

## 4. 工具層：CURRENT 實況與 PROPOSED 抽象介面

### 4.1 CURRENT——目前實際已實作（依程式核對）

| 實際元件 | 位置 | 行為 | 失敗行為 |
| --- | --- | --- | --- |
| `AgentTools.get_market_quote(crop_id, market_id)` | `src/aiot_price/agent/tools.py` | 最新公開行情（回傳 `ok/market_id/crop_id/price/unit/observed_date`；**無年齡欄**——tools.py 之 docstring「年齡」為過時殘留）；非預測 | 查無→明確 `ok:False`＋原因；不以 LLM 補值 |
| `AgentTools.post_forecast(request)` | 同上 | 與 `POST /forecast` 完全同源的預測（重用 ForecastEngine） | 422（參數無效）／資料不足（`stale_data_unusable`）→ 明確錯誤 |
| `ToolCallLimiter` | 同上 | 單一查詢工具呼叫**計數**上限 3 次（`check()` 只計次，超限拒絕）。**逾時**：`TOOL_TIMEOUT_SECONDS=10` 僅為常數、未接線於任何工具路徑（現有唯一 timeout 是 QwenBackend 的 LLM HTTP 請求）——工具路徑的統一逾時強制屬 **PROPOSED** | 超限→拒絕再呼叫 |
| `POST /records`（伺服器端凍結保存） | `src/aiot_price/api/app.py` | 只收 `request_id`、伺服器端凍結當時請求＋回應（不信任客戶端結果）；另有 `GET /records`、`GET /records/export`、`DELETE /records/{id}` | 拒絕寫入時明示 |
| 忠實性驗證器 `validate_qwen_answer` | `src/aiot_price/agent/service.py` | 對照工具真值攔截誇大詞／未驗證數字日期價格／方向衝突（**目前僅掛 Qwen 路徑**：service.py:400；RuleBackend 模板不經驗證器） | 不通過→降級 `RuleBackend` 模板回答 |
| 規則解析 `parse_query()` | `src/aiot_price/agent/tools.py` | 子句級綁定價格/單位/日期/店家線索；缺必要欄位→`missing` 要求補充 | 不猜測、不以預設代填 |

工具呼叫現況為**確定性固定序列**（`handle_agent_query`：解析→`get_market_quote`→`post_forecast`→模板/驗證回答），不是模型自主選擇。

### 4.2 PROPOSED——Proposal 目標 Agent 的統一工具介面（抽象名稱）

下表是 **Proposed Domain Agent 的統一工具抽象介面**；**尚未全部封裝成目前 `AgentTools` 的實際工具**，不得宣稱三者皆已實作：

| Proposed 抽象工具 | 對應目前實作 | 狀態 |
| --- | --- | --- |
| `get_public_quote` | `AgentTools.get_market_quote()` | CURRENT equivalent（名稱為 Proposed 抽象） |
| `call_forecast` | `AgentTools.post_forecast()`（與 `POST /forecast` 同源） | CURRENT equivalent（名稱為 Proposed 抽象） |
| `save_record` | AgentTool（providers/hermes 同一確認門）＋`POST /records` 共用 `_save_record_by_request_id` | **CURRENT（2026-10-09 第二階段）**：已工具化；執行需客戶端 `save_confirmation`（id 由伺服器生成註冊，LLM 換 id 即拒）；Web 保存鈕仍走 `/records`（同核心） |

參數契約（Proposed 版，沿用 `contracts/forecast.schema.json` 語意）：`get_public_quote`（crop_id、market_id 可選、date）；`call_forecast`（ForecastRequest：crop_id、current_price、price_unit、observed_at、選填 previous_price/previous_observed_at、mode）；`save_record`（request_id、使用者確認）。呼叫上限沿用單查詢 3 次；工具名、端點與參數皆白名單，無任意 shell／任意 URL／模型修改權限。

## 5. 領域知識規則（程式化；非 LLM 判斷）

1. **單位**：元/台斤原生；元/公斤×0.6 換算並保留原值；顆/把/袋無重量→拒絕並說明。
2. **可比性（B 五重檢查）**：同店＋同品項＋同規格＋單位換算後可比＋上週日期 7±2 天；任一失敗→回 A 並說明原因。
3. **代填禁令**：不以 0、公開 t−7 或市場均價冒充私人店價。
4. **期限**：t+7/t+14 精確日曆日，t＝使用者今天；不因行情截止日較舊改起點。
5. **門檻**：|r|≤5% flat（含邊界）；sign(r̂)<0 不等於 down。
6. **標示**：輸出必附 target_scope（market_mean／store_price_estimate）與 validation_scope（public_market_test／unvalidated）。
7. **成熟度**：公開標籤 m(t+h)/m(t)−1；同店真值另收，缺到期真值＝無法核對（不是「未漲」）。

## 6. 安全約束（11 條；對應使用者任務書）

1. 沒有 ForecastEngine 的成功結果，Agent 不得自行產生預測數字。
2. A/B 計算一律由程式執行（§5 規則）。
3. AI 不得竄改結構化價格、漲跌方向、日期、來源（真值卡唯讀）。
4. 網站顯示的預測數字直接來自驗證後的工具輸出。
5. AI 只能根據可信結果提供文字說明。
6. 工具失敗時明確告知，不得用 LLM 猜測補值。
7. 單位、日期、品項、店家和規格必須驗證（§4 參數契約＋§5 規則）。
8. 禁止 Agent 編造價格變動原因、準確率、信心機率或採購利益。
9. 工具選擇受白名單及參數契約限制（§4；單查詢≤3 次呼叫）。
10. 驗證器（離線已測）攔截誇大詞、未驗證數字/日期/價格、方向衝突之輸出。
11. 暫緩區（LLM 後端）啟用前須重驗忠實性案例集；金鑰只存環境變數，不入提示詞/日誌/Git。

## 7. Flowchart（Proposed Agent 查詢流程圖；含實際決策分支）

> **圖例聲明**：本流程圖描述**目標系統（Proposed Domain Agent）**。節點標注 CURRENT／PARTIAL／PROPOSED 標示現況；**不能用「除了 LLM 之外全部完成」概括**——底層 API／函式存在，不代表整個 Agent orchestration 已實作。

```text
[開始] 使用者輸入（NL 或表單）
  │
  ▼
[D1 忺必要資訊？] 品項＋今天價＋單位＋日期                ← CURRENT（parse_query missing 機制：品項/價格/單位缺→追問；**日期未提供→以系統 today 預填**（`observed_date or self.today`）；僅「明示但無法解析」的日期才追問）
  │否──▶ 追問缺失欄位 ──▶ 回到 D1（上限後禮貌終止）        ← CURRENT
  │是
  ▼
[D2 單位可換算？]（元/台斤✓；元/公斤→×0.6 換算保留原值）   ← CURRENT（解析層單位綁定＋per_piece 拒絕）
  │否（顆/把/袋等無重量）
  │      └─▶ 拒絕並說明（引導改輸入可換算單位）──▶ [結束-失敗] ← CURRENT
  │是
  ▼
[D3 填上週價？]──否────────────────┐                     ← CURRENT
  │是                              │
  ▼                                │
[D4 同店價可比？] 五重檢查           │                     ← CURRENT（解析層即拒 B：換店/換規格/跨品項/壞日期）
 （同店/品項/規格/單位/7±2天）        │
  │否──▶ 降級：僅 A ＋說明不可比原因  │                     ← CURRENT（b_reject_reason）
  │是                              │
  ▼                                ▼
[D5 公開資料足夠且未過期？] ◀────────┘                    ← **PARTIAL**：引擎現況＝落後>3日**僅加警告**（predict.py 218–224）；該品項/市場無可用特徵才回 `stale_data_unusable`（231–249）。嚴格「過期即拒」hard gate＝**PROPOSED**
  │否/過期──▶ 明確「資料不足」＋資料截止日──▶ [結束-失敗]（現況僅於無可用特徵時走此路；過期>3日為警告標註，非 hard-fail）
  │是
  ▼
[T1] 呼叫 call_forecast（白名單工具）                      ← CURRENT（AgentTools.post_forecast；抽象名稱屬 Proposed）
  │
[D6 工具成功？]                                            ← CURRENT（受控錯誤碼）
  │否（422/503/逾時）──▶ 明確錯誤碼＋「本次無法預測」（不用 LLM 補值）──▶ [結束-失敗]
  │是（結構化 r̂/A/B 真值卡）                                 ← CURRENT（_collect_facts 真值收集）
  ▼
[D7 證據與限制檢查]（驗證器）                                ← **CURRENT（LLM 路徑全面）**：`validate_qwen_answer` 掛於三條 LLM 路徑（QwenBackend、direct 迴圈、Hermes）；RuleBackend 模板仍由工具事實逐字組文不經驗證器（已證設計）；第二階段增 quote-only／save-only 分支與百分之/塊/CJK 數字樣式
  檢查：方向/數字/日期與真值卡一致？無誇大詞？B 有「實驗性」標示？
  │不通過──▶ 擋下該句／改寫為忠實版本（降級 RuleBackend）      ← CURRENT
  │通過
  ▼
[R1] 組裝回答：方向＋估計＋期限（從今天算）＋資料截止日＋來源＋限制   ← CURRENT（RuleBackend 模板）；LLM 生成版＝PROPOSED
  │
  ▼
[D8 使用者選擇保存？]──否──▶ [結束-完成]                     ← PARTIAL（保存 API 有；由 Web 另呼 /records，非 Agent 流內決策）
  │是
  ▼
[T2] save_record：凍結當次請求＋回應（A/B 並存）              ← PARTIAL（POST /records 已實作；save_record AgentTool 未封裝）
  │
  ▼
[D9 到期（t+7/t+14）可取得同店真價？]                         ← PARTIAL（機制/匯出有；T16 真值未收集）
  │否（缺貨/換規格/未訪價）──▶ 記錄「無法核對」，不作「未漲」推論
  │是
  ▼
[T3] 到期核對：A/B vs 同店實價（增益配對比較）──▶ [結束]       ← PARTIAL／PROPOSED（配對比較 orchestration 屬後續工作）
```

**分支覆蓋對照**：D1 缺必要資料／D2 錯誤單位／D4 同店價不可比／D5 公開資料不足或過期／D6 模型工具呼叫失敗／D3 有無上週價→A 或 A+B／D7 回答證據與限制檢查／D8 是否保存／D9 到期可否取得真店價。**LLM Planner（PROPOSED）**只替換「NL→結構化請求」與「真值卡→自然語言回答」兩個語言環節；D2、D4–D7 的程式驗證與降級路徑不變。**Agent 自主工具選擇**屬 PROPOSED——現況為固定序列（§4.1）。

## 8. Algorithm 1: TW01 Domain Price Agent（Proposed 虛擬碼）

```text
Algorithm 1  TW01 Domain Price Agent
Input  : 使用者訊息 M（自然語言或表單）；今日日期 t；白名單工具 W＝{get_public_quote, call_forecast, save_record}
Output : 回答 R（方向＋估計＋期限＋來源＋驗證狀態）；或追問 Q；或受控錯誤 E；（自願時）凍結紀錄 P

01  procedure TW01_AGENT(M, t, W)
02    S ← PARSE_REQUEST(M)                    // ② 現況：規則式解析（未來：LLM Planner，仍經 schema 驗證）
03    if S 缺 品項∨今天價∨單位∨日期 then
04        return Q ← 追問缺失欄位              // 分支 D1；不猜測、不用預設值代填
05    end if
06    u ← NORMALIZE_UNIT(S.單位)               // 領域規則 1
07    if u 不可換算（顆/把/袋 無重量） then
08        return E ← 「單位不可換算，請改以 元/台斤 或 元/公斤 輸入」   // 分支 D2
09    end if
10    comparable ← CHECK_COMPARABILITY(S.上週價)   // 領域規則 2（五重檢查）
11    if S.上週價 存在 ∧ ¬comparable then
12        mode ← "A"；警示 ← 「上週價不可比（原因），本次僅 A」    // 分支 D4：降級不中斷
13    else if S.上週價 存在 then
14        mode ← "both"                          // 分支 D3：A/B 並列
15    else
16        mode ← "A"                             // 無上週價：仍可預測
17    end if
18    if ¬DATA_FRESH() then                      // ④ 檢查：公開歷史涵蓋且未過期
19        return E ← 「資料不足/過期（截止日＝…），本次無法預測」     // 分支 D5；不用 LLM 補值
20    end if
21    F ← CALL_TOOL(call_forecast, S, mode)      // ③ ForecastEngine：唯一計算者（LLM 不計算）
22    if F 失敗 then
23        return E ← 錯誤碼＋「本次無法預測」      // 分支 D6
24    end if
25    // F 內部（③）：唯讀載入④→模型 r̂_7/r̂_14→A＝p(1+r̂)→（mode="both"）B＝r_A+0.3×(Δ店−Δ公)
26    card ← TRUE_VALUE_CARD(F)                  // 結構化真值卡：數字/方向/日期/來源 唯讀
27    draft ← COMPOSE(card)                      // ② 現況：模板；未來：LLM 依 card 生成文字
28    if ¬VALIDATE(draft, card) then
29        draft ← REWRITE_FAITHFUL(card)         // 分支 D7：擋下誇大/未驗證數字/方向衝突
30    end if
31    R ← draft ＋ 期限(t+7,t+14) ＋ 資料截止日 ＋ target_scope ＋ validation_scope ＋ 限制標示
32    if 使用者自願保存 then
33        P ← CALL_TOOL(save_record, S, F)       // ⑤ 凍結請求＋回應；A/B 並存（分支 D8）
34    end if
35    return R（,P）
36  end procedure

37  procedure EXPIRE_CHECK(P, t+7/t+14)          // 到期核對（分支 D9；已實作資料面，T16 待真店資料）
38    g ← 取同店同品項同規格到期實價
39    if g 缺（缺貨/換規格/未訪價） then return 「無法核對」（≠未漲）
40    return 配對比較 A/B vs g（方向一致率、誤差）   // 增益＝同案例 A、B 之差
41  end procedure
```

**虛擬碼邊界聲明（2026-10-09 第二階段後）**：Algorithm 1 的工具呼叫迴圈、白名單（含別名）、TrustedContext 驗證、save_record 工具化與軌跡已於本機實作（mock-LLM 證據）；**真 LLM Provider（GLM/Qwen）行為驗證仍屬 PROPOSED/HOLD**——mock 通過證明調度契約，不證明模型行為。

**Pseudocode ↔ 現有實作對照**（依 2026-10-08 實際核對程式填寫）：

| Pseudocode（行號） | Current implementation | Status |
| --- | --- | --- |
| `PARSE_REQUEST`（02） | `parse_query()`（src/aiot_price/agent/tools.py；子句級綁定、missing 追問） | CURRENT（LLM Planner 版＝PROPOSED） |
| `get_public_quote`（即 `get_market_quote` 語意） | `AgentTools.get_market_quote()` | CURRENT equivalent（名稱為 Proposed 抽象） |
| `call_forecast`（11、21） | `AgentTools.post_forecast()`（與 `POST /forecast` 同源重用 ForecastEngine） | CURRENT equivalent（名稱為 Proposed 抽象） |
| `DATA_FRESH()`（18–19） | ForecastEngine：落後>3日僅加警告（predict.py 218–224）；該品項/市場無可用特徵才 `stale_data_unusable`（231–249） | **PARTIAL**：警告＋無特徵才拒為 CURRENT；嚴格「過期即拒」hard gate＝**PROPOSED** |
| 真值卡 `TRUE_VALUE_CARD`／`VALIDATE`（26、28–29） | `_collect_facts`（事實收集，CURRENT）；`validate_qwen_answer` **僅掛 Qwen 路徑**（service.py:400），RuleBackend 模板由工具事實逐字組文、不經驗證器 | CURRENT（事實收集＋Qwen路徑驗證器）；**跨後端統一驗證＝PROPOSED** |
| 模板回答 `COMPOSE`（27） | `RuleBackend.reply()`（模板、只引用工具結果數字） | CURRENT（LLM 生成版＝PROPOSED） |
| `save_record`（32–34） | `POST /records`（api/app.py；伺服器端凍結）＋prediction records 儲存／匯出 | **PARTIAL**：API 已存在；**未封裝為 AgentTool**，目前由 Web 前端另呼，不在 Agent 工具序列內 |
| `EXPIRE_CHECK`（37–41） | 保存紀錄（凍結＋匯出）機制已實作；**T16 真店到期值未收集**；配對比較 orchestration 未建 | PARTIAL |
| LLM Planner（02 之未來版） | 尚未接線（GLM/Qwen/Hermes 依使用者指示暫緩） | PROPOSED |
| LLM 解釋（27 之未來版） | 尚未接線；現以 `RuleBackend` 模板＋驗證器降級防線 | PROPOSED |
| Agent 自主工具選擇（工具排序策略） | 現況為 `handle_agent_query` 固定序列（quote→forecast→回答） | PROPOSED |

另註：第 25 行 B 之 α=0.3 為固定實驗規則（未訓練）；「單查詢≤3 次工具呼叫」由 `ToolCallLimiter` 實作（CURRENT）。

## 9. 三種表示的一致性對照

| 架構群組 | 流程圖節點 | 虛擬碼行 | 現況 |
| --- | --- | --- | --- |
| ① 使用者與介面 | 開始／R1 回答 | 01（輸入 M）、31（輸出 R） | CURRENT（web 原型） |
| ② Agent 查詢處理 | D1–D8、D7 驗證 | 02–17、27–31 | CURRENT（規則式：parse_query＋固定序列＋模板；驗證器僅 Qwen 路徑，D5/D7 見 §7 標注）；LLM 語言環節與自主選工具＝PROPOSED |
| ③ ForecastEngine | T1、D6 | 21–25 | CURRENT |
| ④ 公開歷史（唯讀） | D5 | 18–19、25（內部載入） | CURRENT（群組與唯讀載入；D5 之嚴格過期 hard gate＝PARTIAL，見 §7） |
| ⑤ 預測紀錄 | D8/T2、D9/T3 | 32–34、37–41 | PARTIAL（/records 保存與匯出 API 已實作；save_record AgentTool 未封裝；到期真值 T16 未收集） |
| 暫緩未來區（LLM 後端） | D1 之 NL 環節、D7 之文字環節 | 02、27（標註「未來」） | PROPOSED（未接線） |

## 10. 技術可行性

- **已驗證（CURRENT）**：工具契約版本化（contracts/forecast.schema.json）；規則原型以**固定序列**（`get_market_quote`→`post_forecast`→模板/驗證回答）本機跑通「理解→驗證→計算→驗證→回答」（`/agent/query` 實測截圖 outputs/e2e/）；忠實性驗證器函式經離線測試（誇大詞/未驗證數字/方向衝突攔截）——**目前僅掛於 Qwen 路徑**（service.py:400），規則模板不經驗證器；`ToolCallLimiter` 計數上限 3；`tests/` 227 項自動化測試通過（另含 Hermes 0.19.0 介面離線驗證——未接線）。
- **PARTIAL／PROPOSED（如實標示）**：保存流程——`POST /records`（伺服器端凍結）與匯出已實作，但由 Web 前端另行呼叫，**尚未封裝為 AgentTool、未納入 Agent 工具序列**；到期核對——凍結/匯出機制有、真店到期值未收集（T16）、配對比較 orchestration 未建；LLM Planner／自主工具選擇——未接線（暫緩）。
- **風險與對策**：(i) LLM 忠實性→上線前重跑固定中文案例集（工具參數正確率、真值對照、降級）；(ii) GLM/Qwen 切換→provider/model/base_url 集中配置，回應記錄實際後端與降級原因；(iii) 雲端隱私→只送必要查詢欄位，不送專案/逐字稿/店家個資；(iv) 工具失敗→一律明示，直接模型結果仍可用（模型失敗才整體不可用）。
- **不可行項（如實標示）**：以 LLM 直接產生價格（違反核心原則）；無真店資料下宣稱 B 增益；本輪接線任何暫緩整合。
