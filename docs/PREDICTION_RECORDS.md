# 預測紀錄（T22）

日期：2026-10-03。實作：`src/aiot_price/api/prediction_records.py`。

## 用途

凍結每次查詢的「當時輸入＋A/B 輸出＋模型/資料版本」，供 7/14 天後同店到期價核對（T16 A/B 配對驗證的事前預測證據）。到期後不得重算冒充原預測。

## 行為

- 保存：使用者選擇保存時呼叫 `save_prediction(response, request)` → `private/predictions/prediction_<timestamp>.json`（git 忽略目錄）。
- 讀回：`load_records()` 供到期核對；壞檔跳過不刪。
- 匯出：`export_anonymous_summary()` 產匿名彙總（品項/市場/模式/方向，不含輸入細節）供公開報告。
- `simulated=True` 的資料一律拒收（不得混入真實紀錄）。
- 關閉保存不影響基本查詢。

## 隱私

- 原始紀錄只在 `private/`（.gitignore 排除）；公開內容一律經匿名彙總。
- 店家以匿名 `store_id` 識別（`^[A-Za-z0-9_-]+$`），不收真名地址。
