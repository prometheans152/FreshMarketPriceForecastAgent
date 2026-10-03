# 模型選擇（T13）

日期：2026-10-03。實作：`src/aiot_price/models/select.py`；證據：`outputs/training/model_selection.json`。選擇標準於看測試前凍結（見 select.py `SELECTION_RULE`）。

## 選擇標準（凍結）

1. 主指標：**驗證集方向 macro-F1**（產品核心是漲跌提示；accuracy 被 flat 多數主導）。
2. 點預測 r 的 MAE 未優於「不變價」基線者，價格點估計須標限制，不作點預測宣稱。
3. 機率／區間：本版無校準驗證，一律不輸出（`probability=null`）。

## 驗證集比較（macro-F1）

| 候選 | h=7 | h=14 |
| --- | ---: | ---: |
| ridge | 0.4183 | 0.3811 |
| hgb_reg | 0.3888 | **0.4591** |
| rf_reg | **0.4334** | 0.4428 |
| hgb_clf | 0.3261 | 0.3624 |
| dummy_majority | 0.2991 | 0.2857 |

## 選定

| 期限 | 模型 | 驗證 macro-F1 | 對 flat 基線 | 點 MAE 對 flat 基線 |
| --- | --- | ---: | --- | --- |
| h=7 | rf_reg（RandomForestRegressor, 300 樹, leaf≥5, seed 42） | 0.4334 | +0.134 ✓ | 0.0705 vs 0.0613 ✗（未優於） |
| h=14 | hgb_reg（HistGradientBoostingRegressor, 200 迭代, seed 42） | 0.4591 | +0.173 ✓ | 0.1115 vs 0.1061 ✗（未優於） |

## 輸出欄位允許條件

| 輸出 | 允許 | 條件 |
| --- | --- | --- |
| direction（up/flat/down/insufficient_data） | ✓ | 由模型 r 預測經 ±5% 門檻導出 |
| relative_change_estimate | ✓ | 附「點估計 MAE 未優於不變價基線」限制說明 |
| price_estimate | ✓（store_price_estimate） | 現價錨定跨場景推估，標 unvalidated |
| probability / interval | ✗ | 未做校準驗證，一律 null |

## 已知限制（如實記錄，不得隱藏）

- up 類召回率低（驗證集 h=7 僅 6/223≈2.7%；h=14 約 16.7%）：模型對「上漲」敏感度有限，多數預測為 flat。
- 點預測 MAE 全部未優於不變價基線：公開模型的核心價值在方向提示，不在點預測。
- 這些是**公開市場均價**成績，與任何單店真值無關。
