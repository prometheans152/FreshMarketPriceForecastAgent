# 投影片製作來源：依賴與重建（D44-R06）

## 依賴（本機 `.venv` 實測版本；2026-10-04 盤點，未做乾淨環境重建驗證）

| 套件 | 版本 | 用途 |
| --- | --- | --- |
| python-pptx | 1.0.2 | 產生可編輯 PPTX（含 notes、connector） |
| pandas | 2.3.3 | 讀 parquet/CSV |
| pyarrow | 25.0.1 | parquet 引擎 |
| matplotlib | 3.11.2 | 圖表素材（微軟正黑體） |
| scikit-learn | （產品既有） | 僅評估重算無關；製作鏈不直接用 |
| pywin32 | 312 | PowerPoint COM 匯出 PDF/PNG |
| pypdf | 6.19.0 | PDF 頁數核對 |
| pytest | （產品既有） | 製作工具測試 |

系統需求：Windows＋PowerPoint（桌面版，COM 匯出用）＋微軟正黑體（`C:\Windows\Fonts\msjh.ttc`）。

## 重建命令（全部參數化；目標已存在即拒絕，`--force` 才覆寫）

```bash
RUN=outputs/proposal_delivery/<新run_id>
# 1) 共享數據主檔（唯讀重算＋與補驗 descriptive_counts.csv 交叉斷言）
.venv/Scripts/python.exe slides/source/build_stats_master.py --out $RUN/stats_master.json
# 2) 圖表素材（讀 stats_master＋封存評估 JSON＋parquet 唯讀 purge 日期）
.venv/Scripts/python.exe slides/source/make_assets.py --out slides/assets_<版本> --stats $RUN/stats_master.json
# 3) 講稿底稿（單一來源：SLIDE_NOTES.md 與 PPT 備註同源）
#    編輯 slides/source/notes_v2.json 後：
.venv/Scripts/python.exe slides/source/make_slide_notes.py --force
# 4) PPTX（notes/數字/素材皆由參數讀入）
.venv/Scripts/python.exe slides/source/make_pptx.py --pptx slides/TW01_..._v2.pptx --assets slides/assets_v2 --notes slides/source/notes_v2.json --stats $RUN/stats_master.json
# 5) PDF＋逐頁 PNG（COM；render_meta.json 記錄頁數一致性）
.venv/Scripts/python.exe slides/source/export_and_render.py --pptx slides/TW01_..._v2.pptx --render $RUN/slides_render_v2
# 6) 測試（數值/slide_id/同源/缺圖失敗/防覆寫/頁數）
.venv/Scripts/python.exe -m pytest slides/source/test_make_tools.py -q
```

## 檔案說明

| 檔案 | 角色 |
| --- | --- |
| `build_stats_master.py` | 唯讀重算 descriptive/eval/purge/splits → `stats_master.json`（與獨立補驗交叉核對） |
| `make_assets.py` | 6 張圖（volatility/f1/mae/time_split/by_crop/confusion）→ 版本化素材目錄 |
| `notes_v2.json` | 19 頁講稿／來源／秒數之**單一底稿** |
| `make_slide_notes.py` | notes_v2.json → `docs/SLIDE_NOTES.md` |
| `make_pptx.py` | notes_v2.json＋stats_master＋素材 → PPTX（備註同源寫入） |
| `export_and_render.py` | COM 匯出 PDF/PNG＋頁數核對（安全 Close/Quit） |
| `test_make_tools.py` | 15 項製作工具測試 |

## 邊界

- 製作鏈只唯讀正式資料（parquet/封存 JSON/原始 JSON），不修改任何產品檔。
- v1 產物（`slides/TW01_..._v1.pptx/.pdf`、`slides/assets/`、run1）受保護不覆寫。
- 依賴清單為現有環境盤點；「乾淨環境完整重建驗證」未執行，屬實列未驗。
