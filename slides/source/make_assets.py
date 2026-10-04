# -*- coding: utf-8 -*-
"""圖表素材生成（D44-R06 v2 參數化）：數值同源 stats_master.json／封存評估 JSON／parquet(唯讀 purge 日期)。

執行範例：
  .venv/Scripts/python.exe slides/source/make_assets.py \
    --out slides/assets_v2 \
    --stats outputs/proposal_delivery/run2_20261004_01/stats_master.json
未指定 --force 時，目標目錄內同名檔案已存在即拒絕（保護 v1 素材）。
"""
import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

plt.rcParams["font.sans-serif"] = ["Microsoft JhengHei", "Microsoft YaHei", "Arial"]
plt.rcParams["axes.unicode_minus"] = False


def savefig(fig, out_dir: Path, name, desc, summary, force=False):
    fig.tight_layout()
    target = out_dir / f"{name}.png"
    if target.exists() and not force:
        print(f"REFUSE: {target} 已存在（用 --force 覆寫）", file=sys.stderr)
        raise SystemExit(2)
    fig.savefig(target, dpi=200, bbox_inches="tight")
    plt.close(fig)
    summary[name] = desc
    print("saved", name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="素材輸出目錄（版本化，如 slides/assets_v2）")
    ap.add_argument("--stats", required=True, help="run2 stats_master.json（共享數據源）")
    ap.add_argument("--force", action="store_true", help="允許覆寫既有檔案")
    args = ap.parse_args()

    out_dir = Path(args.out)
    if out_dir.exists() and any(out_dir.glob("*.png")) and not args.force:
        print(f"REFUSE: {out_dir} 內已有素材（用 --force 覆寫）", file=sys.stderr)
        raise SystemExit(2)
    out_dir.mkdir(parents=True, exist_ok=True)

    stats = json.loads(Path(args.stats).read_text(encoding="utf-8"))
    EVAL = json.loads((ROOT / "outputs/evaluation/public/public_test_results.json").read_text(encoding="utf-8"))
    desc = stats["descriptive"]
    summary = {}

    # ---------- 圖1：價格波動（動機）——數字來自 stats_master ----------
    crops = [("cabbage", "甘藍"), ("bok_choy", "青江白菜"), ("sponge_gourd", "絲瓜")]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    w = 0.35
    xs = [0, 1, 2]
    for i, h in enumerate((7, 14)):
        vals = [desc[f"h{h}|{cid}"]["percent_display"] for cid, _ in crops]
        vals_n = [float(v.rstrip("%")) for v in vals]
        ns = [desc[f"h{h}|{cid}"]["n"] for cid, _ in crops]
        bars = ax.bar([x + (i - 0.5) * w for x in xs], vals_n, w, label=f"{h} 天後")
        for b, v, n in zip(bars, vals_n, ns):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.3, f"{v:.1f}%\n(n={n})", ha="center", fontsize=8)
    ax.set_ylim(0, 24)
    ax.set_xticks(xs)
    ax.set_xticklabels([cn for _, cn in crops])
    ax.set_ylabel("7／14 天相對變化超過 ±5% 的比例（%）")
    ax.set_title("蔬菜市場均價一年內的明顯變動比例（臺中公開資料；正式口徑 ±5% 含邊界）")
    ax.legend()
    savefig(fig, out_dir, "volatility",
            "動機：分品項 |r|>5% 比例，來源 run2 stats_master.json（features_labels.parquet 正式 direction；"
            f"合併 h7={desc['h7|ALL']['nonflat']}/{desc['h7|ALL']['n']}={desc['h7|ALL']['percent_display']}、"
            f"h14={desc['h14|ALL']['nonflat']}/{desc['h14|ALL']['n']}={desc['h14|ALL']['percent_display']}）", summary, args.force)

    # ---------- 圖2：模型 vs 基線 macro-F1（封存 JSON；修正「=7天」標籤） ----------
    fig, ax = plt.subplots(figsize=(8, 4.2))
    labels, series = [], {"選定模型": [], "全持平基線": [], "動量基線": []}
    for h in ("h=7", "h=14"):
        e = EVAL["horizons"][h]
        labels.append(f"{h.replace('h=', '')}天 (n={e['n']})")
        series["選定模型"].append(e["selected"]["direction"]["macro_f1"])
        series["全持平基線"].append(e["baselines"]["flat_no_change"]["direction"]["macro_f1"])
        series["動量基線"].append(e["baselines"]["past_change_continues"]["direction"]["macro_f1"])
    xs = [0, 1]
    for i, (name, vals) in enumerate(series.items()):
        bars = ax.bar([x + (i - 1) * 0.25 for x in xs], vals, 0.25, label=name)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.005, f"{v:.4f}", ha="center", fontsize=8)
    ax.set_ylim(0, 0.55)
    ax.set_xticks(xs)
    ax.set_xticklabels(labels)
    ax.set_ylabel("方向 macro-F1（up/flat/down）")
    ax.set_title("模型 vs 兩個強基線（封存測試；未勝動量——負向結果如實呈現）")
    ax.legend(fontsize=8)
    savefig(fig, out_dir, "f1_vs_baselines", "封存測試 macro-F1 對比，來源 public_test_results.json（SHA256 2d28acd2…）", summary, args.force)

    # ---------- 圖3：點估計 MAE 負向結果（封存 JSON） ----------
    fig, ax = plt.subplots(figsize=(8, 3.8))
    mae_m, mae_f, lbl = [], [], []
    for h in ("h=7", "h=14"):
        e = EVAL["horizons"][h]
        mae_m.append(e["selected"]["return_mae"])
        mae_f.append(e["baselines"]["flat_no_change"]["return_mae"])
        lbl.append(f"{h.replace('h=', '')}天")
    xs = [0, 1]
    b1 = ax.bar([x - 0.17 for x in xs], mae_m, 0.32, label="選定模型")
    b2 = ax.bar([x + 0.17 for x in xs], mae_f, 0.32, label="不變價基線")
    for bs in (b1, b2):
        for b in bs:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.001, f"{b.get_height():.4f}", ha="center", fontsize=8)
    ax.set_xticks(xs)
    ax.set_xticklabels(lbl)
    ax.set_ylabel("相對變化 MAE（非元、非準確率）")
    ax.set_title("點估計誤差：模型未優於不變價基線（負向結果，如實呈現）")
    ax.legend(fontsize=8)
    savefig(fig, out_dir, "mae_negative", "負向結果：return MAE 對比，來源 public_test_results.json", summary, args.force)

    # ---------- 圖4：時間切分＋真實成熟清除帶（parquet 唯讀 purge 分組；期限別 t+h+1） ----------
    df = pd.read_parquet(ROOT / "data/processed/features_labels.parquet")
    pu = df[df["purge_reason"].notna()]

    def seg(reason, h):
        s = pu[(pu["purge_reason"] == reason) & (pu["horizon_days"] == h)]
        return pd.Timestamp(s["t"].min()), pd.Timestamp(s["t"].max()), int(len(s)), int(s["t"].nunique())

    t1a, t1b, n1a, d1a = seg("train_label_not_mature_before_val", 7)
    t2a, t2b, n2a, d2a = seg("train_label_not_mature_before_val", 14)
    t3a, t3b, n3a, d3a = seg("val_label_not_mature_before_test", 7)
    t4a, t4b, n4a, d4a = seg("val_label_not_mature_before_test", 14)
    fig, ax = plt.subplots(figsize=(10, 3.4))
    sp = stats["splits"]
    bands = [
        ("train", pd.Timestamp(sp["train"]["t_min"]), pd.Timestamp(sp["train"]["t_max"]), "#2E75B6"),
        ("validation", pd.Timestamp(sp["validation"]["t_min"]), pd.Timestamp(sp["validation"]["t_max"]), "#70AD47"),
        ("test（封存）", pd.Timestamp(sp["test"]["t_min"]), pd.Timestamp(sp["test"]["t_max"]), "#B03030"),
    ]
    for name, t0, t1, c in bands:
        ax.barh(0, (t1 - t0).days, left=t0, height=0.5, color=c, alpha=0.75, label=name)
        ax.text(t0 + (t1 - t0) / 2, 0.38, f"{name}\n{t0.date()}～{t1.date()}", ha="center", fontsize=8)
    clears = [
        (t2a, t2b, 0.80, pd.Timestamp("2025-12-01"), "left",
         f"成熟清除① train→validation（成熟日 t+h+1）\nh7：{t1a.date()}～{t1b.date()}（{d1a} 日、{n1a} 列）   h14：{t2a.date()}～{t2b.date()}（{d2a} 日、{n2a} 列）"),
        (t4a, t4b, -1.24, pd.Timestamp("2026-01-05"), "left",
         f"成熟清除② validation→test\nh7：{t3a.date()}～{t3b.date()}（{d3a} 日、{n3a} 列）   h14：{t4a.date()}～{t4b.date()}（{d4a} 日、{n4a} 列）"),
    ]
    for t0, t1, yy, tx, ha, lab in clears:
        ax.barh(0, (t1 - t0).days, left=t0, height=0.5, color="none", edgecolor="black", linewidth=2.2)
        ax.annotate(lab, xy=(t0 + (t1 - t0) / 2, 0.25), xytext=(tx, yy),
                    fontsize=7.5, ha=ha, va="bottom", arrowprops=dict(arrowstyle="->", lw=1))
    ax.set_ylim(-1.7, 1.5)
    ax.set_yticks([])
    ax.set_xlim(pd.Timestamp("2025-09-20"), pd.Timestamp("2026-10-15"))
    ax.set_title("時間切分與實際成熟清除帶（合計 1,386 列／聯集 30 起算日；h7 與 h14 帶長不同：8 日 vs 15 日；同日 13 市場同區）")
    ax.legend(loc="upper left", fontsize=8)
    savefig(fig, out_dir, "time_split", "切分＋真實 purge 分組：features_labels.parquet purge_reason 唯讀重算（與複審同口徑）", summary, args.force)

    # ---------- 圖5：分品項 macro-F1（封存 JSON 頂層 by_crop） ----------
    fig, ax = plt.subplots(figsize=(9, 4))
    byc = EVAL.get("by_crop", {})
    xs, vals, lab = [], [], []
    for i, h in enumerate((7, 14)):
        for j, cid in enumerate(["cabbage", "bok_choy", "sponge_gourd"]):
            k = f"h={h}|{cid}"
            if k in byc:
                xs.append(i * 3.6 + j)
                vals.append(byc[k]["macro_f1"])
                lab.append(f"{cn_map[cid]}\n{h}天 (n={byc[k]['n']})")
    if not xs:
        print("FAIL: 封存 JSON 缺 by_crop", file=sys.stderr)
        raise SystemExit(3)
    ax.bar(xs, vals, 0.8, color="#2E75B6")
    for x, v in zip(xs, vals):
        ax.text(x, v + 0.008, f"{v:.3f}", ha="center", fontsize=8)
    ax.set_xticks(xs)
    ax.set_xticklabels(lab, fontsize=8)
    ax.set_ylim(0, 0.6)
    ax.set_ylabel("方向 macro-F1")
    ax.set_title("分品項 macro-F1（甘藍方向事件最少、分數最低——此為觀察，因果待驗證）")
    savefig(fig, out_dir, "by_crop", "分品項成績，來源 public_test_results.json 頂層 by_crop", summary, args.force)

    # ---------- 圖6：7 天混淆矩陣（封存 JSON confusion_matrix/labels） ----------
    d7 = EVAL["horizons"]["h=7"]["selected"]["direction"]
    cm = d7.get("confusion_matrix")
    lbls = d7.get("confusion_labels", ["down", "flat", "up"])
    fig, ax = plt.subplots(figsize=(7, 5.6))
    if not cm:
        print("FAIL: 封存 JSON 缺 confusion_matrix", file=sys.stderr)
        raise SystemExit(3)
    import numpy as np
    mat = np.array(cm)
    names3 = ["down", "flat", "up"]
    order = [lbls.index(c) for c in names3]
    mat = mat[np.ix_(order, order)]
    im = ax.imshow(mat, cmap="Blues")
    for i in range(3):
        for j in range(3):
            ax.text(j, i, mat[i, j], ha="center", va="center", fontsize=10,
                    color="white" if mat[i, j] > mat.max() / 2 else "black")
    ax.set_xticks(range(3)); ax.set_xticklabels([f"預測 {o}" for o in names3])
    ax.set_yticks(range(3)); ax.set_yticklabels([f"實際 {o}" for o in names3])
    fig.colorbar(im, ax=ax, shrink=0.8)
    ax.set_title("7 天方向混淆矩陣（列=實際；RF；up 召回 16/158 約 10.1%）")
    savefig(fig, out_dir, "confusion_h7", "混淆矩陣，來源 public_test_results.json confusion（封存）", summary, args.force)

    (out_dir / "assets_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("assets done:", len(summary))


cn_map = {"cabbage": "甘藍", "bok_choy": "青江白菜", "sponge_gourd": "絲瓜"}

if __name__ == "__main__":
    main()
