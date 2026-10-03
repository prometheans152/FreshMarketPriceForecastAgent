# -*- coding: utf-8 -*-
"""公開零售價格資料的可重現下載、驗證與 provenance 紀錄工具（T05）。

資料特性（重要，勿誤用）：
- 來源欄位為各公有零售市場的「平均價格(元/斤)」；臺中市場按 元/臺斤 解讀
  （1 臺斤 = 0.6 公斤，依標準檢驗局衡器規範，2026-10-03 查核）。
- 0 代表該品項當日「無價格」（缺測），絕不能當成 0 元的便宜價或持平。
- 「市場均價」不是任何單一店家的真實售價，只能作公開行情參考；
  61 個價格欄也不是 61 種蔬菜（含禽肉等品項）。

設計原則：
- 只用 Python 標準庫：urllib.request 下載（免裝 requests）、json/hashlib
  解析與校驗；讀 YAML 設定優先 PyYAML，未安裝時退回內建最小解析器。
- 絕不覆蓋既有檔案：目標檔名已存在時自動加時間戳後綴（_HHMMSS）。
- 每次下載都寫 provenance JSON：URL、時間、HTTP 狀態、bytes、SHA256、
  列數、欄位、市場、日期範圍、授權，供資料卡與 manifest 追溯。

用法（Git Bash，於專案根目錄）：
    PYTHONPATH=src python -m aiot_price.data.fetch_public \
        --config configs/data_sources.yaml --out-dir data/raw/taichung
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

__all__ = [
    "load_config",
    "parse_mini_yaml",
    "sha256_file",
    "unique_path",
    "download_file",
    "analyze_snapshot",
    "write_provenance",
    "main",
]


# ---------------------------------------------------------------------------
# YAML 設定讀取：優先 PyYAML，未安裝時用僅支援本專案設定格式的最小解析器。
# 支援子集：註解、縮排巢狀映射、純量、行內清單 [a, b]、區塊清單（- 項目）。
# 限制：純量中不可出現「 #」形式的註解樣式；不支援錨點、多行字串。
# ---------------------------------------------------------------------------

def _parse_scalar(text: str):
    """把 YAML 純量轉成 Python 值；其餘一律當字串。"""
    t = text.strip()
    if len(t) >= 2 and t[0] == t[-1] and t[0] in "\"'":
        return t[1:-1]
    if t.startswith("[") and t.endswith("]"):
        inner = t[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part) for part in inner.split(",")]
    if t in ("true", "True"):
        return True
    if t in ("false", "False"):
        return False
    if t in ("null", "~", ""):
        return None
    if re.fullmatch(r"-?\d+", t):
        return int(t)
    if re.fullmatch(r"-?\d+\.\d+", t):
        return float(t)
    return t


def _strip_comment(raw_line: str) -> str:
    """移除行尾註解：只認空白後接 # 的形式（YAML 純量規則的簡化版）。"""
    return re.sub(r"(^|\s)#.*$", "", raw_line).rstrip()


def _parse_block(lines: list, i: int, indent: int):
    """遞迴解析同一縮排層的區塊；依首行判斷是清單或映射。"""
    if i < len(lines) and lines[i][1].startswith("- "):
        items = []
        while i < len(lines) and lines[i][0] == indent and lines[i][1].startswith("- "):
            items.append(_parse_scalar(lines[i][1][2:]))
            i += 1
        return items, i
    obj: dict = {}
    while i < len(lines) and lines[i][0] == indent and not lines[i][1].startswith("- "):
        # 注意：值本身可能含冒號（如 https://），partition 只切第一個冒號。
        key, _, value = lines[i][1].partition(":")
        if value.strip():
            obj[key.strip()] = _parse_scalar(value)
            i += 1
        else:
            i += 1
            if i < len(lines) and lines[i][0] > indent:
                child, i = _parse_block(lines, i, lines[i][0])
                obj[key.strip()] = child
            else:
                obj[key.strip()] = None
    return obj, i


