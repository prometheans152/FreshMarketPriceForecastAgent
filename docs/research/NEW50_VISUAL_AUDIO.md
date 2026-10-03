# 新一輪候選：影像、物理聲音、寵物量測與合奏

查核日期：2026-10-03。分支識別 V01–V15，正式新 50 題編號由整合者指派。這 15 題是可供進一步選擇的**條件候選**；有公開學習標籤及具體差異實驗，不代表已訓練、資料全量下載、自家有效或全球首次。沒有新增程式、登入、條款同意、裝置控制或採集家庭資料。

已讀工作區入口、決策與 aiot-topic-review 技能，承接 TW_FOOD_VISUAL、TW_TEXT_AUDIO、TW_MORE_PERSONAL 的排除紀錄。此次不重列菜籃價格、臺語指令、PM 可靠性、均一數學、業餘羽球，亦不重列普通菜色分類、鳥叫日誌、家庭多人筆跡、錄音品質、寵物臉尋寵。

臺灣實拍來源是 V01/V02 的 TaiwanVQA。其他題使用可對應的物理標籤：克重、畫素／例項遮罩、流量、聲音事件時間、同種動物關鍵點、色度或樂器音符／踏板時間。**這只證明學習目標在臺灣也有定義，不證明外國模型在家庭一定準確**；各卡列出需要自家獨立測試的適配項。國外地址、物價、文化習慣或人體診斷不是這些資料的移植依據。

## 共用資料核對

### D-VQA：TaiwanVQA，臺灣實拍與人工問答

