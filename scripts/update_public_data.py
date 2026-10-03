"""公開行情手動更新流程（T30）。

流程：取得最新 JSON（下載或 --input 本地檔）→ 驗證（HTTP 狀態／SHA256／schema／
日期格式）→ 與 data/raw/ 最新快照比較（新增觀測日數）→ 存新快照（帶日期、永不
覆蓋舊檔）→（選配）--refresh-release-history 把「release 截止日之後的新日期」
追加到模型包的 public_history.parquet（推論特徵來源）。

設計原則（design.md §8）：「行情刷新、模型發布、Qwen 載入是不同操作」。
本腳本只刷新公開行情（快照＋推論歷史 parquet），**完全不動**：
- 模型權重 model_h7.joblib／model_h14.joblib（重訓一律回 TRAIN_LOCAL 的 T08–T18）
- manifest.json／fixtures.json（記錄的是訓練當時的資料切分與 hash，不隨行情漂移）
- Qwen 或任何 SERVER 服務（載入與重啟是另一件事）

用法（專案根目錄，Git Bash；PYTHONPATH=src）：
  # 標準流程：從官方 URL 下載、驗證、比較、有新資料才存快照
  PYTHONPATH=src .venv/Scripts/python.exe scripts/update_public_data.py

  # 只報告、不寫入任何檔案
  PYTHONPATH=src .venv/Scripts/python.exe scripts/update_public_data.py --dry-run

  # 用本地 JSON 代替下載（測試／離線核對用）
  PYTHONPATH=src .venv/Scripts/python.exe scripts/update_public_data.py \
      --input data/raw/taichung/retail_prices_20261003.json --dry-run

  # 下載並把新觀測日期追加到模型包推論歷史（寫入前自動備份原 parquet）
  PYTHONPATH=src .venv/Scripts/python.exe scripts/update_public_data.py --refresh-release-history

  # 指定其他下載 URL（例：測試失效來源的錯誤處理）
  PYTHONPATH=src .venv/Scripts/python.exe scripts/update_public_data.py --url http://127.0.0.1:9/

離開代碼：0＝成功（含「無新資料」）；1＝下載失敗；2＝schema 驗證失敗；3＝release 歷史刷新失敗。
失敗一律保留舊檔，只寫報告 JSON。
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# 重用 T05 既有工具：下載、hash、不覆蓋命名、provenance（不重造，不改 src/）
from aiot_price.data.fetch_public import (
    analyze_snapshot,
    download_file,
    load_config,
    sha256_file,
    unique_path,
    write_provenance,
)
from aiot_price.data.load import KEY_DATE, KEY_MARKET, load_taichung_long
from aiot_price.data.schema import CROP_MAPPINGS

# 與 scripts/prepare_data.py 完全一致的排除規則：T06 品質決策，(停) 前綴市場排除
EXCLUDED_MARKET_PATTERN = "(停)"
# release 推論歷史 parquet 的固定欄位（package.py 產出）
HISTORY_COLUMNS = ["market_id", "date", "crop_id", "price"]


# ---------------------------------------------------------------------------
# 驗證
# ---------------------------------------------------------------------------

def validate_schema(path: Path) -> tuple[dict, list[str]]:
    """基本 schema 檢查：頂層非空陣列、必要欄位存在、訪價日期為 YYYYMMDD。

    回傳 (stats, errors)：errors 非空＝驗證失敗，呼叫端不得用該檔做任何更新。
    """
    errors: list[str] = []
    with open(path, encoding="utf-8") as fh:
        rows = json.load(fh)

    if not isinstance(rows, list):
        return {}, [f"頂層應為 JSON 陣列，實為 {type(rows).__name__}"]
    if len(rows) == 0:
        return {"row_count": 0}, ["列數為 0（空檔）"]

    fields = list(rows[0].keys())
    for required in (KEY_MARKET, KEY_DATE):
        if required not in fields:
            errors.append(f"缺少必要欄位：{required}（現有欄位數 {len(fields)}）")

    bad_dates = 0
    bad_examples: list[str] = []
    for row in rows:
        d = str(row.get(KEY_DATE, ""))
        if not re.fullmatch(r"\d{8}", d):
            bad_dates += 1
            if len(bad_examples) < 3:
                bad_examples.append(d if d else "<空>")
        else:
            try:
                datetime.strptime(d, "%Y%m%d")
            except ValueError:
                bad_dates += 1
                if len(bad_examples) < 3:
                    bad_examples.append(f"{d}(無效日)")
    if bad_dates:
        errors.append(
            f"訪價日期格式錯誤 {bad_dates} 列（應為 YYYYMMDD，例：{bad_examples}）"
        )

    stats = analyze_snapshot(path) if not errors else {"row_count": len(rows), "fields": fields}
    stats["row_count"] = len(rows)
    return stats, errors


# ---------------------------------------------------------------------------
# 快照比較
# ---------------------------------------------------------------------------

def find_latest_snapshot(out_dir: Path) -> tuple[Path | None, dict]:
    """找 out_dir 內內容日期最新的既有快照（retail_prices_*.json）當比較基準。

    以檔案內容的 max_date 為準（檔名日期只是下載日，不是觀測日）；
    同 max_date 時取 mtime 最新。沒有任何快照時回傳 (None, {})。
    """
    candidates = sorted(out_dir.glob("retail_prices_*.json"))
    best: Path | None = None
    best_key = ("", 0.0)
    for cand in candidates:
        try:
            stats = analyze_snapshot(cand)
        except (ValueError, json.JSONDecodeError, OSError):
            continue  # 壞檔不作為基準，也不刪除
        key = (stats["max_date"], cand.stat().st_mtime)
        if key > best_key:
            best, best_key = cand, key
    if best is None:
        return None, {}
    return best, {
        "path": str(best),
        "max_date": best_key[0],
        "sha256": sha256_file(best),
        "row_count": None,  # 由呼叫端視需要補
    }


def new_observation_dates(new_path: Path, baseline_dates: set[str]) -> list[str]:
    """回傳新檔有、基準沒有的觀測日期（YYYYMMDD 字串，排序）。"""
    with open(new_path, encoding="utf-8") as fh:
        rows = json.load(fh)
    return sorted({str(r.get(KEY_DATE, "")) for r in rows} - baseline_dates)


def baseline_date_set(baseline: Path) -> set[str]:
    with open(baseline, encoding="utf-8") as fh:
        rows = json.load(fh)
    return {str(r.get(KEY_DATE, "")) for r in rows}


# ---------------------------------------------------------------------------
# release 推論歷史刷新（--refresh-release-history）
# ---------------------------------------------------------------------------

def build_release_rows(json_path: Path) -> pd.DataFrame:
    """把新 JSON 轉成與 public_history.parquet 同結構的長表。

    與訓練前處理（prepare_data.py／package.py）一致：
    - 只取 CROP_MAPPINGS 三品項欄位（crop_raw → crop_id）
    - 0／負值／解析失敗 → NaN（load_taichung_long 已處理）
    - 排除 (停) 前綴市場
    """
    crop_cols = [m.source_column for m in CROP_MAPPINGS.values()]
    long_df, _report = load_taichung_long(json_path, crop_columns=crop_cols)
    keep = ~long_df["market_id"].str.contains(EXCLUDED_MARKET_PATTERN, regex=False)
    df = long_df[keep].copy()
    df["crop_id"] = df["crop_raw"].map(
        {m.source_column: cid for cid, m in CROP_MAPPINGS.items()}
    )
    return df[HISTORY_COLUMNS]


def refresh_release_history(
    json_path: Path,
    release_dir: Path,
    dry_run: bool,
) -> dict:
    """把 release 截止日之後的新日期列「只追加」到 public_history.parquet。

    保證：
    - 舊列一列不改（先 concat 舊＋新、寫回後逐列核對舊區段）
    - 寫入前先備份原檔（public_history.backup_YYYYMMDD_HHMMSS.parquet）
    - 模型權重／manifest／fixtures 完全不讀寫
    - 新列若有 (市場,品項,日期) 鍵已存在於 release，則略過（防重複追加）
    """
    result: dict = {"release_dir": str(release_dir), "dry_run": dry_run}
    hist_path = release_dir / "public_history.parquet"
    if not hist_path.exists():
        result.update({"ok": False, "error": f"找不到 {hist_path}"})
        return result

    history = pd.read_parquet(hist_path)
    missing_cols = [c for c in HISTORY_COLUMNS if c not in history.columns]
    if missing_cols:
        result.update({"ok": False, "error": f"release 歷史缺欄位：{missing_cols}"})
        return result

    cutoff = history["date"].max()
    result["release_cutoff_date"] = pd.Timestamp(cutoff).strftime("%Y-%m-%d")

    # manifest 只讀取對照用（observation_end 是訓練當時的快照截止，不隨刷新改）
    manifest_path = release_dir / "manifest.json"
    if manifest_path.exists():
        with open(manifest_path, encoding="utf-8") as fh:
            manifest = json.load(fh)
        result["manifest_observation_end"] = manifest.get("source", {}).get("observation_end")
        result["manifest_note"] = "manifest 記錄訓練快照截止日，行情刷新不修改 manifest"

    new_df = build_release_rows(json_path)
    beyond = new_df[new_df["date"] > cutoff]
    new_dates = sorted({pd.Timestamp(d).strftime("%Y-%m-%d") for d in beyond["date"]})

    result.update({
        "history_rows_before": int(len(history)),
        "new_dates_beyond_cutoff": new_dates,
        "n_new_dates": len(new_dates),
    })

    if beyond.empty:
        result.update({"ok": True, "changed": False,
                       "reason": "release 截止日之後沒有新觀測日期，不修改任何檔案"})
        return result

    # 防重複：排除 release 已存在的 (market, crop, date) 鍵
    existing_keys = set(
        zip(history["market_id"], history["crop_id"],
            pd.DatetimeIndex(history["date"]).strftime("%Y-%m-%d"))
    )
    beyond = beyond.copy()
    beyond["_key"] = list(zip(
        beyond["market_id"], beyond["crop_id"],
        pd.DatetimeIndex(beyond["date"]).strftime("%Y-%m-%d"),
    ))
    n_dup = int(beyond["_key"].isin(existing_keys).sum())
    beyond = beyond[~beyond["_key"].isin(existing_keys)]
    beyond = beyond.drop(columns="_key")
    result["n_duplicate_keys_skipped"] = n_dup

    append = beyond.sort_values(["date", "market_id", "crop_id"])[HISTORY_COLUMNS].reset_index(drop=True)
    result["rows_to_append"] = int(len(append))
    result["appended_markets"] = sorted(append["market_id"].unique().tolist())
    result["appended_crops"] = sorted(append["crop_id"].unique().tolist())

    if dry_run:
        result.update({"ok": True, "changed": False, "dry_run_note": "僅報告，未寫入"})
        return result

    # 備份 → 寫入 → 逐列核對（舊區段必須與備份完全相同）
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = release_dir / f"public_history.backup_{stamp}.parquet"
    shutil.copyfile(hist_path, backup)

    combined = pd.concat([history, append], ignore_index=True)
    combined.to_parquet(hist_path, index=False)

    check = pd.read_parquet(hist_path)
    old_part = check.iloc[: len(history)].reset_index(drop=True)
    same_old = old_part.equals(history.reset_index(drop=True))
    result.update({
        "ok": bool(len(check) == len(history) + len(append) and same_old),
        "changed": True,
        "history_rows_after": int(len(check)),
        "backup_path": str(backup),
        "old_rows_unchanged": bool(same_old),
        "written_dates": sorted({pd.Timestamp(d).strftime("%Y-%m-%d") for d in append["date"]}),
    })
    if not result["ok"]:
        result["error"] = "寫入後核對失敗（列數或舊列內容不一致）；原檔備份於 backup_path，請以備份還原"
    return result


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="公開行情手動更新：下載→驗證→與最新快照比較→（選配）刷新模型包推論歷史",
    )
    parser.add_argument("--config", default="configs/data_sources.yaml", help="來源設定 YAML")
    parser.add_argument("--source", default=None, help="設定檔中的來源鍵；預設第一個採用中來源")
    parser.add_argument("--url", default=None, help="覆蓋下載 URL（測試失效來源用）")
    parser.add_argument("--input", default=None, help="以本地 JSON 檔代替下載（測試用；與 --url 互斥）")
    parser.add_argument("--out-dir", default="data/raw/taichung", help="快照與 provenance 目錄")
    parser.add_argument("--release-dir", default="models/releases/0.1.0", help="要刷新推論歷史的模型包目錄")
    parser.add_argument("--refresh-release-history", action="store_true",
                        help="把 release 截止日之後的新日期追加到 public_history.parquet（模型權重不動）")
    parser.add_argument("--dry-run", action="store_true", help="只報告，不寫入任何檔案")
    parser.add_argument("--timeout", type=float, default=120.0, help="下載逾時秒數")
    parser.add_argument("--report", default=None, help="把完整報告寫成 JSON（例：outputs/update_tests/x.json）")
    args = parser.parse_args(argv)

    if args.input and args.url:
        print("錯誤：--input 與 --url 互斥（本地檔不需要下載 URL）", file=sys.stderr)
        return 2

    report: dict = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "script": "scripts/update_public_data.py",
        "argv": vars(args),
        "mode": {"dry_run": bool(args.dry_run), "refresh_release_history": bool(args.refresh_release_history)},
        "status": None,
        "error": None,
    }
    exit_code = 0

    # ---- 第 0 步：決定下載 URL（--url > 設定檔採用中來源） ----
    url = args.url
    source_cfg: dict = {}
    if not args.input:
        config = load_config(args.config)
        sources = (config or {}).get("sources") or {}
        if args.source:
            source_cfg = sources.get(args.source) or {}
        else:
            adopted = [(k, v) for k, v in sources.items()
                       if isinstance(v, dict) and v.get("adopted")]
            if adopted:
                args.source, source_cfg = adopted[0]
        if url is None:
            url = source_cfg.get("download_url")
        if not url:
            report.update({"status": "failed", "error": f"無法決定下載 URL（--url 未給、設定檔無採用中來源）"})
            _emit(report, args)
            return 1
    report["source"] = {"type": "local_file" if args.input else "download",
                        "url": url, "source_key": args.source or None,
                        "input_path": args.input}

    # ---- 第 1 步：取得 JSON（下載到系統暫存，驗證通過且非 dry-run 才落盤） ----
    tmp_dir = Path(tempfile.mkdtemp(prefix="aiot_update_"))
    candidate = Path(args.input) if args.input else tmp_dir / "candidate.json"
    if args.input:
        if not candidate.exists():
            report.update({"status": "failed", "error": f"--input 檔不存在：{candidate}"})
            _emit(report, args)
            return 1
        report["sha256"] = sha256_file(candidate)
    else:
        try:
            info = download_file(url, candidate, timeout=args.timeout)
            report["download"] = info
            report["sha256"] = sha256_file(candidate)
            print(f"下載：HTTP {info['http_status']}｜{info['bytes']} bytes｜{info['duration_seconds']}s")
            print(f"SHA256：{report['sha256']}")
        except Exception as exc:  # URLError／HTTPError／timeout／OSError 統一處理，不崩潰
            report.update({"status": "failed",
                           "error": f"下載失敗：{url} → {type(exc).__name__}: {exc}",
                           "old_files_kept": True})
            shutil.rmtree(tmp_dir, ignore_errors=True)
            _emit(report, args)
            print(f"錯誤：下載失敗（{type(exc).__name__}: {exc}）；舊檔全部保留，未寫入任何資料。",
                  file=sys.stderr)
            return 1

    # ---- 第 2 步：schema 驗證 ----
    stats, schema_errors = validate_schema(candidate)
    report["schema_check"] = {"ok": not schema_errors, "errors": schema_errors, "stats": stats}
    if schema_errors:
        report.update({"status": "failed",
                       "error": "schema 驗證失敗：" + "；".join(schema_errors),
                       "old_files_kept": True})
        shutil.rmtree(tmp_dir, ignore_errors=True)
        _emit(report, args)
        print(f"錯誤：schema 驗證失敗，不採用此檔；" + "；".join(schema_errors), file=sys.stderr)
        return 2
    print(f"schema 檢查通過：列數 {stats['row_count']}｜欄位 {stats['field_count']}｜"
          f"日期 {stats['min_date']}~{stats['max_date']}（{stats['date_count']} 日）｜市場 {stats['market_count']}")

    # ---- 第 3 步：與現有最新快照比較 ----
    out_dir = Path(args.out_dir)
    baseline, base_meta = find_latest_snapshot(out_dir)
    if baseline is None:
        report["snapshot_comparison"] = {"baseline": None,
                                         "note": "out-dir 沒有既有快照，本次全部日期均視為新取得"}
        new_dates = sorted({str(r.get(KEY_DATE, "")) for r in json.load(open(candidate, encoding="utf-8"))})
    else:
        base_dates = baseline_date_set(baseline)
        new_dates = new_observation_dates(candidate, base_dates)
        same_hash = report["sha256"] == base_meta["sha256"]
        report["snapshot_comparison"] = {
            "baseline": base_meta["path"],
            "baseline_max_date": base_meta["max_date"],
            "baseline_sha256": base_meta["sha256"],
            "same_hash_as_baseline": same_hash,
            "new_dates": new_dates,
            "n_new_dates": len(new_dates),
        }
        print(f"比較基準：{baseline.name}（觀測至 {base_meta['max_date']}，SHA256 {'相同' if same_hash else '不同'}）")
        print(f"新增觀測日期：{len(new_dates)} 日{(' ' + '、'.join(new_dates)) if new_dates else ''}")

    has_new = len(new_dates) > 0
    report["has_new_data"] = has_new

    # ---- 第 4 步：存快照（僅非 dry-run 且有新資料；hash 相同＝無新資料不動） ----
    saved = None
    provenance = None
    if not args.dry_run and has_new:
        stamp = datetime.now().strftime("%Y%m%d")
        out_dir.mkdir(parents=True, exist_ok=True)
        dest = unique_path(out_dir / f"retail_prices_{stamp}.json")
        if args.input:
            shutil.copyfile(candidate, dest)
        else:
            shutil.move(str(candidate), str(dest))
        saved = dest
        report["snapshot_saved"] = str(dest)
        if not args.input and source_cfg:
            provenance = write_provenance(out_dir, dest, source_cfg,
                                          report.get("download", {}), stats)
            report["provenance"] = str(provenance)
        print(f"新快照已存：{dest}" + (f"｜provenance：{provenance}" if provenance else ""))
    else:
        reason = "dry-run" if args.dry_run else ("無新資料（hash/日期與既有快照相同），依策略不另存檔" if not has_new else "")
        report["snapshot_saved"] = None
        report["snapshot_not_saved_reason"] = reason
        if reason:
            print(f"快照未存：{reason}")

    # ---- 第 5 步：（選配）刷新 release 推論歷史 ----
    if args.refresh_release_history:
        refresh = refresh_release_history(candidate, Path(args.release_dir), dry_run=args.dry_run)
        report["release_history"] = refresh
        if not refresh.get("ok", False):
            report.update({"status": "failed", "error": f"release 歷史刷新失敗：{refresh.get('error')}"})
            _emit(report, args)
            print(f"錯誤：release 歷史刷新失敗：{refresh.get('error')}", file=sys.stderr)
            return 3
        rh = refresh
        if rh.get("changed"):
            print(f"release 歷史已更新：{rh['history_rows_before']} → {rh['history_rows_after']} 列"
                  f"（追加 {rh['rows_to_append']} 列、新日期 {rh['n_new_dates']} 日、備份 {rh['backup_path']}）")
        else:
            print(f"release 歷史未變更：{rh.get('reason') or rh.get('dry_run_note')}")

    # ---- 收尾 ----
    report["status"] = "ok" if has_new else "no_new_data"
    shutil.rmtree(tmp_dir, ignore_errors=True)
    _emit(report, args)
    print(f"狀態：{report['status']}")
    return 0


def _emit(report: dict, args) -> None:
    """把報告寫到 --report 指定路徑（沒指定就只印在 stdout）。"""
    if not args.report:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
        return
    path = Path(args.report)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2, default=str)
    print(f"報告 → {path}")


if __name__ == "__main__":
    sys.exit(main())
