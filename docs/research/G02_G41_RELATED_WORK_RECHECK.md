# G02／G41既有作品重查

查核日期：2026-10-03。直接要求：使用者詢問「這兩個題目你去確認一下真的沒有人做過？」

## 結論與選題狀態

**兩題的基本功能都已有作品，不能寫成沒有人做過。**

| 題目 | 本次判定 | 對既有紀錄的處理 |
| --- | --- | --- |
| G02 明天停班停課機率與依據 | 查到同台灣資料、明日放假預測、訓練模型、機率、因素解釋與介面作品；原一般版差異不足 | 助理撤回一般版推薦。使用者要求保留的紀錄仍在，不記成使用者自行拒絕。 |
| G41 出國前抓不易超支的預算帶 | 費用估計、上下界、預備金、依本人既有成本建預算，以及台灣出境支出分位模型都已有 | 一般估價／預算帶不再當特色；個人資料校正與未來整趟支出驗證暫列差異待查核，尚非已通過門檻的推薦。 |

查核涵蓋公開研究、原作者開源程式、產品官方說明及可取得的學生作品，由三個唯讀查核分支與主對話整合。未安裝或執行前作、未訓練模型、未驗證產品效果；未取得本課程歷屆完整作品，也無法證明全球沒有某個更細的同題。海外作品只用於查重，未改成台灣訓練來源。

## G02：直接前作

