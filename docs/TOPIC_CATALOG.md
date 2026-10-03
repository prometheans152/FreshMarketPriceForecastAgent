# 期末專題候選題目清單

資料快照日期：2026-10-03。狀態：**尚未選題**。

> **歷史清單，已由新篩選條件取代推薦用途。** 使用者於 2026-10-03 要求實際查重、剔除找不到實質差異者，且以台灣資料為主。本檔保留原 1–50 編號及早期判讀供追溯；其中高／中評語與星號不是現行推薦。後續選題請看 [台灣資料短名單](TAIWAN_TOPIC_SHORTLIST.md)及其實查來源。London 用電、ASHRAE 等舊來源尚不符合本次台灣適用門檻。

本檔保存對話中提出的 50 個候選題目，供選題及後續查核使用。編號 1–50 是固定識別碼；修改題目內容時應保留編號，避免選題討論失去對照。

選題條件：必須有公開資料可訓練模型；優先考慮能套用個人或家庭資料的題目。若不使用個人或家庭資料，需以具體情境、資料條件或評估方式說明差異。使用者目前沒有指定想改善的個人問題。

**證據界線**：以下資料來源、標籤與限制整理自前一輪對話的研究結果。本檔的建立未重新下載資料或再次查核各網頁。網址可用性、授權、下載方式與標籤內容，需在選定題目後重新確認。尤其第 14、18、30 題已有載點或外站可用性限制，不能把它們當成已保證取得的完整訓練資料。

## 重複風險與差異化的判讀

- **高**：核心辨識／預測任務已有成熟研究，需要具體的差異化實驗。
- **中**：已有相關研究，但較容易用特定情境、資料條件與評估方式縮出特色。
- 風險是初步判斷；差異化方向是提案，**尚未證明原創性**。
- 加入自家資料時，應比較校正前後，並保留另一批資料測試；上傳個人資料本身不代表完成差異化。
- 「★」是優先深入評估的建議，沒有代表使用者已選定。

課程查重目前只完成部分檢視：課程資料出現手寫數字辨識、垃圾郵件分類；歷屆清單有「食物」「Farm Agent」「智慧水產」等方向。部分作品頁只有題名或簡短描述，**不足以完成歷屆作品的重複性審核**，也不能判定與下列某題完全相同。

