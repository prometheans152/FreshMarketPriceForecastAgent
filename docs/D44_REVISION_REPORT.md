# D44-R01–R06 研究內容與交付修訂報告

日期：2026-10-04（Asia/Taipei）。執行者：GLM（coding agent，自驗）。
依據：`outputs/audits/d44_independent_6eb4adf/REVIEW_6eb4adf.md`＋`outputs/audits/d44_resume_6eb4adf_20261004_01/REVIEW_SUPPLEMENT.md`＋`docs/GLM_D44_R01_R06_REVISION_20261004.md`（與使用者最新提示詞範圍不一致時以使用者提示詞為準）。
基準 HEAD：`6eb4adf`；證據目錄：`outputs/proposal_delivery/run2_20261004_01/`；v1／run1／舊審查全部保留未覆寫。

**總結：R01–R06 六項修訂全部完成並通過 GLM 自驗（含 15/15 製作工具測試與 v2 全 19 頁逐頁視覺驗收）；本報告為執行者自驗紀錄，交 ChatGPT 獨立複審，複審結論以前者為準之前不得視為最終驗收。**

---

## R01｜研究動機：來源與證據範圍校正

**原問題**：公視報導誤標 2026-09-14；農業部 219 期作者/年份/範圍未交代；未核實 RSS 新聞被用於情境；「13–19% 機率」把描述統計當預測機率；45→85 未核對且隱含天氣歸因。

**實際改檔**：`docs/RESEARCH_MOTIVATION.md`（E2/E3a/E3b/§3.1/§3.5/來源表 S4-S6/§6 邊界）、`docs/PROPOSAL_REPORT.md` G 節、v2 投影片 p2＋notes。

**來源/驗證證據**（`run2_20261004_01/r01_source_cards_v2.json`）：
- 公視官網 `https://news.pts.org.tw/article/765375` 實讀：**2025-08-13、楊柳颱風**，「一把蔥380元」在文中；YouTube `_AMNwXkOsEg` 標題含 20250813 判定同則。→ 修正日期並標「早於本案資料期間（2025-10-04 起），僅歷史背景」。
- 農業部 `https://www.moa.gov.tw/ws.php?id=22086` 實讀：作者**王鎬杰**（原稿「王鎰杰」誤）、2010 年 9 月出刊、分析 **2004–2009（民國93–98）批發市場週均價**；文稿加適用範圍（非本案期間地區之因果證明）。
- 自由 2026-07-11／UDN 2026-07-12：**七種管道未尋得原文**且「大漲32%」與官方可查數字不符 → **撤回**（來源表 S6 改已撤回）。
- 「機率」→「歷史配對變動比例（母體＝市場×品項×起算日×期限；非未來機率）」；摘要 3.5 改 12.8%–18.3% 歷史比例。
- 45→85：本輪重新逐格核對原始 JSON（合作市場 20260702/20260709「甘藍（平地高麗菜）」欄 45→85，元/台斤，+88.9%）；**明文「成因不作主張」**，並撤銷與任何新聞的因果連結句。

**驗證**：`grep` 掃 RESEARCH_MOTIVATION 無殘留舊值（10.6%/16.7%/12.9%/18.7%/486/685/1,156/1,787/王鎰杰/2026-09-14 均 0 命中）；claims_master MOT-PTS/MOT-MOA/MOT-LTN-UDN/MOT-EXTREME 列可追溯。

**剩餘限制**：撤回的兩則 2026-07 新聞如未來取得原文可再納入；45→85 成因永遠無法由本資料集證明。

## R02｜相關研究與差異：實查與措辭收縮

**原問題**：P2 未新增網路檢索卻自稱重查；無範圍否定（「沒有工具回答未來」「無人以此期限」「已建立並開放」）；回測與前瞻混淆；R08/R09 書目不完整仍湊 10 件；R01 摘要已知指標被標 UNKNOWN。

**實際改檔**：`docs/REFERENCES.md`、`docs/RELATED_WORK_MATRIX.md`、`docs/RESEARCH_GAP.md`、`docs/CONTRIBUTIONS.md`、`docs/PROPOSAL_REPORT.md` M–O 節、v2 投影片 p4/p5/p18＋notes。