def parse_mini_yaml(text: str) -> dict:
    """最小 YAML 解析器：僅支援本專案 data_sources.yaml 用的子集。"""
    lines: list = []
    for raw_line in text.splitlines():
        line = _strip_comment(raw_line)
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        lines.append((indent, line.strip()))
    if not lines:
        return {}
    obj, _ = _parse_block(lines, 0, lines[0][0])
    return obj


def load_config(path: str | Path) -> dict:
    """讀設定檔；有 PyYAML 用 PyYAML，否則退回內建解析器。"""
    text = Path(path).read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text)
    except ImportError:
        return parse_mini_yaml(text)


# ---------------------------------------------------------------------------
# 下載與校驗
# ---------------------------------------------------------------------------

def sha256_file(path: str | Path, chunk_size: int = 1 << 20) -> str:
    """串流計算檔案 SHA256，避免一次把大檔讀進記憶體。"""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def unique_path(path: Path) -> Path:
    """目標已存在時加 _HHMMSS 時間戳後綴，保證不覆蓋任何舊檔。"""
    if not path.exists():
        return path
    stamp = datetime.now().strftime("%H%M%S")
    candidate = path.with_name(f"{path.stem}_{stamp}{path.suffix}")
    while candidate.exists():
        time.sleep(1)
        stamp = datetime.now().strftime("%H%M%S")
        candidate = path.with_name(f"{path.stem}_{stamp}{path.suffix}")
    return candidate


def download_file(url: str, dest: Path, timeout: float = 120.0) -> dict:
    """用 urllib 下載到 dest，回傳 HTTP 狀態、bytes、耗時。失敗時不留下半截檔。"""
    request = urllib.request.Request(url, headers={"User-Agent": "aiot-price-fetch/0.1"})
    started = datetime.now().astimezone().isoformat(timespec="seconds")
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", None) or response.getcode()
            data = response.read()
    except urllib.error.HTTPError as exc:  # HTTP 錯誤碼仍屬「有回應」，如實記錄
        status = exc.code
        raise RuntimeError(f"HTTP {status}") from exc
    duration = round(time.monotonic() - t0, 3)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return {
        "http_status": int(status),
        "download_started_local": started,
        "duration_seconds": duration,
        "bytes": len(data),
    }


# ---------------------------------------------------------------------------
# 快照解析與基本統計
# ---------------------------------------------------------------------------

def analyze_snapshot(path: str | Path, key_fields=("市場名稱", "訪價日期")) -> dict:
    """解析官方 JSON：列數、欄位、市場、日期範圍、鍵唯一性與 0 值統計。

    - 訪價日期為 YYYYMMDD 字串，min/max 用字串排序即時間順序。
    - 0 = 無該品項價格（缺測）：這裡只計數證據，後續清理任務（T06）才轉缺測。
    """
    with open(path, encoding="utf-8") as fh:
        rows = json.load(fh)
    if not isinstance(rows, list) or not rows:
        raise ValueError("檔案頂層應為非空的 JSON 陣列（每列一個市場×日期）")

    fields = list(rows[0].keys())
    markets = sorted({row.get(key_fields[0]) for row in rows})
    dates = sorted({row.get(key_fields[1]) for row in rows})
    keys = [(row.get(key_fields[0]), row.get(key_fields[1])) for row in rows]
    price_fields = [f for f in fields if f not in key_fields]

    zero_cells = 0
    nonfinite_cells = 0
    for row in rows:
        for name in price_fields:
            value = row.get(name)
            if value is None or value == "":
                continue
            try:
                number = float(value)
            except (TypeError, ValueError):
                nonfinite_cells += 1
                continue
            if number == 0:
                zero_cells += 1
            elif number != number or number in (float("inf"), float("-inf")):
                nonfinite_cells += 1

    return {
        "row_count": len(rows),
        "field_count": len(fields),
        "fields": fields,
        "market_count": len(markets),
        "markets": markets,
        "date_count": len(dates),
        "min_date": dates[0],
        "max_date": dates[-1],
        "duplicate_market_date_keys": len(keys) - len(set(keys)),
        "zero_price_cells": zero_cells,  # 0=無價格的證據計數；非 0 元成交
        "unparsable_price_cells": nonfinite_cells,
    }


