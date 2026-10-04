# TW01 研究提案、設計、OpenSpec 與正式投影片：本輪驗收（P1–P6）

日期：2026-10-04（Asia/Taipei）。依據 [PROPOSAL_DELIVERY_PLAN.md](PROPOSAL_DELIVERY_PLAN.md) 的六工作包驗收。
證據目錄：`outputs/proposal_delivery/run1_20261004/`。

> **2026-10-04 修訂輪公告**：本檔下方的 D44 首輪「六包全部通過」結論已被獨立審查（`outputs/audits/d44_independent_6eb4adf/REVIEW_6eb4adf.md`）要求修訂——新聞日期、前作措辭、數字口徑、主稿敘事、設計圖與講稿同步等六項（R01–R06）當時未達標。同日 GLM 已完成 D44-R01–R06 修訂並自驗，**修訂內容與證據見 [D44_REVISION_REPORT.md](D44_REVISION_REPORT.md)**（v2 成品：`slides/TW01_菜價預測_研究提案與初步成果_v2.pptx`＋PDF；證據 `outputs/proposal_delivery/run2_20261004_01/`）。本檔首輪記錄保留為歷史；**最新驗收狀態以修訂報告＋ChatGPT 後續獨立複審為準**，GLM 自驗不等於複審通過。

**總結（D44 首輪自驗，歷史記錄）：P1–P6 六包全部通過。** 本輪交付的是研究文稿、設計藍圖、規格管理與正式簡報；真店 A/B、代理人後端整合、SERVER 部署、影片與外網展示維持各自原有狀態（T16/T23–T32/T35–T36 不因此輪 PASS）。

| 包 | 交付物 | 判定 | 關鍵證據 |
|---|---|---|---|
| P1 | [RESEARCH_MOTIVATION.md](RESEARCH_MOTIVATION.md) | **通過** | 問題證據表＋5 項可查證據（E1a/E1b/E2/E3a/E3b，各有來源與日期）；RQ1–RQ3；100–180 字投影片版摘要；無「一定省錢／所有菜店適用」用語 |
| P2 | [RELATED_WORK_MATRIX.md](RELATED_WORK_MATRIX.md)＋[RESEARCH_GAP.md](RESEARCH_GAP.md)＋[REFERENCES.md](REFERENCES.md) | **通過（附讀取層級限制）** | 10 件關鍵作品（5 件 2021–2026）固定欄位矩陣；UNKNOWN 12 處如實標記；[R01–R10] 統一編號；Related Work 正文過半直接談菜價；三組缺口按「已做到→不足→另測→公平驗證」撰寫；未重現前作協議故不跨資料比分數 |
| P3 | [CONTRIBUTIONS.md](CONTRIBUTIONS.md)＋[PROPOSAL_REPORT.md](PROPOSAL_REPORT.md) | **通過** | C1（已驗證）／C2（待驗證）／C3（初步）各有問題、最近前作、方法、證據與缺失；A–Z 結構完整（A–F 摘要、G–L 導論、M–O 文獻、P＝PA–PM、Q–V 實驗、W–Z 結論）；不變價與動量基線並列、負向結果保留、無「顯著／全球首次／B 更準」用語 |
| P4 | 根目錄 [design.md](../design.md) | **通過** | 現況藍圖置頂（§0–§5）＋歷史附錄保留；架構／A-B 資料流／時間切分三圖文字版，未部署項虛線標記；r_h、A 錨定、B 規則公式附符號來源與數字例；錨定不變向命題含適用條件；C/RQ→證據對照表；0.3 來源與未訓練狀態明示 |
| P5 | `openspec/`＋[OPENSPEC_WORKFLOW.md](OPENSPEC_WORKFLOW.md) | **通過** | 官方 CLI 1.14.0 局部安裝（`tools/openspec/`，node_modules 不入 Git）；init（--tools none --language zh-TW）；change `prepare-tw01-proposal-package` 4/4 artifacts；11/11 tasks 勾選；`validate --strict --no-interactive` exit 0（P6 後複驗亦通過）；命令輸出存 `openspec_cli_evidence.txt` |
| P6 | `slides/TW01_菜價預測_研究提案與初步成果_v1.pptx`＋同名 `.pdf`＋[SLIDE_NOTES.md](SLIDE_NOTES.md) | **通過** | 可編輯 PPTX 19 頁＝PDF 19 頁（render_meta.json）；逐頁 PNG 渲染＋獨立視覺驗收兩輪：rev1 13/19 通過→修正 6 頁→rev2 **19/19 PASS**（render_review.md）；講者備忘錄嵌入 PPT 且對應 SLIDE_NOTES.md（主講約 11 分 15 秒＋10 分鐘快版路徑）；6 張圖表全由凍結 JSON 實算生成並標來源；負向結果留在主講頁 12；介面頁標示原型狀態與拍攝日期 |

## 主張-證據追溯

`claims_evidence.csv` 15 列主張全部回填文稿段落（PROPOSAL_REPORT A–Z 對應節）與投影片頁碼；凍結評估 `public_test_results.json` SHA256 重算為 `2d28acd2f2c3e5ce566b9095c6a85477db8faf858d9ce29e974caaedc25674b8`，與宣稱一致。

## 保護檔核對（本輪結束時）

六個保護檔 SHA256 與 `protected_before.json` 基準完全一致：eval_json、eval_csv、manifest、train_json、split_csv、逐字稿。模型未重訓、參數未調、fixtures 未重生成、`src/`、`tests/`、`web/`、`contracts/`、正式 configs 無修改（`git status` 可覆核）。

## 誠實邊界（與 PASS 並存，非本輪缺陷）

- B（上週價）增益零證據：α=0.3 是開發期固定規則，真店到期驗證 T16 未開始。
- 模型 macro-F1 未勝動量、點 MAE 未勝不變價、up 召回 ≈10%：以負向結果形式呈現於報告 Q–V 與主講頁 12。
- 代理人後端（GLM API／Qwen3.8-27B／SERVER）依 D44 暫緩，介面以規則模式展示；不宣稱已通過課程全部要求。
- 文獻矩陣部分作品僅摘要層級閱讀（12 處 UNKNOWN），主張範圍已對應縮小。
- 簡報未錄影、未發布、未推送遠端。

## 剩餘待填（不阻塞本輪交付）

- 封面組員名單（≤4 人）與正式發表日期。
- 下一步時間表的具體日期（真店收集啟動、SERVER 部署、期末驗收）。

## 後續入口

- 全案狀態：[TASKS.md](../TASKS.md)；進度：[GLM_PROGRESS.md](GLM_PROGRESS.md)；交付清單：[DELIVERY_CHECKLIST.md](DELIVERY_CHECKLIST.md)。
- 簡報重建：`slides/source/make_assets.py → make_pptx.py → export_and_render.py`（依賴：python-pptx、matplotlib、PowerPoint COM）。
