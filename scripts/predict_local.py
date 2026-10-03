"""本機推論 CLI（T19）。

用法（專案根目錄）：
  PYTHONPATH=src .venv/Scripts/python.exe scripts/predict_local.py --request '<JSON>'
  PYTHONPATH=src .venv/Scripts/python.exe scripts/predict_local.py --request-file req.json
  PYTHONPATH=src .venv/Scripts/python.exe scripts/predict_local.py --update-fixtures   # 產生/更新 T18 fixtures 預期輸出
  PYTHONPATH=src .venv/Scripts/python.exe scripts/predict_local.py --check-fixtures    # 與 fixtures 比對（重現驗證）
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aiot_price.models.predict import ForecastEngine


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", default="models/releases/0.1.0")
    parser.add_argument("--request", default=None)
    parser.add_argument("--request-file", default=None)
    parser.add_argument("--update-fixtures", action="store_true")
    parser.add_argument("--check-fixtures", action="store_true")
    args = parser.parse_args()

    engine = ForecastEngine(args.release)

    fixtures_path = Path(args.release) / "fixtures.json"

    if args.update_fixtures:
        fixtures = json.loads(fixtures_path.read_text(encoding="utf-8"))
        expected = []
        for req in fixtures["requests"]:
            t0 = time.perf_counter()
            resp = engine.forecast(req)
            dt = round((time.perf_counter() - t0) * 1000, 1)
            expected.append({"request_id": req["request_id"], "latency_ms": dt, "response": resp})
        fixtures["expected"] = expected
        fixtures_path.write_text(json.dumps(fixtures, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"fixtures updated: {fixtures_path} ({len(expected)} cases)")
        return

    if args.check_fixtures:
        fixtures = json.loads(fixtures_path.read_text(encoding="utf-8"))
        assert fixtures.get("expected"), "fixtures 尚無 expected；先跑 --update-fixtures"
        n_ok = 0
        for case in fixtures["expected"]:
            req = next(r for r in fixtures["requests"] if r["request_id"] == case["request_id"])
            resp = engine.forecast(req)
            got = json.dumps(resp, ensure_ascii=False, sort_keys=True)
            want = json.dumps(case["response"], ensure_ascii=False, sort_keys=True)
            if got == want:
                n_ok += 1
            else:
                print(f"MISMATCH {case['request_id']}")
                print("  got :", got[:400])
                print("  want:", want[:400])
        print(f"fixtures check: {n_ok}/{len(case) if False else len(fixtures['expected'])} passed")
        sys.exit(0 if n_ok == len(fixtures["expected"]) else 1)

    if args.request_file:
        req = json.loads(Path(args.request_file).read_text(encoding="utf-8"))
    elif args.request:
        req = json.loads(args.request)
    else:
        parser.error("需要 --request、--request-file、--update-fixtures 或 --check-fixtures")

    t0 = time.perf_counter()
    resp = engine.forecast(req)
    dt = (time.perf_counter() - t0) * 1000
    print(json.dumps(resp, ensure_ascii=False, indent=2))
    print(f"--- latency: {dt:.1f} ms", file=sys.stderr)


if __name__ == "__main__":
    main()
