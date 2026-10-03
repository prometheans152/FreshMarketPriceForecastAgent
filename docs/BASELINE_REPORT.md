# 基線報告（T11）

日期：2026-10-03。實作：`src/aiot_price/models/baselines.py`；數據：`outputs/training/training_results.json`（驗證集）與 `outputs/evaluation/public/public_test_results.json`（封存測試）。全部基線與候選使用相同特徵表、切分、7/14 口徑與相同評估列（`feature_ready`：price_last 非缺且標籤已成熟）。

## 基線定義

| 基線 | 定義 | 手算檢查 |
| --- | --- | --- |
| flat_no_change | r_hat=0（方向恆 flat） | r=0 → \|0\|≤5% → flat ✓ |
| past_change_continues | h=7 用 ret_7d、h=14 用 ret_14d（過去同長度變化延續） | 測試涵蓋於 test_features |
| train_mean_return_by_crop | 訓練集同品項同 h 平均 r（訓練區 fit） | 驗證集僅供比較 |

## 驗證集結果（方向三類，n 同候選模型）

| h | 基線 | return MAE | 方向 accuracy | macro-F1 |
| --- | --- | ---: | ---: | ---: |
| 7 | flat | **0.0613** | **0.8139** | 0.2991 |
| 7 | momentum | 0.0972 | 0.7794 | 0.4125 |
| 7 | train_mean | 0.0644 | 0.8139 | 0.2991 |
| 14 | flat | **0.1061** | **0.7499** | 0.2857 |
| 14 | momentum | 0.1461 | 0.7184 | 0.4022 |
| 14 | train_mean | 0.1126 | 0.7499 | 0.2857 |

## 錨定假設註記（依 MODEL_VALIDATION_PLAN §4.1）

「今天店價 × (1+公開預測變化率)」的店價估計不改變漲跌方向（正價格錨定下方向由公開 r 決定）；在 API／UI 中此路徑標 `target_scope=store_price_estimate`、`validation_scope=unvalidated`，不作「現價輸入改善方向」宣稱。

## 誠實結論

- 持平類佔驗證集約 81%（h=7）／75%（h=14），「不變價」是點預測 MAE 與 accuracy 的強基線。
- 基線間比較：momentum 的 macro-F1 高於 flat（0.41 vs 0.30），但點 MAE 更差——方向訊號與點預測精度分開呈報。
