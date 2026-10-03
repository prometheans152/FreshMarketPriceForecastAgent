# 台灣家庭與環境選題查核

查核日期：2026-10-03。範圍：台灣環境／家庭能源資料、實際既有作品與可實驗的差異；未訓練模型，未採集家庭資料。

本輪只保留一個值得由主代理人再比較的候選。沒有為湊數留下國外住宅模型換地名、換介面或加上一般拒答功能的題目。

## E1：資料延遲或測站斷訊時，空品建議何時仍能使用？

對應原候選 38、41，重新縮範圍；尚未選定。

### 用途與最低成果

在台灣歷史濃度資料上，人工設定延遲、單站與多站連續遮蔽情境，判斷未來 1–3 小時是否能對使用者設定的 PM2.5 上限提供可靠提示。輸出分成「符合上限」「將超過上限」「資料不足」；同時交代最近有效讀值、時效與不確定性。公開檔沒有歷史發布時刻或故障原因標籤，這不是重現真實失聯當時可用資料，也不是證明實際家庭行動安全。

特色不是一般空品預測加一個拒答按鈕。需證明：相同可提供建議比例下，延遲／失聯感知模型比單純讀值過期門檻更少給出錯誤的低污染提示。若這個比較沒有改善，這題也應淘汰。

### 真實公開資料與本次樣本

