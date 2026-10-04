# -*- coding: utf-8 -*-
"""D44-R03：建立本輪共享數據主檔 stats_master.json（唯讀重算，不改任何正式工件）。

執行：.venv/Scripts/python.exe slides/source/build_stats_master.py --out <run_dir>/stats_master.json
規則：與正式 labels 相同口徑（±5% 含邊界、eps=1e-9，直接採 parquet 已存 direction）；
     與補驗 descriptive_counts.csv 逐值斷言一致（交叉核對，不通過即失敗退出）。
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="輸出 stats_master.json 路徑（不得存在）")
    ap.add_argument("--crosscheck", default=str(ROOT / "outputs/audits/d44_resume_6eb4adf_20261004_01/descriptive_counts.csv"))
    args = ap.parse_args()

    out = Path(args.out)
    if out.exists():
        print(f"REFUSE: {out} 已存在，不覆寫", file=sys.stderr)
        return 2

    pq = ROOT / "data/processed/features_labels.parquet"
    ev = ROOT / "outputs/evaluation/public/public_test_results.json"
    prep = ROOT / "outputs/data_quality/prepare_summary.json"

    df = pd.read_parquet(pq)
    valid = df[df["direction"] != "insufficient_data"]

    desc = {}
    crop_map = {"cabbage": "cabbage", "bok_choy": "bok_choy", "sponge_gourd": "sponge_gourd"}
    for h in (7, 14):
        sub = valid[valid["horizon_days"] == h]
        for cid in ["ALL"] + list(crop_map):
            s = sub if cid == "ALL" else sub[sub["crop_id"] == cid]
            n = len(s)
            up = int((s["direction"] == "up").sum())
            down = int((s["direction"] == "down").sum())
            nonflat = up + down
            pct = nonflat / n * 100 if n else float("nan")
            flat = int((s["direction"] == "flat").sum())
            exactly_same = int((s["relative_change"] == 0).sum())
            desc[f"h{h}|{cid}"] = {
                "n": n, "up": up, "down": down, "flat": flat, "nonflat": nonflat,
                "percent_exact": pct, "percent_display": f"{round(pct, 1):.1f}%",
                "same_price_share_display": f"{exactly_same / n * 100:.1f}%" if n else "-",
                "n_markets": int(s["market_id"].nunique()),
                "origin_t_max": str(pd.to_datetime(s["t"]).max().date()),
            }

    # 交叉核對：與補驗 descriptive_counts.csv 一致（分子/分母/顯示值）
    cc_path = Path(args.crosscheck)
    if cc_path.exists():
        cc = pd.read_csv(cc_path)
        mismatches = []
        for _, r in cc.iterrows():
            key = f"h{int(r['horizon_days'])}|{'ALL' if r['crop_id'] == 'ALL' else r['crop_id']}"
            d = desc.get(key)
            if d is None:
                mismatches.append(f"{key} missing")
                continue
            if d["nonflat"] != int(r["nonflat_numerator"]) or d["n"] != int(r["valid_rows"]) or d["percent_display"] != str(r["nonflat_display_1dp"]):
                mismatches.append(f"{key}: mine {d['nonflat']}/{d['n']}={d['percent_display']} vs csv {r['nonflat_numerator']}/{r['valid_rows']}={r['nonflat_display_1dp']}")
        if mismatches:
            print("CROSSCHECK FAILED:", mismatches, file=sys.stderr)
            return 3
        crosscheck = f"passed ({len(cc)} data rows: nonflat/n/display all match)"
    else:
        crosscheck = "skipped (crosscheck csv not found)"

    # 浮點邊界（僅記錄，不作正式口徑）
    boundary = {}
    for h in (7, 14):
        sub = valid[valid["horizon_days"] == h]
        raw = sub[sub["relative_change"].abs() > 0.05]
        boundary[f"h{h}"] = {"raw_abs_gt_005": int(len(raw)), "minus_label": int(len(raw)) - int((sub["direction"] != "flat").sum())}

    # 封存評估數字（唯讀抽取）
    evj = json.loads(ev.read_text(encoding="utf-8"))
    eval_out = {}
    for h in ("h=7", "h=14"):
        e = evj["horizons"][h]
        eval_out[h] = {
            "n": e["n"],
            "selected_direction_macro_f1": e["selected"]["direction"]["macro_f1"],
            "baseline_flat": e["baselines"]["flat_no_change"]["direction"]["macro_f1"],
            "baseline_momentum": e["baselines"]["past_change_continues"]["direction"]["macro_f1"],
        }

    # purge 真實分布（R05 時間軸圖依據；期限別分組 t+h+1）
    pu = df[df["purge_reason"].notna()]

    def seg(reason, h):
        s2 = pu[(pu["purge_reason"] == reason) & (pu["horizon_days"] == h)]
        return {"t_min": str(pd.to_datetime(s2["t"]).min().date()), "t_max": str(pd.to_datetime(s2["t"]).max().date()),
                "dates": int(s2["t"].nunique()), "rows": int(len(s2))}

    purge = {
        "rows": int(len(pu)),
        "distinct_t": int(pu["t"].nunique()),
        "reasons": {k: int(v) for k, v in pu["purge_reason"].value_counts().items()},
        "per_horizon": {str(k): int(v) for k, v in pu.groupby("horizon_days").size().items()},
        "segments": {
            "train_to_val": {"h7": seg("train_label_not_mature_before_val", 7), "h14": seg("train_label_not_mature_before_val", 14)},
            "val_to_test": {"h7": seg("val_label_not_mature_before_test", 7), "h14": seg("val_label_not_mature_before_test", 14)},
        },
        "maturity_rule": "標籤成熟日 = t+h+1（7天目標 t+8、14天目標 t+15）",
        "t_min": str(pd.to_datetime(pu["t"]).min().date()),
        "t_max": str(pd.to_datetime(pu["t"]).max().date()),
    }

    # 切分區間
    splits = {}
    for sp, g in df[df["split"].notna()].groupby("split"):
        splits[sp] = {"t_min": str(pd.to_datetime(g["t"]).min().date()), "t_max": str(pd.to_datetime(g["t"]).max().date()), "rows": int(len(g))}

    prepj = json.loads(prep.read_text(encoding="utf-8"))
    train_dir = prepj.get("split_stats", {}).get("train", {}).get("direction_counts", {})

    master = {
        "meta": {
            "built_by": "slides/source/build_stats_master.py",
            "built_date": "2026-10-04",
            "population": "公開市場×品項×起算日×期限歷史觀測（含各 split，排除 insufficient_data）；描述統計，非未來機率",
            "threshold": "±5% 含邊界（|r|<=5% flat），epsilon=1e-9；直接採 parquet 既有 direction 欄",
            "sources_sha256": {
                "features_labels.parquet": sha256(pq),
                "public_test_results.json": sha256(ev),
                "prepare_summary.json": sha256(prep),
            },
            "crosscheck_vs_resume_audit": crosscheck,
        },
        "descriptive": desc,
        "float_boundary_note": {
            **boundary,
            "note": "直接 abs(r)>0.05 會比正式標籤多算 h7 7 列、h14 14 列（皆絲瓜、恰在 1e-9 容差邊界、正式為 flat）；正式口徑採已存 direction",
        },
        "eval": eval_out,
        "train_direction_counts": train_dir,
        "purge": purge,
        "splits": splits,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(master, ensure_ascii=False, indent=2), encoding="utf-8")
    print("saved:", out)
    print("crosscheck:", crosscheck)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
