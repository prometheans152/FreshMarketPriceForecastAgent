# -*- coding: utf-8 -*-
"""P6 圖表素材生成：全部數值來自凍結工件，圖上標目標/期限/單位/樣本與來源。

執行：.venv/Scripts/python.exe slides/source/make_assets.py
產出：slides/assets/*.png + slides/assets/assets_summary.json
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "slides" / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

plt.rcParams["font.sans-serif"] = ["Microsoft JhengHei", "Microsoft YaHei", "Arial"]
plt.rcParams["axes.unicode_minus"] = False

EVAL = json.loads((ROOT / "outputs/evaluation/public/public_test_results.json").read_text(encoding="utf-8"))
DATA = pd.read_parquet(ROOT / "data/processed/features_labels.parquet")

summary = {}


def savefig(fig, name, desc):
    fig.tight_layout()
    fig.savefig(ASSETS / f"{name}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    summary[name] = desc
    print("saved", name)


# ---------- 圖1：價格波動（動機） ----------
df = DATA[DATA["direction"] != "insufficient_data"]
rows = []
for h in (7, 14):
    sub = df[df["horizon_days"] == h]
    for crop, cn in [("cabbage", "甘藍"), ("bok_choy", "青江白菜"), ("sponge_gourd", "絲瓜")]:
        s = sub[sub["crop_id"] == crop]
        move = (~s["direction"].isin(["flat"])).mean() * 100
        rows.append((cn, h, move, len(s)))
fig, ax = plt.subplots(figsize=(8, 4.2))
w = 0.35
xs = [0, 1, 2]
for i, h in enumerate((7, 14)):
    vals = [r[2] for r in rows if r[1] == h]
    ns = [r[3] for r in rows if r[1] == h]
    bars = ax.bar([x + (i - 0.5) * w for x in xs], vals, w, label=f"{h} 天後")
    for b, v, n in zip(bars, vals, ns):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.4, f"{v:.1f}%\n(n={n})", ha="center", fontsize=8)
ax.set_ylim(0, max(r[2] for r in rows) * 1.32)
ax.set_xticks(xs)
ax.set_xticklabels([r[0] for r in rows if r[1] == 7])
ax.set_ylabel("7／14 天相對變化超過 ±5% 的比例（%）")
ax.set_title("蔬菜市場均價一年內的明顯變動比例（臺中公開資料）")
ax.legend()
savefig(fig, "volatility", "動機：各品項 |r|>5% 比例，來源 data/processed/features_labels.parquet（凍結 2026-10-03 快照）")

# ---------- 圖2：模型 vs 基線 macro-F1 ----------
fig, ax = plt.subplots(figsize=(8, 4.2))
labels, series = [], {"選定模型": [], "全持平基線": [], "動量基線": []}
for h in ("h=7", "h=14"):
    e = EVAL["horizons"][h]
    labels.append(f"{h[-2:]}天 (n={e['n']})")
    series["選定模型"].append(e["selected"]["direction"]["macro_f1"])
    series["全持平基線"].append(e["baselines"]["flat_no_change"]["direction"]["macro_f1"])
    series["動量基線"].append(e["baselines"]["past_change_continues"]["direction"]["macro_f1"])
w = 0.25
for i, (name, vals) in enumerate(series.items()):
    bars = ax.bar([x + (i - 1) * w for x in range(len(labels))], vals, w, label=name)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.005, f"{v:.3f}", ha="center", fontsize=8)
ax.set_xticks(range(len(labels)))
ax.set_xticklabels(labels)
ax.set_ylabel("方向三類 macro-F1（越高越好）")
ax.set_ylim(0, 0.55)
ax.set_title("封存測試：方向 macro-F1 與基線比較（公開市場均價）")
ax.legend()
savefig(fig, "f1_vs_baselines", "來源 outputs/evaluation/public/public_test_results.json（SHA256 2d28acd2…）")

# ---------- 圖3：報酬 MAE（負向結果） ----------
fig, ax = plt.subplots(figsize=(8, 3.8))
labels, sel, flat = [], [], []
for h in ("h=7", "h=14"):
    e = EVAL["horizons"][h]
    labels.append(f"{h[-2:]}天")
    sel.append(e["selected"]["return_mae"])
    flat.append(e["baselines"]["flat_no_change"]["return_mae"])
w = 0.35
b1 = ax.bar([x - w / 2 for x in range(2)], sel, w, label="選定模型")
b2 = ax.bar([x + w / 2 for x in range(2)], flat, w, label="不變價基線")
for bs in (b1, b2):
    for b in bs:
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.001, f"{b.get_height():.4f}", ha="center", fontsize=8)
ax.set_xticks(range(2))
ax.set_xticklabels(labels)
ax.set_ylabel("相對變化 r 的 MAE（越低越好；非元、非準確率）")
ax.set_title("點估計誤差：模型未優於不變價基線（負向結果，如實呈現）")
ax.legend()
savefig(fig, "mae_negative", "同上來源；點估計未勝基線為本案明示限制")

# ---------- 圖4：時間切分 ----------
fig, ax = plt.subplots(figsize=(9, 2.8))
import matplotlib.patches as mpatches

segs = [
    ("訓練", "2025-10-04", "2026-05-08", "#4C72B0"),
    ("驗證（選型）", "2026-05-10", "2026-07-21", "#DD8452"),
    ("封存測試（一次性）", "2026-07-22", "2026-10-02", "#55A868"),
]
import matplotlib.dates as mdates

x0, x1 = pd.Timestamp("2025-09-20"), pd.Timestamp("2026-10-20")
for i, (name, s, e, c) in enumerate(segs):
    ax.barh(0, (pd.Timestamp(e) - pd.Timestamp(s)).days, left=mdates.date2num(pd.Timestamp(s)), height=0.5, color=c, edgecolor="white")
    ax.text(mdates.date2num(pd.Timestamp(s)) + (pd.Timestamp(e) - pd.Timestamp(s)).days / 2, 0, name, ha="center", va="center", fontsize=9, color="white", fontweight="bold")
ax.text(mdates.date2num(pd.Timestamp("2026-05-09")), 0.45, "成熟清除（14+1天）", ha="center", fontsize=7, rotation=0, color="#666")
ax.set_xlim(mdates.date2num(x0), mdates.date2num(x1))
ax.set_ylim(-0.6, 0.8)
ax.set_yticks([])
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
ax.set_title("時間切分：同日多市場同區；標籤成熟後才跨區（凍結清單 SHA256 4e136574…）")
for sp in ("top", "right", "left"):
    ax.spines[sp].set_visible(False)
savefig(fig, "time_split", "來源 manifest.json splits + outputs/splits/split_list.csv")

# ---------- 圖5：分品項 macro-F1（附錄） ----------
fig, ax = plt.subplots(figsize=(8, 4))
byc = EVAL["by_crop"]
names = {"cabbage": "甘藍", "bok_choy": "青江白菜", "sponge_gourd": "絲瓜"}
w = 0.35
for i, h in enumerate((7, 14)):
    vals = [byc[f"h={h}|{c}"]["macro_f1"] for c in names]
    ns = [byc[f"h={h}|{c}"]["n"] for c in names]
    bars = ax.bar([x + (i - 0.5) * w for x in range(3)], vals, w, label=f"{h} 天")
    for b, v, n in zip(bars, vals, ns):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.005, f"{v:.2f}\n(n={n})", ha="center", fontsize=8)
ax.set_xticks(range(3))
ax.set_xticklabels(list(names.values()))
ax.set_ylabel("macro-F1")
ax.set_ylim(0, 0.6)
ax.set_title("分品項方向 macro-F1（公開市場均價測試）")
ax.legend()
savefig(fig, "by_crop", "來源 public_test_results.json by_crop")

# ---------- 圖6：混淆矩陣 h7（附錄） ----------
import numpy as np

cm = EVAL["horizons"]["h=7"]["selected"]["direction"]["confusion_matrix"]
lbl = EVAL["horizons"]["h=7"]["selected"]["direction"]["confusion_labels"]
zh = {"down": "跌", "flat": "平", "up": "漲"}
fig, ax = plt.subplots(figsize=(4.6, 4.2))
im = ax.imshow(cm, cmap="Blues")
ax.set_xticks(range(3)); ax.set_yticks(range(3))
ax.set_xticklabels([f"預測{zh[l]}" for l in lbl])
ax.set_yticklabels([f"實際{zh[l]}" for l in lbl])
for i in range(3):
    for j in range(3):
        ax.text(j, i, str(cm[i][j]), ha="center", va="center", fontsize=11,
                color="white" if cm[i][j] > max(map(max, cm)) / 2 else "black")
ax.set_title("7 天混淆矩陣（列=實際；RF）")
fig.colorbar(im, shrink=0.8)
savefig(fig, "confusion_h7", f"來源同上；漲召回偏低為明示限制（up recall ≈ 10%）")

(ASSETS / "assets_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print("\nassets done:", len(summary))
