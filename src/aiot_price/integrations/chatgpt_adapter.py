"""Read-only TW01 tools using the original frozen ForecastEngine and AgentTools."""
from __future__ import annotations

import hashlib
import math
import os
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from aiot_price.integrations.chatgpt_contracts import (
    ContractError, MARKETS, normalized_forecast_request, taipei_today,
    validate_arguments,
)

# DE00 first-run observed hashes; do not regenerate these when protected data changes.
FROZEN_SHA256 = {
    "manifest.json": "6f82dac547a72a692f8352a14ece77d7b94a53b85f7844dba0aa2eb291e15f5d",
    "fixtures.json": "235a7e23d2fa31c23cab26e878dbd842ab81d923e775aa93f6d0503b94e284c6",
    "model_h7.joblib": "ea98f31d91d27e18644c61736534483b443429e940cf474ee8a1adb9f7c5b327",
    "model_h14.joblib": "d88fd53d25f62e3737444609c2769f1ab9d547783ee2b0ff6a1128aa24dae92a",
    "public_history.parquet": "e53e34c49098e309544b902dbff29708cde2f969035dd13995e64deed2ba2e3c",
}


class ToolUnavailable(RuntimeError):
    """Controlled no-data or invalid frozen-release error."""


def verify_frozen_release(release_dir: Path):
    for name, expected in FROZEN_SHA256.items():
        p = release_dir / name
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != expected:
            raise ToolUnavailable(f"凍結 release 檢查失敗：{name}，拒絕繼續推論。")


@contextmanager
def verified_release_snapshot(release_dir: Path):
    """Copy/hash exactly the frozen bytes, then load ONLY the verified snapshot.

    This closes the shared release check/load race for normal concurrent file
    replacement. A malicious process with the SAME Windows user rights to
    the private runtime snapshot itself is outside this process trust boundary.
    """
    release_dir = Path(release_dir)
    parent = os.environ.get("AIOT_MCP_SNAPSHOT_DIR")
    if parent:
        Path(parent).mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="tw01_verified_", dir=parent) as work:
        snapshot = Path(work)
        for name, expected in FROZEN_SHA256.items():
            source = release_dir / name
            dest = snapshot / name
            if not source.is_file():
                raise ToolUnavailable(f"凍結 release 檔案遺失：{name}。")
            hash_obj = hashlib.sha256()
            # Keep the source descriptor open while copying, then validate the
            # bytes ACTUALLY copied (not a separate prior path read).
            with source.open("rb") as reader, dest.open("xb") as writer:
                for block in iter(lambda: reader.read(1024 * 1024), b""):
                    hash_obj.update(block)
                    writer.write(block)
            if hash_obj.hexdigest() != expected:
                raise ToolUnavailable(f"凍結 release 複本 SHA-256 不符：{name}。")
        yield snapshot


def execute_tool(name: str, arguments: dict, release_dir: Path, *, today: date | None = None) -> dict:
    """One call with byte-identical isolated release; no HTTP/records/providers."""
    cleaned = validate_arguments(name, arguments, today=today)
    with verified_release_snapshot(Path(release_dir)) as snapshot:
        return _execute_verified_tool(name, cleaned, snapshot, today=today)