**來源/驗證證據**（`run2_20261004_01/r02_work_checks_v2.json`；R02 查核 subagent 被內容過濾器阻擋，由主對話 webReader/WebFetch 接手完成）：
- **R01 陳泯宏 2024**：tdr handle 92775 摘要**全文實讀**——正式題名、臺大統計碩士學位學程、DOI 10.6342/NTU202400875、2012–2022 批發、ARIMA/ETS/TDNN/LSTM、**摘要明列 RMSE/MAD/MAPE/方向正確率**、甘藍前 1 期 LSTM 最佳（方向約 6 成）。矩陣指標欄由 UNKNOWN 改為已知。
- **R02 李岱鑫 2015**：NYCU ETD GH02102077503 書目+摘要實讀——正式題名《高雄果菜運銷公司高麗菜批發價格預測之研究—蒐集私有資料的價值》、指導徐茉莉、66 週、下週批發價、私有中盤商手寫筆記、RMSE/MAE、結論私有資料有價值。
- **R04**：agriharvest 12897（webReader 取得 description；本輪 429 未重讀全文，沿用 2026-10-03 report 層級）。
- **R05 白菜即時**：`https://cabbagelive.com/` 官網實讀——逐字列出「智慧行情預測…中長期趨勢預測」「超市零售換算」「價格溫度計」「AI 趨勢洞察 PRO」等文案 → **撤回「所有工具只看今天」**；效果未證實同步標示。
- **R06 農產分析**：Google Play 商店頁實讀——「輸入您購買的價格→智能換算→對比當日行情」逐字確認；未列功能標 UNKNOWN。
- **R08 洪士育／R09 陳澤維**：本輪再查（NDLTD 驗證碼、政大系統 404/500）仍未尋得可定位書目 → **降為待查線索區，移出核心論證**；新增 **R11 廖啜翔 2021**（臺大農經，結球白菜深度學習；書目層級，錄自陳泯宏參考文獻）補足近年直接相關研究。
- 矩陣拆**「歷史回測／前瞻到期驗證」兩欄**（回測≠沒有真值）；C1「已建立並開放」→「材料可重現，預計隨課程交付公開」；CONTRIBUTIONS 三處「無人」→「本次查核範圍內未見」。

**驗證**：`grep` 確認 RESEARCH_GAP/CONTRIBUTIONS 無「沒有工具」「無人」「已建立並開放」殘留；矩陣計數自查更新（核心 8＋官方 1；近年 6）。

**剩餘限制**：R08/R09 書目待查；R11 僅書目層級未讀摘要；R04 平台 2018 後現況未驗證；查核範圍仍限本兩輪檢索方式。

## R03｜數字與方法：統一口徑

**原問題**：同一波動比例三種數字（10.6/16.7 vs 10.5/16.6 vs 圖 12.7/18.3）；第 7 頁混入舊 14 市場甘藍 3,615/3,523；364/905 母體未標；「12 維」與「分類樹」不準；`=7天` 標籤；claims 只有 15 條模型分數。

**實際改檔**：`slides/source/build_stats_master.py`（沿用並強化）、`stats_master.json`（唯讀重算＋交叉核對）、`claims_master.csv`（27 列）、`make_assets.py`（圖表從 stats_master 讀）、`make_pptx.py`（p2/p7/p11 數字）、RESEARCH_MOTIVATION E2、PROPOSAL_REPORT G/S/U 節。