# ---------------------------------------------------------------------------
# provenance 寫檔
# ---------------------------------------------------------------------------

def write_provenance(out_dir: Path, snapshot_path: Path, source_cfg: dict,
                     download_info: dict, content_stats: dict) -> Path:
    """把本次取得的完整證據寫成 provenance JSON（同樣不覆蓋既有檔）。"""
    payload = {
        "snapshot_file": str(snapshot_path).replace("\\", "/"),
        "dataset": {
            "name": source_cfg.get("name"),
            "dataset_id": source_cfg.get("dataset_id"),
            "page_url": source_cfg.get("page_url"),
        },
        "download": {
            "url": source_cfg.get("download_url"),
            "method": "urllib.request (Python 標準庫)",
            **download_info,
            "sha256": sha256_file(snapshot_path),
        },
        "license": source_cfg.get("license"),
        "unit": {
            "declared": source_cfg.get("unit_declared"),
            "interpretation": source_cfg.get("unit_interpretation"),
            "zero_means": source_cfg.get("zero_means"),
        },
        "content": content_stats,
        "generated_by": "src/aiot_price/data/fetch_public.py",
    }
    stamp = datetime.now().strftime("%Y%m%d")
    dest = unique_path(out_dir / f"provenance_{stamp}.json")
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    return dest


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="下載公開零售價格 JSON、計算 SHA256、解析基本統計並寫 provenance（不覆蓋舊檔）",
    )
    parser.add_argument("--config", default="configs/data_sources.yaml", help="來源設定 YAML")
    parser.add_argument("--out-dir", default="data/raw/taichung", help="快照與 provenance 輸出目錄")
    parser.add_argument("--source", default=None, help="設定檔中的來源鍵；預設取第一個採用中的來源")
    parser.add_argument("--timeout", type=float, default=120.0, help="下載逾時秒數")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    sources = (config or {}).get("sources") or {}
    if not sources:
        print(f"錯誤：{args.config} 沒有 sources 區段", file=sys.stderr)
        return 2

    if args.source:
        if args.source not in sources:
            print(f"錯誤：設定檔沒有來源 {args.source}", file=sys.stderr)
            return 2
        source_cfg = sources[args.source]
    else:
        adopted = [(k, v) for k, v in sources.items() if isinstance(v, dict) and v.get("adopted")]
        if not adopted:
            print("錯誤：設定檔沒有 adopted: true 的來源", file=sys.stderr)
            return 2
        args.source, source_cfg = adopted[0]

    if not source_cfg.get("download_url"):
        print(f"錯誤：來源 {args.source} 沒有 download_url（不採用的來源不能下載）", file=sys.stderr)
        return 2

    out_dir = Path(args.out_dir)
    stamp = datetime.now().strftime("%Y%m%d")
    dest = unique_path(out_dir / f"retail_prices_{stamp}.json")
    print(f"來源：{args.source}（{source_cfg.get('name', '')}）")
    print(f"下載 → {dest}")

    try:
        info = download_file(source_cfg["download_url"], dest, timeout=args.timeout)
    except (RuntimeError, urllib.error.URLError, OSError) as exc:
        print(f"下載失敗：{exc}", file=sys.stderr)
        return 1

    stats = analyze_snapshot(dest)
    provenance = write_provenance(out_dir, dest, source_cfg, info, stats)
    print(f"HTTP {info['http_status']}｜{info['bytes']} bytes｜{info['duration_seconds']}s")
    print(f"SHA256：{sha256_file(dest)}")
    print(f"列數 {stats['row_count']}｜欄位 {stats['field_count']}｜市場 {stats['market_count']}｜"
          f"日期 {stats['min_date']}~{stats['max_date']}（{stats['date_count']} 日）")
    print(f"provenance → {provenance}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