- [原作者資料](https://huggingface.co/datasets/hhhuang/TaiwanVQA)、[2025 原始會議論文](https://aclanthology.org/2025.evalmg-1.6.pdf)、[NeurIPS 擴充版](https://openreview.net/pdf?id=atofIc3x1q)。CC BY-SA 4.0；公開下載，無登入要求。
- 原作者說明為團隊在臺灣拍攝 2,736 圖、5,472 人工問題。官方評估用 1,000 圖、2,000 問；訓練用另外 1,736 圖。此次實讀 README 與 split API，train_set 確有 8,680 筆：3,472 人工種子 QA + 5,208 自動生成對話。人工真值與生成資料要分開；README 仍有舊句「training support planned」，不能據此忽略已存在的 train_set。
- 此次實讀 test 與 train 的 first-rows JSON。test 真實欄位有 image_id、location、question、A/B/C/D、answer、question_type、topic、sub_topic、is_ocr、difficulty_level、is_time_relevence。train 改為 conversations（from/value）、filename、data_source 等，已見 data_source=annotator。
- 例項：冰淇淋菜單「買甜鹹爆米花與伯爵香茅，付 200 找多少」；店家價目表「15:00、16:00 聚餐、交通 30 分，哪方案能完成」。test 的 8,000 筆是同 2,000 問迴圈排列選項四次；不是 8,000 個獨立問題。另一 data_noncircular 有 2,000 筆。**保留官方 train/test；同圖、同問題、選項排列及生成對話不得跨組**。
- 狀態：來源與授權已讀、train/test schema 與小量 QA 樣本已讀；未下載影象全集、未數出菜單／時間條件子集數量，未訓練。

### D-SOUND：RealDESED，國外家庭聲音實錄

- [原作者資料與程式](https://github.com/fschmid56/RealDESED)、[資料下載](https://zenodo.org/records/20056072)、[2026 原論文全文](https://arxiv.org/html/2607.16736v1)。作者為奧地利 JKU；文章未逐筆列國家，不能稱全在奧地利或在臺灣錄製。
- 5,710 段、652 位採集者、每段 15–35 秒、15 類真實家庭聲音，有 class 與起迄區間，多標記者與審閱；包含 coffee machine、microwave、window opening or closing、running water 等。**窗開關是一個合併類別；咖啡機標籤不含「沖煮／清洗」細分；微波爐標籤不是微波能量或溫度**。
- 每檔音訊／其 metadata 為採集者選定 CC0 或 CC BY；其餘 metadata／annotations 為 CC BY 4.0。程式 MIT 不代替資料逐檔條款。此次實讀 README 與 Zenodo API：train.zip 5,647,895,421 bytes、test.zip 1,508,251,418、validation.zip 1,586,397,692。
- 原文已做 ATST-F 基準、多人標籤合併、長錄音推論及裝置／環境 metadata 分析。原收集規則**不允許 speech**，家人聊天背景需另測，不能宣稱公共集已涵蓋。
- 狀態：來源、原文方法、schema 說明、授權及檔案清單已讀；ZIP 尚未下載、音訊及實際 annotation CSV 尚未實讀，未訓練。V06–V08 正好三題；它們的家庭輸出目標不同，不再由此資料擴出更多換器具名字的題。

## V01：拍菜單核對一家人的總價與找零

- **一般人輸入／輸出**：拍一張臺灣店家菜單，輸入品項、份數與付款額，輸出逐項價錢、合計及找零。最小成果先限固定價菜單，先排除套餐自選、服務費或條件未寫清楚的折扣。
- **公開訓練與標籤**：用 D-VQA 的人工菜單問答與真實影象訓練視覺問答；價格／總額是已有答案中的數字。若要訓練「價目格位置與算式」，公共集沒有這種標註，須另標選中的 30–50 圖，不能把對話直接說成定位真值。臺灣來源、CC BY-SA 4.0，train schema 已讀。
- **已有人做**：[TaiwanVQA 原作](https://openreview.net/pdf?id=atofIc3x1q) 已做臺灣菜單辨讀、算術問答與文化模型增強；不是首次拍菜單或微調。其一般 QA 正確率不等於跨品項／份數修改後還維持帳目一致。
- **這題另測**：同一菜單改購買組合與份數，比較「直接生成答案」與「辨讀逐項價錢後固定計算」的完整帳目一致率；追蹤錯在價格讀錯、品項對錯或算術。家庭只校正常去店家的字型／排版，測試保留新拍攝日期及沒用過的購買組合。
- **最小對照／負擔／瓶頸**：無校正公共模型、公共模型加 10/20 張自家菜單、OCR+計算三者；看總價 exact match、每項 price MAE、份數變更一致率。約 20–30 張菜單、每張人工核對 2–3 個訂單；按原圖／店家切分。先數訓練集真實菜單算術有多少，數量不足就只保留固定價少品項試點；不能用 test 菜單回頭教模型。

## V02：店家告示的時間／資格條件，真的適合這次行程嗎？

- **一般人輸入／輸出**：拍店家告示或服務價目表，輸入「現在幾點、幾點要離開、可用時間」，輸出符合條件的服務專案與被哪項文字限制。先限服務時長／營業時段；不是即時交通、安全過馬路或法律判斷。
- **公開訓練與標籤**：D-VQA 有帶時間、價格與情境的 reasoning QA，已讀到按摩服務時間題。訓練學影象條件與答案；開始／截止時間的結構化欄位及條件適用性成對真值要從人工問答核對後建立。只有 source QA，不假稱已有人標完整告示邏輯。
- **已有人做**：[TaiwanVQA](https://aclanthology.org/2025.evalmg-1.6.pdf) 已測情境推理，[擴充版](https://openreview.net/pdf?id=atofIc3x1q) 已增強對話；普通「讀告示回答」沒有差異。
- **這題另測**：把同一告示中能直接讀到的限制轉為可計算條件，建立「現在時間或可停留時間只差 10 分鐘」的成對測試。比較模型是否改對適用專案，與是否維持讀出的告示條件一致；不以新介面或拒答按鈕當特色。條件集合仍以真實文字為準，不用模型猜未寫出的慣例。
- **最小對照／負擔／瓶頸**：直接 VQA、OCR+規則、經公共 QA 訓練的條件抽取+計算；主指標成對一致率、條件抽取 F1、錯推不符合專案率。家庭 15–25 張不同告示，人工各寫 3–4 個可驗證情境，依告示／店家分組；重拍同張只測攝影變化。時間／條件子集規模尚未計數；生成對話可能夾帶未由影象證實的材料／背景知識，先只用人工 data_source。

## V03：同一個飯碗吃前吃後，剩下幾克？

- **一般人輸入／輸出**：同一碗／盤飯菜吃前、吃後各拍一張，估剩食克重與本餐減少克數。最小版限米飯或可分開盛裝的固定熟食；不算熱量或營養療效。
- **公開訓練與標籤**：[Nutrition5k 原作者](https://github.com/google-research-datasets/Nutrition5k)，加州 Google 食堂約 5,000 餐盤、旋轉視角影片／RGB-D、總克重與各食材克重；CC BY 4.0。此次成功讀到 [cafe1 實際 CSV](https://storage.googleapis.com/nutrition5k_dataset/nutrition5k_dataset/metadata/dish_metadata_cafe1.csv) 2,206,282 字元，首筆總重 193g，實際含 white rice、bok choy、pork 等；不是隻有西式菜名。實際列在六個總量欄位後直接接重複食材欄位，與 README 中 num_ingrs 示例不完全相同，解析須以原檔核對。全影片未下載。
- **臺灣適用**：公共學習標籤是同種米飯等食材的物理質量；只選可對應的食材、熟度與盛裝型態。臺式混炒、湯汁和隱藏層不由外國食堂資料證明。自家深碗與公共餐盤幾何差異需實測。
- **已有人做**：[Nutrition5k/CVPR2021](https://openaccess.thecvf.com/content/CVPR2021/papers/Thames_Nutrition5k_Towards_Automatic_Nutritional_Understanding_of_Generic_Food_CVPR_2021_paper.pdf) 已做圖片／深度預測份量；[公開重作](https://github.com/AmirrrezaZ/dish2calories) 已做食材分類+克重回歸。不能稱圖片估重量為特色。
- **這題另測**：同碗小量校正與吃前後配對，是否比把兩張圖各自估重再相減更穩定；分「食物攤開」與「堆在碗側」，測誤差能否相消及何時相加。公共集有增加食材的 incremental scans；增量不等於真實吃後樣本，兩者分開。
- **最小對照／負擔／瓶頸**：單圖公共回歸、單圖家庭校正、配對差值三者；剩重 MAE、減少量 MAE、每次均用秤真值。約 2 個碗×3 種份量×不同日期 30–50 組前後照，保留新日期／新份量測試。秤只用於標籤，不作模型輸入。2D 可見表面無法唯一決定重量；報告各盛裝形態失敗，不承諾無秤精準測量。

## V04：分裝三個便當，配菜是否真的分得平均？

- **一般人輸入／輸出**：一次拍 2–3 個分裝便當，標定今天同一批的玉米／紅蘿蔔／蛋等可見配菜，輸出各盒同種配菜的可見塊數、面積與可能偏少的那盒。最小成果是同批分裝比較，不從照片推熱量。
- **公開訓練與標籤**：[FoodInsSeg 原作者](https://github.com/jamesjg/FoodInsSeg)：7,118 圖、103 食材類、119,048 個例項遮罩，COCO 格式；4,983 train / 2,135 test。原作者明列 academic research only 及 CC BY-NC-SA 4.0；影象延續 FoodSeg103/Recipe1M，不能把它稱臺灣菜圖或把其他程式 Apache 授權套到圖片。Google Drive 與百度下載連結已讀；本輪未下載 COCO 樣本。
- **臺灣適用**：只取兩邊共有、形態可比的可見食材類，例如切塊 carrot、corn、egg；臺灣常見菜名與口味不是依據。不同切塊厚度不能以同畫素面積直接比較克重。
- **已有人做**：[FoodInsSeg 原作／實作](https://github.com/jamesjg/FoodInsSeg) 已做食材 instance segmentation；[2026 食材面積摘要研究](https://arxiv.org/abs/2606.24059) 已把分割轉成可見面積比例，且明確不是重量。
- **這題另測**：同一批切塊在同型與不同型便當盒分裝，加入盒底尺度與少量同批秤重校正，測「哪盒較少」能否比單純可見面積更可靠。以秤重核對排序，不把遮罩面積當克數真值；整顆、切半、堆疊分開。
- **最小對照／負擔／瓶頸**：可見面積、例項計數、公共模型+同批校正；最少盒判定正確率、各盒相對重量誤差與人工改遮罩時間。家庭 10–15 次分裝、每次 3 盒；按食材原批次／日期分組。食物遮蔽、碎粒或醬汁可能失敗；若盒中份量只能靠隱藏層區分，本題無法只靠照片完成。

## V05：水龍頭換出水口後，聲音還能估一次用了多少水嗎？

- **一般人輸入／輸出**：選定一個自家水龍頭，錄一次用水聲，估大致流量與這次用量；比較原出水口與既有起泡器／不同正常出水設定。只觀察正常操作，最小成果不是漏水警報。
- **公開訓練與標籤**：[Water Leakage Voice Data 原作者](https://huggingface.co/datasets/aemreozturk/water_leakage_voice_data)、[2025 原論文](https://www.nature.com/articles/s41598-025-18154-z)。國外 WC 實錄；資料卡沒有逐點所在地，不能只憑土耳其作者單位斷言每個音檔位置。CC BY 4.0；公開 WAV，真實標籤 1–3 個水龍頭×3 流量級，另有 hand washing／flush。原文測得三流量為約 0.50、1.92、4.30 L/min，不是所有水龍頭通用刻度。
- **此次狀態／臺灣適用**：已讀公開目錄 Train/11–33，成功對 [Train/11/r1_1-1.WAV](https://huggingface.co/datasets/aemreozturk/water_leakage_voice_data/resolve/main/dataset/Labelled/Train/11/r1_1-1.WAV) 讀 512-byte Range、HTTP206、RIFF/WAVE，16kHz、雙聲道；尚未解碼音訊內容或全量切段。流量級與水聲可作起始監督，但水壓、盆材質、起泡器與手機距離必須家庭量杯校正，不能直接套公共 L/min。
- **已有人做**：[原論文](https://www.nature.com/articles/s41598-025-18154-z) 已做水龍頭數／流量級分類；[2025 Water Flow Detection Device](https://arxiv.org/abs/2501.11151) 已用水聲與微控制器估流量。因此「聽水聲省水」不是差異。
- **這題另測／對照**：換出水口時，先前校正是要重做整份，還是少量 3–5 次量杯紀錄足夠；比較公共流量級、每配置完整校正、只加少量新配置的模型。主指標每次總 L 絕對誤差、每分鐘校正帶來的誤差下降；按原始錄音／配置／日期切分，不能把長 WAV 的近鄰片段拆到測試。
- **家庭負擔／瓶頸**：約 2–3 正常配置×3 流量×5 次 10–20 秒錄音，量杯測每次水量；再另一天獨立測。水聲來自落水、盆中水位與空氣混入，多源相同音色不可唯一反推流量。多水龍頭公共標籤只作背景／負例，不宣稱單麥克風能分清不同房間的各別流量。

## V06：咖啡機的開機清洗，不要被算成又喝一杯

- **一般人輸入／輸出**：錄自家咖啡機運作片段，輸出這次是沖一杯、清洗或僅開機的紀錄與杯數。最小版固定一臺機器及它現有的兩三種操作。
- **公開訓練與標籤**：D-SOUND 的 coffee machine 時間區間可訓練「何時是咖啡機事件」；公共集沒有清洗／沖煮真值，第二階段須自己按實際操作標註，不能說公共資料已教模型分清杯數。聲音片段國外、每檔 CC0/CC BY；ZIP 清單可讀，未讀 WAV。
- **已有人做**：[fresh-coffee-listener 原作者實作](https://github.com/datarootsio/fresh-coffee-listener) 已用自家磨豆聲 MFCC 範本匹配計杯，並要求換成自己的機器錄音；[DeLonghi 原廠](https://www.delonghi.com/en-ca/faqs/What-does-the-noise-I-can-hear-during-the-brewing-cycle-mean-on-my-TrueBrew/a/562938) 說明磨豆、沖煮單元移動、浸泡等階段。自家聲音校正與計杯本身均已有。
- **這題另測**：以少量「沖煮／清洗／開機」整個序列標記，測序列模式是否比單一磨豆事件計數更少把清洗算杯；另測同臺機器移到另一個正常檯面後，是否需要重標全部。這是操作語義與重新校正成本，不能僅換一臺咖啡機做同一分類。
- **最小對照／負擔／瓶頸**：MFCC 自家範本、公共事件模型、公共模型+少量操作序列；真杯數 MAE、清洗誤計比例、每種操作至少跨 3 天 8–10 次，按完整cycle／日期分組。磨豆可能一次對應多杯，預磨模式也沒有磨豆聲；機器不具可區分序列或使用者沒有咖啡機則不選。

## V07：不裝每扇窗的感測器，聲音能記住窗開還是關嗎？

- **一般人輸入／輸出**：對固定一扇非安全用途的窗，從人工確認初始狀態起記錄開關聲，顯示狀態時間線與需重新確認的時段。最小實驗是通風記錄，不用來保證防盜、雨天保護或自動關窗。
- **公開訓練與標籤**：D-SOUND 有 window opening or closing 事件；公共模型只學候選事件。開／關方向和初始狀態需自家標記，特別臺灣常見滑窗可能異於國外鉸鏈窗。相同機械動作聲的可觀測標籤可用，但狀態必須由完整歷史推導；聽見一次事件不是已知道當前狀態。
- **已有人做**：[RealDESED](https://arxiv.org/html/2607.16736v1) 已做開關事件檢測；[小米原廠窗門感測器](https://www.mi.com/global/product/mi-window-and-door-sensor/) 已直接提供開閉狀態；[Fraunhofer acoustic window control](https://www.ibp.fraunhofer.de/en/projects-references/acoustic-window-control.html) 是依外部噪音控制通風，不能誤說成以開關聲估窗狀態。
- **這題另測**：公共事件模型加少量同扇窗方向標記，能否在漏掉一次事件或錄音中斷後仍避免把狀態「確定地記錯」；對照接觸感測器真值，研究聲音方案節省佈署的代價。核心是長時狀態累積與錯誤恢復，不是加拒答按鈕。
- **最小對照／負擔／瓶頸**：事件出現就翻轉、方向分類+狀態模型、磁簧／人工時間真值；最終狀態錯誤率、錯誤持續分鐘、重新確認次數。約 40–60 次正常開關，另一天連續 1–2 小時測試，按錄音session分組。兩扇相同窗同時動作或完全沒錄到動作時無法還原；只做單窗低風險通風紀錄。

## V08：微波爐聲音持續了多久，等於真的加熱多久嗎？

- **一般人輸入／輸出**：錄自家微波爐一次運作，輸出聲音運作區間與估計的有效加熱秒數；明確比較「風扇還在轉」和「磁控管間歇加熱」。固定一臺、既有功率檔正常使用。
- **公開訓練與標籤**：D-SOUND 的 microwave 起迄標籤可訓練器具聲事件；沒有磁控管狀態、耗電或食物溫度標籤。加熱真值需用可測功率的插座／合格量測器同步取得；聲音檢測只是第一階段。國外裝置電源頻率／機種差異需自家校正，不直接轉國外50Hz頻譜為臺灣60Hz標籤。
- **已有人做**：[RealDESED](https://arxiv.org/html/2607.16736v1) 已有 microwave sound detection 與裝置metadata比較；不能把聲音分類或長度統計當差異。
- **這題另測**：同機不同功率檔、餐盤、量與擺放位置下，聲音事件總長是否系統性高估實際加熱，加入少量公共模型+自家功率標籤能否降低偏差；與「直接信設定時間」及「音量門檻持續時間」比較。輸出只用於記錄，不能推食物是否煮熟。
- **最小對照／負擔／瓶頸**：有效加熱秒數 MAE、風扇被算加熱比例、每分鐘額外真值標記的增益；約 30–50 次本來會用的正常加熱記錄，跨日期留測試，同一cycle不能拆。若沒有安全的既有功率量測器，則只能測聲音區間而失去本題差異，應換題。靜音或連續變頻機型可能根本無法從音訊分出加熱狀態。

## V09：換到不同正常地面後，狗的步幅記錄是否可信？

- **一般人輸入／輸出**：側拍狗正常經過家中既有地毯／地板的影片，輸出步幅、步頻與左右時間差的記錄，幫助比較錄影中運動形式。只記錄自然行走，不製造溼滑地面、不解釋為疾病或舒適度。
- **公開訓練與標籤**：[3DDogs 原作者](https://cvssp.org/data/3DDogs/) 的 Lab 有 RGB-D、光學3D關鍵點、IMU與壓力墊；有效37犬143試次。Wild 是抹除markers與替換背景後的自然化版本，286序列12,940幀，**背景地面不是犬真的走過的地面**。研究非商業、須引用、禁止再散佈，下載tar連結公開；本輪讀來源與方法，未下載motion樣本。
- **臺灣適用**：同物種可觀察到相同關節／腳點與時序，臺灣的狗也有這個幾何標記目標；不把英國犬資料的步態統計當自家正常標準。身體型態、鏡頭角度、長毛及遮擋需校正。
- **已有人做**：[2024 原作](https://arxiv.org/abs/2406.14412) 已比較單眼3D pose與背景泛化；[DeepLabCut markerless 系統比較](https://arxiv.org/abs/2407.10590) 已有動物／步態量測相關方法。家庭影片與markerless不是首創。
- **這題另測**：公共pose加少量自家點標記時，哪些步幅變化是真的運動差、哪些只因相機／地板反光改變；相同狗同路線重複拍攝，用畫面尺度及人工腳接觸幀核對。以「量測重複性與校正成本」為成果，不說鋪地毯會改善健康。
- **最小對照／負擔／瓶頸**：公共2D pose、加10/30/60自家幀、固定側拍幾何；腳點normalized error、步幅MAE、同條件重複測量差。約 2 正常地面×3天×5短次，人工點30–60幀、接觸幀另核對；按犬／整序列／日期切分。一個相機看不到離鏡頭較遠的腳時，左右差必須報告不可測，不憑模型補出3D真值。

## V10：寵物在不同吃飯位置的姿勢，能少標記地記錄嗎？

- **一般人輸入／輸出**：家人拍固定貓／狗正常吃飯的側面短片，比較原來兩三個餵食位置的「鼻端到頸部的投影距離、頭部投影位置與前腳支撐」時間曲線。用途是自己的錄影量測，不產生痛、情緒、碗高度是否健康的診斷。
- **公開訓練與標籤**：[AP-10K 原作者](https://github.com/airhors/Animal-Pose-Estimation-i)：10,015網路圖、54物種、23科、COCO關鍵點，另約50k種屬標籤圖；CC BY 4.0。含貓狗，但沒有吃飯舒適度／碗高度效果標籤。此次實讀作者README、標記過程與授權；未下載COCO完整annotation。類別來源不是臺灣實拍。
- **臺灣適用／限制**：貓狗相同體表關鍵點定義可用；不同種的同名knee/hip在原文有簡化對應，不跨物種套成醫學關節角。只報2D投影量，攝像機位置必須穩定。
- **已有人做**：[AP-10K](https://arxiv.org/abs/2108.12617) 已做跨物種pose；[2026 犬多動物監測原作](https://www.frontiersin.org/journals/toxicology/articles/10.3389/ftox.2026.1758963/full) 已做站姿、吃喝與不同hopper/bowl條件識別，不能把寵物吃飯監測當新意。
- **這題另測**：只用少量自家關鍵點校正，能否比直接行為分類更可靠量到「同寵物不同既有位置的投影姿勢差」，並比較鼻端被碗遮住時人工補點成本。差異是低標記預算下的細量測與可重複性，不是換成自家貓做同一吃喝分類。
- **最小對照／負擔／瓶頸**：公共pose、少量自家pose、人工點；投影距離MAE、跨天重複性、每段需改點數。約2位置×3天各5短片，30–60人工幀，按片與日期分組。鼻端／頸部無法看見的片段不能可靠算此指標；沒有寵物或只願拍幾張照片，不選。

## V11：手作零件混在一起，還夠分給幾個人？

- **一般人輸入／輸出**：拍自家同一種較大的手作零件／紐扣，指定每組需要幾個，輸出可見數量和可完整分幾組；先不做不同顏色混合珠子、透明小珠或看不到的庫存。
- **公開訓練與標籤**：[Ai2 PixMo-Count](https://huggingface.co/datasets/allenai/pixmo-count)，train36,916、val/test各540，有count、points{x,y}、label、image_url、image_sha256。ODC-BY1.0針對資料庫；網路原圖權利不能自動由資料庫授權代替。訓練點來自Detic並篩選，val/test人工核對，測試只2–10個且不含points。此次實讀first-rows的0、8計數與xy陣列；圖片URL可能重用，尚未讀影象pixels。
- **臺灣適用**：計數和物件中心是幾何目標，紐扣／手作物不需要外國語意或物價；只訓練通用計數特徵，是否能遷移到自家零件需要真實手工數標籤。選擇有可復現來源／授權的影象子集；不把網頁相簿變成臺灣樣本。
- **已有人做**：[Molmo/PixMo 原作者](https://molmo.allenai.org/paper.pdf) 已做pointing與counting；[FamNet/CVPR2021](https://github.com/cvlab-stonybrook/LearningToCountEverything) 已可用少量樣例計未知物件。無需重複一般拍照計數APP。
- **這題另測**：給家庭一個固定標記預算，比較公共模型、只標3個示例、加10張自家整圖count；看「可完整分幾組」的錯誤是否比單純MAE更受少數漏數影響。加入真實零件貼邊、相互碰觸／同色桌布對照，但不用多個閾值冒充多個題。
- **最小對照／負擔／瓶頸**：count MAE、組數exact match、點漏計／重計、每張人工修正時間。30–50組真實擺放手數，早期校正後期測試，按零件批次／原圖切分。訓練偽點質量與原圖許可需篩；幾百小珠的高密度不能由public僅2–10的評估數字保證，先限10–40個較大不透明物件。

## V12：木作修補前後，刮痕真的少了還是燈光變了？

- **一般人輸入／輸出**：對既有木作表面修補前後同一區域拍照，輸出可見損傷區域的面積變化和同條件重拍差異；不自動生成修補圖，不判結構強度。
- **公開訓練與標籤**：[MVTec AD 官方](https://www.mvtec.com/research-teaching/datasets/mvtec-ad)，5,000+圖、15物體／紋理類別，有wood等，正常訓練圖與缺陷測試圖pixel masks，CC BY-NC-SA4。最後補核[官方分類下載頁](https://www.mvtec.com/research-teaching/datasets/mvtec-ad/downloads)有免填表的 wood.tar.xz；[官方連出的木材檔](https://www.mydrive.ch/shares/150465/d5b4115b720cdb54d217e75636e6e374/download/420938383-1629960649/wood.tar.xz)實測 Range 回應 HTTP 206、總長 498,057,680 bytes、64 bytes 的 XZ 標頭。不是只看到表單。另實讀[Anomalib 下載實作](https://raw.githubusercontent.com/open-edge-platform/anomalib/main/src/anomalib/data/datamodules/image/mvtecad.py)，有官方同網域全資料 URL 與 SHA256。尚未下載整檔／讀木材圖片與遮罩，狀態為公開下載入口與小量檔頭已讀。
- **臺灣適用**：正常木紋與表面刮痕pixel masks可訓練正常基線／定位，臺灣相同木材也有可觀察表面；家中透明漆、不同樹種／紋理／反光要自家正常照片校正。公共正常圖不是自家修補前後配對。
- **已有人做**：[MVTec/CVPR2019](https://openaccess.thecvf.com/content_CVPR_2019/papers/Bergmann_MVTec_AD_--_A_Comprehensive_Real-World_Dataset_for_Unsupervised_Anomaly_CVPR_2019_paper.pdf)、[PatchCore 原作者](https://github.com/amazon-science/patchcore-inspection) 已做異常定位；[木製品塗層公開資料](https://zenodo.org/records/15679291) 已有scratch/crack/bubble/hole檢測，拍在中國江山工廠。不能說木頭刮痕classifier本身新。
- **這題另測**：只標一個參考區域加幾張正常重拍，比較單圖異常分數與配準後前後殘留面積；能否減少光照變化被誤當「已修好／變更壞」。修補area是可見外觀，人標mask核對，不推出強度或原漆完全恢復。
- **最小對照／負擔／瓶頸**：PatchCore、畫素差、正常參考+配準方案；殘留area誤差、無修補重拍的假變化、人工勾痕分鐘。2–3已有小木件、每件不同光照10–15張，按物件／日期切分；缺陷test masks不能既當訓練又當評估。正式選題前仍須下載木材子集，核對刮痕種類與家庭修補外觀是否相同；深裂紋、漆面反光或整片重新塗色未必能配準比較。

## V13：室內兩種燈下，選的線材顏色會不會完全換了？

- **一般人輸入／輸出**：拍自家實體線材色樣和目標布料，在窗邊／室內燈下輸出同一批線中最接近的幾款，以及照明校正前後排名；不用未量測的網路色票替代手邊染批。
- **公開訓練與標籤**：[Cube++ 原作者](https://github.com/Visillect/CubePlusPlus)、[正式資料](https://zenodo.org/records/4153431)。4,890 RAW圖、SpyderCube參考、照明色度與light/shadow metadata；SimpleCube++約2GB。CC BY4.0。國外實拍，包含舊Cube/Cube+資料，來源頁不逐筆列國家；不是臺灣圖。
- **此次狀態／臺灣適用**：實讀Zenodo API許可與檔案；實讀[00_0001圖metadata](https://raw.githubusercontent.com/Visillect/CubePlusPlus/master/annotation/JPG.JSON/00_0001.jpg.json)，original_gt=(0.16238344,0.45326359,0.38435297)、左右白面位置、natural/outdoor/shadows。色度物理座標在臺灣同定義，但線材反光、手機處理與混合照明須自家同批實體參考。未下載RAWpixels或訓練。
- **已有人做**：[Stitchers Suite](https://stitcherssuite.com/colour-matcher) 已做照片→DMC/Anchor、CIEDE2000匹配，並建議鎖白平衡；[GET!Threads](https://play.google.com/store/apps/details?id=com.arrobots.GET) 已即時拍色找線號。拍顏色選線和ΔE排名皆已做。
- **這題另測**：對同一批實體線，比較公共照明估計、放灰卡、每種燈少量自家校正，測跨燈同線ID的排名穩定性與混光下失效。目標是減少家中光源導致「上次相同，今天換號」；不是再建立品牌色票轉換介面。
- **最小對照／負擔／瓶頸**：top-1/top-3實體線選擇、一致排名、ΔE相對參考誤差；約15–20色樣×2燈×3日期，按色樣/日期分組，新日期留測。選擇參考需實體並排確認，光澤、纖維方向與同色異譜可能沒有唯一RGB答案；不能承諾拍照辨真實染料。

## V14：家庭合奏，究竟哪一個聲部比較晚？

- **一般人輸入／輸出**：家人用絃樂做短二重奏，提供樂譜及一段手機混音，輸出應同時進入的音符中，各聲部onset差與可核對片段；不是單人節拍評分，不把所有不齊都說成錯誤。
- **公開訓練與標籤**：[ARME Virtuoso Strings 原作者](https://github.com/arme-project/virtuoso-strings)：英國專業絃樂四重奏，VN1/VN2/VA/VC、solo/duet/trio/quartet、normal/deadpan/speed、take1–12，44.1kHz16bit mono各聲部錄音，txt逐音onset秒數。CC BY-NC-SA4；公開GitHub檔案，本輪實讀LICENSE與[中提琴duet onset](https://raw.githubusercontent.com/arme-project/virtuoso-strings/main/annotations/DUET/D-AM-VN1_VA-NR/10/VA-D-AM-B-NR-10.txt)開頭0.17415、0.571791、0.699501、0.998458、1.285805、1.964989，未讀WAV。
- **臺灣適用**：相同絃樂的物理音符起始與樂譜同時點可訓練；這與國籍無關。先限資料有的violin/viola/cello，不能直接說可用於臺語歌唱、鋼琴／直笛組合。家庭水平、樂器音色、單麥混音與專業分軌不同。
- **已有人做**：[Virtuoso原作](https://github.com/arme-project/virtuoso-strings) 就為ensemble timing analysis；[2014四重奏同步模型](https://research.birmingham.ac.uk/en/publications/optimal-feedback-correction-in-string-quartet-synchronization/) 已研究onset asynchrony與互相修正；[URMP](https://labsites.rochester.edu/air/projects/URMP.html) 已有分軌、樂譜與多聲部轉錄，但是先分別錄再組合。不是首次測拖拍。
- **這題另測**：少量各家人單獨錄音校正，能否用**單支手機混音**歸屬拖拍聲部，接近逐人麥克風的真值；重點量測省掉多麥／逐音標記的代價。同音高／同樂器合奏尤其可能無法辨出誰晚，明確分報。
- **最小對照／負擔／瓶頸**：混音共用onset、公共分聲部模型、加每人2–3分鐘個人錄音；聲部歸屬F1、onset差MAE、偏早偏晚符號正確率。兩位家人6–10段30秒短合奏，驗證階段暫用各自近錄音／人工spectrogram真值；按曲目、take、成員分組，公共同一次演出的分軌不能跨組。需家人會對應絃樂；沒有逐聲部真值或同頻譜無法分辨時，僅輸出總體不齊不算完成本題。

## V15：自家琴的餘響，會不會被誤認為踏板沒放？

- **一般人輸入／輸出**：錄家人的固定短練習，輸出換和絃時踏板釋放的時間估計，並跟同步MIDI真值比；最小成果評估自家琴與房間少量校正，既有USB/MIDI電子琴最易取得真值。不是唱歌／字幕／錄音品質評分。
- **公開訓練與標籤**：[MAESTRO v3 原作者](https://magenta.tensorflow.org/datasets/maestro)：美國國際鋼琴賽演出1,276首198.7h、44.1–48kHz16bit、audio/MIDI約3ms對齊；含鍵擊velocity與CC64 sustain、CC66 sostenuto、CC67 una corda。CC BY-NC-SA4；101GB音訊包、56MB MIDI-only及CSV/JSON公開。此次來源頁、metadata欄位與split說明已讀，未下載音訊/MIDI樣本。相同MIDI控制含義與鋼琴共鳴物理可臺灣用，訓練譜風格／演奏程度不自動適合家庭。
- **已有人做**：[2020 high-resolution piano transcription](https://arxiv.org/abs/2010.01815) 已做pedal onset/offset；[2025 across-room pedal-depth資料](https://zenodo.org/records/15659089) 已做off/partial/full、真實+Pianoteq合成房間，不可把「加房間混響」當新方法。其公開H5為特徵，合成完整音訊另需作者；本題主訓練仍用MAESTRO。
- **這題另測**：比較不校正、用2/5分鐘自家固定音型校正、較多完整練習校正，測消費電子琴外放／擺位變化能否用很少同步MIDI標記達成可用的釋放時間估計；評估的是家庭標記預算與真實裝置適配，不聲稱首次聽出踏板。
- **最小對照／負擔／瓶頸**：public transcriber、簡單能量尾音規則、個人少量校正；踏板release時間MAE、放開後仍被判踩住的持續秒數，按完整曲／日期留獨立測試。總約15–20分鐘audio+MIDI，對測試練習不得回頭校正。音符鍵放開和踏板釋放是不同事件；某些電子琴CC64只有binary或輸出預設常值，必須先核對控制資料，否則不能做連續depth真值。

## 不計入這15張卡的線索與淘汰

- **SoundOfWater／倒水杯位**：[作者805影片與幾何](https://github.com/bpiyush/SoundOfWater)、[HF資料](https://huggingface.co/datasets/bpiyush/sound-of-water) 已有杯型／材質／溫度／高度推斷。程式碼與model MIT不能代替data；此次dataset README授權段為空，HF viewer還出現schema parse error。可讀部分幾何metadata不等於已核對資料再利用許可；當前不入可執行短名單。
- **普通吉他個人手掌跨度運指**：已有[Tabfier](https://jailson.com/side-projects/tabfier/)手位置／span成本、[Orfeo](https://orfeo-score.com/docs/practice/fingering/)相機量手與個人hand profile。不能用GuitarSet再做同一個個人跨度功能。
- **普通手機樂譜去彎曲接OMR**：[oemer](https://github.com/BreezeWhite/oemer)已把手機樂譜、staffline-based dewarp與MusicXML結合；Doc3D/MUSCIMA++有標籤也不足以保留同功能。
- **臺灣番茄葉病害classifier**：[原作者資料](https://data.mendeley.com/datasets/ngdgg79rzb/1)明確分別含PlantVillage與臺灣622圖六類，不能把第一套也說成臺灣。僅套分類、自家盆栽遷移目前沒有多於普通病害識別的實質差異，不納入。
- **透明杯櫃內尺寸**：[ClearGrasp](https://sites.google.com/view/cleargrasp/data)有50k+合成depth/normal/mask與286真實RGB-D；程式碼Apache2，當前未找到單獨dataset再利用條款。深度相機需求／反光尺寸真值亦待查，當前不計入。
- **TAI KIT 臺式廚房3D**：[作者卡](https://huggingface.co/datasets/dAAAb/tai-kit-v1)是從產品圖AI重建，不是6,281臺灣實測物件；39% FLOOR、單檢視無法證明背面形狀，產品圖來源權利需核對，暫不以其名稱當臺灣實拍訓練來源。

## 本輪查重覆蓋與下一步

已實際查原作者資料卡、許可證、公開目錄／API、原論文與方法描述、相關產品和開放實現；未全面取得本課歷屆作品全文，未窮盡付費產品或所有論文。代表作同領域不直接淘汰；卡中另測的問題有明確對照和指標。差異效果仍需驗證。

整合時建議區分：臺灣資料（V01/V02）、共用物理標籤且家庭校正可驗證（其餘），與實質取得門檻（尤其V11原圖權利、V08功率真值、V14聲部分軌真值）。V12 已補核免填表官方子集下載，不再列為表單阻礙，但仍未讀完整圖像。優先讓使用者挑興趣和願意付出的家庭採集；不能在此階段寫成任何裝置已擁有、模型已有效或已選擇題目。
