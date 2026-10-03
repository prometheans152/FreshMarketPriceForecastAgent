# 模型卡（T18）— aiot-price v0.1.0

- **任務**：臺中公有零售市場均價之 7／14 天相對變化（r_h=m(t+h)/m(t)−1）回歸與 ±5% 三類方向。
- **訓練資料**：`data/raw/taichung/retail_prices_20261003.json`（SHA256 `172dffc76e82…`，2025-10-04～2026-10-02，政府資料開放授權條款第1版）；三品項（甘藍/青江白菜/絲瓜）、排除 (停)建國市場；切分 train≤2026-05-08／val≤2026-07-21／test≤2026-10-02，凍結清單 SHA256 `4e136574…`。
- **模型**：h=7 RandomForestRegressor（300樹）、h=14 HistGradientBoostingRegressor（200迭代），seed 42，CPU 訓練（TRAIN_LOCAL）。
- **特徵**：只用查詢時點 t−1（發布延遲假設）前可見資料——最新價與年齡、7/14/28 天滾動均値/標準差/極値、7/14 天向後報酬、星期/月、品項 one-hot；無市場 one-hot（未見市場可推論）。
- **成績（封存測試）**：h=7 macro-F1 0.422（持平基線 0.309）、accuracy 0.766；h=14 macro-F1 0.417（基線 0.295）、accuracy 0.711；點回歸 MAE 0.066/0.098 **未優於**不變價基線 0.044/0.075。
- **限制**：up 召回率低（≈10%）；僅一年臺中資料；市場均價非單店真值；機率/區間未校準不輸出；同店 B 為實驗性規則未驗證。
- **工件**：`models/releases/0.1.0/`（manifest.json、model_h7/h14.joblib、public_history.parquet、fixtures.json 3 案例重現通過）。
- **契約**：`contracts/forecast.schema.json`、`contracts/model-manifest.schema.json`。

完整指標：[PUBLIC_MODEL_EVALUATION](PUBLIC_MODEL_EVALUATION.md)、[MODEL_SELECTION](MODEL_SELECTION.md)、[ERROR_ANALYSIS](ERROR_ANALYSIS.md)。
