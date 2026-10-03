"""本機推論入口（T19）：ForecastRequest → ForecastResponse。

共用推論：CLI（scripts/predict_local.py）、HTTP API（T20）、Qwen 工具（T26）。
推論不重新訓練；載入 T18 模型包並驗 hash；特徵由模型包內公開歷史即時建立
（與訓練同一 build_features，只向後看）。
起點 t＝使用者 observed_at 日期；公開資料截止與 t 分開回報。
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd

from aiot_price.data.labels import classify_direction
from aiot_price.data.schema import CROP_MAPPINGS, UnitError, resolve_crop, to_taiwan_jin
from aiot_price.features.build import build_features
from .baselines import FLAT_THRESHOLD
from .store_adapter import ALPHA_EXPERIMENTAL, check_b_input, experimental_b_return
from .train import build_design_matrix

MODE = ("without_last_week", "with_last_week", "both")
KNOWN_MARKETS = [
    "中義市場", "南屯市場", "合作市場", "大甲第二市場", "東光市場", "梧棲第一市場",
    "沙鹿市場", "清水第一市場", "第三市場", "第二市場", "第五市場", "豐原第一市場", "霧峰市場",
]
POINT_ESTIMATE_LIMITATION = "點估計 MAE 未優於不變價基線，僅供參考"
STORE_ESTIMATE_NOTE = "店價估計為現價錨定推估（公開市場變化×今天店價），未在同店驗證"
B_EXPERIMENTAL_NOTE = f"B 為實驗性規則（係數 {ALPHA_EXPERIMENTAL}），未經同店資料訓練或驗證"


def _parse_dt(s: str) -> datetime:
    return datetime.fromisoformat(s)


class ForecastEngine:
    """載入模型包並執行預測；不重新訓練。"""

    def __init__(self, release_dir: str | Path):
        self.release_dir = Path(release_dir)
        with open(self.release_dir / "manifest.json", encoding="utf-8") as f:
            self.manifest = json.load(f)
        self.models = {}
        for entry in self.manifest["models"]:
            path = self.release_dir / entry["file"]
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != entry["sha256"]:
                raise RuntimeError(f"模型檔 hash 不符：{path}（{actual[:12]}…≠{entry['sha256'][:12]}…）")
            self.models[entry["horizon_days"]] = joblib.load(path)
        self.history = pd.read_parquet(self.release_dir / "public_history.parquet")
        self.history["date"] = pd.to_datetime(self.history["date"])

    @property
    def public_cutoff(self) -> pd.Timestamp:
        """最新可見公開觀測日；即時計算，行情快取更新後自動跟著走。"""
        return self.history["date"].max()

    # ---------- 驗證 ----------

    def _validate(self, req: dict) -> tuple[dict | None, dict | None]:
        """回 (error, normalized)；error 符合 forecast.schema.json 的 error 欄位。"""
        try:
            crop_id = resolve_crop(req["crop_id"])
        except KeyError:
            supported = "、".join(m.display_name for m in CROP_MAPPINGS.values())
            return {"code": "unsupported_crop", "message": f"尚未支援此品項。目前支援：{supported}"}, None
        market_id = req.get("market_id")
        if market_id not in KNOWN_MARKETS:
            return {"code": "unsupported_market", "message": "不認得此參考市場；請由支援清單選擇臺中市場。"}, None
        try:
            price = float(req["current_price"])
            if price <= 0:
                raise ValueError
        except (KeyError, TypeError, ValueError):
            return {"code": "invalid_price", "message": "請輸入有效的今天價格（正數）。"}, None
        try:
            price_jin = to_taiwan_jin(price, req.get("price_unit", "unknown"))
        except UnitError as e:
            return {"code": "non_comparable_unit", "message": str(e)}, None
        try:
            observed_at = _parse_dt(req["observed_at"])
        except (KeyError, TypeError, ValueError):
            return {"code": "invalid_date", "message": "請提供含時區的報價時間（ISO8601）。"}, None
        mode = req.get("mode", "without_last_week")
        if mode not in MODE:
            return {"code": "bad_request", "message": f"mode 須為 {MODE} 之一。"}, None
        sanity = self.manifest.get("price_sanity_jin", {}).get(resolve_crop(req["crop_id"]))
        price_out_of_range = bool(
            sanity and (price_jin < sanity[0] or price_jin > sanity[1])
        )
        return None, {
            "crop_id": crop_id,
            "market_id": market_id,
            "price": price,
            "price_jin": price_jin,
            "price_unit": req.get("price_unit"),
            "observed_at": observed_at,
            "mode": mode,
            "store_id": req.get("store_id"),
            "price_out_of_range": price_out_of_range,
        }

    # ---------- 特徵與預測 ----------

    def _features_for(self, crop_id: str, market_id: str, t: pd.Timestamp) -> pd.DataFrame | None:
        sub = self.history[(self.history["crop_id"] == crop_id) & (self.history["market_id"] == market_id)]
        if sub.empty:
            return None
        feats = build_features(sub, [t], delay_days=self.manifest["features"]["visible_delay_days"])
        row = feats.loc[(market_id, crop_id, t)]
        if pd.isna(row["price_last"]):
            return None
        return row

    def _predict_return(self, crop_id: str, row: pd.DataFrame, h: int) -> float:
        model = self.models[h]
        X = build_design_matrix(
            pd.DataFrame([{**row.to_dict(), "crop_id": crop_id}])
        )
        cols = getattr(model, "feature_names_in_", None)
        if cols is not None:
            X = X.reindex(columns=cols, fill_value=0.0)
        return float(model.predict(X)[0])

    # ---------- 主流程 ----------

    def forecast(self, req: dict) -> dict:
        request_id = req.get("request_id") or f"req-{pd.Timestamp.now(tz='Asia/Taipei').strftime('%Y%m%d%H%M%S%f')}"
        error, n = self._validate(req)
        if error:
            return {"request_id": request_id, "mode_executed": None, "error": error, "results": []}

        t = pd.Timestamp(n["observed_at"].date())
        age_days = int((t - self.public_cutoff).days)
        warnings = []
        if age_days > 3:
            warnings.append(
                f"最新公開行情日期為 {self.public_cutoff.date()}（距今 {age_days} 天）；預測仍從今天 {t.date()} 起算 7/14 天。"
            )

        if n.get("price_out_of_range"):
            warnings.append(
                f"輸入價格換算後（{n['price_jin']:.0f} 元/台斤）偏離歷史常見範圍，請確認品項與單位。"
            )

        row = self._features_for(n["crop_id"], n["market_id"], t)
        if row is None:
            return {
                "request_id": request_id,
                "mode_executed": n["mode"],
                "model_version": self.manifest["model_version"],
                "data_version": self.manifest["source"]["json_sha256"][:12],
                "public_data_cutoff": str(self.public_cutoff.date()),
                "public_data_age_days": age_days,
                "crop_id": n["crop_id"],
                "market_id": n["market_id"],
                "store_id": n["store_id"],
                "results": [],
                "results_without_last_week": [],
                "results_with_last_week": [],
                "b_unavailable_reason": None,
                "warnings": warnings + ["該市場此品項在查詢日前無可用公開價格，無法估計。"],
                "error": {"code": "stale_data_unusable", "message": "公開資料不足，無法提供預測。"},
            }

        # A：公開模型（方向＝市場方向；店價估計＝現價錨定）
        results_a = []
        for h in (7, 14):
            r = self._predict_return(n["crop_id"], row, h)
            direction = classify_direction(r, FLAT_THRESHOLD)
            results_a.append(
                {
                    "horizon_days": h,
                    "target_date": str((t + pd.Timedelta(days=h)).date()),
                    "direction": direction,
                    "relative_change_estimate": round(r, 4),
                    "price_estimate": round(n["price"] * (1 + r), 1),
                    "price_estimate_unit": n["price_unit"],
                    "target_scope": "store_price_estimate",
                    "validation_scope": "public_market_test" if direction == "insufficient_data" else "unvalidated",
                    "probability": None,
                    "interval_low": None,
                    "interval_high": None,
                    "warnings": [POINT_ESTIMATE_LIMITATION, STORE_ESTIMATE_NOTE],
                    "evidence_summary": (
                        f"臺中{n['market_id']}均價特徵（最新可見 {self.public_cutoff.date()}），"
                        f"{self.manifest['models'][0 if h == 7 else 1]['name']} 預測相對變化後以現價 {n['price']} 錨定。"
                    ),
                }
            )

        # B：實驗性規則（可比性檢查）
        b_check = check_b_input(
            n["observed_at"],
            n["price_jin"],
            req.get("previous_price"),
            req.get("previous_price_unit") or req.get("price_unit"),
            _parse_dt(req["previous_observed_at"]) if req.get("previous_observed_at") else None,
        )
        results_b, b_reason = [], None
        if b_check.ok:
            public_week_change = row["ret_7d"]
            if pd.isna(public_week_change):
                public_week_change = None
                warnings.append("該市場無同期公開一週變化可比，B 退回 A 結果。")
            for a in results_a:
                r_b = experimental_b_return(a["relative_change_estimate"], b_check.store_week_change, public_week_change)
                results_b.append(
                    {
                        **a,
                        "direction": classify_direction(r_b, FLAT_THRESHOLD),
                        "relative_change_estimate": round(r_b, 4),
                        "price_estimate": round(n["price"] * (1 + r_b), 1),
                        "validation_scope": "unvalidated",
                        "warnings": a["warnings"] + [B_EXPERIMENTAL_NOTE],
                        "evidence_summary": (
                            f"A 的公開預測＋實驗性調整：店價一週變化 {b_check.store_week_change:+.1%}"
                            f"（實際間隔 {b_check.actual_interval_days} 天）對比公開同期 {public_week_change if public_week_change is None else format(public_week_change, '+.1%')}。"
                        ),
                    }
                )
        else:
            b_reason = b_check.reason

        mode = n["mode"]
        mode_executed = mode if mode != "with_last_week" or results_b else (
            "with_last_week" if results_b else "fallback_without_last_week"
        )
        if mode in ("with_last_week", "both") and not results_b:
            mode_executed = "fallback_without_last_week"
            warnings.append(f"{b_reason}；顯示不含上週價的 A 結果。")
        if mode == "with_last_week" and results_b:
            results_a_out = []  # 只要 B
        else:
            results_a_out = results_a

        return {
            "request_id": request_id,
            "mode_executed": mode_executed,
            "model_version": self.manifest["model_version"],
            "data_version": self.manifest["source"]["json_sha256"][:12],
            "input_observed_at": req["observed_at"],
            "public_data_cutoff": str(self.public_cutoff.date()),
            "public_data_age_days": age_days,
            "crop_id": n["crop_id"],
            "market_id": n["market_id"],
            "store_id": n["store_id"],
            "results": results_b if (mode == "with_last_week" and results_b) else results_a_out,
            "results_without_last_week": results_a if mode in ("both", "with_last_week") else [],
            "results_with_last_week": results_b,
            "b_unavailable_reason": b_reason,
            "warnings": warnings,
            "error": None,
        }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="本機推論（T19）")
    parser.add_argument("--release", default="models/releases/0.1.0")
    parser.add_argument("--request", required=True, help="ForecastRequest JSON 檔或內聯 JSON")
    args = parser.parse_args()
    engine = ForecastEngine(args.release)
    req = json.loads(Path(args.request).read_text(encoding="utf-8")) if args.request.endswith(".json") else json.loads(args.request)
    print(json.dumps(engine.forecast(req), ensure_ascii=False, indent=2))