| 作品與一手來源 | 實際做過什麼 | 證據與限制 |
| --- | --- | --- |
| [TyphoonDayoffPrediction](https://github.com/kxykxyou/TyphoonDayoffPrediction)，2023 | 人事行政總處歷次公告＋氣象測站／颱風警報資料，預測明天是否放假；含LINE介面、機率及ROC／混淆矩陣 | 主對話與查核分支均實讀原notebook；[固定提交](https://github.com/kxykxyou/TyphoonDayoffPrediction/blob/762df51b3968ae84167f4176806ab11dee4a7cef/DCT_model_training.ipynb)日期2023-02-13。目標TmrDayoff，RandomForestClassifier＋RandomizedSearchCV；隨機80／20切分，predict_proba。檔名DCT不代表只訓練決策樹；註解的XGBoost不算實作。未見完整颱風分組或獨立校準證據，未執行模型。 |
| 陳智昆，2024，[《颱風假決策之研究：影響縣市首長決定停班與停課的因素》](https://pa.nccu.edu.tw/upload/2/publication_file/637/66-2%20%E9%99%B3%E6%99%BA%E6%98%86--C.pdf) | 以邏輯斯迴歸分析停班停課決策，提供停班機率曲線、因素解釋及法定風雨基準的情境比較 | 查核分支實讀40頁；主對話的PDF直接開啟失敗，但已取得同一原文的搜尋索引段落。印刷頁57明說以事後觀測替代逐梯次災前預報；頁60–65有門檻比較、機率及擬合資訊。不能當已完成公告前的獨立預測驗證。 |
| 明道中學，2024，[《嘿颱風，你假不假－颱風假預測之大數據分析》競賽作品](https://sciexplore2024.colife.org.tw/work/2024/C0089)、[原報告](https://sciexplore2024.colife.org.tw/work/2024/C0089/pdf) | 用風速、雨量、路徑、強度與選舉年，比較Logistic Regression、Random Forest、SVC與KNN；另作決策樹／因素重要性說明 | 主對話與分支實讀6頁報告。屬直接學生前作，不只是天氣預報。作者近100%的自述成績，未清楚交代事件切分、資料期間與機率校準；不採為可靠成績或前作效果證明。 |
| [SecTools颱風假機率計算器](https://typhoon.sectools.tw/)、[作者repo](https://github.com/stwater20/typhoon) | 縣市／日期＋風雨資訊，以門檻及歷史傾向估隔天放假機率，列依據 | 主對話實讀官方產品頁與repo。屬已有同用途工具；頁面宣稱的歷史權重不是已校準機率，也不當官方公告或本次已核對的法規解釋。 |

G02不能再把「明日機率」「因素解釋」「多模型比較」「規則與決策模型比較」當成未做過的差異。固定公告前查詢時間、僅用當時已發布預報、留出完整颱風及獨立校準，是值得核對的嚴謹比較設計；本次未確認上述作品完成整套設計，但這不是原創證明，也不自動保住原一般版。

### G02原稿勘誤

原稿的「風雨只解釋32%，因此是準確率或決策雜訊上限」撤回。原文頁63的0.322是Cox–Snell pseudo-R²，另有Nagelkerke R²=0.470；不是準確率或任何模型的上限。原文84%正確分類率也不能當事前獨立預測效果。原稿以「決策雜訊天花板」作新穎性理由沒有足夠依據。

## G41：研究、產品與學生前作

| 作品與一手來源 | 實際做過什麼 | 重疊與限制 |
| --- | --- | --- |
| 歐陽紀佩，2020，[《財富效果與生命週期對出境旅遊支出影響之研究》校方PDF](https://ir.lib.cyut.edu.tw/bitstream/310901800/38261/1/108CYUT0675018-002.pdf)、[國圖期刊紀錄](https://tci.ncl.edu.tw/cgi-bin/gs32/gsweb.cgi?o=dnclresource&s=id%3D%22A2023026141%22.&searchmode=basic&tcihsspage=tcisearch_opt1_search) | 用96–107年國人旅遊狀況調查原始資料，對出境支出作分量迴歸；支出低、中、高分位已有同台灣資料前作 | 本輪取得校方PDF搜尋索引的摘要／方法段及國圖、[中研院TESD](https://tesd.survey.sinica.edu.tw/trending-topics/2/9)關聯紀錄；PDF直接開啟為空回應，未稱全文已下載或通讀。它是支出因素及分位分析，不能說已提供同一個出發前個人預算工具；也不能靠改成年份較新資料或換成預算帶介面當差異。 |
| [Budget Your Trip官方About](https://www.budgetyourtrip.com/about/)、[費用風格選擇器](https://www.budgetyourtrip.com/travel-cost-widget)、[預算指引](https://www.budgetyourtrip.com/travel-planning-guide/planning-a-travel-budget)、[AI Planner](https://www.budgetyourtrip.com/ai) | 依目的地與旅遊風格提供旅客成本參考；可依目的地平均或自己的既有成本建未來預算，另有預備金指引與AI規劃 | 主對話實讀About，分支實讀其餘官方頁。不能聲稱現有產品只有記帳、沒有個人化／AI。未見足以核實個人回歸與未來支出覆蓋率的公開模型證據。 |
| [Travel Package Cost Predictor／dnomads](https://github.com/Portfolio-KRV/dnomads)、[訓練碼](https://github.com/Portfolio-KRV/dnomads/blob/771e9fd6a02bc5d9fd581ddd1cbe50d1de36e051/src/train.py)、[API碼](https://github.com/Portfolio-KRV/dnomads/blob/771e9fd6a02bc5d9fd581ddd1cbe50d1de36e051/api/app.py) | 旅遊方案特徵＋Ridge回歸，回傳估價與固定±15%的價格範圍 | 主對話與分支實讀原碼；提交日期2026-05-05，目標欄位ppprice，API碼168–170行是估價×0.85／1.15。已證明有人寫模型與區間功能；未執行，未核實原CSV是否旅客完整實支。方案價格不等於整趟實際花費；固定±15%也不等於覆蓋率校準。 |
| [TripCostGuides計算器](https://tripcostguides.com/pages/trip-budget-calculator) | 目的地區域、天數、人數及旅遊風格估費，另加10%預備金 | 分支實讀官方頁。是已有預算功能；固定預備金不當訓練模型、可靠上界或本人多趟校正。沒有把不同TripCost同名網站混成同一專案。 |
| [TravelSpend每日預算說明](https://help.travel-spend.com/daily-metrics/nsEZBhRKe4aEiaHGB4fnwF/how-does-the-remaining-daily-budget-work/uT5EPNGKPV3AFsgGuuKQGq) | 由剩餘預算與剩餘天數算每日可花額，協助旅程中控制支出 | 分支實讀官方公式。是相近使用目的，屬旅途中算術記帳，不能當出發前的費用區間預測。 |
| 香港科技大學2024–2025畢業專題，[Personalized Travel Budget Planning using Large Language Models – AI Trip Helper](https://cse.hkust.edu.hk/ug/fyp/posters/gallery/2024-2025/kymaaf_WDY1_Media.pdf) | 依個人偏好搜尋航班／旅館及景點，生成行程、計算分類旅費 | 主對話與分支實讀學校海報。學生個人化旅遊預算前作已存在；海報測流程與速度，未見完整實支預測或預算上界可靠性驗證。 |

費用估計、給範圍、加預備金、出發前預算、個人化成本與AI介面均不是G41獨有。原卡引用的台灣支出研究之外，本輪新增同出境調查的分位前作及直接產品／模型／學生證據。

學術分支另核對下列相關方法；它們不是全部完成同一個G41功能，不能混成完全同題：

- Seiler等，2003，[Modeling Travel Expenditures for Taiwanese Tourism](https://www.tandfonline.com/doi/abs/10.1300/J073v13n04_03)：1,097名台灣赴美旅客，迴歸／結構模型建模支出與停留。正式卷期為2003，出版社2008是上線日期；摘要未見本人多趟校正與預算覆蓋率。
- Kuo／Lu，2013，[旅遊支出分量迴歸研究](https://journals.sagepub.com/doi/10.5367/te.2013.0268)：2008台灣家庭收支調查、嬰兒潮家戶年度支出；分位方法已有，標籤並非個別出國旅次。
- Gómez-Déniz／Dávila-Cárdenes，2024，[作者文章全文](https://pmc.ncbi.nlm.nih.gov/articles/PMC11483324/)：38,759筆2019年Canary Islands離境訪談，群體先驗與Bayes後驗支出預測。分支實讀資料／模型段，n指不同旅客；不是同人三趟歷史或未來整趟超支驗證。
- Romano／Patterson／Candès，2019，[Conformalized Quantile Regression](https://arxiv.org/abs/1905.03222)、[作者程式](https://github.com/yromano/cqr)：分位回歸與獨立校準結合已有方法；採用校準不能稱新模型。公共群體覆蓋也不直接等於單一使用者的可靠性。

仍待查核的比較問題是：公共模型加入少量本人旅行紀錄後，在完整保留的未來旅次或逐趟時間回測中，是否能比目的地／風格平均＋固定預備金、固定比例價格範圍、本人上次支出基準，更少低估預算上限，同時不把區間無限制拉寬。這是待驗證用途與分析差異，並非新模型或全球首次；3–5趟自己的資料更不能證明穩定的90%不超支。

## 查找範圍與尚未證實的事

- G02關鍵詞包含「颱風假／停班停課＋預測／機率／機器學習／專題／GitHub」、Typhoon Dayoff Prediction與decision factors；實際讀到台灣開源、學術及學生作品。
- G41包含旅遊支出／出境支出／費用預測／分量迴歸、travel budget／cost predictor／prediction interval、個人歷史校正，並讀產品官方頁、原作者程式及學生海報。
- 某些原文只能取得搜尋索引／摘要，不能當已通讀；未取得完整資料、模型未重跑，也未親用產品，相關限制已逐列記錄。
- 本次未找到的更細組合不能寫成無人做過；不得由舊卡的覆核✓、換地區／年份、換模型名稱或界面加欄位，自動判為通過差異門檻。
- 使用者保留偏好仍成立；本次是助理研究修正，不是使用者選題、改功能或承諾採集本人資料。
