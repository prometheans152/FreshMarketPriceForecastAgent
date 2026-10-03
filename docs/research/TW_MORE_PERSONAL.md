# 追加台灣個人／家庭候選資料查核

查核日期：2026-10-03。這是選題研究，不代表題目已決定、模型已訓練或家庭驗證已完成。暫用 P01／P02 作本文件識別碼，正式候選編號由整合者決定。

本輪只留下兩個有實際訓練欄位、可量測差異的條件式候選。已有「個人化學習」與「羽球回球預測」實作，不能以這兩個功能本身宣稱獨特；下面限定的是不同的家庭任務、標記成本與測試條件。尚未查到相同完整評估不等於全球首創。

## P01：提示後答對，隔天換一道題還會嗎？家庭數學複習排序

### 使用者看得懂的成果

把「剛剛答對」與「之後能獨立完成同觀念的新題」分開。模型依過去練習紀錄預測：之後遇到同觀念、不同題號、未用提示的第一次作答，能否答對。每天只安排少量複習，比較會不會把仍需練習的觀念誤判成已熟練。

這個題目適合願意在均一平台做數學練習的人或家人。沒有這樣的對象，也可以先做公開資料的離線分析，但不能聲稱已改善家人的學習。

### 台灣資料與實際取得證據

- 來源：[均一教育平台本人發布的 Kaggle 資料集](https://www.kaggle.com/datasets/junyiacademy/learning-activity-public-dataset-by-junyi-academy)。發布帳號為 `junyiacademy`，是台灣均一教育平台；不是把國外學生紀錄改稱台灣資料。
- [官方帳號資料集中繼資料 API](https://www.kaggle.com/api/v1/datasets/view/junyiacademy/learning-activity-public-dataset-by-junyi-academy) 本輪可免登入讀取。版本 9、最後更新 2020-05-13；作者說明的資料期間為 2018-08 至 2019-07，16,217,311 次作答、72,630 位學生。不要與較早的 2012–2015 均一資料版本混用人數與筆數。
- 授權：作者描述及 API 為 **CC BY-NC-SA 4.0**，本案研究用途需署名、限非商業，衍生資料公開時遵守相同方式分享。
- [實際檔案列表](https://www.kaggle.com/api/v1/datasets/list/junyiacademy/learning-activity-public-dataset-by-junyi-academy)：`Info_Content.csv` 389,397 bytes、`Info_UserData.csv` 6,363,597 bytes、`Log_Problem.csv` 3,020,754,300 bytes。不能把整份下載與抽樣讀取當成同一狀態。
- 本輪成功讀取 [Info_Content.csv](https://www.kaggle.com/api/v1/datasets/download/junyiacademy/learning-activity-public-dataset-by-junyi-academy/Info_Content.csv) 的實際文字表頭和數筆內容；有 `ucid`、練習標題、難度、學科、學段及四層分類 ID。例子包含「【基礎】和差問題 1」，學科 `math`、學段 `elementary`。**沒有實際題幹全文**，不能因此承諾自動生成或解答同一題。
- 本輪從 [Log_Problem.csv](https://www.kaggle.com/api/v1/datasets/download/junyiacademy/learning-activity-public-dataset-by-junyi-academy/Log_Problem.csv) 取得 HTTP 206 的首 16 KiB ZIP 片段，在記憶體解壓讀到表頭及兩筆實際作答；不是只讀資料介紹。

實際作答欄位：

```text
timestamp_TW,uuid,ucid,upid,problem_number,
exercise_problem_repeat_session,is_correct,total_sec_taken,
total_attempt_cnt,used_hint_cnt,is_hint_used,
is_downgrade,is_upgrade,level
```

其中一筆實際資料為 2019-05-26 的作答：題序 18、重複練習 session 2、答對、33 秒、嘗試 1 次、提示 0 次。時間欄位名是 `timestamp_TW`，但字串含 `UTC`，時間換算需依作者定義核對，不能直接猜。

### 真正可訓練的目標與限制

整合審查修正：`ucid`先稱「練習單元」，不是精確知識點真值；需核對內容分類才能當同觀念代理。下文的「新題」必須是该學生此前沒做過的`upid`，不同於上一題不代表從未見過。離線排序只證明能找到後續易錯單元，不代表按推薦複習已改善學習。

輸入僅使用目前以前的作答紀錄，例如答對比例、過去提示次數、不同題的獨立成功次數與距離上次練習的時間。標籤從後續**同 `ucid`、不同 `upid`、沒有提示、第一次嘗試**的 `is_correct` 建立，再分「當天」與「至少隔一天」測試。

這是可觀察的作答表現代理標籤，不是直接量到腦中的熟練度。沒有符合條件的後續紀錄是缺標籤，不能記成答錯。依「未來未用提示」篩出樣本也會產生選擇偏差，需報告覆蓋率及提示使用者被排除的比例；不能從離線紀錄宣稱提示造成學習變差。

本輪只讀到少量樣本，尚未數出符合此目標的學生、觀念及延遲作答數。選定前先做資料計數：若隔日新題標籤太少，縮小到有足夠事件的數學觀念，或淘汰此候選，而非偷偷改回一般下一題預測。

### 實查過的既有作品

| 實際作品 | 已做的範圍 | 本題不能宣稱的差異 |
| --- | --- | --- |
| [CPKT，CIKM 2023，作者所屬 SUNY 書目及摘要](https://researchconnect.suny.edu/en/publications/continuous-personalized-knowledge-tracing-modeling-long-term-lear/)、[作者實作](https://github.com/persai-lab/CIKM2023-CPKT) | 持續更新個人的知識狀態、長期學習、遺忘與個人化作答預測。 | 「家人資料校正」「追蹤遺忘」已有人做。 |
| [MHG-KT，Discover Artificial Intelligence，2026](https://link.springer.com/article/10.1007/s44163-026-02049-7) | 以包括均一在內的資料進行知識追蹤，納入提示、嘗試等互動資訊，並做模型解釋。 | 加提示次數或解釋圖，不足以成為差異。 |
| [MC-CPO v2，2026-06-08，作者公開論文](https://arxiv.org/html/2604.04251v2) | 已用均一資料分析活動表現與估計熟練度不一致，再以熟練條件限制教學策略。 | 「答對不等於學會」「依熟練度安排教學」已有人研究。 |
| [公開均一時序預測實作](https://github.com/rizalfanex/junyi-temporal-learning-prediction) | GRU／Transformer、提示與嘗試行為、下一次作答預測及不確定性。 | 一般下一題答對預測已有可直接照做的實作。 |

### 保留的實質差異與對照

差異限定為**家庭很少量紀錄下，以隔日同觀念新題的獨立答對表現決定有限複習名額**，不是建立另一套大平台教學策略。主成果是驗證代理標籤是否比「最近答對率」更可靠地分配複習時間。

1. 比較近期答對率規則、一般下一次作答預測、針對隔日新題獨立成功所訓練的模型。
2. 固定每日最多複習 3 個觀念，報告「被判定已熟練但隔日新題答錯」比例，以及同一複習額度涵蓋多少後續會失敗的觀念；同時報告機率校準，不能只挑 AUC 好看的數字。
3. 在「曾經用提示後答對」與「未用提示答對」兩群各自測試。家人早期資料校正、後期資料獨立測試，與不校正作比較。
4. 公開資料按學生分組、各學生按時間前後切分；家庭資料按人及日期切分。不能讓同一道重複題的近鄰紀錄跨到測試集，也不能把未來的作答時間、提示與升級結果當預測輸入。

家庭原型收集量可先規劃每人跨 3–4 週、20–50 次練習，記錄同觀念新題是否一次完成、是否用提示與日期；這是可行性試驗量，並非足以證明學習成效的統計門檻。2019 舊課程分類與目前家庭使用的練習必須能對應；對應不可靠時只能先留在公開資料驗證。

**保留條件：**使用者願意做數學練習，且資料計數證明隔日同觀念新題標籤足夠。若只想展示下一題正確率，此題不列入選項。

## P02：少量自己的羽球回合，粗略落點標記夠不夠預測球友回球？

### 使用者看得懂的成果

自己或家人有打羽球時，以既有回合紀錄學習球友下一拍常用球路與落點區域。重點是回答：不花時間逐幀追蹤精確座標，只手動標記球路和粗落點，加少量自己的回合校正，能不能得到有用的預測。

成果可顯示不同對手回球區域的機率和測試表現，**不把最可能回球直接當作最佳戰術，也不聲稱提高實戰勝率**。

### 台灣來源、適用情境與實際樣本

- 來源為陽明交通大學研究團隊的 [CoachAI-Projects](https://github.com/wywyWang/CoachAI-Projects)、[ShuttleSet 原作者資料說明](https://github.com/wywyWang/CoachAI-Projects/blob/main/ShuttleSet/README.md) 及 [ShuttleSet 論文](https://arxiv.org/abs/2306.04948)。資料由台灣研究團隊公開，但影片是國際職業賽，不是全在台灣拍攝的業餘家庭資料。
- 作者目前的 ShuttleSet 說明列 2018–2021 年 44 場比賽、104 局、3,685 回合、36,492 拍、27 位選手；包含台灣選手周天成等。不要與不同版本的 ShuttleSet22 筆數混用。
- [根目錄 LICENSE](https://github.com/wywyWang/CoachAI-Projects/blob/main/LICENSE) 為 MIT。已讀原文；資料在該公開倉庫，未看見此子目錄另列不同授權。下載影片與重新發布轉播影像不能只憑程式庫 MIT 推論，原型可先使用 CSV。
- 本輪免登入實際取得 [2019 丹麥公開賽陳龍對周天成，第一局 CSV](https://raw.githubusercontent.com/wywyWang/CoachAI-Projects/main/ShuttleSet/set/CHEN_Long_CHOU_Tien_Chen_Denmark_Open_2019_QuarterFinal/set1.csv)，HTTP 200、46,607 bytes；讀到實際表頭與球路、落點資料。其他比賽尚未全量下載。
- 欄位包含回合／拍序、影片時間／幀、比分、擊球者、球路中文標籤、擊球及落點區域／座標、雙方所在位置、得失分原因等。實際前兩拍為「發短球」和「推球」，有 `landing_area` 與 `landing_x/y`，可直接形成下一拍球路／粗落點標籤。
- 台灣可用性依據是同樣的單打球場幾何及球路定義，且資料中有台灣選手；**職業球員行為是否能轉到家人／業餘球友尚未驗證**，這正是需要自己的資料做對照的部分。若題目只接受台灣日常實際拍攝的資料，此候選不符合，需剔除。

### 學習任務

輸入本回合過去的球路、粗落點、雙方粗位置和擊球次序，預測下一拍的球路分類與落點區域分布。只使用已發生的拍，不使用未來得失分原因或下一拍座標。

作者說明將 A／B 依整場勝負指派；若直接以 A／B 當球員能力輸入，等於提前知道比賽結果。要用 `match.csv` 對應穩定球員身分，或以當回合擊球次序重編，不把「最終勝者」當預測特徵。依球場 homography 處理不同影片方向，缺座標的拍不能盲目填零。

### 實查過的既有作品

| 實際作品 | 已有範圍 | 本題不能宣稱的差異 |
| --- | --- | --- |
| [ShuttleNet，AAAI 2022，原會議論文](https://ojs.aaai.org/index.php/AAAI/article/view/20341) | 融合回合進展與球員風格，預測下一拍球路及位置。 | 下一拍預測、個人球風已做。 |
| [CoachAI 原作者倉庫](https://github.com/wywyWang/CoachAI-Projects) 中 DyMF／RallyNet／ShuttleSHAP／CoachAI 環境 | 包含球員移動預測、模仿球員行為、解釋預測及對手模擬。 | 加球員位置、解釋或模擬對手不構成差異。 |
| [BST 原作者實作](https://github.com/Va6lue/BST-Badminton-Stroke-type-Transformer)、[論文](https://arxiv.org/abs/2502.21085) | 以骨架和羽球軌跡進行球路辨識，倉庫列 CVPR Workshops 2026。 | 「看影片辨識球路」也已有方法。 |

### 保留的實質差異與對照

把**家庭能付出的標記時間**當成限制，測量「每增加幾分鐘標記／幾個自己的回合，能換到多少回球預測改善」，並測試職業資料預訓練對業餘球友是否有效。

1. 公開資料比較精確座標方案與 4／6 區域方案，目標統一為同一套粗落點區域，另比較簡單條件頻率／Markov 基線。不能用不同難度的標籤直接比較準確率。
2. 實測人工標記每個回合的時間和兩位標記者一致性；單用公開資料自動把座標轉成格子，不能聲稱已降低真實家庭標記成本。
3. 自己的資料按早期 20／40／80 個回合比較校正曲線，在另一天完整球局測試；與完全不校正比較。初期可先收 20–40 回合作可行性檢查，這不是保證足夠的統計樣本數。
4. 以對手、球局和日期分組，測球路 macro-F1、粗落點 log loss／校準、每分鐘標記帶來的增益。對同一回合的不同拍不能隨機拆成訓練和測試。

這個差異有家庭用途與可測成本，仍需要先實測粗標記一致性和職業到業餘的落差。若使用者沒有打羽球或不願錄／標自己的回合，只展示職業賽回球預測會直接重做既有 ShuttleNet，應剔除。

## 本輪明確排除或不列推薦的方向

- [文化部公開電影活動資料](https://data.gov.tw/en/datasets/6010)：本輪找到的是場次／活動資訊，沒有觀眾偏好或評分標籤。不能拿節目表訓練「家人喜不喜歡這部片」。
- [台北市銀髮族食譜資料](https://data.taipei/dataset/detail?id=7d202683-b3a7-4a4d-8099-d60bfc1dd5c2)：有食譜資訊，但本輪未確認足量的家庭採用、接受度或味覺評分標籤；不以食譜可下載就宣稱偏好模型能訓練。
- [PTT 文本研究，ROCLING 2018 原論文](https://aclanthology.org/O18-1021.pdf)：找到研究描述，但本輪未完成實際可下載訓練檔與標籤授權核對，不作已確認候選。

## 查重搜尋範圍與證據界線

2026-10-03 使用「Junyi Academy hint mastery personalized knowledge tracing」「Continuous Personalized Knowledge Tracing」「Junyi next correct hint」「MC-CPO」「CoachAI ShuttleSet badminton amateur personal calibration」「ShuttleNet coarse landing annotation」等中英文組合，查看原資料發布帳號、原作者 GitHub、原會議／期刊頁及作者論文。已找到上述直接相關作品；未做所有付費全文及全球全部產品的完整查重。

本輪只證明兩個資料來源有實際可讀的訓練欄位，並提出可量測的家庭任務差異。未訓練模型、未做全資料標籤數量統計、未收家庭資料，差異的實際效果仍待選題後驗證。
