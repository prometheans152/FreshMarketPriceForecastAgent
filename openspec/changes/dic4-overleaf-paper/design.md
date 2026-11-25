# DIC4 設計決策

## Context
使用原專案已確認的 FMPA 範圍。教師白板只有簡短條目，因此投稿期刊、最終格式、截止時間未被本地照片證實，不以此虛構格式要求。目標是通用 academic article LaTeX，pdfLaTeX 可編譯。

## Decisions
1. **版本隔離**：v1 在本輪建立作比較，不冒充歷史 Overleaf 修訂；v2 以完整小論文型式呈現，兩者各有 `main.tex` 和 `references.bib`。
2. **數值與實驗誠實**：唯讀取 `docs/midterm/public_test_results.json`；RF/HGB 均不勝同母體指定基線；不重新訓練。
3. **工具邊界**：Agent 只解釋事實；正式 MCP 兩工具為市場查價與匿名 A 預測；B 僅 Web，無 LLM 自動造價。
4. **Overleaf**：當使用者完成登入後，採官方 Upload Project ZIP 流程，編譯後檢查 PDF。LaTeX 套件採平台常見預裝套件，不從陌生 MCP 服務讀取帳密。
5. **OpenSpec / GitHub**：OpenSpec change 保留在本機 repo，CLI strict validate。若 Git main 有舊的 dirty changes，Git 操作精確 staging；不覆蓋既有工作階段。

## Traceability
| 原始證據 | 稿件 | 檢查 |
| --- | --- | --- |
| DIC4 白板 429406.jpg | 雙版本＋工作流 | 檔名、章節、修訂矩陣 |
| `docs/dic3/DIC3_PROPOSAL_REFACTOR.md` | Abstract, Intro, Related Work, A/B | 來源／證據層級 |
| `docs/midterm/public_test_results.json` | Table 1: test n, F1, MAE, up recall | 本機程式精確值比對 |
| `design.md` | 系統工具、規格、限制 | 不超稱實際實作 |
| Overleaf 專案與重編 PDF | 交付 | 真正編譯驗證（帳號登入後） |

## Risks
姓名羅馬拼音、個別文獻英譯題與正式投稿期刊仍待人工書目校對。使用本輪白板照片推論無法證明教授指定某期刊、頁數或格式。 Overleaf 雲端匯入成功不代表論文已正式投稿。
