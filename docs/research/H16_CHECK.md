# H批查核證據（第三輪）

查核日期：2026-10-03。五個查核代理＋主對話覆抽（會考PDF 81,870 bytes實抓、教育部114_basec.xlsx 490,483 bytes實測、ARME onset值實讀、環境部平臺頁實測；data.gov.tw本輪再回500，8116之CSV為代理同日206實讀）。本檔是[H16清單](../H16_TOPIC_CATALOG.md)的證據基礎；「已驗證」均指2026-10-03實測，未驗證項如實標明。

## 一、全新發想15題判定

| 題 | 判定 | 關鍵證據 |
| --- | --- | --- |
| T1 新生兒命名 | 淘汰 | 戶政司僅PDF年報（112年報31.8MB HEAD 200）；「名字×出生年」CSV查無；官方線上姓名統計查詢已覆蓋撞名查詢；SSA式研究為美國資料。 |
| T2 海灘水質 | **有條件合格（→H02）** | 資料存在但需moenv金鑰（API實測「api_key不存在」）；夏季約10–20處、每月至雙週取樣，20年約2–4千筆；台灣無預測模型（僅規則宣導）；前作：[美EPA Virtual Beach](https://nepis.epa.gov)、[Zimmer-Faust 2018](https://www.sciencedirect.com)、[香港泳灘預報指數](https://cd.epic.epd.gov.hk)已上線。 |
| T3 家庭支出對標 | 淘汰（備案） | 主計總處微資料走[SRDA](https://srda.sinica.edu.tw)會員申請；stat.gov.tw被Cloudflare擋（403）；彙總表僅能查格對照非模型訓練；Status Money（美）為同構產品。 |
| T4 時間分配對標 | 淘汰 | 同SRDA申請制；調查間斷辦理；「相似族群對標」彙均表即可完成大半，模型必要性弱。 |
| T5 陪練會考 | **合格（→H01）** | cap.rcpet.edu.tw題本PDF 200；110年各科通過率PDF 82KB**樣本已讀**（國文#1 P=0.93、英讀#13 P=0.38）、鑑別度PDF樣本已讀（#1 D=0.41）；110–112直鏈200、113–115轉302待補；[question_database](https://github.com/ChihHsiangChien/question_database)整合103–115年（無LICENSE、無模型）；台灣查無難度預測論文；前作：ACL試題難度共享任務、[ACM系統性回顧](https://dl.acm.org)、韓國KCSAT。 |
| T6 自選車牌 | 淘汰 | 監理[標售查詢](https://www.mvdis.gov.tw/m3-emv-plate/bid/queryBid)需驗證碼且僅一年回溯；[開放資料建議案132755](https://data.gov.tw/suggests/132755)結案未承諾開放；前作：香港車牌吉祥數字Woo 2008。 |
| T7 收容所認養 | 淘汰 | [認領養資料集](https://data.gov.tw/dataset/85903)25欄**樣本已讀**但無入所/出所日期，官方留言證實出所即下架；[統計表](https://data.gov.tw/dataset/73396)僅縣市月彙總；Austin/Sonoma intake-outcome預測為國外經典。 |
| T8 素食成分 | 淘汰 | 無「成分→素食五類」公開配對資料；TFDA規則查表即得、模型無空間；Open Food Facts掃碼App與VeganAI前作已覆蓋。 |
| T9 客語練習 | **有條件合格（→H03）** | [Elearning-Hakka](https://github.com/i3thuan5/Elearning-Hakka)（MIT）五腔調CSV**樣本已讀**（四縣3-1共2,254筆；欄位：客家語/標音/音檔URL/華語詞義/例句），推估3萬+詞條；wiki.hakka.gov.tw音檔TLS錯誤待解；NYCU已辦客語ASR挑戰賽（2023/2025），發音評分前作未找到（推測性缺口）。 |
| T10 寵物名字 | 淘汰 | [寵物登記狀況](https://www.pet.gov.tw/Web/O302.aspx)僅縣市彙總無名字/品種明細；遺失啟事有名字但為現行偏差小樣本含個資；西雅圖寵物名為TidyTuesday經典。 |

## 二、N輪18題重驗判定

| 題 | 判定 | 關鍵證據 |
| --- | --- | --- |
| N14 散步雨斷 | 備案 | CODiS站表API匿名200（1,265站）；10分鐘雨量O-A0002-001確認但屬即時型；**官方QPESUMS App已含未來1小時雨區預報**；與G01配方重疊。 |
| N16 霧事件 | **證實（→H06）** | CODiS能見度逐時欄位存在；臺北2024有效值僅約1,830筆（21%）；官方僅濃霧特報無定點預報值；三篇前作為數值預測，事件層（散霧時刻＋復發）可測。 |
| N17 陣風 | 備案 | F-D0047-093鄉鎮預報含陣風（文件層）；自家風向校正與G01同構；學期內無颱風則極端值未驗。 |
| N19 眼鏡起霧 | 推翻 | 公開起霧標籤完全不存在（僅物理文獻Laroche 2018）；原卡自認不收私人真值即不成立。 |
| N22 最大浪 | 備案 | 浮標浪高歷史1997起（站表證實）；**官方近海海象預報72h/17海域營運中**＋GRU/VMD-LSTM論文；差異僅剩事件校準，規則3風險高。 |
| N23 近岸水溫 | 有條件（→H12） | 潮位站海溫1946起、浮標1997起（站表）；個人點位校正真值須自建20–40筆；前作2024兩篇海溫預測；校正層與G01配方同構（明記）。 |
| N24 安靜通話 | 有條件（→H13） | 嘉義dataset/52435 CSV重抓15,634 bytes**樣本已讀**（24小時欄）；僅監測日非連續、僅嘉義市；NYCU GRU前作；家庭安靜窗自建。 |
| N25 景點恢復 | **證實（→H05）** | dataset/8116 CSV Range 206實讀（月報、2012起、陽明山2012-01=12,187）；[觀光放大鏡](https://tourismlens.dream-coders.com/method/)為量測前作；斷點後季節性保留比較（MASE＋恢復月數）未見同作。 |
| N26 集雨桶 | 推翻 | 入桶量標籤公開不存在；建研所智慧雨水貯集＋AI雨桶綜述已做滿規劃/操作層。 |
| N27 車內溫度 | 推翻 | 車內溫度＋遮蔭條件訓練集查無；PLOS 2022已實測環境分類；自家需探頭2–4週。 |
| N29 告示時間 | 有條件（→H11） | TaiwanVQA時間子集**抽樣400筆僅11筆（2.75%）**，估約55題僅夠評估集；成對真值自建；opening_hours.js規則解析成熟（基線強）。 |
| N38 木作刮痕 | 有條件（→H14） | MVTec wood.tar.xz HEAD 200、498,057,680 bytes、XZ魔數驗證；修補前後配對標籤公開不存在；[Zenodo木塗層缺陷集](https://zenodo.org/records/15679291)＋PatchCore前作。 |
| N39 燈下配色 | 有條件（→H15） | [Cube++](https://zenodo.org/records/4153431) 2,113,441,199 bytes CC BY 4.0、標註JSON實讀；刺繡App（CIEDE2000）與GET!Threads前作完整覆蓋拍色選線；差異僅跨燈排名穩定性。 |
| N40 合奏聲部 | 有條件（→H16） | ARME duet onset首值0.17415**實讀**；授權檔為LICENSE.md（CC BY-NC-SA）；Spleeter/URMP前作；家庭弦樂前提稀有。 |
| N44 活動改期 | 淘汰 | 主任務標籤全自建；Temporal Conflict QA/TimelyRAG前作已到基準級；DRCD第4題。 |
| N48/N49 地址 | 有條件（→H09，合併一題） | [donma路名JSON](https://github.com/donma/TaiwanAddressCityAreaRoadChineseEnglishJSON) MIT、2026-09更新、樣本已讀；Zipkit已做逐級選擇；與G46追問機制重疊→以同名路錯併為主軸。 |
| N50 罕見字 | 有條件（→H10） | [全字庫data.gov.tw/5961](https://data.gov.tw/dataset/5961)（OGDL/OFL、2026-08更新）＋TCSynth（Apache-2.0）；STAR/FaRE零樣本前作強→定位工程評估。 |

## 三、TW短名單重驗

- **TW02 證實（→H07）**：TaigiSpeech train 1,600行/143,000 bytes、val 519行5人、test 960行6人；8意圖全部重現；p001_0001_1_tw.wav RIFF/48kHz檔頭實讀；四個前作連結（TaigiSpeech論文、ZP-KWS、Google個人化關鍵詞、PoPETs）全部200。
- **TW03 部分證實（→H08）**：AQX_P_15頁面實讀（31欄、531月份檔、每日更新）；API v2需金鑰；「2025/01、79站、41,077行」月檔樣本沿用舊快照未重現；MDPI台灣AQI預測論文證實、AGU論文僅DOI存在（內容403未讀）。

## 四、開放式探勘

- **候選三（→H04）**：教育部[校別統計](https://stats.moe.gov.tw/files/detail/114/114_basec.xlsx)實測200（490KB）、95–114學年約30檔/年；官方《學生數預測報告》只做總量；g0v廢校盤點佐證（未驗證原文）。
- **候選一（菜價時機）**：農業部[交易行情API](https://data.moa.gov.tw/api/v1/AgriProductsTransType/)當日值已讀（欄位：均價/交易量/市場）；**非會員僅第一頁**、歷史回溯需會員或AMIS；政大蔬果價格預測論文為前作；構想（批發→自家零售轉換校正）**併入TW01筆記討論**。
- **候選二（臺北1999派工）**：[dataset/121414](https://data.gov.tw/dataset/121414)逐月CSV 104年起、2026-08實案列已讀；無結案時間欄位；NYC 311與顏晟伍為前作；**因偏公共事務、與已拒W06同源，列備案**。
- 淘汰線索：提點子（無開放資料）、潮汐（觀測30天窗＋App多）、翡翠水庫（資料優但[乾旱預測](http://www.ai.tku.edu.tw/)飽和）、類流感（[疾管署流感預報站](https://at.cdc.gov.tw/)已上線——G批備案A4改判淘汰）、實價/落點/負載（前作密度，推測級）。
- 未完成線索（下輪可續查）：營業稅籍登記→街區機能變化、動物園逐日入園、河川水質長時序、村里年齡結構月報。

## 五、工具與未驗證項

- 本日data.gov.tw搜尋頁再回500、CKAN API 404、stat.gov.tw Cloudflare、WebSearch間續限流——影響範圍均已在各節標明。
- 未驗證：H02海灘CSV欄位與超標筆數（需金鑰）、H03音檔批次下載與客委會授權、H01官方113–115年指標檔新址與授權條款、H05月檔完整重抓（平臺不穩）、探勘線索四條。
- 未訓練任何模型、未採集家庭資料、未建立應用程式；Sol級覆核仍因無對應子代理/技能未執行。