**計算證據**：
- 唯讀重算 parquet 22,930 列（正式 direction）→ 與補驗 `descriptive_counts.csv` **9 列逐值核對一致**（交叉核對寫入 stats_master.meta）；正式值：合併 h7 **1,149/10,952=10.5%**、h14 **1,773/10,680=16.6%**；甘藍 6.8%/12.8%、青江 11.6%/18.3%、絲瓜 12.7%/18.3%。
- 浮點邊界：`abs(r)>0.05` 比正式標籤多 h7 7 列＋h14 14 列（全絲瓜、1e-9 容差邊界）→ 文稿註記「不改正式標籤迎合舊數字」。
- 母體界定句寫入動機文稿與 p2 說明條（非獨立天數、非測試 n、非未來機率；h7 起算至 2026-09-25、h14 至 09-18；甘藍 12 市場）。
- 第 7 頁配對數改為同階段三品項 10,952/10,680（舊 3,615/3,523 移除）；364/905 母體標示（全資料日數／前三品項 0 值格）。
- 模型輸入＝**12 個數值特徵＋品項 one-hot**（對照 `features/build.py:17-30`＋`train.py:31-37`）；候選＝回歸 Ridge/HGBRegressor/RFRegressor＋分類 DummyMajority/**HistGradientBoostingClassifier**（對照 `train.py` regression/classification_candidates）。
- f1 圖 `=7天`→`7天`（`h.replace('h=','')`）。

**驗證**：`pytest slides/source/test_make_tools.py -q` → **15 passed**（含 8 組正式計數、21 列邊界、purge 兩段、MD/PPT 同源正規化包含、頁數一致、v1 hash 不變）。

**剩餘限制**：描述統計重算不是新模型實驗；舊文稿 1,156/1,787 之成因已解釋但無法對原作者當時命令取證（補驗報告同此結論）。

## R04｜研究正文：完成期中必要論證

**原問題**：主稿近擴充大綱（M/N/O 一行、「見其他文件」）；T/U 對照反置；−0.1%「貼近門檻」錯；混淆矩陣頁碼錯（12→實際 17）；accuracy「失真」表述。

**實際改檔**：`docs/PROPOSAL_REPORT.md` 全文重寫為可獨立閱讀敘事（保留 A–Z 對照表於篇首）。

**內容證據**：
- 摘要 A–F／導論 G–L（含客觀動機數字與來源）／**Related Work M–O 完整三段分類＋最近前作四欄比較表入主稿**／方法 P＝PA–PM 完整敘述（資料、公式、**PJ 教學計算例逐欄標示來源**：32/28/+1% 教學假設、r̂ 封存 fixture）／評估 Q–V／結論 W–Z。
- **T＝參數分析（未執行）／U＝主要結果／Y＝Yields 主要成果／Z＝限制與未來**——對照表與節名均已修正。
- PJ：**「−0.1% 接近 0，不是接近 ±5% 門檻；與 −4.1% 同屬 flat」**；A 例中間值 32×0.959=30.688→30.7 逐步代入。
- U 節混淆矩陣指向**投影片（v2）第 17 頁（附錄 A2）**；H(iii) accuracy→「在多數類上偏高、容易誤導解讀」。
- README 提案摘要段同步（題目/情境/RQ/三貢獻/方法/初步結果/入口）。

**驗證**：主稿不再有「見 RESEARCH_GAP」「見 design.md」作為段落本體（僅細節外連）；講稿（notes_v2 p10/p11/p12）補 A/B 差異、均價≠店價、未勝基線含義之簡明解釋。

**剩餘限制**：使用者本人理解驗證（逐字稿 145–208 要求）未執行，不宣稱。

## R05｜design.md 與架構圖

**原問題**：架構圖無連線；`/agent` 非實際路由；時間軸以單日空檔冒充 15 天清除；錨定命題 sign 表述；「第五輪已修」當現況；「rule 零 LLM」無條件宣稱。

**實際改檔**：`design.md` §1（架構①–⑤分組編號＋請求/回傳/讀取/保存/查閱箭頭＋端點 `/forecast` `/agent/query` `/records`＋TRAIN_LOCAL/未來A–D 分層）、§2（教學假設標示＋特徵描述）、§3（命題改 **p>0 時 [p(1+r̂)−p]/p=r̂，同一 ±5% 分類器方向不變；sign 負≠down，−4.1% 仍 flat；α 屬 B 實驗規則非命題條件**）、§4（**真實清除兩段**：train 尾 04-25～05-09 共 695 列、val 尾 07-08～07-21 共 691 列＝1,386 列/30 起算日，唯讀重算）、§5（S01–S09 定位為「第五輪自驗、未經新審查；暫緩不修不驗」；rule「設計上不呼叫語言模型，邊界隨代理人整體暫緩保留已知缺口」）。

**驗證**：purge 數字由 parquet 唯讀重算並寫入 stats_master（測試斷言兩段 695/691）；投影片 p8 connector ≥6（測試斷言）；p9 圖改真實兩段清除帶（複查 PASS）。

**剩餘限制**：`保存可精確重播` 仍未驗收（原文僅描述計畫）；截圖 2026-10-03 情境以描述對齊。

## R06｜投影片、講稿、README、OpenSpec 與交付同步

**原問題**：三腳本硬碼輸出（會覆寫 v1/run1）；PPT 備註與 MD 講稿不同源（v1 notes 僅短導讀）；claims 頁碼過時；依賴清單缺；OpenSpec 文件留 7/11。

**實際改檔與產出**：
- **腳本參數化＋防覆寫**：`make_assets.py`/`make_pptx.py`/`export_and_render.py`（argparse＋`--force`；目標存在即 REFUSE exit 2；缺圖 FAIL exit 3）；新增 `build_stats_master.py`、`make_slide_notes.py`、`notes_v2.json`、`test_make_tools.py`、`REBUILD.md`（依賴與重建命令）。
- **同源講稿**：`slides/source/notes_v2.json` 單一底稿 → PPT 內嵌備註（含完整講稿＋逐來源＋秒數）與 `docs/SLIDE_NOTES.md`（`--force` 再生成）；測試以正規化包含斷言兩者同源。
- **v2 成品**：`slides/TW01_菜價預測_研究提案與初步成果_v2.pptx`＋同名 PDF（**各 19 頁，render_meta match=True**；pypdf 實讀核對）；素材版本化 `slides/assets_v2/`。
- **渲染與視覺驗收**：兩輪獨立 visual-judge——第一輪 12 PASS／7 FAIL（2/6/8/9/11/16/17：版面、穿框斜線、by_crop 與 confusion 鍵路徑錯誤觸發示意/空白）→ 修正 → **複查 7/7 PASS，最終 19/19 PASS**（`run2/slides_render_v2/render_review.md`）。
- **README 重整**：主頁改為教授可讀之提案入口（情境/RQ/三貢獻/方法/初步結果含負向/交付入口表/已完成-待驗證-暫緩分列/重現命令）；選題清單與修復歷史移「歷史與輔助文件」區（保留不刪）。
- **AGENTS 同步**：頂部改「題目已定不再選題；GLM 執行／ChatGPT 獨立審查分工；D44-R01–R06 自驗完成待複審；代理人暫緩」。
- **OpenSpec**：不重裝不 init；既有 change 加入 R01–R06 六項 tasks（17/17 勾選，標明自驗性質）；`OPENSPEC_WORKFLOW.md` 任務數更新；CLI 實跑 `validate --strict`（**exit 0**）／list（Complete）／status（4/4）→ `run2/openspec_cli_evidence.txt`；未 archive。
- **製作工具測試**：15/15 passed（正式數值、slide_id 映射、MD/PPT 同源、connector、頁數、防覆寫、缺圖失敗、v1 hash 不變）。

**驗證**：見上述各命令輸出；PPT 備註由 python-pptx 實際解析比對（非僅生成端自證）。

**剩餘限制**：影片未錄製；GitHub／YouTube／課程提交未發布（待授權）；組員／組長／正式發表日期待填；乾淨環境重建未驗證；格式驗證通過≠研究內容驗收。

---

## 保護與一致性（收尾檢查）

- 永久保護 11 檔（eval JSON/CSV、manifest、train JSON、split CSV、逐字稿、parquet、原始 JSON、prepare_summary、v1 PPTX/PDF）hash 前後核對：見 `run2/protected_before.json`（收尾復核於 commit 前執行，結果記錄於最終回報）。
- `src/`、`tests/`、`web/`、`contracts/`、產品 configs：零修改（git status 可覆核）。
- 負向結果（未勝動量、MAE 未勝不變價、up 召回低、B 零證據）在文稿、矩陣、主稿、投影片、講稿五處一致保留。

## 期中交付狀態（分開列）

| 項目 | 狀態 |
| --- | --- |
| 提案文件（動機/前作/貢獻/主稿/design） | 本輪修訂完成，GLM 自驗 |
| PPTX/PDF v2＋講稿 | 19 頁實檔；渲染視覺 19/19 PASS；講稿同源內嵌 |
| OpenSpec | validate --strict exit 0；未 archive |
| 約 10 分鐘講稿 | 設計完成（11:15＋10:05 快版）；**未錄影** |
| 影片／YouTube／GitHub／課程提交 | **未執行，待授權** |
| 組員／組長／正式日期 | **待填** |
| 真店 A/B（T16）／SERVER／代理人後端 | 維持暫緩／HOLD |