def _execute_verified_tool(name: str, cleaned: dict, release_dir: Path, *, today: date | None = None) -> dict:
    # Delayed imports confine the ML stack to the original worker interpreter.
    from aiot_price.models.predict import ForecastEngine, KNOWN_MARKETS
    from aiot_price.agent.tools import AgentTools
    from aiot_price.data.labels import classify_direction
    from aiot_price.models.baselines import FLAT_THRESHOLD

    if tuple(KNOWN_MARKETS) != MARKETS:
        raise ToolUnavailable("市場清單已與 ForecastEngine 分歧。")
    engine = ForecastEngine(release_dir)
    tools = AgentTools(engine)
    query_date = (today or taipei_today()).isoformat()
    limits = [
        "公開市場均價不等於個別店家真值，也不是即時報價。",
        "店價 A 為現價錨定推估，尚未完成同店到期配對驗證。",
        "公開方向模型未勝動量基線；點估計 MAE 未勝不變價基線。",
        "第一版不支援 B、保存、讀取私人紀錄、任意程式或 URL。",
    ]
    if name == "get_market_quote":
        raw = tools.get_market_quote(cleaned["crop_id"], cleaned["market_id"])
        price = raw.get("price")
        if not raw.get("ok") or isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 0:
            raise ToolUnavailable(raw.get("reason", "查無有效公開市場報價。"))
        if not raw.get("observed_date") or not raw.get("public_data_cutoff"):
            raise ToolUnavailable("公開行情日期無法確認。")
        cutoff_age = raw.get("price_age_days_at_cutoff")
        if (
            raw.get("crop_id") != cleaned["crop_id"]
            or raw.get("market_id") != cleaned["market_id"]
            or raw.get("unit") != "NTD_per_taiwan_jin"
            or isinstance(cutoff_age, bool)
            or not isinstance(cutoff_age, int)
            or cutoff_age < 0
            or (date.fromisoformat(raw["public_data_cutoff"]) -
                date.fromisoformat(raw["observed_date"])).days != cutoff_age
        ):
            raise ToolUnavailable("公開行情來源、市場、單位或觀測日不一致。")
        age = (date.fromisoformat(query_date) - date.fromisoformat(raw["observed_date"])).days
        structured = {
            "tool": name, "input_echo": dict(cleaned), "normalized_request": None,
            "query_date": query_date, "engine_result": raw,
            "price_age_days_at_query": age, "limits": limits,
        }
        structured["fact_text"] = (
            f"公開市場行情：{raw['market_id']}／{raw['crop_id']}，"
            f"{raw['price']} 元／台斤；實際觀測日 {raw['observed_date']}，"
            f"快照截止 {raw['public_data_cutoff']}。"
            f"截止時價齡 {raw['price_age_days_at_cutoff']} 天；"
            f"截至臺北查詢日 {query_date} 已過 {age} 天。"
            + " ".join(limits)
        )
        return structured
    if name != "post_forecast":
        raise ContractError("未知工具。")
    req = normalized_forecast_request(cleaned)
    raw = tools.post_forecast(req)
    if raw.get("error"):
        raise ToolUnavailable(str(raw["error"].get("message", "預測資料不足。")))
    if raw.get("store_id") is not None or raw.get("mode_executed") != "without_last_week":
        raise ToolUnavailable("推論結果不是規定的匿名 A 模式。")
    if (
        raw.get("crop_id") != cleaned["crop_id"]
        or raw.get("market_id") != cleaned["market_id"]
        or raw.get("model_version") != engine.manifest["model_version"]
        or raw.get("data_version") != engine.manifest["source"]["json_sha256"][:12]
        or raw.get("public_data_cutoff") != str(engine.public_cutoff.date())
        or raw.get("results_with_last_week")
    ):
        raise ToolUnavailable("預測結果的來源、版本、市場或 A 模式資料不一致。")
    rows = raw.get("results")
    if not isinstance(rows, list) or len(rows) != 2 or [item.get("horizon_days") for item in rows if isinstance(item, dict)] != [7, 14]:
        raise ToolUnavailable("必須恰好取得一筆 7 天與一筆 14 天的推估。")
    expected = {7: (date.fromisoformat(cleaned["observed_on"])).toordinal() + 7,
                14: (date.fromisoformat(cleaned["observed_on"])).toordinal() + 14}
    for item in rows:
        h = item.get("horizon_days")
        if h not in expected or date.fromisoformat(item["target_date"]).toordinal() != expected[h]:
            raise ToolUnavailable("引擎回傳的期限不是精確 t+7/t+14 日。")
        if any(item.get(k) is not None for k in ("probability", "interval_low", "interval_high")):
            raise ToolUnavailable("引擎未經校準，不允許機率或區間值。")
        price_estimate = item.get("price_estimate")
        delta = item.get("relative_change_estimate")
        if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in (price_estimate, delta)):
            raise ToolUnavailable("引擎回傳非有限價格／相對變化。")
        if price_estimate <= 0 or item.get("price_estimate_unit") != cleaned["price_unit"]:
            raise ToolUnavailable("引擎回傳的店價估計或單位不合法。")
        if item.get("target_scope") != "store_price_estimate":
            raise ToolUnavailable("預測目標必須維持店價現價錨定估計。")
        direction = item.get("direction")
        # The engine only returns a numeric model estimate on this success
        # path; insufficient_data requires its separate controlled no-data
        # error response. Do not let an arbitrary label at the 5% rounding
        # boundary bypass direction validation.
        if direction not in ("up", "down", "flat"):
            raise ToolUnavailable("引擎回傳未知或不適用的方向分類。")
        if item.get("validation_scope") != "unvalidated":
            raise ToolUnavailable("引擎回傳與凍結契約不一致的驗證範圍。")
        near_rounded_boundary = abs(abs(delta) - FLAT_THRESHOLD) <= 0.000051
        if near_rounded_boundary:
            # The published delta is rounded to four decimals, whereas the
            # engine classified its full-precision return. At +/-5% the only
            # plausible second class is flat, never an opposite direction.
            allowed = ("flat", "up" if delta >= 0 else "down")
            if direction not in allowed:
                raise ToolUnavailable("方向與相對變化不一致。")
        elif classify_direction(delta, FLAT_THRESHOLD) != direction:
            raise ToolUnavailable("方向與相對變化不一致。")
        # The engine uses full model delta for price, while the response delta
        # is rounded to 4 decimals; allow only that rounding margin.
        approximate_price = round(cleaned["current_price"] * (1 + delta), 1)
        rounding_tolerance = 0.11 + cleaned["current_price"] * 0.000051
        if abs(price_estimate - approximate_price) > rounding_tolerance:
            raise ToolUnavailable("引擎店價點估計與原相對變化不一致。")
    structured = {
        "tool": name, "input_echo": dict(cleaned), "normalized_request": req,
        "query_date": query_date, "engine_result": raw,
        "price_age_days_at_query": (
            date.fromisoformat(query_date) - date.fromisoformat(raw["public_data_cutoff"])
        ).days,
        "limits": limits + ["引擎原警告中的「今天／距今」意指報價基準日 t，不必然是查詢當日。"],
    }
    facts = [
        f"A 模式：{cleaned['crop_id']}／{cleaned['market_id']}，"
        f"店價 {cleaned['current_price']} {cleaned['price_unit']}，"
        f"觀測日 {cleaned['observed_on']}（台北中午）／查詢日 {query_date}。",
    ]
    for item in rows:
        facts.append(
            f"{item['horizon_days']} 天（{item['target_date']}）方向 {item['direction']}，"
            f"相對變化 {item['relative_change_estimate']}，"
            f"店價點估計 {item['price_estimate']} {item['price_estimate_unit']}，"
            f"驗證範圍 {item['validation_scope']}；"
            f"注意：{'；'.join(item.get('warnings', []))}。"
        )
    facts.append(
        f"模型版本 {raw['model_version']}，資料版本 {raw['data_version']}，"
        f"公開資料截止 {raw['public_data_cutoff']}；"
        f"引擎警告：{'；'.join(raw.get('warnings', [])) or '無'}。"
    )
    structured["fact_text"] = " ".join(facts + limits + structured["limits"][-1:])
    return structured