課程來源：[課程資料](https://app.notion.com/p/O-AIoT-DA-2026-9-30-67148cb998b3405b91b83cc995dd0588)、[歷屆專題清單](https://app.notion.com/p/Final-Project-2-2d3c47529811800aa16aebb82d3dc13b)。本檔不將候選題目或網站中的示範當成老師指定的必做題目。

## 1–12：家庭能源與室內環境

| 編號 | 題目 | 公開資料／可訓練目標 | 重複風險、差異與關鍵限制 |
|---|---|---|---|
| **1 ★** | **下月家庭用電與下期電費預測** | [London SmartMeter](https://data.london.gov.uk/dataset/smartmeter-energy-consumption-data-in-london-households-vqm0d)：多戶半小時用電 | **高**。比較公共模型加入少量自家用電後的改善；先預測度數，再依台灣計費規則換算。只有幾張帳單時，校正能力有限。 |
| 2 | 從全屋用電推估各家電耗電占比 | [AMPds2](https://pmc.ncbi.nlm.nih.gov/articles/PMC4896126/)：全屋與家電分表功率 | **高**，已有 NILM 研究。限定最關心的兩三種家電，測少量自家分表資料能改善多少；需相容的取樣頻率。 |
| 3 | 熱水器／熱泵異常運轉期間提示 | [NIST 住宅資料](https://pages.nist.gov/netzero/data.html)：設備感測與官方故障日期 | **中**。區分設備異常、感測錯值與資料中斷；故障事件少，只適合個案研究。 |
| 4 | 屋頂太陽能發電量預報 | [OPSD Household Data](https://data.open-power-system-data.org/household_data/2020-04-15/)：住宅太陽能發電 | **高**。加入自家容量、遮蔭時段校正，分晴陰天測試；國外資料需要本地驗證。 |
| 5 | 電動車本次充電剩餘用電估計 | [OPSD](https://data.open-power-system-data.org/household_data/2020-04-15/)：實測電動車充電通道 | **高**。學習個人充電功率與停止習慣；資料沒有電池 SOC，不能直接估電池健康。 |
| 6 | 夜間持續用水異常提醒 | [AMPds2](https://pmc.ncbi.nlm.nih.gov/articles/PMC4896126/)：分鐘級水量與流率 | **高**。學習自家夜間基線，以使用者回饋降低誤報；沒有完整漏水標籤，只能先做用量異常。 |
| 7 | 家庭瓦斯消耗習慣與異常時段分析 | [AMPds2](https://pmc.ncbi.nlm.nih.gov/articles/PMC4896126/)：瓦斯用量與氣象 | **高**。加入自家使用時段，辨識偏離習慣的消耗；不是漏氣偵測，台灣與加拿大用途也不同。 |
| 8 | 從總水量推估熱水使用比例 | [AMPds2](https://pmc.ncbi.nlm.nih.gov/articles/PMC4896126/)：全屋水量與熱水分表 | **中**。比較加入少量自家分表資料前後的誤差；不能把熱水量直接當洗澡次數。 |
| **9 ★** | **不使用攝影機的房間有人／無人辨識** | [UCI Occupancy](https://archive.ics.uci.edu/dataset/357/occupancy+detection)：環境感測與占用標籤 | **高**。比較少感測器方案、判斷延遲與自家校正；原資料是辦公室，家庭環境需再測。 |
| 10 | 室內 CO₂ 升高的提前提醒 | [SML2010](https://archive.ics.uci.edu/dataset/274/sml2010)：室內 CO₂ 時序 | **中**。比較提前預測與當下超標提醒，加入自家房間資料；需要真正的 CO₂ 感測器。 |
| **11 ★** | **學習個人「想更涼／維持／更暖」的舒適偏好** | [ASHRAE DB II](https://github.com/CenterForTheBuiltEnvironment/ashrae-db-II)：環境條件與真人偏好回饋 | **高**。用本人或家人的每日少量回饋校正，測不同成員的改善；不能直接宣稱省電或找到最佳冷氣設定。 |
| 12 | 房間升降溫趨勢與到達目標溫度時間預估 | [SML2010](https://archive.ics.uci.edu/dataset/274/sml2010)：室溫、外溫、日照等 | **高**。測自家房間校正，以及門窗狀態改變後的失準；公開資料沒有最佳控制動作標籤。 |

## 13–24：食品、植物與寵物影像

食物、農業題要額外對照老師的歷屆作品；下面的分類、定位、分割是不同訓練目標。

| 編號 | 題目 | 公開資料／可訓練目標 | 重複風險、差異與關鍵限制 |
|---|---|---|---|
| 13 | 家常菜照片自動分類與飲食相簿 | [Food-101](https://data.vision.ee.ethz.ch/cvl/datasets_extra/food-101/)：菜餚類別 | **高**。選資料包含的常吃菜，加入自家照片，測陌生菜的拒答能力；沒有份量或熱量標籤。 |
| 14 | 便當照片中的可見食材分割 | [FoodSeg103](https://github.com/LARC-CMU-SMU/FoodSeg103-Benchmark-v1)：食材像素標籤 | **高**。測家中便當、遮擋與混合食材；需手工畫遮罩。前輪研究中官方載點失敗，[鏡像可讀](https://huggingface.co/datasets/EduardoPacheco/FoodSeg103)。 |
| 15 | 家庭採買水果與蔬菜種類辨識 | [Fruits-360](https://github.com/fruits-360/fruits-360-100x100)：水果蔬菜種類 | **高**。比較白背景與自家桌面背景，測不同實體水果；種類標籤不能拿來判新鮮度。 |
| 16 | 水果可見腐敗外觀提醒 | [Mendeley 水果資料](https://data.mendeley.com/datasets/bdd69gyhv8/1)：fresh／rotten 外觀標籤 | **高**。測冰箱、水果盤環境及漏判腐敗的比例；只能判可見外觀，不能判食用安全或保存天數。 |
| **17 ★** | **家庭食品照片登錄與不確定商品分類** | [Grocery Store Dataset](https://github.com/marcusklasson/GroceryStoreDataset)：商品細類與粗類 | **高**。不確定時退回大類，測自家商品需要人工修正幾次；台灣品牌需新增標籤，資料沒有庫存或有效期限。 |
| 18 | 地面散落垃圾定位與輪廓分割 | [TACO](https://github.com/pedropro/TACO)：垃圾類別、位置與輪廓 | **高**。測自家瓷磚、地毯、小垃圾及非垃圾誤報；需畫框／輪廓，部分外站圖片可能失效。 |
| 19 | 單片陽台作物葉片病徵分類 | [PlantDoc](https://github.com/pratikkayal/PlantDoc-Dataset)：作物與病徵類別 | **高**。選自己種的一種作物，測逆光、模糊與本地校正；自家病徵的可信標籤較難取得。 |
| 20 | 多片葉子照片中的病徵葉定位 | [PlantDoc 偵測資料](https://github.com/pratikkayal/PlantDoc-Object-Detection-Dataset)：葉片位置與類別 | **高**。測重疊葉、小葉的漏判；需逐葉標註，框的位置不能直接代表感染面積。 |
| 21 | 陽台與庭園花種相簿標記 | [Flowers102](https://www.robots.ox.ac.uk/~vgg/data/flowers/102/)：花種標籤 | **高**。測自家花朵在不同光線、距離下的辨識；自家花種須在資料類別內。 |
| 22 | 寵物品種分類與未知品種拒答 | [Oxford-IIIT Pet](https://www.robots.ox.ac.uk/~vgg/data/pets/)：貓狗品種 | **高**。加入混種或未知品種的拒答評估；只有自己的一隻寵物，無法驗證整套品種辨識。 |
| 23 | 寵物毛髮輪廓自動去背 | [Oxford-IIIT Pet](https://www.robots.ox.ac.uk/~vgg/data/pets/)：寵物像素輪廓 | **高**。測毛色與背景相近、暗處的邊界效果；自家精細輪廓標註較花時間。 |
| 24 | 家中寵物關節位置與動作軌跡視覺化 | [AP-10K](https://github.com/AlexTheBad/AP-10K)：動物關鍵點 | **高**。測自家寵物、遮擋與影片延遲；需要標記關節，資料沒有情緒或疼痛標籤。 |

## 25–37：個人活動、聲音、文字與娛樂

| 編號 | 題目 | 公開資料／可訓練目標 | 重複風險、差異與關鍵限制 |
|---|---|---|---|
| 25 | 手機自動記錄走路、坐著與上下樓時間 | [UCI HAR](https://archive.ics.uci.edu/dataset/240/human+activity+recognition+using+smartphones)：六種活動 | **高**。比較加入本人短期資料後的改善；手機位置、取樣率要相容。 |
| 26 | 智慧手錶辨識刷牙、打字、摺衣等活動 | [WISDM](https://archive.ics.uci.edu/dataset/507/wisdm+smartphone+and+smartwatch+activity+and+biometrics+dataset)：日常活動 | **高**。測不同家人、手腕與手錶的轉移效果；需能取得原始感測資料。 |
| 27 | 運動種類與各種運動時長紀錄 | [Daily and Sports Activities](https://archive.ics.uci.edu/dataset/256/daily)：19 種活動 | **高**。比較減少感測器後的準確度；原資料使用五個感測器，適合先做公開資料研究。 |
| 28 | 用門磁與動作感測建立家庭活動時間軸 | [CASAS](https://casas.wsu.edu/datasets/index)：家庭感測事件與活動標籤 | **高**。測不同房屋配置與少量家庭校正；自家應用需要感測器及活動標記。 |
| **29 ★** | **家中噪音來源日誌：吸塵器、洗衣機、敲門等** | [ESC-50](https://github.com/karolpiczak/ESC-50)：環境聲音類別 | **高**。加入自家聲音，測不同房間、距離、手機的改善；先做短音訊分類，不直接假設能處理重疊聲音。 |
| 30 | 家務聲音事件時間軸：水聲、煎炒、吸塵 | [DESED](https://github.com/turpaultn/DESED)：聲音事件及部分起訖標籤 | **高**。測多種聲音同時出現時的漏判與時間誤差；部分原始音訊取決於外站可用性。 |
| 31 | 設備異音辨識與換設備後的誤報校正 | [MIMII](https://zenodo.org/records/3384388)：機械正常／異常聲音 | **高**。測新設備、不同背景噪音與少量正常聲音校正；工業機械不能直接等同家電。 |
| 32 | 適應家人口音與背景聲的短語音指令辨識 | [Speech Commands](https://arxiv.org/abs/1804.03209)：短單字指令 | **高**。測家人、遠距離與雜音下的誤觸發；公開資料主要是英文，中文指令需另採標註。 |
| 33 | 家庭錄音與線上會議語音降噪 | [VoiceBank＋DEMAND](https://datashare.ed.ac.uk/items/6ed35425-bf14-4d2b-93a1-0a4984952757)：配對乾淨／含噪語音 | **高**。加入家人語音與家中噪聲，測清晰度及中文語音保真；訓練與評估成本較高。 |
| 34 | 家庭手寫數字紀錄辨識與模糊字拒答 | [EMNIST](https://www.nist.gov/itl/products-and-services/emnist-dataset)：手寫數字 | **高，課程已有相近範例**。限定家人的手寫紀錄，測不同筆跡與不確定字的拒答；不是直接辨識整張帳單。 |
| 35 | 垃圾簡訊分類與重要訊息誤攔截評估 | [SMS Spam Collection](https://archive.ics.uci.edu/dataset/228/sms+spam+collection)：spam／ham | **高，與課程垃圾郵件方向相近**。重點測誤攔截與個人回饋校正；英文資料不能直接證明台灣中文效果。 |
| 36 | 商品評論正負面歸類與個人修正學習 | [Sentiment Labelled Sentences](https://archive.ics.uci.edu/dataset/331/sentiment+labelled+sentences)：正／負面句子 | **高**。測跨商品類型、反諷與使用者修正；資料主要是英文，沒有優缺點細項標籤。 |
| 37 | 全家一起看電影的折衷推薦 | [MovieLens](https://grouplens.org/datasets/movielens/1m/)：個人電影評分 | **高**。加入家人少量評分，比較平均滿意度與最不滿意成員的分數；電影需在資料範圍內。 |

## 38–50：公共環境、交通、設備與學習

這組多數可以先用公開資料完成；特色可放在特定路段、測站、失效情境或評估方式。

| 編號 | 題目 | 公開資料／可訓練目標 | 重複風險、差異與關鍵限制 |
|---|---|---|---|
| **38 ★** | **住家周邊 PM2.5 未來 1～6 小時預測** | [環境部 AQX_P_15](https://data.moenv.gov.tw/dataset/detail/aqx_p_15)：台灣測站歷史濃度 | **高**。固定鄰近測站，特別測濃度突升與預測區間；戶外測站不能直接代表室內。 |
| **39 ★** | **固定通勤國道路段的旅行時間與延誤區間** | [高公局 M04A](https://tisvcloud.freeway.gov.tw/history/TDCS/M04A/)：五分鐘站間旅行時間 | **高**。聚焦自己的路段，測尖峰漏估延誤與區間可靠性；缺資料的零值要排除。 |
| 40 | 共享單車每小時需求與雨天尖峰預測 | [UCI Bike Sharing](https://archive.ics.uci.edu/dataset/275/bike+sharing+dataset)：每小時租借總量 | **高**。比較雨天、假日、通勤時段誤差；資料是華盛頓全系統，不能推稱某個 YouBike 站有車。 |
| 41 | 空品感測站斷訊後的濃度補值 | [Beijing Multi-Site Air Quality](https://archive.ics.uci.edu/dataset/501/beijing+multi+site+air+quality+data)：多站歷史濃度 | **中**。測連續斷訊、整站失聯與污染突升；用有真值的資料遮蔽測試。 |
| 42 | 低價空氣感測器的濃度校準與漂移提示 | [UCI Air Quality](https://archive.ics.uci.edu/dataset/360/air+quality)：感測響應與參考儀器值 | **高**。只用前幾週校正，測後續漂移；不同型號自家感測器仍需要同址參考量測。 |
| 43 | 水質感測資料異常事件偵測 | [GECCO 2017](https://zenodo.org/records/3884465)：水質感測與事件標籤 | **中；歷屆有水產監控相鄰方向**。比較每週誤報與偵測延遲；事件標籤不代表飲用安全。 |
| 44 | 小流域隔日高流量事件提醒 | [CAMELS](https://zenodo.org/records/15529996)：氣象與河川流量 | **中**。測未見過的流域及高流量漏報；日資料不能支援分鐘級洪水預警。 |
| 45 | 戶外風速突升的短期提醒 | [Jena 天氣資料](https://www.tensorflow.org/tutorials/structured_data/time_series)：風速、最大風速等 | **高**。針對晾衣、戶外活動測誤報成本；國外天氣資料需本地驗證，事件門檻是專題自行定義。 |
| 46 | 低光、模糊情境的道路標誌辨識 | [GTSRB](https://docs.pytorch.org/vision/stable/generated/torchvision.datasets.GTSRB.html)：交通標誌類別 | **高**。測模糊、逆光及不確定時拒答；德國標誌不等於台灣標誌全集。 |
| 47 | 住家周邊路面裂縫與坑洞定位 | [RDD2022](https://github.com/sekilab/RoadDamageDetector)：路損種類與位置 | **高**。跨國測試，再標註固定住家路段；辨識位置不能直接代表工程危險程度。 |
| 48 | 不同負載下的軸承振動故障分類 | [CWRU](https://engineering.case.edu/bearingdatacenter/download-data-file)：振動與故障類別 | **高**。整個負載條件留作測試，比較低取樣率效果；人工故障不能直接代表自然老化。 |
| 49 | 線上課程前四週的完成風險提醒 | [OULAD](https://archive.ics.uci.edu/dataset/349/open+university+learning+analytics+dataset)：學習事件、作業、最終結果 | **高**。只使用當時已知資料，跨課程測試；預測準確不代表提醒能改善成績。 |
| 50 | 依答題歷史估計下一題答對機率 | [EdNet](https://github.com/riiid/ednet)：答題紀錄與正解 | **高**。比較新使用者只有少量答題時的效果，可加入自己的練習紀錄；資料是 TOEIC，不能直接套到數學。 |

## 建議先評估的編號

**1、9、11、17、29、38、39**。

第 1 題電費預測有公開用電資料可訓練，但需先預測用電度數，再依本地計費規則換算。第 11 題舒適偏好與第 29 題家中聲音較容易收集個人資料；第 38 題空品與第 39 題國道通勤有台灣歷史資料。這些是前輪對話的初步建議，尚未取代使用者選題。

選出候選後，下一步應逐題確認資料取得與授權、實際標籤、個人資料採集負擔、代表研究及歷屆作品內容，再決定最小可行範圍與評估方式。
