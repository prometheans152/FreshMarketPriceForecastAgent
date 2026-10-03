"""模型選擇（T13）：依預先固定標準由驗證結果選型，記錄理由與限制。

選擇標準（凍結於 2026-10-03，看測試前）：
- 主指標：驗證集方向 macro-F1（產品核心是漲跌提示；accuracy 被持平多數主導）
- 點預測（r 的 MAE）未優於「不變價」基線 → 價格估計須標註限制，不作強宣稱
- 機率／區間：本版不做校準驗證 → 一律不輸出（validation_scope 誠實標示）
"""

from __future__ import annotations

import json
from pathlib import Path

SELECTION_RULE = {
    "primary_metric": "validation direction macro_f1",
    "fallback_if_no_model_beats_flat_accuracy": "仍選 macro_f1 最佳者，但回應標註方向能力有限",
    "probability_policy": "not_calibrated_not_provided",
    "chosen": {"h=7": "rf_reg", "h=14": "hgb_reg"},
}


def select_models(results_path: str | Path = "outputs/training/training_results.json") -> dict:
    with open(results_path, encoding="utf-8") as f:
        results = json.load(f)
    selection: dict = {"rule": SELECTION_RULE, "horizons": {}}
    for h, res in results["horizons"].items():
        candidates: dict = {}
        for name, m in res["regression"].items():
            candidates[name] = {
                "macro_f1": m["direction"]["macro_f1"],
                "accuracy": m["direction"]["accuracy"],
                "return_mae": m["return_mae"],
            }
        for name, m in res["classification"].items():
            candidates[name] = {
                "macro_f1": m["macro_f1"],
                "accuracy": m["accuracy"],
                "return_mae": None,
            }
        best = max(candidates, key=lambda k: candidates[k]["macro_f1"])
        flat_f1 = res["baselines"]["flat_no_change"]["direction"]["macro_f1"]
        flat_mae = res["baselines"]["flat_no_change"]["return_mae"]
        best_mae = candidates[best]["return_mae"]
        selection["horizons"][h] = {
            "candidates": candidates,
            "selected": best,
            "selected_macro_f1": candidates[best]["macro_f1"],
            "flat_baseline_macro_f1": flat_f1,
            "flat_baseline_return_mae": flat_mae,
            "selected_return_mae": best_mae,
            "beats_flat_on_macro_f1": bool(candidates[best]["macro_f1"] > flat_f1),
            "beats_flat_on_return_mae": bool(best_mae is not None and best_mae < flat_mae),
            "claims_allowed": {
                "direction_macro_f1_vs_flat": True,
                "point_return_beats_flat": bool(best_mae is not None and best_mae < flat_mae),
                "probability_or_interval": False,
            },
        }
    out = Path("outputs/training") / "model_selection.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(selection, f, ensure_ascii=False, indent=2)
    return selection


if __name__ == "__main__":
    sel = select_models()
    print(json.dumps(sel, ensure_ascii=False, indent=2)[:3000])