- 機構：[環境部 AQX_P_15](https://data.moenv.gov.tw/dataset/detail/aqx_p_15)，空氣品質監測小時值，一般污染物；是台灣測站觀測。
- 官方資源列表本次可讀，包含 1982/07 至 2026/09 的月檔條目；沒有逐月驗證完整性。實作建議先選近兩年與少量相鄰測站。
- 本次實際下載 2025/01 ZIP，HTTP 200、application/octet-stream、2,454,876 bytes。ZIP 內有 CSV 與 hash.txt。沒有保存大型原始資料。
- CSV 原始 80,826 行，79 個測站，日期 2025-01-01 至 2025-01-31；欄位是小寫 `siteid`、`sitename`、`itemid`、`itemengname`、`itemunit`、`monitordate`、`monitorvalue00` 至 `monitorvalue23`。
- 真實測項包括 PM2.5、PM10、CO、NO2、O3、RH、AMB_TEMP、RAINFALL、WIND_SPEED、WIND_DIREC 等。
- 本次發現 39,749 組測站／測項／日期有完全相同的重複行；整列去重後只有 41,077 行。這不是額外獨立樣本，必須先去重再切分。
- 大城站 2025-01-01 的 PM2.5 小時值前四筆為 36、40、45、48 μg/m³；10 時為 `x`，11–15 時空白，16 時為 `x`。同站溫濕度有相近缺值段。這是實際缺值樣本，不能直接證明整段是通訊故障。
- 來源頁標明免費、依政府資料開放平臺使用規範，連到 [政府資料開放授權](https://data.gov.tw/license)。本次匿名下載不需 API Key；公開 API 的資格與 Key 另行處理。

可重現下載方式（公開網頁下載功能使用的讀取請求，不是變更外部資料）：

```json
POST https://data.moenv.gov.tw/api/frontstage/dataset/resource.download
Content-Type: application/json
{
  "rid": ["5b91e855-83e7-4d90-97da-946fda6bb72e"],
  "download_type": "csv",
  "pid": "fe04e4a8-e3ee-44ae-8db7-8eb296facf18"
}
```

資源識別碼由本次官方網頁資源列表取得；網頁版本改變時應重新讀列表。

### 已實際查到的既有作品

| 作品 | 已做到的內容 | 本題不能當成特色的部分／仍可比較的範圍 |
| --- | --- | --- |
| [Liu 與 Cheng，2026，Intelligent Particulate Matter 2.5 Forecasting for Real-Time Air Quality Intelligence](https://www.mdpi.com/2673-4591/141/1/12) | 雲林附近 10 站，2024–2025 小時資料，ST-GCN 預測 1–2 小時，線性補值、依時間切分、RMSE／MAE／R² | 多站、短期預測、時間切分都已有。文章將更完善缺值處理與不確定性列為後續方向；未報告連續失聯下的可回答比例與錯誤提示取捨。 |
| [2020，Machine Learning-Based Prediction of Air Quality](https://www.mdpi.com/2076-3417/10/24/9151) | 台灣 3 站、11 年資料，AQI 預測與補值、1／8／24 小時的 95% 區間 | 台灣資料、補值、預測區間都已有；一般「加上信賴區間」不能算差異。 |
| [Malings 等，2024，Air Quality Estimation and Forecasting via Data Fusion With Uncertainty Quantification](https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2024JH000183) | 多來源融合、缺輸入、濃度不確定性、14 日滾動校正；案例主要為 NO2 | 資料融合與缺值下的區間也已有。原文明示資料延遲效應未納入實驗；本題可做延遲＋連續失聯的明確壓力測試，而非宣稱首創拒答。 |
| [2026，Regime-aware hybrid ensemble learning for adaptive PM2.5 forecasting in urban environments](https://www.nature.com/articles/s41598-026-45437-w) | 感測器卡值偵測、短缺口插值、較長缺口保留缺值／排除資料 | 感測器失常與長缺口處理也已有；把失聯列拿掉後取得較好平均誤差，不等於仍能為失聯時段給建議。 |
| [2026，Simultaneous Inference for Partially Observed Functional Time Series](https://arxiv.org/abs/2606.31269) | 部分觀測時間序列的推論，空污資料及區間型／序列型缺失 | 缺失下的不確定性方法不是原創點；本題定位為台灣資料上的行動可靠度比較，不另聲稱發明統計方法。 |

本次檢索：`Taiwan PM2.5 selective prediction abstention conformal missing data`、`air quality selective prediction`、`air pollution forecasting abstention`、`PM2.5 sensor failure forecasting uncertainty`、`air quality data latency forecasting reliable`。已查看上述原作者／出版者材料。未找到本次候選的完整同實驗設計，不足以證明全球首次；同課歷屆完整內容未在本分工重查。

### 具體差異與最小比較

1. 不只是處理隨機空白：分別測單站連續 1／3／6／24 小時缺值、兩站同時缺值、風向改變與污染突升；延遲也是受控情境，不冒充已取得歷史發布時刻。
2. 不拿事後才能取得的氣象值當預測當下輸入。所有特徵只取各情境中已提供的過去資料；只在有真實目標值的區段遮蔽輸入，保留真值評分。
3. 三個對照：沿用最後讀值／簡單預測；讀值過期就停止提示的固定門檻；加入資料年齡、缺失遮罩與鄰站狀態的模型加決策。
4. 報告同樣可提示比例下的「誤判低於上限比例」、超標漏報、建議可用比例、區間涵蓋率，另外保留 MAE。不能靠永遠拒答獲得漂亮錯誤率。
5. 整段時間與完整污染事件留作測試；校正集與測試集分開，去重後才建滑動視窗。時間相依資料的區間可靠度以實測呈現，不保證理論覆蓋率。

個人／家庭資料可選：使用者設定固定活動時段、願意延後的時間與濃度上限，評估自己的時段還剩多少可用建議。戶外參考站不代表室內或門口實際濃度；若加入自家 PM 感測器，需獨立校正與驗證，不能把國家測站值當同位置真值。

主要限制：這是公共資料可靠度研究題，個人化程度比直接訓練自家影像或聲音弱。只有歷史觀測時間、缺乏逐筆發布時間；因此第一版只能做明確標示的延遲情境重播。即時版要另確認資料延遲、可當下取得的欄位與 API 授權。

## 本輪排除或暫不推薦的方向

### 原 1：台灣家庭下月電費

[台電住宅月平均資料](https://data.gov.tw/dataset/17062) 欄位是全體住宅每戶平均度數／電費與去年同期值，沒有個別戶號或單戶負載。不能把全台平均當台灣家庭訓練標籤。London、UCI 法國單戶或加拿大 AMPds2 的簡單縮放，沒有台灣住宅適配證據，故不保留舊版方案。

找到 [清大 107 學年度專題摘要](https://ieem.site.nthu.edu.tw/var/file/310/1310/img/3494/147751133.pdf) 曾使用 106 年低壓智慧電表競賽提供的 105 年台電數據；本次尚未找到目前仍可公開取得、授權可核對的原始低壓競賽檔，不能說已找到可用資料。搜索包括 `低壓 智慧電表 大數據 分析 競賽 2017 資料 下載`、`Taiwan smart meter 2016 2017 dataset download GitHub`。

### 原 11：ASHRAE 個人舒適偏好

本次匿名下載並解析 [ASHRAE DB II v2.1.0 metadata](https://raw.githubusercontent.com/CenterForTheBuiltEnvironment/ashrae-db-II/master/v2.1.0/db_metadata.csv) 與 [109,033 筆量測](https://raw.githubusercontent.com/CenterForTheBuiltEnvironment/ashrae-db-II/master/v2.1.0/db_measurements_v2.1.0.csv.gz)。country／city／contributor／publication 等搜尋 Taiwan、Taipei、Taichung、Tainan、Kaohsiung、Hsinchu、Hwang，沒有台灣建築或量測；其中標示 china 的城市也不是台灣城市。不能說此版本含台灣子集。

國外舒適模型直接套台灣家庭尚無本地效能證據。少量個人化已有 [Cohort comfort models，2022](https://arxiv.org/abs/2208.03078) 與 [Personal comfort models，2018](https://escholarship.org/uc/item/54n6b7m3)；不能只用加入家人回饋當差異。本輪不保留。

### 自動晾衣／遇雨收衣

已有 [台灣 2020 智慧晾衣架研究](https://doi.org/10.1088/1755-1315/603/1/012047)，並有 [2021 雨／光感測收衣](https://ieeexplore.ieee.org/document/9678412/) 與 [2025 天氣 API＋本地感測提前收衣](https://www.ijcrt.org/viewfull.php?paper=IJCRT2508248)。若只做台灣雨量預測加通知，差異不足，暫不列。公開逐時雨量也不能直接支持 15 分鐘提前量或衣服乾燥時間標籤。

### 開窗降濕／PM2.5 聯動

已找到 [台灣住宅室內 PM2.5 機器學習，2022](https://proceedings.open.tudelft.nl/clima2022/article/download/247/228) 以開窗有效面積、溫度、濕度等建模；[高雄家庭，2019](https://www.mdpi.com/2076-3417/9/20/4306) 已量測開窗期間污染改變；[2022 智慧窗戶＋清淨機控制](https://journals.sagepub.com/doi/pdf/10.1177/01436244221099482) 已實作同用途的控制。沒有公開台灣室內反應／操作標籤與超越既有方法的具體比較時，不保留簡單聯動版本。

### 低價空品感測器校正／少樣本校正

已查到 [台灣在地機器學習校正，2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7506620/)、[台灣空間校正，2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7745024/)、[少樣本校正，2021](https://arxiv.org/abs/2108.00640) 與 [Veli／AQ-SDR，2025](https://github.com/YahiDar/AQ-SDR)。附近環保站並非自家同位置參考儀器；缺少可信校正真值、且只換模型時，不保留。

### 颱風前家庭停電準備

找到可下載且實際讀取的 [2017 台灣停電競賽作者資料](https://github.com/Tang-Li-Jen/Power-outage-prediction-competition)：[final_data.zip](https://raw.githubusercontent.com/Tang-Li-Jen/Power-outage-prediction-competition/master/final_data.zip)，12,626,239 bytes；內有 `df_1120.csv`，78,510 資料行。

欄位包括 CityName、TownName、VilName、VilCode、typhoon、elect_down、year、arrive、leave、duration_h、風雨與電杆等。`elect_down` 是停電戶數；`duration_h` 是颱風期間，不是單戶停電時長。作者說訓練只有 8 個歷史颱風，測試颱風標籤以 0 初始化，不能把它們當真實零停電。原始樣本筆數不是 78,510 個獨立颱風事件。

作者已用風雨、路徑、電杆、人口資料及 RF 預測村里停電戶數。台電 [2026 天災停電預測系統](https://www.inventaipei.com.tw/en/product/CBA4659B8C39B7F71895F39F7F5E7CC886C84E5AB43A843C9D43687DF11C48F7/info.html) 也已提供受影響地區、停電戶數與事前資源部署。只改成家庭提醒不足。GitHub 官方 API 回傳 repo license = null，尚未核對原競賽再利用授權；本輪暫不推薦。

### 洪水／土壤與紫外線備選

搜尋官方災害歷史、公開農業月資料、紫外線即時資料。找到的農業月資料有土溫但沒有土壤含水量，不能直接訓練盆栽澆水；部分紫外線來源只剩鹿林山即時資料，沒有本次讀取的在地歷史標籤；水利歷史／預測接口另有取得條件。本輪未達實際樣本＋代表作品差異門檻，未列可選題。

## 狀態與交接

- 已完成：公開來源與既有作品查核、兩份公開資料的實際樣本解析、ASHRAE 全部 metadata／量測的台灣子集檢查。
- 未完成：E1 的模型與決策比較；同課歷屆完整作品查重；即時資料可取得延遲的現場紀錄；家庭測試。
- E1 只是候選實驗題，不是使用者決定、全球原創聲明或部署成果。若主代理人認為其他題的使用價值／差異更具體，可不放進本輪使用者清單。
