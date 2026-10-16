"""Turn the existing 61-item public website into a truthfully trained-ML site.

Only display-method metadata and the explanatory labels change; JS behavior,
original name "菜市場現場價格預測", A/B UI, browser records and public data
prices/dates are preserved. Source catalog/model release bytes remain intact.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from build_web_assets import replace_once

OLD_HINT = (
    "此品項使用「未訓練的歷史趨勢基準」，不是 RF／HGB 已訓練模型，"
    "也沒有真店準確度驗證。"
)
NEW_HINT = (
    "此品項使用真正訓練的 HGB 監督式 ML 模型（57 品項共同訓練），"
    "7／14 天各有一個模型。時間留出測試 MAE 仍未優於不變價基準；"
    "同店到期準確度尚未驗證。"
)
OLD_FOOTER = (
    "官方 61 個價格欄有 60 項曾有有效行情；牛心柿全部缺測。"
    "只有原三項使用凍結 RF/HGB，其他為未訓練歷史趨勢基準。全部皆非單店真值驗證。"
)
NEW_FOOTER = (
    "官方資料共 61 項，60 項有歷史價格；原三品項保留凍結 RF/HGB，"
    "其餘 57 項使用獨立訓練的 HGB ML 模型（7／14 天）。"
    "牛心柿無有效行情不可預測；模型 MAE 未勝不變價基準，且未經同店到期驗證。"
)


def build(previous: Path, output: Path, trained: dict):
    if output.exists():
        raise FileExistsError("Refusing overwrite of existing website bundle")
    if trained.get("model_version") != "multi-crop-ml/1.0.0":
        raise ValueError("Unexpected ML release")
    trained_ids = set(trained["trained_crop_ids"])
    if len(trained_ids) != 57:
        raise ValueError("Expected 57 trained new crops")
    old_js = (previous / "app.js").read_text(encoding="utf-8")
    raw = old_js.split("const CROPS = ", 1)
    if len(raw) != 2:
        raise ValueError("Missing catalog source declaration")
    source = raw[1].split(";\n", 1)[0]
    items = json.loads(source)
    if len(items) != 61:
        raise ValueError("Expected full catalog embedded in JS")
    old_catalog = json.loads((previous / "catalog.json").read_text(encoding="utf-8"))
    if len(old_catalog["items"]) != 61:
        raise ValueError("Expected full catalog in public JSON")
    by_id = {e["crop_id"]: e for e in old_catalog["items"]}
    for item in items:
        cid = item["id"]
        if cid in trained_ids:
            if item["method"] != "historical_momentum_baseline":
                raise ValueError("Unexpected old public method for " + cid)
            item["method"] = "trained_pooled_hgb_ml_1.0.0"
            item["model_version"] = trained["model_version"]
            by_id[cid]["method"] = "trained_pooled_hgb_ml_1.0.0"
            by_id[cid]["model_version"] = trained["model_version"]
            by_id[cid]["training_coverage"] = "pooled_cross_crop_supervised_learning"
        elif cid == "taichung_25":
            if item["has_data"]:
                raise ValueError("No-data fruit cannot be predicted")
            item["method"] = "no_public_price"
            by_id[cid]["method"] = "no_public_price"
        elif cid in {"cabbage", "bok_choy", "sponge_gourd"}:
            if item["method"] != "frozen_rf_hgb_v0.1.0":
                raise ValueError("Cannot change a frozen crop's method")
        else:
            raise ValueError("Unexpected crop not covered by trained or frozen model")
    old_catalog["extended_ml_model_version"] = trained["model_version"]
    old_catalog["additional_trained_crop_count"] = 57
    old_catalog["frozen_original_crop_count"] = 3
    old_catalog["no_public_price_crop_count"] = 1
    old_catalog["model_warning"] = (
        "本新版 57 品項採用另外訓練的兩個 pooled HGB 模型；"
        "7/14 天模型留出測試的 MAE 都不如不變價基準；"
        "不是同店真價驗證。原三項 0.1.0 RF/HGB 不變。"
    )
    transformed_source = json.dumps(items, ensure_ascii=False, separators=(",", ":"))
    js = old_js.replace(
        "const CROPS = " + source + ";\n",
        "const CROPS = " + transformed_source + ";\n",
        1,
    )
    js = replace_once(js, OLD_HINT, NEW_HINT)
    html = (previous / "index.html").read_text(encoding="utf-8")
    if "<title>菜市場現場價格預測</title>" not in html:
        raise ValueError("User-approved website name must remain unchanged")
    html = replace_once(html, OLD_FOOTER, NEW_FOOTER)
    html = replace_once(
        html,
        "不需帳號密碼，支援 61 個官方市場品項（蔬菜、水果、魚肉蛋）；7／14 天來源與估計方法會明確標示。",
        "免帳密，完整 61 項市場行情；其中 60 項可依資料可用性提供已訓練的 ML 預測，"
        "每次會顯示模型版本、警示及 7／14 天結果。",
    )
    output.mkdir(parents=True)
    (output / "index.html").write_text(html, encoding="utf-8")
    (output / "app.js").write_text(js, encoding="utf-8")
    (output / "style.css").write_bytes((previous / "style.css").read_bytes())
    (output / "catalog.json").write_text(json.dumps(
        old_catalog, ensure_ascii=False, separators=(",", ":")
    ), encoding="utf-8")
    return {"status": "rebuilt", "trained_new_items": len(trained_ids),
            "frozen_items": 3, "unpriced_items": 1,
            "source_data_changed": False,
            "old_windows_web_changed": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--previous-site", type=Path, required=True)
    parser.add_argument("--ml-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build(
        args.previous_site, args.output,
        json.loads(args.ml_manifest.read_text(encoding="utf-8")),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
