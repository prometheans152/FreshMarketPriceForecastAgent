# 給 ChatGPT：用 Windows COS 執行 TW01 雙入口工作包

以下工作單可整段貼給 ChatGPT。完整階段卡見同目錄 TASKS.md；目前只有文件安排完成，後續程式／接線／產品驗收均 NOT_RUN。

---

你現在是本輪 **ChatGPT Coding Agent（執行者），透過 Windows COS 實際操作**。請做完整工作，不要只回計畫或叫我自己改程式。

## 1. 原始要求與授權

專題 TW01「現場菜價7／14天預測與分析代理人」。我已決定且說「動手」：

- 保留原網頁，改為不依賴 GLM 的菜價表單；保留既有 A／B 和本機紀錄功能。
- 同時新增在我個人 ChatGPT 使用的 TW01 MCP 插件；第一版查行情及 A 預測，插件 B／保存另議。
- 正式數字仍來自凍結 ForecastEngine／RF7天／HGB14天；不重訓、不改模型與資料。
- Qwen 和 RTX3090 部署先不要動；GLM／Hermes 不接這兩條新運行路徑，舊來源與憑證保留。
- 不 commit、push、公開上架、買訂閱、開入站防火牆或對外課程交件。

我的此次角色安排優先於 AGENTS.md 舊「GLM 執行者、ChatGPT 審查者」描述；你現在是作者，但獨立品質檢查仍保留。作者自驗不能寫 EXTERNAL_PASS。

## 2. 先證明用到正確 Windows

選 **Windows COS 的 read／exec_command／view_image** 能力；工具名稱以目前可用清單與描述核對。不要選 `COS Ubuntu Server`，不要連3090，也不要因 Windows 不可讀而在 Linux 重建專案。COS 操作通道與要新增的 TW01 插件通道不同。

先用唯讀命令核對 OS、hostname、cwd、路徑與 Git，再讀檔。以下是應執行的起始核對，不是已通過的證據：

```powershell
Get-Location
$env:OS
$env:COMPUTERNAME
Test-Path -LiteralPath 'C:\Users\prometheans\Documents\AIOT_FinishProject'
Set-Location -LiteralPath 'C:\Users\prometheans\Documents\AIOT_FinishProject'
.\.venv\Scripts\python.exe -X utf8 --version
git rev-parse HEAD
git status --short
git diff --name-only
```

讀取這些本機原檔，不靠以前的 PASS 或摘要接手：

1. `C:\Users\prometheans\Documents\AIOT_FinishProject\AGENTS.md`
2. `C:\Users\prometheans\Documents\AIOT_FinishProject\docs\chatgpt_dual_entry\20261013_01\CONCLUSION.md`
3. `C:\Users\prometheans\Documents\AIOT_FinishProject\docs\chatgpt_dual_entry\20261013_01\TASKS.md`
4. 根 `TASKS.md`、README.md、design.md 中相關現況。
5. `outputs\audits\proposal_v5_r3_independent_20261009_01\REVIEW_R3.md` 與 `outputs\proposal_delivery\run3_20261004_01\protected_before.json`。
6. 工作卡指定的真原碼／schema／呼叫者／測試。先盤點既有修改與未追蹤項再動。

只有 Ubuntu 能力、Windows路徑不可讀或 COS 操作失敗時，記 BLOCKED、原始錯誤及缺哪項能力。不要假裝已讀／已跑或用歷史成功替代。

## 3. 連續執行任務，分開記帳號停點

按完整 TASKS.md 的 **DE00→DE12** 完成工作：基準→實作契約→manual後端與表單→SDK隔離→MCP兩工具→原生協定／超時→回歸→獨立複審→本機網頁→私人通道→真ChatGPT→交付。依賴與部分平行安排以工作卡為準。

已授權的本機範圍不用每個小步重問；先做出可審查的程式、測試及證據。本人登入／工作區選擇／缺權限或憑證只 HOLD DE10／DE11，繼續能完成的本機項與 DE12。重要缺陷退回來源階段；同原因連續兩次修失敗，先查根因，不盲目重試或削弱測試。

另開唯一證據目錄 `outputs/quality_runs/chatgpt_dual_entry_impl_<actual_run_id>/`，不得覆寫前輪。記 state.yaml、evidence.md、commands.log、diff_scope.txt、驗收／視覺及失敗紀錄，各 DE 子目錄保存原輸出。具體命令、時間、退出碼、收集數、PASS／FAIL、警告、環境及限制照實填；沒有跑的保留 NOT_RUN。

### 改檔白名單

- 新增 `src/aiot_price/integrations/` 的 package entry、manual_web.py、chatgpt_mcp.py 與達成真程序超時所需的小型 worker/helper。
- `src/aiot_price/api/app.py` 只限 manual模式守衛、agent import時機與 server-only records-dir 設定注入。
- `web/index.html`、app.js、style.css 只移除聊天、改初始化與必要表單／紀錄相容性。
- 新增 integrations 測試及有原始需求依據的相關既有測試調整；不刪測試或降低斷言求綠。
- pyproject.toml 的獨立 MCP extra、經查證 pin 的隔離依賴清單；相關新操作文件與根 TASKS 的本工作包狀態。

其他改檔須先寫出具體必要性；本包不授權模型、資料、訓練、舊Hermes/provider source、Qwen設定、Claude／GLM憑證、正式提案、簡報、歷屆產物、既有外審或公開部署。既有未提交修改保留，不 reset／clean／盲目 add -A。每輪前後核原14組基準，再核本輪補充的 release 全5檔（含 joblib／parquet）hash／size；不得替換原基準掩蓋污染。

