# 資料卡：臺中公有零售市場每日蔬果價格

建立日期：2026-10-03（T05）。本卡描述實際取得的正式快照；執行細節見[模型驗證方案](MODEL_VALIDATION_PLAN.md)第2節，原始查核見[零售資料查核](research/TW01_PUBLIC_RETAIL_DATA.md)。

## 快照識別

| 項目 | 內容 |
| --- | --- |
| 正式快照 | `data/raw/taichung/retail_prices_20261003.json`（curl，2026-10-03 23:25 +08:00 下載） |
| 重現驗證 | `data/raw/taichung/retail_prices_20261003_232854.json`（`fetch_public.py` urllib 重下載，23:28 +08:00） |
| SHA256（三次下載相同） | `172dffc76e8249026ac2ad89cc1a9f68bcfb686fd64a2820b38e949fe7e2e259` |
| 檔案大小 | 5,323,185 bytes |
| HTTP 狀態 | 兩次下載均 HTTP 200（curl 0.839 秒；urllib 0.422 秒） |
| provenance | `data/raw/taichung/provenance_20261003.json`（curl 版）、`provenance_20261003_232854.json`（CLI 版） |
| 歷史研究快照 | `data/retail_recheck/taichung/retail_prices_20261003.json`（同日 21:19 下載，保留不覆蓋） |

## 來源與授權

| 項目 | 內容 |
| --- | --- |
| 資料集 | 臺中市政府公有零售市場每日蔬果價格（[data.gov.tw dataset 84539](https://data.gov.tw/dataset/84539)） |
| 官方下載 | `https://newdatacenter.taichung.gov.tw/api/v1/no-auth/resource.download?rid=495aff49-3547-4055-aacd-f0781c6f733e` |
| 授權 | [政府資料開放授權條款第1版](https://data.gov.tw/license)（Open Government Data License 1.0） |
| 下載方式 | 免帳號直接 HTTP GET；可重現指令見下節 |

## 觀測範圍與結構（本檔實測）

| 項目 | 實測值 |
| --- | --- |
| 列數 | 4,450（每列＝一個市場×一個訪價日期） |
| 欄位數 | 63＝`市場名稱`＋`訪價日期`＋61個價格欄 |
| 價格欄內容 | 蔬果為主但**含禽肉**（如`土雞`、`仿雞`、`鴨子(土番鴨)`），61欄不是61種蔬菜 |
| 市場數 | 14（含停用市場`(停)建國市場`；是否排除由T06品質報告決定） |
| 日期範圍 | 2025-10-04 ～ 2026-10-02，共364個日期（YYYYMMDD字串） |
| 鍵唯一性 | （市場名稱，訪價日期）0重複 |
| 0值格數 | 107,777（約佔61×4,450格的39.7%） |
| 無法解析價格 | 0 格 |

## 單位與0值意義（資料契約，誤用即污染標籤）

- **單位：元／臺斤。** 來源中文說明為「平均價格(元/斤)」；臺中市場按臺斤解讀，1臺斤＝0.6公斤（[標準檢驗局衡器規範4.8](https://www.bsmi.gov.tw/SafetyGIP/wSite/laws/review.jsp?lawId=2c9081fe1cb0bfc1011cb1593d190699&mp=65)，2026-10-03查核）。頁面英文描述將元/斤譯為NTD/kg，**以中文元/斤為準**。使用者輸入元/公斤時明確換算，保留原輸入與換算值。
- **0＝無價格（缺測），不是0元。** 分析時一律轉缺測；不能當便宜價、持平或0元標籤。
- **市場均價非單店真值。** 每格是該市場訪價平均，不代表任何一家店的實際售價；同店實價標籤須另行取得（見驗證方案第5節）。
- 每把／每顆／每袋等無重量單位不可與每斤均價混比，也不換算。

## 與舊快照差異（2026-10-03 21:19 研究快照 vs 23:25 正式快照）

| 項目 | 舊快照 | 本次快照 | 差異 |
| --- | --- | --- | --- |
| 列數 | 4,450 | 4,450 | 無 |
| 日期範圍 | 20251004～20261002 | 20251004～20261002 | 無 |
| SHA256 | 172dffc7…e2e259 | 172dffc7…e2e259 | **逐位元組相同** |

兩次下載都在2026-10-03晚間，伺服器內容未更新，屬同日重複取得、非新增觀測日期。正式快照的意義是封存與provenance紀錄（獨立URL、時間、HTTP與hash證據），**不是**更長時間軸或更新日期的資料。更多年度歷史是否可另取，T05尚未驗證。

## 可重現下載

Git Bash（專案根目錄）：

```bash
# 方式一：官方工具（urllib，免第三方依賴；目標存在時自動加時間戳，不覆蓋）
PYTHONPATH=src python -m aiot_price.data.fetch_public \
    --config configs/data_sources.yaml --out-dir data/raw/taichung

# 方式二：curl
curl -o data/raw/taichung/retail_prices_$(date +%Y%m%d).json \
    "https://newdatacenter.taichung.gov.tw/api/v1/no-auth/resource.download?rid=495aff49-3547-4055-aacd-f0781c6f733e"
sha256sum data/raw/taichung/retail_prices_*.json
```

來源設定（含單位、0值意義、欄位結構與不採用來源）見[configs/data_sources.yaml](../configs/data_sources.yaml)。

## 不採用來源（防止誤當訓練輸入）

| 來源 | 不採用原因 |
| --- | --- |
| 臺北市公有零售市場月均價表 | 月表無逐日訪價日期，不能建立7/14天日曆日標籤（驗證方案3.1） |
| 高雄市零售市場每日價格 | 來源已下架，下載連結回404；失效來源不列為訓練輸入 |

## 已驗證與未驗證

| 類別 | 項目 |
| --- | --- |
| 已驗證（2026-10-03實測） | 下載HTTP 200且可解析；三次獨立下載hash相同；列數、欄位數、市場數、日期範圍、鍵唯一、0值格數如上表 |
| 未驗證 | 發布延遲（觀測日期≠可下載日期，尚無逐日實測）；更多年度歷史可得性；單一市場逐日是否有缺行（屬T06）；`(停)建國市場`沿用價詳情（屬T06） |
| 不可宣稱 | 觀測日期即發布日期；市場均價可當單店價格；0元便宜價；臺北月表可併入訓練 |
