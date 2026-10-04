# GLM 本輪執行提示詞：菜價研究、設計、OpenSpec 與正式投影片

請在唯一正式專案 `C:\Users\prometheans\Documents\AIOT_FinishProject` 執行本輪任務；COS 映射為 `/aiot_finishproject`。先檢查真正 HEAD／git status／git diff，保留 ChatGPT 剛加入的 D44 與規劃文件，不 reset、不 clean、不另建替代專案。

## 本輪方向已確定

代理人問題先擱置，保留現有介面作為展示載體。不要繼續修 Hermes/direct、接 GLM API、下載 Qwen、部署 SERVER或跑第六輪代理人審查。不要因缺金鑰、SERVER、真店到期價而停止這批文稿、設計与簡報工作。

保留未來 Qwen3.8-27B／GLM 可替換方向，不改型號，也不擅自移除 Hermes。介面與模型原型如實描述，未驗證能力列未來擴充；不新增教授未明講的合格宣稱，不把舊缺陷改成已修。

## 先讀這三份

1. `docs/PROPOSAL_SOURCE_AUDIT_20261004.md`
2. `docs/PROPOSAL_DELIVERY_PLAN.md`
3. `TASKS.md` 最上方 D44 本輪工作包，以及 `docs/DECISIONS.md` D44

然後按需讀 `AGENTS.md`、現有 `design.md`、`RELATED_WORK_MATRIX.md`、`FINAL_REPORT.md`、`FINAL_SLIDES.md`、資料卡與正式模型／評估工件。本輪提示詞優先於那些文件中較舊的「先修代理人／等待SERVER再製作簡報」。

教授來源：
https://app.notion.com/p/AIoT-DA-L4-1-Proposal-1-3ebc4752981180d8842fd7e253962c4e

ChatGPT本次已經用COS讀完該頁A–Z可取得正文與檢視A–Z圖；不是空白外殼。來源核對文件載有讀取範圍與逐字稿行段。這次先利用該核對，不要再把「Notion無法讀」當整批工作不能開始的理由；遇到附件未讀或來源不明，要實查或限縮主張。

## 實際完成六個工作包

- P1：研究動機與RQ。用官方／可核對證據說清楚誰有什麼問題，產出 `RESEARCH_MOTIVATION.md`，不寫空泛AI宣傳。
- P2：相關研究與差異。重查最接近的前作，分類比較方法、資料、期限、輸入與驗證，更新矩陣，新增 `RESEARCH_GAP.md`、`REFERENCES.md`。未知不能當「沒有」，Related Work過半要直接談題目。
- P3：三項主要貢獻。完成 `CONTRIBUTIONS.md` 的C1–C3，每項有問題、前作、方法、证据或待驗證狀態；完成 `PROPOSAL_REPORT.md` 的A–Z研究稿。不要硬寫三個已證實突破。
- P4：重整根目錄 `design.md`。包含現況架構、資料流、模型／A/B公式與數字例、時間切分、驗證計畫、風險与未來範圍；不改程式迎合文件。
- P5：真正建立OpenSpec管理。核對官方版本與help、局部安裝／鎖版、初始化、建立 `prepare-tw01-proposal-package` change、requirements/scenarios/tasks、記錄真CLI list/status/validate。只寫「我們用OpenSpec」不算完成。
- P6：真正產生可編輯的 `slides/TW01_菜價預測_研究提案與初步成果_v1.pptx`、同名PDF、講者備註、製作來源與逐頁渲染檢查。主講15頁＋必要附錄，約10分鐘的講稿設計；不是只交MD大綱，也不是宣稱已錄影。

每包的精確檔案、步驟、依賴及驗收以 `PROPOSAL_DELIVERY_PLAN.md` 為準。
順序：來源／數字核對 → P5a管理初始化 → P1/P2可平行 → P3 → P4 → P5b對照驗證 → P6 → 最終交付檢查。

## 必須守住

模型、資料、封存評估、fixtures與原始逐字稿不變；不重訓、不調參、不覆寫正式私人紀錄。報告須並列不變價與momentum基線，保留點MAE未勝、上漲召回偏低、B為未驗證規則等結果。機率、同店增益、使用者研究、顯著性及全球首次皆不能編造。

簡報要有真圖表、來源、具體例子、三貢獻狀態與可讀的圖文，不沿用WattWise；每頁一個主要問題，公式與數字要說來源及意思。正式投影片是完成度高的提案／初步成果簡報，不把未完成系統寫成期末全案已驗收。

所有本輪證據放 `outputs/proposal_delivery/<run_id>/`；不覆寫歷史審查。程式與模型缺陷只寫為範圍／風險，不把研究簡報批次變成除錯工程。

組員、日期或最終公告未明，只在對應欄位標待填，其他內容照做。不錄影片、不上傳、不推GitHub、不開公開服務。可逐檔審查後建立本地commit，不能把秘密、私人資料或大型權重加入Git。

最後提供P1–P6逐項狀態、成品絕對路徑、OpenSpec版本與驗證輸出、PPT/PDF頁數与逐頁目視驗收、保護檔hash及剩餘待填項；完成 `docs/PROPOSAL_ACCEPTANCE.md` 並同步TASKS／README／GLM_PROGRESS。本輪成品驗收與全系統驗收分開。

現在讀文件後直接動工，不要只重述規劃，不要再次要求確認已確定方向，也不要重新追問GLM API或SERVER資訊。