## 4. 必須做實的實作契約

**manual 網頁：** 新 launcher 首次 import API 前設定 AIOT_RUNTIME_ISOLATED=1 並清除 provider 設定，禁止讀 GLM 專用 KEY。處理 app.py 頂層 agent import、status及query；query 在 provider／Qwen／Hermes建立前拒絕，status只回停用。profile=rule 仍可能 Qwen，不能拿它證明無LLM。只監聽 loopback；前端不呼叫agent端點，表單A／B與紀錄保留。

**紀錄隔離：** 新 server-only records-dir／launcher選項供回歸使用，默認仍 private/predictions；所有保存、讀取、匯出、刪除路徑一致，不接受客戶端任意路徑。用合成價格經原真引擎驗收，不把案例寫入正式私人紀錄或稱同店準確率。

**MCP：** stdio，只 expose get_market_quote／post_forecast；直接調原 AgentTools／ForecastEngine，不走 /agent/query 或 HTTP保存暫存。兩工具read-only，但 schema／dispatch實際拒URL、path、code、extra、B與保存。原公開行情日期／cutoff／age與台北查詢日時年齡分清，不稱即時。

**A預測：** crop／market枚舉照原schema；current_price非bool且正有限；單位台斤／公斤；observed_on嚴格YYYY-MM-DD，未填用Asia/Taipei今天，拒未來日，轉該日T12:00:00+08:00，exact t+7/t+14。固定without_last_week、store_id=null，不寫私人紀錄。structuredContent和受控文字回顯原數值、全部實際輸入、日期／單位／版本／警告；機率／區間null。歴史輸入警告的「今天」須註為報價基準日，不改引擎。echo不能當真人確認或原聊天忠實性證明。

**依賴與故障：** 安裝前查官方Python MCP SDK release再pin；先隔離試驗，不升級現有ML運行依賴。衝突時採隔離transport環境＋原venv worker。單worker串行15秒上限，真可終止worker／程序，超時後人工重開並實測initialize恢復；不拿threadtimer當硬終止。stdout只協定、stderr診斷，不記KEY。

## 5. 驗證與獨立複審

- 獨立HOME／編碼在首次Python/import前設定；記PYTHONUTF8=1、PYTHONIOENCODING=utf-8與-X utf8。
- 跑新功能反向控制、tests/、repo-wide適用檢查。裸pytest若收集outputs舊副本失敗，保存原錯與exit，再明示ignoreoutputs範圍重跑；不刪封存或冒稱裸全repo通過。
- 真MCP initialize／tools/list／tools/call，沿原release出數值，與引擎／網頁同輸入逐欄核對；排除動態request_id等明示非數值欄位。故意錯價的隔離checker副本須非零。
- 真瀏覽器表單A／B、精確日期與單位、保存／讀取／匯出／刪除隔離紀錄，檢查畫面、等待與錯誤、無agent／模型API流量；ChatGPT離線也應可用。
- 8766先查listener／PID／exe／啟動資料，保存可逆啟動資料後才重啟本專題；身分不明換空闲loopbackport。不能殺8765或其他服務。
- DE08由另一個獨立上下文審查原規範、實際diff、原碼與輸出，不餵作者PASS。可用子代理人時記錄獨立代理人的身分與結論，不冒稱使用者／正式外部驗收。無獨立reviewer時明記SELF_CHECK／外審HOLD；DE09只測隔離本機候選，DE10／DE11待審查，仍做DE12交付，不能升格正式final。

本機、原生MCP、通道、真ChatGPT、正式外審各自記結果，不互相冒充。合成價格不是真店驗證；舊Proposal EXTERNAL_PASS不是本插件PASS。

## 6. 個人 ChatGPT 接線

本機候選與審查完成後，按執行當時的官方文件查本人ChatGPT自訂MCP能力與個人Platform organization的Tunnels Read／Manage／Use，建立私人通道與本人插件。本人登入／選工作區由本人操作；只有真的缺憑證時，先提供受保護的本機檔案位置讓我填，不要叫我把KEY貼對話，不讀shell history或借用Claude／GLM KEY。

通道 runtime API key只用於tunnel-client控制，不代表需要再接模型API。保留真實doctor與啟動結果，不猜已連通或工具清單。缺帳號條件只HOLD此層，不改成公開代理。

參考：[OpenAI Secure MCP Tunnels](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)、[ChatGPT 插件連線及驗證](https://developers.openai.com/plugins/deploy/connect-chatgpt)。檔案與當時實際畫面優先於記憶；不保證任何帳號已有權限。

DE11用我本人ChatGPT做真實行情／A預測／缺欄追問／單位／日期／陳舊資料／B及保存拒絕。保存合成案例的原工具輸入／輸出，核對最後ChatGPT文字，不拿本機Inspector通過當真對話。

## 7. 最終交付

完整更新本包DE任務、操作文件、保護hash、原始命令與失敗返修史。繁體中文先說可用結果：

1. 給我**實際試過的網頁網址**、現行架構與如何重開。
2. 告知本人ChatGPT插件是否真的裝好／真對話通過；未通就列DE10／11實際HOLD與我須做的最小操作。
3. 列改檔、測試命令／exit／真數量、模型與資料保護結果、獨立reviewer與限定結論。
4. 列真店A／B、Qwen／3090、插件B／保存、外網、影片及公開發布尚未完成。
5. 給精確證據目錄與重現指令。未經獨立驗收的候選不要叫正式final。

請從DE00現在開始執行；不要重問我已選的雙入口方向。
