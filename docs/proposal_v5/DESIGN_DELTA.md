# DESIGN_DELTA：proposal_v5 與根目錄 design.md 的差異對照

**2026-10-09 升格狀態更新：** v5 r3 已通過 ChatGPT/COS 第三輪獨立複審；根目錄 design.md 現已在 §6 接入 v5 CURRENT／PARTIAL／PROPOSED 導覽與安全約束的摘要。本文件下列「待同步」表為 v5 r3 撰寫時的原始差異清單，其他完整流程／虛擬碼仍由 AGENT_DESIGN.md 維護，未整段複製進設計檔；不得把它解讀成所有 Proposed 功能已實作。


版本：2026-10-08。目的：說明 [AGENT_DESIGN.md](AGENT_DESIGN.md)／[PROPOSAL.md](PROPOSAL.md) 與正式 `design.md`（D44-R05 修訂版，2026-10-04）之間——哪些內容已存在可沿用、哪些是 v5 新增、哪些需要在審查通過後同步、哪些只屬未來設計。**本輪不覆寫正式 `design.md`。**

## 1. 已存在於 design.md、v5 直接沿用（不改寫）

| 內容 | design.md 位置 | v5 對應 |
| --- | --- | --- |
| 使用情境與 A/B 輸入輸出 | §0（PA–PE） | PROPOSAL §4.2–4.3 |
| 五群組架構①–⑤＋端點＋語意箭頭＋「數字是索引非順序」 | §1（圖一＋對照解說） | AGENT_DESIGN §3（同編號重繪，新增虛線未來區展開與工具白名單） |
| 一次 A/B 查詢資料流（教學例 32/28 元） | §2（圖二） | PROPOSAL §4.3 教學例 |
| 標籤公式／±5% 門檻／錨定不變向命題／單位換算 | §3（PF） | PROPOSAL §4.2、AGENT_DESIGN §5 |
| 時間切分與成熟清除（t+h+1、1,386 列、8/15 日帶） | §4（PH/PL） | PROPOSAL §4.2 |
| 風險、版本與未來範圍（up 召回低、模型包 v0.1.0、暫緩區） | §5 | PROPOSAL §5–6、AGENT_DESIGN §2/§10 |

**結論**：v5 的資料、公式、切分、架構骨架與正式設計**零衝突**；所有凍結數字（評估 SHA256、清除列數、split 日期）兩邊同源。

## 2. v5 新增（design.md 尚無，待審查通過後同步）

| 新增內容 | v5 位置 | 同步建議 |
| --- | --- | --- |
| **工具層 CURRENT／PROPOSED 對照**（實況：`AgentTools` 兩工具 `get_market_quote`／`post_forecast`＋`ToolCallLimiter`＋`/records` 保存 API；Proposed 抽象 `get_public_quote`／`call_forecast`／`save_record`，後者尚未工具化） | AGENT_DESIGN §4 | 審查通過後併入 design.md §6（工具契約與介面）或新增小節；同步時保留 CURRENT/PROPOSED 邊界，不得寫成三工具皆已實作 |
| **查詢流程圖**（D1–D9 十類決策分支，含降級與到期核對；節點標 CURRENT／PARTIAL／PROPOSED，屬 Proposed Agent Flowchart） | AGENT_DESIGN §7 | design.md 目前只有資料流圖（圖二），建議新增「圖四：查詢決策流程（Proposed）」 |
| **Algorithm 1 虛擬碼**（41 行逐行編號＋Pseudocode↔現有實作映射表＋邊界聲明） | AGENT_DESIGN §8 | design.md 無虛擬碼；建議以附錄形式加入並連結三者對照表（§9） |
| **安全約束 11 條**（含真值卡唯讀、禁止補值/編造、驗證器） | AGENT_DESIGN §6 | 與 docs/AGENT_RUNTIME_DIRECTION.md §3–5 部分重疊；建議統一為一份清單 |
| **三種表示一致性對照表**（架構↔流程↔虛擬碼） | AGENT_DESIGN §9 | 隨流程圖/虛擬碼一併入 design.md |
| **Deep Research 三問**（5 思維/3 爭論/10 問題） | DEEP_RESEARCH.md | 屬研究文件，不建議入 engineering design.md；放 docs/proposal_v5/ |
| **Article Summary Table 八欄** | ARTICLE_SUMMARY_TABLE.md | 屬研究文件；與 docs/RELATED_WORK_MATRIX.md 並存（後者欄位較寬，前者為教授指定格式） |

## 3. 只屬未來設計（兩份文件都以暫緩標示，不寫成已實作）

- LLM Planner／Tool-calling Agent（模型自行提出 tool_calls）——AGENT_DESIGN §2/§8 標「未來」；對應 design.md 暫緩未來區與 T26 未完成項。
- GLM API 後端（金鑰未配置）、Qwen3.8-27B 端點（SERVER 未部署）、Hermes 0.19.0 接線（離線驗證過、未接線）。
- SERVER_3090 部署與外網手機（T29/T32）、真店到期收集（T16）。

## 4. 措辭差異（不影響實質，同步時統一）

| 主題 | design.md 現況 | v5 用語 | 說明 |
| --- | --- | --- | --- |
| ② 群組名稱 | 「查詢處理（api/app.py）」 | 「Agent 查詢處理」 | v5 為對應教授 Domain Agent 要求凸顯 Agent 角色；程式位置相同（`api/app.py` 之 `/agent/query`） |
| ⑤ 群組說明 | 「預測紀錄」 | 同 | 一致 |
| 暫緩區 | 「┄ 暫緩未來區（虛線）」 | 同＋「LLM 非猜菜價」強調 | v5 在圖說與安全約束中重申 |

## 5. 同步時程（建議；本輪不執行）

1. ChatGPT 獨立複審 proposal_v5 → 修訂定案。
2. 定案後：將 §2 表列之新增內容併入 design.md（一次修訂、保留歷史附錄結構），並同步 `docs/AGENT_RUNTIME_DIRECTION.md` 的安全清單。
3. 產品 Agent 程式改造（T26 規則層→LLM Planner）在設計定案後才開始；本輪未動 `src/aiot_price/`。
