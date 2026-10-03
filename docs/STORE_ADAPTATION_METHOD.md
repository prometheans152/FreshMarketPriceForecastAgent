# 店價適配方法（T14）：A／B 兩種輸入路徑

日期：2026-10-03。實作：`src/aiot_price/models/store_adapter.py`＋`predict.py`；測試：`tests/model/test_store_adapter.py`。

## A（無上週店價）

- 輸入：今天店價 p(t)（元/台斤或元/公斤換算）＋公開歷史。
- 輸出：方向＝公開市場模型 r 預測經 ±5% 門檻；店價估計＝p(t)×(1+r̂)。
- **性質（明示）**：正價格錨定不改變方向——A 的方向完全等於公開市場方向；「現價輸入」只影響金額換算，不是方向資訊增益（MODEL_VALIDATION_PLAN §4.1）。`target_scope=store_price_estimate`、`validation_scope=unvalidated`。

## B（有上週店價）＝實驗性規則原型

- 可比性檢查：previous_observed_at ∈ [t−9, t−5]（7±2 天，記錄實際間隔）、單位可比（kg↔斤換算）、規格標示一致；不過→回 A 附原因，不以 0 或市場均價代填。
- 規則：`r_B = r_A + 0.3 × (店價一週變化 − 公開同期一週變化)`。
- **已訓練部分**：無。ALPHA=0.3 是開發期固定係數，未經任何同店資料擬合。
- **尚無證據部分**：B 是否比 A 準（需 T16 真實同店到期價配對驗證；目前 HOLD）。
- 輸出一律帶「實驗性規則（係數 0.3），未經同店資料訓練或驗證」警示與 `validation_scope=unvalidated`；mode=both 時 A/B 並列，使用者可比較。

## 禁止事項（程式與測試釘死）

- 把同份公開 t−7 欄位改名當「上週私人價」宣稱 B 增益（MODEL_VALIDATION_PLAN §4.3）。
- 公開市場模擬的分數寫成同店成果。
- B 缺輸入時杜撰上週價。

## 兩筆價格不訓練個店模型

僅有 p(t−7) 與 p(t) 兩筆價格無法監督訓練店家規律；待 `private/store_quotes/` 依 [STORE_DATA_PROTOCOL](STORE_DATA_PROTOCOL.md) 累積到期配對後，依 MODEL_VALIDATION_PLAN §4.2 第 3 階段（同店報酬殘差校正）再訓練，並以 T16 配對設計驗證。
