# 工作候選：資訊維運與檔案影像

查核日期：2026-10-03。T01–T13 是整合前識別（T12只作備案，不納正式50），不是使用者選定。原 N18 與 TW01 仍保留。本次只查資料與前作，沒有訓練、執行公開專案程式或蒐集公司資料。

## 共用資料與實際取得

| 來源 | 來源國／版本、授權、真實欄位 | 此次取得狀態與限制 |
|---|---|---|
| D1 [臺灣司法周刊 OCR](https://huggingface.co/datasets/andynoodles/Taiwan-JudicialYuanPublication) | 司法院1981–1995直書掃描；2026-06-24，commit `087a9f52d8b9b0fe0dab6da73f5ad67da97658d2`。資料卡 `other`，內文說明原網站政府開放授權第1版、須顯名司法院並引用整理者。image/type/bbox/group_id/doc_id/page_index/block_index/ocr/ocr_revised。 | raw README與first-rows API均HTTP200；已讀第一頁「第一版」修訂文字、版面框及檔案ID。**標籤由PaddleOCR-VL／Qwen產生，非人工真值**；README104,938與viewer約99.7k口徑不一致，選中需按固定版本重數。未取完整Parquet或實際影像像素。不能把block_index當人工閱讀順序。 |
| D2 [臺灣都市計畫書 OCR](https://huggingface.co/datasets/andynoodles/Taiwan-UrbanPlan) | 屏東、嘉義1950s–2020s計畫書；2026-06-24，commit `ec8b1456971daacfb4eeffca40b6109885cd0d03`。同為 `other`，內文說明政府開放第1版、顯名兩政府＋整理者。欄同D1，table文字使用OTSL，**不是HTML**。 | README／first-rows HTTP200；已讀嘉義計畫書表格，原OCR「一機三部份」與修訂「『機三』部分」不同，bbox、doc_id、page_index可讀。模型蒸餾標籤、無人工金標；未全檔下載。README119,735與viewer約110k需版本核數。 |
| D3 [臺灣藥品外盒／仿單影像](https://huggingface.co/datasets/twinkle-ai/tw-drug-labels-vision) | TFDA臺灣許可證PDF；2025-12-22來源清單，2026-05-03 commit `d882d4457ed957bed68a112a593cea279864a99b`，CC BY4.0。images、license_id、drug_name_zh/en、strength、package、manufacturer、source_type、folder、source_urls等。 | README、`sample.json`、first-rows均HTTP200，已讀真欄位與來源URL。第一筆字號／0.2%／450cc可見。文字由OCR＋LLM抽取，非藥師核定；README44,663與viewer72.3k計數不同，先固定版本去重。不是實拍盒子，不是現行庫存或批號資料。尚未下載影像像素／全檔。 |
| D4 [tw-PII-bench](https://huggingface.co/datasets/lianghsun/tw-PII-bench) | 臺灣繁中情境、個資皆虛構；2026-04-28 commit `62bdad506803b15e1a4193f4493200ad431b1af7`，Apache2.0；910段分short/mid/long，text與start/end/label/spans、負例。 | README／first-rows HTTP200，已讀姓名與手機span及負例schema。可把一部分重新劃為小模型訓練，必保留不相似的獨立題目，不能再把全910當未見官方benchmark。另184k的tw-PII-chat需要人工申請，**本次沒取得，不算可立即訓練源**。 |
| D5 [Python Runtime Errors](https://github.com/google-research/runtime-error-prediction) | CodeNet Python3競賽程式，主要日本AtCoder/AIZU來源；2021-12-29，資料CDLA-Permissive2.0、程式Apache2.0分開。[資料授權](https://storage.googleapis.com/python-runtime-errors/datasets/project-codenet/LICENSE)HTTP200。tokens/CFG/target/error location/problem_id/submission_id。 | [train.tfrecord](https://storage.googleapis.com/python-runtime-errors/datasets/project-codenet/2021-12-29/train.tfrecord) Range HTTP206；只讀64KiB，第一record1824bytes已解欄位，problem_id=p00001、submission_id=s105926465、target=1、129tokens／11nodes。未下載3.5GB完整檔。標籤只代表一個sample input的執行結果，不能當所有輸入安全證明。 |
| D6 [缺陷資料可重現性研究原始資料](https://github.com/ucd-plse/On-the-Reproducibility) | 國外開源Java／Maven／Gradle／Ubuntu軟體；2023研究、BSD3-Clause庫。1795個非flaky BugSwarm案例、13月36次檢查，另8月20次測試。原始／重現logs、各次Broken/Reproducible、修補種類列表。 | GitHub樹43028項已讀；`section-3/RQ4/Patches-Applied.csv`、`test-suites-for-eval-after-study-range/suite-1.csv` HTTP200，已讀Maven TLS、多重patch、逐案例重現標籤。已讀原始研究與RQ4原因表；尚未取得全logs或執行Docker。修補種類不等於所有失敗都只來自一個原因。 |
| D7 [Loghub](https://github.com/logpai/loghub)／[Loglizer](https://github.com/logpai/loglizer) | 國外HDFS／Apache等同軟體日誌。Loghub資料只明列研究／學術免費與引用義務，**不是MIT商業授權**。HDFS_v1有block異常標籤；Apache／Linux／Windows不是天然故障標籤。 | HDFS及Apache各2k structured CSV、template CSV HTTP200已讀，含EventId/EventTemplate、原Content、時間。Loglizer HDFS `anomaly_label.csv` Range HTTP206前1500bytes已讀，Normal／Anomaly與BlockId可見；[完整HDFS_v1入口](https://zenodo.org/records/8196385/files/HDFS_v1.zip?download=1)存在，1.47GiB未全下載。保留block事件，不推成真實故障根因。 |
| D8 [RETECS真實測試結果](https://github.com/mregorova/RETECS/tree/main/DATA) | ABB Robotics Norway歷史測試；Paint114tests／352cycles、IOF2086tests／320cycles；2015–2016。庫MIT，原來源資料引用與各檔宣告仍需保留。Id/Name/Duration/LastRun/LastResults/Verdict/Cycle；Duration是**近似**時長。 | DATA/README.MD、iofrol.csv、paintcontrol.csv HTTP200，欄與前列已讀；紀錄1=failed、0=passed。`kael-pan/retecs`雖README寫DATA但實際樹沒有資料，不能用該fork冒稱下載成功。非臺灣工廠資料，適用條件另列T12。 |

資料卡的授權說明是此次來源宣告；沒有把「other」自動翻成任意商業使用許可。選中要固定完整檔案、顯名條款與原始政府網站宣告。頁面／JSON樣本可讀與影像已讀／全檔已下載是不同狀態。

## T01 舊直書檔案轉可搜尋文字：欄序錯了，句子還能接對嗎？

- **工作／輸入：**檔案管理、行政掃描；提供原PDF或掃描頁。需要文欄位落順序，不只逐字辨識。
- **訓練：**D1臺灣版面框與蒸餾文字作版面／文字預訓練；先人工標100–200頁的相鄰欄位關係，再訓練小型欄序排序器。block_index只是模型輸出，不能直接當金標；合成欄位互換只作代理例。
- **已做：**[PaddleOCR-VL技術報告](https://ernie.baidu.com/blog/publication/PaddleOCR-VL_Technical_Report.pdf)已有直書、版面与表格閱讀；D1整理者也已完整OCR＋修訂。單純重做台灣OCR淘汰。
- **另測／對照：**右至左規則、通用版面OCR與加入自家掃描校正，比較同頁直書正文／橫書表頭交錯時的段落斷裂、錯接欄比例及人工重排秒數。文字CER另報，不能讓字元高分掩蓋順序錯。
- **自己的資料／切分：**20–30頁自家非敏感舊表或檔案，人工確認閱讀關係；不同原檔案／期刊期號整組留出，不能讓相鄰頁進兩邊。公開年代字型與現代掃描不同，單一公報測試不等於所有公司檔案。

## T02 地號清單轉Excel：主地號、分號和下一列是否串錯？

- **工作／輸入：**工程資料整理或土地表冊抄錄；提供掃描清單、指定地號欄與人工確認的一小段對照。
- **真目標：**D2 OTSL學習表格／列關係，人工確認公開地號表100–200列的字串和儲存格關聯。OCR修訂只作弱標籤；地號不存在於可讀樣本的頁需先由固定版實圖確認，不能把第一頁標題算成地號金標。
- **前作：**[Table Transformer](https://github.com/microsoft/table-transformer)與[PaddleOCR表格結構模組](https://www.paddleocr.ai/latest/version3.x/module_usage/table_structure_recognition.html)已做表格圖轉結構。一般表格轉CSV不是本題差異。
- **另測：**同一張表，固定OCR，比較最近鄰儲存格、一般表格辨識與欄位關係校正。目標是破折號／分隔符／換列時的「完整地號與所屬列都對」，報行配對率、分號漏接率、人工更正時間；與N50稀有字辨識是不同目標。
- **工作成本／測試：**需20–30張自己已有且獲授權的表冊；每張人工核對10–20列。整份計畫書、同地段各版本同組留出。只輸出抄錄候選，不能從識別字串推成土地權利、交易或現行法規結論。

## T03 每份檔案只有五分鐘核對：先查哪些OCR區塊最划算？

- **工作／輸入：**檔案數位化／行政檔案品管；提供掃描檔案與必須正確的欄位清單，例如案號、表頭、數字或公司名稱，再給人工核對分鐘數。
- **資料／標籤：**D1/D2兩套OCR原文／修訂差異提供「兩模型不一致」代理標籤，bbox與文字長度支援成本估計。它不是正確／錯誤真值。另由人工標100–200區塊的實際錯字、重要欄位錯誤及修正秒數，訓練小排序器；自然完整頁的成本需保留。
- **已做：**[DeQA-Doc原始擴充](https://github.com/ByronWilliamsCPA/DeQA-Doc)已用多訊號不確定性與active learning選檔案；D1/D2也已全量第二模型修訂。單純挑低信心OCR、不確定性抽樣淘汰。
- **具體另測：**與按信心、隨機、平均每頁核對比較，在相同5分鐘下最大限度減少**指定關鍵欄位的未修正錯誤**；對照含／不含人工修正成本與自家欄位權重。衡量剩餘關鍵錯誤數、每分鐘修正數和漏掉的高信心錯誤。
- **切分／負擔：**20–30份不敏感自家檔案及核對計時；留整份檔案與新掃描裝置獨立測。重要性由使用者先定，不能事後挑得分好看的欄位；本文不宣稱目前已有人工錯誤／成本標籤。

## T04 掃描檔案遮個資：跨行姓名與號碼能否完整遮住？

- **工作／輸入：**行政、人資或客服將已授權檔案交接給另一部門前，提供掃描檔案與要遮的型別；所有預覽先在本機。
- **公共訓練：**D4臺灣虛構文字＋span可訓練小型NER，並渲染不同字型／換行的模擬頁，把span對映到像素框。渲染框是合成標籤，**不是天然臺灣掃描個資集**；公開910段只能做小模型／校正，不能假稱184k gated資料已取得。
- **前作：**[Presidio Image Redactor](https://github.com/data-privacy-stack/presidio/blob/main/docs/image-redactor/index.md)已有OCR＋PII框遮蔽；[privacy-filter-tw](https://huggingface.co/lianghsun/privacy-filter-tw)已有台灣19類個資NER与長文本。一般去識別化同功能不保留。
- **另測：**固定文字NER，測OCR跨行／框被截掉時的漏遮：逐詞框遮蔽、合併跨行區塊、加自家掃描樣本校正三組；目標是每件識別資訊是否**全部字元**遮住、無關工作欄位誤遮比例及人工更正秒數。文字NER F1與像素漏遮分開。
- **自己的資料／切分：**20–30張只含虛構姓名與號碼的自製表，印出用兩臺裝置掃描；依原文字／模板／字型整組留出。真客戶資料不是必要輸入。合成驗證只證明該模擬流程，現場可靠度待實拍。

## T05 相似藥盒入庫核對：名稱一樣，規格不同會不會認錯？

- **工作／輸入：**藥品倉儲檔案／收貨核對研究；提供盒面照片與預計收貨的許可證／規格，回傳需人工核對的識別候選，不給用藥建議。
- **資料：**D3臺灣許可證、名稱、規格與PDF面圖可預訓練圖文配對。相同名稱不同字號／strength形成難負例前，須核對原PDF和官方標籤；LLM抽取不是專家金標。只使用字號、名稱、規格、包裝，不訓練臨牀決策。
- **已做：**[Medicinal Boxes Recognition 2022](https://arxiv.org/abs/2203.14031)已有深度遷移辨識盒子，D3已做圖轉17欄。一般藥名辨識或仿單問答淘汰。
- **另測：**通用整盒分類、只OCR名稱、名稱＋規格／字號配對；在同廠牌近似包裝羣與遮住條碼時，比較錯收規格率、固定退回人工比例的識別錯誤、兩張補拍是否降低錯誤。PDF渲染與實物反光的落差是待測問題。
- **個人／工作成本：**20–30個空盒或不敏感包裝、每盒3–5張手機照，由負責人確認識別欄；不能只拍同盒放進train/test。依許可證、產品家族整組留出，不把字號直接塞進欲辨識照片的輸入文字。不從資料快照推現行停證、庫存效期或批號。

## T06 多頁附件混入別的產品：能否找出那一張異常頁？

- **工作／輸入：**供應商檔案、藥政行政的附件整併品管；給一份PDF，不用手動逐頁填值。
- **公開資料／標籤：**D3的folder/source_urls/license_id與已取得PDF的完整頁組能建立同檔案正對；交換其他產品一頁生成明示的合成混頁負例。同字號不同原始檔案不直接當錯頁；紙本常見的共同附錄也須人工標。固定版本README明列約3,305筆多URL仿單只抓首份PDF，這些不能當原附件全集，須排除或補齊原始來源。蒸餾字號先人工核對，未下載像素前不宣稱已有可視頁面訓練表。
- **已做：**[2026 Multi-Split Boundary Decisions](https://arxiv.org/abs/2609.22620)已有頁流切件與成本研究；[2023 context-aware page classification](https://arxiv.org/abs/2304.02787)已有相鄰頁上下文分類。一般文件分類／批次PDF分割淘汰。
- **另測：**研究「已知應是一件」卻被混入**同廠牌近似產品**頁，對照頁型分類、只比字號和學習頁面一致性；測錯頁定位F1、共同附錄誤報與同產品多檔案誤拆。沒有字號的內頁另分組，讓簡單主鍵檢查成真正基準。
- **自己的資料／切分：**20–30組自行組合、非敏感供應商附件，由人標真混頁與合法共同附錄；同產品／原始PDF所有頁與交換負例同組。自然現場錯頁要另測；合成混頁效果不能冒稱公司實際錯誤率。

## T07 小型Python工具改輸入後，先補哪種邊界測試？

- **工作／輸入：**資料整理／資訊人員提供讀檔、字串轉數值、清單索引等小型Python3片段及新的輸入格式；輸出優先測試候選，不自動改檔。
- **公開學習：**D5有實執行錯誤型別，可預訓練error分類器；但每程式只測一組sample，不能用其NoError證明空值、零值、超界都透過。公司工具的「新輸入會出何錯」必用自己的固定測試輸入建立真值，合成空值插入則列代理情境。
- **臺灣適配依據：**適用範圍限同版本CPython3、同內建操作與[例外語意](https://docs.python.org/zh-tw/3.10/library/exceptions.html)；台灣工具也使用IndexError/ValueError等相同執行標籤。競賽程式不是Excel／pandas公司工具，涉及第三方套件或業務邏輯時不沿用公開標籤，必另測。
- **前作：**[2022 Static Prediction of Runtime Errors](https://arxiv.org/abs/2203.03771)已分類錯誤、定位行號。一般靜態錯誤預測同題不保留。
- **另測：**輸入契約變動後，在固定5個測試額度下，與每類邊界都測、原有測試、通用錯誤分類比較，評估優先測試找到真異常的比例、浪費測試數及原本成功案例誤報。模型計分必以修改前可得資訊，不拿執行stderr當預測輸入。
- **自己的成本／切分：**10–20個非機密小工具，每個固定正常／邊界fixture；依問題ID、同人同題提交與自己的完整工具分組。只適合本來就會寫指令碼的工作者。

## T08 程式沒改卻突然建置失敗：先查環境還是查程式？

- **工作／輸入：**Java維護人員提供同commit前一次成功與此次失敗logs、鎖定的建置設定；輸出原文證據與環境問題候選，不自動修改TLS／套件。
- **標籤界線：**D6的Broken是各次是否偏離原結果的真實記錄，可作輔助學習；10種修補型別是案例層級人工總結，只作弱監督，不能複製成同案例36次失敗的即時原因金標。必須取同一fixed版本確曾成功與後來失敗的配對log；原buggy與fixed不是同commit，不當成前後配對。當次環境／程式原因與支援行另由人對齊20–30件已結案紀錄，沒有這份真值便不報原因分類效果。不把Patches List放入輸入，也不拿fail/pass檔名當原因。
- **臺灣可用性：**限定資料對應的Maven／Gradle／Ubuntu／JDK版本及相同公開套件解析；同版本TLS、repository與建置規則不受使用國別改變。現代JDK／私有映象要用本身20–30件歷史建置對照，未測不能擴大到所有臺灣CI。
- **已做：**[原2023重現性研究](https://web.cs.ucdavis.edu/~rubio/includes/icse23.pdf)已分析10種原因与修補；[LogSage](https://arxiv.org/abs/2506.03691)已有CI診斷／歷史方案RAG。一般log找根因淘汰。
- **另測：**相同模型，只有本次失敗log，對照加入**同commit先前成功log**，能否減少把外部失效歸錯程式碼；當次原因由獨立人覆核後，才報環境類macro-F1、錯派到程式修改的比例、引用log行真正支援判斷比例，並比較固定字串規則。若始終取不到同版本配對與原因真值，撤下此題，不退回一般log分類仍稱同一差異。
- **負擔／切分：**適合有舊Java工具的人；20–30件已結案紀錄另留10件測試。原project／artifact及全部重跑logs同組，後期執行批次獨立。資料年代老，是受控同版本研究，不假稱最新CI診斷大全。

## T09 快取空間不夠：先儲存哪些專案依賴比較值得？

- **工作／輸入：**維運提供專案建置設定、快取容量與重建成本；先學習哪些外部依賴較易令舊程式無法重建。
- **真目標／資料：**D6逐案例13月36次重現結果，是未來Broken機率的真歷史標籤；cache size／公司停工成本不在公開資料裡，必自己量20個專案的依賴大小及重建分鐘。Patches List或未來broken狀態不能當當時輸入。
- **臺灣適配：**與T08同特定Java建置鏈，重用的只是相同軟體依賴失效模式；不是國外企業營運風險倍率。不同私有repository、受公司政策限制不能假定公共模型可部署。
- **前作已做：**D6的[cache與isolation評估](https://github.com/ucd-plse/On-the-Reproducibility)已測20次整批快取／隔離是否較能重現；全量打包所有依賴的展示淘汰。
- **另測：**在同樣有限GB下，比較先快取最大、最近用過、全部均分與以**未來失效機率×重建代價**選擇；公開後期資料先報「容量內涵蓋的後期Broken案例」代理指標與浪費GB。未確認同日期、同artifact有／無快取完整配對，不能預設每次Broken均可快取解決。真實避免失敗與節省工時須自家公司同版本有／無快取對照、實際命中及重建計時；共享依賴須去重計算容量。大小是自己實測或明示假設，不宣稱已有最佳公司決策。
- **切分／成本：**依project留出與後期批次測；自己的20專案需2–3週紀錄／既有快取清單，資料不夠則限定公開歷史模擬。這是預先分配容量，與T08當次失敗診斷不同。

## T10 HDFS日誌去識別後，還能把同一次事件接起來嗎？

- **工作／輸入：**有HDFS的資訊維運提供需隱藏的路徑/IP與可保留的事件關聯規則；先在公開資料離線研究，不用上傳公司的原日誌。
- **訓練／真值：**D7 HDFS_v1有BlockId→Normal/Anomaly，可訓練事件序列模型。公共2k檔只確認格式，不足完整事件測試；選中先取得全HDFS及對應label。Apache、Windows無同類故障標籤，不冒充本題正負例。
- **臺灣條件：**來源國外，限定同HDFS事件語法／操作，block本身與IP是區域性識別符，不以國外網路攻擊盛行率轉用。若公司的軟體／版本不同，先做正常日誌模板相容檢查，不能宣稱通用資安偵測。
- **已有：**[Drain3](https://github.com/logpai/Drain3)已有IP／數字mask；[OneLog](https://arxiv.org/abs/2104.07324)已有HDFS異常序列，去名稱或換模型本身不算差異。
- **另測：**固定模型，全部ID移成同字串、穩定匿名ID、只保留事件內關聯三組；在相同被遮資訊下，測**跨事件串錯／單事件被拆開**比例和block異常召回損失。原始BlockId只供切分與評估，不從metadata偷偷還給模型。穩定ID保留跨事件追蹤能力，不能聲稱與事件內ID有完全相同隱私；效用與可追蹤性分開報，不宣稱匿名hash必然不可再識別。
- **公司成本／split：**已有HDFS者可加30個已人工確認的事件序列；沒有此係統不推薦。所有同BlockId先分組，再按實際時間分期；真根因與攻擊類別不存在於public label。Loghub限學術研究，工作部署授權另核。

## T11 軟體更新後，少量人工標記能否保住重要日誌事件？

- **工作／輸入：**Apache/HDFS等維運提供新版本日誌與10–30個應分開的事件例；目標是原告警依賴的事件類別不被錯合併。
- **公開標籤：**D7 EventId/EventTemplate可監督模板抽取；[Loghub2.0](https://github.com/logpai/loghub-2.0)提供更大人工整理模板，但本次未下載全量。古早Apache樣本有mod_jk狀態，不能直接当今天Nginx例；沒有故障原因label。
- **臺灣可用條件：**只對相同軟體、既有英文機器訊息格式使用；中文客訴不是這套標籤。自己的版本變更前後需各至少100–200行人工模板，不能用人為同義改寫當真實更新。
- **前作：**[Drain3](https://github.com/logpai/Drain3)已在線新增模板；[UNLEASH](https://github.com/LogIntelligence/UNLEASH/)及[MicLog](https://github.com/arjen-yu/MicLog)已有少樣本模板學習和示例選取。一般few-shot日誌分類淘汰。
- **另測／對照：**固定10/20/30次人工標記額度，通用平均類別抽樣與按**告警誤合併後果**選取新模板比較；另留新版本未見行，看重要事件合併率、其他模板退化與所需人工分鐘。重要事件集合事先由維運標，不事後挑好看的模板；整體template-F1另報。
- **切分／成本：**需要版本更新記錄或自行控制兩個同軟體版本的測試服務。依原始事件族／版本／完整來源檔分組。沒有真新版資料時只做模板新類別留出壓力測試，不宣稱版本更新已驗證。

## T12 固定CI截止時間：測試偶爾變慢，會不會漏掉最重要的測試？

- **工作／輸入：**測試工程師給截止分鐘、既有測試的過往結果與時長；先排序必測候選。
- **公開資料：**D8真Verdict/Cycle與近似Duration可訓練下一次失敗／選取模型；Duration不是每次實測執行分佈，不足證明deadline。自己的30–50次CI要逐測試記開始／結束、共用setup與runner開銷，纔有完整排程成本。
- **國外資料具體適配與限制：**ABB在挪威，**不把其測試ID或失敗率直接搬到臺灣**。限也使用「每週期同測試ID、失敗0/1、近似毫秒成本」的工業回歸測試；先以自家歷史評估該特徵機制，公共資料用於方法預訓練／對照，而非產品故障判斷。若測試工作沒有相同可記錄欄位，淘汰。
- **已做：**[RETECS](https://github.com/mregorova/RETECS)已按過往失败、時長与上次執行學習排序；只做失敗率／測試優先序淘汰。
- **另測：**相同測試排名，平均Duration固定成本排程，對照加入**共享setup成本、時長上界**校正；測截止超時率、截止前抓到的真正失敗數、未完成必測集合與額外預留分鐘。若只有公共近似時長，必將setup／抖動作明示模擬，結果限定壓力測試。
- **負擔／split：**已有CI時可自動記錄，不必人工逐筆輸入；各cycle整組按時間留出，再留全新測試族。只適合有公司真CI紀錄的人，沒有者優先選臺灣公共檔案題。

## T13 Excel整理前先預估會動到哪些格：是否超出預期範圍？

- **工作／輸入：**行政、業務或資料整理人員給一份XLSX與整理要求，例如按日期篩選、兩張表依參考碼合併；模型先預估受影響儲存格／列與可能跨表連動，供人核對。
- **公開資料已取得：**[SpreadsheetBench Verified400](https://github.com/RUCKBReasoning/SpreadsheetBench/tree/main/data)，2025-12發布、CC BY-SA4.0；來源是國外Excel論壇。此次匿名下載`spreadsheetbench_verified_400.tar.gz` HTTP200、14,958,255bytes，在記憶體解開1603項，`dataset.json`400題與init/golden XLSX真檔已讀，未儲存大型檔。欄位instruction、answer_position、answer_sheet、data_position與原檔／金標；例13-1是RANGES→LISTS依DATE/REF合併、TOTAL列，17-35是I2/J2日期篩選到I6。前三個XLSX無公式，**不聲稱全資料含充足公式錯誤標籤**。
- **訓練標籤與限制：**官方answer_position是真評估範圍；init/golden逐格差異可形成實際改動範圍。金標的其他格式差異不自動當使用者授權，需人工核對50–100題再訓練小範圍／表關係預測模型。人工增加保護欄或錯改儲存格屬明示代理情境。
- **臺灣可用依據：**只選同XLSX／OpenXML、相同[Excel日期篩選](https://support.microsoft.com/zh-tw/excel/get-started/filter-data-in-a-range-or-table-in-excel)／合併／排序操作；這些儲存格與表關係是同一軟體格式，不用海外稅率、薪資或國家業務規則。台灣自家活頁簿與中文版要求仍需20–30件獨立測試；不把英文指令翻譯直接當適配完成。
- **前作：**[原始2024 SpreadsheetBench](https://arxiv.org/abs/2406.14991)已評估LLM整理Excel、輸出指定答案範圍；一般Excel聊天助手或自動改檔淘汰。 [ExceLint](https://arxiv.org/abs/1901.11100)已有公式錯誤分析，因此本題不另宣稱新公式除錯器。
- **另測／對照：**在實際寫檔前預估**整份檔案的參考變更範圍**，不只看答案格是否相同。比較只看官方answer_position、通用描述範圍與學習原檔／金標關係；先報參考金標變更格召回、跨表漏列與人工審查分鐘。金標不是唯一正確解法；只有人工按要求確認必要／容許／未授權範圍後，才報必要格召回與未授權格誤列。若鎖定一個實際整理器，另以其真正輸出前後差異建立行為真值，不能用golden冒充它一定會改哪些格。保護欄命中可用規則檢查，模型負責推估未知範圍。
- **成本／split：**20–30份虛構或已授權去敏感工作檔、人工確認操作影響範圍；依完整原始工作簿、相同論壇題／變體分組，train/test不能共享模板。學術訓練重新切出子集後，不能再將全部400題報成未見官方測試；尚未實際改Excel或驗證臺灣公司檔。

## 淘汰／不算已取得

- ZYELL-NCTU NetTraffic-1.0：原論文已讀，但未找到可匿名下載且授權明確的真正資料檔。22.5M流量／攻擊說明不等於訓練檔可取得；不計正式。
- ReproFlake：2026論文有1115可重現測試，作者網站指向anonymous.4open.science，實際HTTP401 `not_connected`；不以論文附表代替已可訓練檔，不計正式。
- Taiwan-Financial：有圖文蒸餾資料及企業申報原來源，但原企業PDF與整理標籤的用途條款尚未充分確認；不把政府公開上市檔案自動稱政府開放授權，暫不用。
- 通用RAG、檔案摘要、一般藥名分類、一般CI修復agent：既有原作已提供，不靠換UI、繁中prompt、另一個模型名稱納題。

本分支另查公開課程／學校作品（`site:edu.tw 專題 日誌 異常`、`site:edu.tw 專題 OCR 表格`）、原始庫與作者論文。取得的前作支援上述對照，不支援「全球首次」。未取得像素／全檔的來源要在候選被挑進短名單後完成樣本取得再實作；以上從未宣稱模型或工作效益已證實。
