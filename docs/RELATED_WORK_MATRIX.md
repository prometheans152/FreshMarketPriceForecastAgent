# TW01既有作品查核矩陣

建立日期：2026-10-03（T04補查輪）。本表彙整[前輪重查](research/TW01_RELATED_WORK_RECHECK.md)已確認作品與本輪新增查核，用於對照本案可測差異主張：

> 使用者在蔬果行現場輸入今天單品店價（上週同店同規格價選填），預測從今天起7／14天的漲跌，並以真實同店到期價驗證A（無上週價）／B（有上週價）兩種輸入的增益。

查核方式：WebSearch、GitHub API檢索、Google Play商店頁、官方文章與PDF下載。連結均來自實際查詢結果；查不到的方向如實標「本輪未查到」。「讀取狀態」區分只讀摘要／商店文案／repo頁面／全文；未安裝App、未執行他人程式碼、未重現任何前作結果。

## 一、前輪已查作品（摘錄，詳見重查筆記）

| 名稱／連結 | 類型 | 資料 | 預測目標 | 使用者輸入現場店價 | 驗證同店增益 | 相同處 | 不同處 | 讀取狀態 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [陳泯宏，臺大2024，國產大宗蔬菜價格預測模型之比較](https://tdr.lib.ntu.edu.tw/handle/123456789/92775) | 論文 | 公開批發2012–2022 | 批發價格與方向（ARIMA/ETS/TDNN/LSTM） | 否 | 否 | 菜價預測、方向正確率 | 批發非零售店價；歷史輸入非未來期限 | 書目與摘要已讀，全文未取得（2029解禁） |
| [李岱鑫，清華2015，高麗菜批發價預測](https://etd.lib.nycu.edu.tw/cgi-bin/gs32/hugsweb.cgi?o=dnthucdr&s=id%3D%22GH02102077503%22.&searchmode=basic) | 論文 | 公開＋中盤商私人紀錄66週 | 下一週批發價 | 否 | 有（使用／不使用私人資料比較，非同店零售） | 公開＋私人、一週預測、增益比較 | 私人資料是中盤商紀錄非消費者現場報價；目標批發 | 中英文摘要與目次已讀，全文未取得 |
| [林沂臻，中山醫大2017，HHT菜價預測](https://ndltd.ncl.edu.tw/cgi-bin/gs32/gsweb.cgi/login?o=dnclcdr&s=id%3D%22105CSMU5585004%22.&searchmode=basic) | 論文 | 高雄公有零售市場均價 | 零售趨勢與價格區間 | 否 | 否 | 零售菜價預測 | 市場均價非單店；無7／14天期限與到期驗證 | 索引摘要已讀，全文未取得 |
| [白菜即時開發者網站](https://cabbagelive.com/)／[Google Play](https://play.google.com/store/apps/details?id=com.flux6lab.cabbagelive&hl=zh-TW) | 產品 | 批發行情（12市場） | 即時行情＋AI中長期走勢預測＋批發零售換算＋採購建議 | 否（本輪商店文案未見店價輸入） | 否 | 手機菜價、AI走勢、零售換算 | 未見明確7／14天期限、店價輸入與同店到期驗證 | 前輪網站已讀；本輪Play商店文案已讀（2026-08-31更新、下載1萬+、評分4.7），未安裝實測 |
| [Cha.tw蔬菜價格](https://cha.tw/market-price/vegetable) | 產品 | 批發 | 批發×2.5建議零售、歷史漲跌 | 否 | 否 | 單位換算、倍率零售 | 無單店未來實價預測 | 公開頁已讀（前輪） |
| [林文雄，桃園農改場，甘藍價格變動分析](https://www.tydares.gov.tw/redirect_files.php?file_name=DLYJURyOj1niqesb2QWGEqual2fAolih7WCoFqL5kmaUolFINS&id=18518) | 官方研究 | 農場／批發／零售 | 零售迴歸式 | 否 | 否 | 批發對應零售關係 | 迴歸配適非當下可用的期限預報 | 索引摘要已讀，PDF全文辨識失敗 |
| [臺北市主計處2015，颱風對蔬菜價格影響](https://www-ws.gov.taipei/Download.ashx?icon=.pdf&n=MTA0MDLporHpoqjlsI3oh7rljJfluILolKzoj5zlg7nmoLzlvbHpn7%2FliIbmnpAucGRm&u=LzAwMS9VcGxvYWQvMzY3L3JlbGZpbGUvNDUwMDAvNzY2MjU4NC8yNmYwZTlmNC1jNjIyLTQ2YmMtYTFhYi1hMDc4MWUxMTcxZGYucGRm) | 官方研究 | 批發變動＋每旬CPI | 以批發推估零售變動 | 否 | 否 | 零售預警構想 | 代理指標非店家實價 | 官方清單與PDF索引結論已讀，全文未讀 |

## 二、本輪（2026-10-03）新增查核：GitHub開源

| 名稱／連結 | 類型 | 資料 | 預測目標 | 使用者輸入現場店價 | 驗證同店增益 | 相同處 | 不同處 | 讀取狀態 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [kristenchan/agricultural-product](https://github.com/kristenchan/agricultural-product)（2020-10） | 開源（學生專題形態） | 批發市場交易行情系統 | 宣稱預測蔬菜價格、產銷決策輔助；期限與模型未在README說明 | 否 | 否 | 台灣菜價預測開源、公開批發資料 | 批發非店價；僅README＋單一notebook，無期限設定與驗證 | repo頁與README已讀；notebook內容未逐格讀 |
| [coolthor/tw-vegprice](https://github.com/coolthor/tw-vegprice)（2026-03更新） | 開源 | 批發行情 | 即時追蹤顯示，未見預測功能 | 否 | 否 | 台灣菜價工具、公開行情 | 查價非預測 | repo頁已讀（無README細節），未執行 |
| [YuehChun/NCHU-Data-Mining-Project](https://github.com/YuehChun/NCHU-Data-Mining-Project)（2025-05更新） | 開源（課程專題） | 氣候資料＋台灣蔬菜價格（Scrapy爬取、MySQL） | 氣候欄位對菜價探勘分析；含決策樹跡證（D3Tree.py、tree.dot）；未見7／14天期限 | 否 | 否 | 氣候×菜價課程實作 | 探勘分析非消費者期限預測；無店價輸入 | repo頁與README已讀；程式碼未逐檔讀 |
| [sovmedcare/hackthon-farm-stats-tw](https://github.com/sovmedcare/hackthon-farm-stats-tw) | 開源（hackathon） | 果菜市場價格 | 全台果菜市場價格查詢 | 否 | 否 | 市場行情查詢工具 | 查詢非預測 | 僅GitHub API描述已讀，未入repo細讀 |

其他「菜價」關鍵字檢索結果（[kaojarher/Veg_price-](https://github.com/kaojarher/Veg_price-)查菜價工具、[Snershen-Practice/2023-06-price](https://github.com/Snershen-Practice/2023-06-price)蔬菜比價網、[BoyiLee-l/FarmerGood](https://github.com/BoyiLee-l/FarmerGood)菜價即時通）：均為查價／比價工具，描述中未見預測功能與店價輸入，僅讀API描述。檢索「高麗菜價格」「農產品價格預測」「農產品＋預測」等組合：GitHub API回傳0筆或無相關，**本輪未查到完整重現本案組合的開源專案**。

## 三、本輪新增查核：台灣學術論文／研討會

| 名稱／連結 | 類型 | 資料 | 預測目標 | 使用者輸入現場店價 | 驗證同店增益 | 相同處 | 不同處 | 讀取狀態 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 洪士育，[基於發掘氣候資料來預測蔬菜價格](https://ndltd.ncl.edu.tw/handle/usjrfz)，臺北科技大學 | 論文 | 氣候資料＋蔬菜價格 | 以資料發掘技術從氣候預測蔬菜價格，目標協助政府改善產銷 | 否 | 否 | 氣候→菜價預測 | 政策端用途；非消費者現場輸入與期限預測 | 僅搜尋結果摘要片段與第三方索引（zhupiter）已讀；NDLTD遇驗證碼，書目頁與全文未取得，年份未確認 |
| 陳澤維，[臺灣蔬果批發市場價格預測模型](https://thesis.lib.nccu.edu.tw)，政大碩士（引用資料記2017；前輪記錄之政大批發模型摘要ah.lib item_id=136134可能為同篇，年份表述待統一） | 論文 | 公開電子資料（批發行情等） | 程式自動化預估各品項蔬果未來每日平均批發價格 | 否 | 否 | 公開資料自動化批發預測 | 批發非零售店價；無店價輸入與A／B增益 | 僅論文系統摘要片段已讀，全文未取得 |
| [臺灣水果價格之預測─機器學習之應用](https://www.airitilibrary.com/Article/Detail/U0001-0355230911317025)（臺大碩士；[TDR典藏](https://tdr.lib.ntu.edu.tw/jspui/handle/123456789/92161)） | 論文 | 釋迦、鳳梨、芒果；北中南三市場；2002–2021價格 | LSTM價格預測（水果） | 否 | 否 | 台灣農產價格LSTM預測 | 水果非蔬菜；批發市場價格；無店價輸入 | 僅搜尋結果摘要片段已讀；Airiti／TDR頁面本輪開啟失敗，作者與年份未確認 |
| Yi-Wen Yeh（臺北大學），EcoSta 2019發表"search volume: An application of price forecast on vegetables"，[議程](https://www.cmstatistics.org) | 研討會 | 搜尋量資料＋蔬菜價格 | 以搜尋量輔助蔬菜價格預測 | 否 | 否 | 菜價預測、非傳統資料源 | 非消費者輸入情境 | 僅研討會節目摘要片段已讀，全文未查得 |

XGBoost×台灣零售蔬菜的組合：本輪搜尋僅命中非台灣的零售農產銷量預測文獻，**台灣零售蔬菜價格XGBoost論文本輪未查到**（未查到不代表不存在，NDLTD全文檢索受限於驗證碼）。

## 四、本輪新增查核：產品／App

| 名稱／連結 | 類型 | 資料 | 預測目標 | 使用者輸入現場店價 | 驗證同店增益 | 相同處 | 不同處 | 讀取狀態 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [農產分析](https://play.google.com/store/apps/details?id=com.bvc_dev_team.androidapp)（鹿中創客，2026-07-30更新） | App | 農糧署農產品交易行情 | **輸入購買價格→自動智能換算→與當日果菜市場行情對比→告知價差是否合理**；無未來預測、無AI預測宣稱 | **有（輸入自己買的價格比對當日行情）** | 否（僅當日價差對比） | 使用者輸入價格＋換算單位＋與行情比對；自稱「全台第一」價格分析 | 只比對當日，不預測7／14天後漲跌；無到期驗證；無模型訓練 | Google Play商店文案已讀；未安裝實測 |
| [白菜即時](https://play.google.com/store/apps/details?id=com.flux6lab.cabbagelive&hl=zh-TW)（flux6lab，2026-08-31更新，下載1萬+，評分4.7） | App | 12大批發市場行情 | 即時行情＋AI批發零售換算＋AI短中長期採購建議＋AI中長期走勢預測 | 否（文案未見） | 否 | 手機菜價AI、走勢預測、零售換算、採買建議 | 未見7／14天明確期限、店價輸入、同店到期驗證；模型與準確率未公開 | 前輪網站已讀＋本輪Play商店文案已讀；未安裝實測 |
| [i農市－蔬菜交易行情](https://play.google.com/store/apps/details?id=com.jmistudio.agriproductstransinfo.vegetable)（J米資訊工作室，2025-08-29更新） | App | 農民市場蔬菜交易行情 | 即時查詢，無預測宣稱 | 否 | 否 | 菜價查詢工具 | 查詢非預測 | 商店文案已讀；未安裝 |
| [北農蔬果行情查詢](https://play.google.com/store/apps/details?id=tpmc.com.tw.orderdealsapp)（北農官方，下載5K+） | App | 北農批發行情 | 行情查詢與預約交易資訊 | 否 | 否 | 官方批發行情App | 面向拍賣員／承銷人；無零售預測 | 商店文案（搜尋摘要）已讀 |
| [台灣市場交易行情－農漁禽](https://play.google.com/store/apps/details?id=idv.shuhao.app.ag2&hl=gu) | App | 批發市場行情 | 市場趨勢查詢（選市場／類別／單位） | 否 | 否 | 行情趨勢查詢 | 查詢非預測 | 僅搜尋摘要已讀 |
| [悠由數據DataYoo](https://datayoo.com.tw)（悠由金錢報AGinteller） | 商用服務 | 衛星／土地／大數據 | 企業端農產品價格資訊與預測工具（500+作物產期產量為另一產品） | 否 | 否 | 台灣農產AI預測商業服務 | B2B企業導向；批零售與預測天數未公開；無消費者店價輸入 | 官網已讀；產品內部資訊未取得 |

## 五、本輪新增查核：官方研究與平台

| 名稱／連結 | 類型 | 資料 | 預測目標 | 使用者輸入現場店價 | 驗證同店增益 | 相同處 | 不同處 | 讀取狀態 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [農業大數據平台](https://www.agriharvest.tw/archives/12897)（農委會與財政部財政資訊中心合作；農傳媒2018-05-06報導） | 官方平台 | 104–106年29億筆電子發票＋批發行情等 | 15項農產品（甘藍、香蕉等，含8項蔬菜）之零售價格估計與預測模型、颱風路徑菜價模擬、輿情分析 | 否 | 否（以網路查價對照電子發票價格，非同店到期驗證） | **零售價格預測已有官方大資料版本**；品項與本案候選（甘藍、青江菜、絲瓜）重疊 | 電子發票通路段估計非單店真值；供內部決策；無消費者輸入與A／B增益比較；平台2018後現況未驗證 | 報導全文已讀；平台本身未登入驗證 |
| 農糧署115年度補助計畫公告：[結合生成式AI與預測式機器學習於農產品產銷決策支援架構之先導研究](https://www.afa.gov.tw/cht/index.php?act=download&ids=47334)（計畫編號115農科-4.4.1-糧-02） | 官方徵求 | 農業生產、區域、市場交易開放資料 | 評估主要農產品供需與價格預測模型＋產銷儀表板 | 否 | 否（徵件說明未見） | **官方正在推動「生成式AI＋預測式ML＋農產品價格」組合** | 產銷決策支援（生產端）非消費者現場店價輸入；無同店增益驗證設計 | 公告PDF已下載並全文已讀（本機data/recheck_t04/afa_ai_pilot.pdf）；屬徵件公告非成果報告 |

## 六、本輪新增查核：課程歷屆作品

- 已查到可連結課程專題：[NCHU-Data-Mining-Project](https://github.com/YuehChun/NCHU-Data-Mining-Project)（中興大學資料探勘課程，氣候×菜價，見第二節）。
- 以「期末專題＋菜價預測」「課程專案＋蔬菜價格」等多組關鍵字搜尋，其餘多為高中職課程計畫文件或不相關結果；**AIoT／資料分析課程的菜價期末完整作品本輪未查到其他可連結者**。GitHub上學生形態專案（kristenchan等）無法僅由repo確認是否為課程作業，標推測。

## 七、本案另測什麼（差異主張與尚無證據部分）

**查核範圍內未見完全相同做法；組成元件各自有前作，差異主張維持但範圍收斂如下。**

各元件的前作狀態：

1. 「使用者輸入自己買到的價格」：[農產分析](https://play.google.com/store/apps/details?id=com.bvc_dev_team.androidapp)App已有（輸入購買價→換算→比對當日行情→價差是否合理）。不能把「現場輸入價格」本身當差異。
2. 「零售菜價預測模型」：[農業大數據平台](https://www.agriharvest.tw/archives/12897)已用電子發票建15項農產品零售估計與預測模型，品項與本案候選重疊；[林沂臻2017](https://ndltd.ncl.edu.tw/cgi-bin/gs32/gsweb.cgi/login?o=dnclcdr&s=id%3D%22105CSMU5585004%22.&searchmode=basic)已做零售趨勢。不能把「預測零售菜價」本身當差異。
3. 「公開＋私人資料增益比較」：[李岱鑫2015](https://etd.lib.nycu.edu.tw/cgi-bin/gs32/hugsweb.cgi?o=dnthucdr&s=id%3D%22GH02102077503%22.&searchmode=basic)已做（私人紀錄進出模型的誤差比較）。不能把「比較有無私人資料」本身當差異。
4. 「手機AI菜價走勢」：[白菜即時](https://cabbagelive.com/)已宣稱中長期走勢預測與採購建議。不能把「手機＋AI走勢」本身當差異。

本案另測的具體組合（查核範圍內未見相同做法）：

- **以使用者當天在單一店家的現場報價為預測基準點**，預測「從使用者今天算起」固定日曆期限（t＋7／t＋14）的同店相對漲跌——前作要麼預測市場均價、要麼比對當日價差，未見以現場單筆報價為基準的期限預測。
- **上週同店同規格價選填的A／B兩模式**，且以**真實後續同店到期價**（非市場均價、非倍率換算）驗證B相對A的增益——查核範圍內未見此驗證設計；李岱鑫的增益比較對象是批發價且私人資料型態不同。

尚無證據、不能預先宣稱的部分：

- B模式增益是否存在、多大，本案尚無資料；單筆現價僅改尺度不保證改善方向判斷（見[重查筆記](research/TW01_RELATED_WORK_RECHECK.md)數學討論）。
- 農業大數據平台2018年後是否持續更新、其模型對2026的適用性未驗證；官方115年度先導研究屬徵件公告，無成果可比。
- NDLTD全文、中國與其他語言文獻、App安裝後實測功能，本輪均未完成；「未查到」僅指本輪檢索範圍。

結論用語規範：只寫「查核範圍內未見相同做法」，不宣稱全球首次；若後續查到完全相同做法，依[TASKS T04](../TASKS.md)記錄並縮小或修正設計。
