"""Rolling public market history for inference (D48).

The frozen 0.1.0 RF/HGB and the 57-item pooled HGB stay pinned to the public
snapshot they were trained on (Taichung data.gov.tw/84539 up to 2026-10-02).
This module keeps a SEPARATE inference history: that snapshot byte for byte,
plus the market days the same source has published since. It never touches
model weights, frozen files or reported evaluation numbers.

A version holds the new source rows and everything derived from them in the
formats the image already reads (release-style public_history.parquet for the
3 frozen crops, catalog.json and public_history.json.gz for the 61 items).
It is validated before it can be switched to, written atomically, and pinned
by SHA-256 from CURRENT.json, which also lists earlier good versions to fall
back to. Shared by the updater (rolling_update.py) and the serving process
(rolling_runtime.py); error messages never contain host paths because the
server reports them on /healthz.
"""
from __future__ import annotations

import copy
import gzip
import hashlib
import io
import json
import math
import os
import re
import shutil
import tempfile
from bisect import bisect_left
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

SCHEMA = "fmpa-rolling-public-history/1"
DATASET_ID = "data.gov.tw/84539"
DOWNLOAD_URL = (
    "https://newdatacenter.taichung.gov.tw/api/v1/no-auth/resource.download"
    "?rid=495aff49-3547-4055-aacd-f0781c6f733e"
)
MARKET = "市場名稱"
OBS_DATE = "訪價日期"
RETIRED_PREFIX = "(停)"
FROZEN_BY_COLUMN = {1: "sponge_gourd", 8: "bok_choy", 10: "cabbage"}

MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024
MAX_PRICE = 100_000.0           # 元/臺斤; far above any real quote, catches unit blow-ups
MIN_DOWNLOAD_RATIO = 0.9        # a download may not shrink by more than 10%
MAX_MISMATCH_RATE = 0.01        # share of re-published values that may differ
REVISION_WINDOW_DAYS = 7        # only this recent a day may be revised
JUMP_FACTOR = 5.0               # x5 or /5 against the recent median is a jump
JUMP_WINDOW = 28
JUMP_MIN_POINTS = 5
MAX_JUMP_RATE = 0.05            # more jumps than this looks like a unit change
KEEP_VERSIONS = 20

FILES = (
    "source_rows.json.gz",      # canonical new source rows (dates after the frozen cutoff)
    "download.json.gz",         # the raw download this version was built from
    "public_history.parquet",   # 3 frozen crops, release 0.1.0 format
    "catalog.json",             # 61 items, full_catalog_runtime format
    "public_history.json.gz",   # 61 items, full_catalog_runtime format
)
VERSION_RE = re.compile(r"\d{8}-[0-9a-f]{12}\Z")
NUMBER_RE = re.compile(r"\d+(\.\d+)?\Z")
FRAME_COLUMNS = ["market_id", "date", "crop_id", "price"]


class Rejected(Exception):
    """A download or stored version that must not be served."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(obj) -> bytes:
    """The serialization build_full_market_catalog used for public_history.json.gz."""
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def gzip_bytes(data: bytes) -> bytes:
    return gzip.compress(data, compresslevel=9, mtime=0)


def price_value(value) -> float | None:
    """Same rule as build_full_market_catalog._price: 0, blank or junk is missing."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number > 0 else None


def iso_day(day: str) -> str:
    return datetime.strptime(day, "%Y%m%d").date().isoformat()


# ---------- the frozen snapshot the models are pinned to ----------

@dataclass(frozen=True)
class FrozenBase:
    catalog: dict
    index: dict
    manifest: dict
    columns: tuple            # the 61 source price columns, in source order
    crop_ids: tuple           # crop id of each column
    markets: tuple            # the 13 active markets
    cutoff: str               # ISO date, 2026-10-02
    history_sha256: str       # canonical JSON of the frozen 61-item history
    frame: pd.DataFrame       # release 0.1.0 public_history.parquet
    frame_sha256: str
    market_days: int          # active market days in the frozen snapshot
    training_source_sha256: str


def load_frozen_base(release_dir: Path, bundle: tuple) -> FrozenBase:
    """bundle is the ORIGINAL verified full_catalog_runtime.data_bundle() result."""
    from aiot_price.data.schema import CROP_MAPPINGS
    from aiot_price.integrations.chatgpt_adapter import FROZEN_SHA256

    catalog, history, index, manifest = bundle
    release_dir = Path(release_dir)
    release_bytes = (release_dir / "manifest.json").read_bytes()
    parquet_bytes = (release_dir / "public_history.parquet").read_bytes()
    if (sha256(release_bytes) != FROZEN_SHA256["manifest.json"]
            or sha256(parquet_bytes) != FROZEN_SHA256["public_history.parquet"]):
        raise Rejected("frozen_release", "release 0.1.0 manifest or public history hash mismatch")
    release = json.loads(release_bytes.decode("utf-8"))
    if (release["source"]["json_sha256"] != manifest["source_sha256"]
            or release["source"]["observation_end"] != manifest["source_cutoff"]):
        raise Rejected("frozen_release", "release 0.1.0 and the catalog were not built from one snapshot")
    items = sorted(catalog["items"], key=lambda entry: entry["source_column_index"])
    columns = tuple(entry["display_name"] for entry in items)
    crop_ids = tuple(entry["crop_id"] for entry in items)
    expected_ids = tuple(FROZEN_BY_COLUMN.get(i, f"taichung_{i:02d}") for i in range(1, 62))
    if len(columns) != 61 or crop_ids != expected_ids or [e["source_column_index"] for e in items] != list(range(1, 62)):
        raise Rejected("frozen_catalog", "catalog columns are not the 61 source columns in order")
    mapped = {m.source_column: crop for crop, m in CROP_MAPPINGS.items()}
    if mapped != {columns[i - 1]: crop for i, crop in FROZEN_BY_COLUMN.items()}:
        raise Rejected("frozen_catalog", "frozen crop mapping no longer matches the source columns")
    frame = pd.read_parquet(io.BytesIO(parquet_bytes))
    if list(frame.columns) != FRAME_COLUMNS:
        raise Rejected("frozen_release", "unexpected frozen public history columns")
    return FrozenBase(
        catalog=catalog, index=index, manifest=manifest, columns=columns, crop_ids=crop_ids,
        markets=tuple(catalog["markets"]), cutoff=manifest["source_cutoff"],
        history_sha256=sha256(canonical(history)), frame=frame,
        frame_sha256=sha256(parquet_bytes),
        market_days=len(frame[["market_id", "date"]].drop_duplicates()),
        training_source_sha256=manifest["source_sha256"],
    )


def frozen_identity(base: FrozenBase) -> dict:
    return {
        "training_source_sha256": base.training_source_sha256,
        "cutoff": base.cutoff,
        "release_public_history_sha256": base.frame_sha256,
        "catalog_sha256": base.manifest["catalog_sha256"],
        "catalog_history_sha256": base.manifest["history_sha256"],
        "history_canonical_sha256": base.history_sha256,
    }


# ---------- a new download ----------

@dataclass(frozen=True)
class Download:
    rows: list                # active-market rows, de-duplicated, sorted by (date, market)
    sha256: str
    size: int
    total_rows: int
    retired_rows: int
    first_day: str
    last_day: str


def _check_value(value, where: str) -> None:
    if isinstance(value, bool):
        raise Rejected("bad_price", f"{where}: boolean price")
    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, str):
        text = value.strip()
        if text == "":
            return
        if not NUMBER_RE.fullmatch(text):
            raise Rejected("bad_price", f"{where}: price is not a non-negative number")
        number = float(text)
    else:
        raise Rejected("bad_price", f"{where}: price has an unexpected type")
    if not math.isfinite(number) or number < 0 or number > MAX_PRICE:
        raise Rejected("bad_price", f"{where}: price outside 0..{MAX_PRICE:g}")


def parse_download(raw: bytes, base: FrozenBase, today: date) -> Download:
    if not raw or len(raw) > MAX_DOWNLOAD_BYTES:
        raise Rejected("download_size", f"download is empty or larger than {MAX_DOWNLOAD_BYTES} bytes")
    try:
        rows = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise Rejected("download_not_json", "download is not valid UTF-8 JSON") from None
    if not isinstance(rows, list) or not rows:
        raise Rejected("download_shape", "download is not a non-empty JSON list")
    expected = [MARKET, OBS_DATE, *base.columns]
    seen: dict[tuple[str, str], dict] = {}
    retired = 0
    for number, row in enumerate(rows, 1):
        if not isinstance(row, dict) or list(row) != expected:
            raise Rejected("schema_changed", f"row {number} is not the 63-field source schema")
        market, day = row[MARKET], row[OBS_DATE]
        if not isinstance(market, str) or not isinstance(day, str) or not re.fullmatch(r"\d{8}", day):
            raise Rejected("bad_date", f"row {number}: market or date field malformed")
        try:
            when = datetime.strptime(day, "%Y%m%d").date()
        except ValueError:
            raise Rejected("bad_date", f"row {number}: {day} is not a calendar date") from None
        if when > today or when.year < 2020:
            raise Rejected("bad_date", f"row {number}: {day} is in the future or implausibly old")
        for name in base.columns:
            _check_value(row[name], f"row {number}")
        if market.startswith(RETIRED_PREFIX):
            retired += 1
            continue
        if market not in base.markets:
            raise Rejected("unknown_market", f"row {number}: market not among the 13 supported")
        key = (day, market)
        if key in seen and seen[key] != row:
            raise Rejected("conflicting_duplicate", f"row {number}: two different rows for one market day")
        seen[key] = row
    if not seen:
        raise Rejected("download_shape", "download has no active-market rows")
    active = [seen[key] for key in sorted(seen)]
    return Download(rows=active, sha256=sha256(raw), size=len(raw), total_rows=len(rows),
                    retired_rows=retired, first_day=iso_day(active[0][OBS_DATE]),
                    last_day=iso_day(active[-1][OBS_DATE]))


# ---------- merging onto the last good version ----------

def _points(history: dict) -> dict:
    return {(crop, market, day): price
            for crop, groups in history.items()
            for market, points in groups.items()
            for day, price in points}


def merge(base: FrozenBase, frozen_history: dict, previous: "Version | None",
          download: Download, *, accept_shorter: bool = False) -> tuple[list, dict]:
    """New post-cutoff rows = previous rows, plus new days, plus recent revisions.

    Rows are never dropped. Frozen-period values are never changed; they are
    only compared, to catch a source that redefined its columns or units.
    """
    previous_rows = previous.rows if previous else []
    previous_cutoff = previous.cutoff if previous else base.cutoff
    reference = previous.download_rows if previous else base.market_days
    if len(download.rows) < MIN_DOWNLOAD_RATIO * reference and not accept_shorter:
        raise Rejected("download_shrank", f"{len(download.rows)} active rows, previous download {reference}")
    if download.last_day < previous_cutoff:
        raise Rejected("download_older", f"latest day {download.last_day} is before the current {previous_cutoff}")

    frozen_points = _points(frozen_history)
    frozen_days = {(market, str(day.date())) for market, day in
                   base.frame[["market_id", "date"]].drop_duplicates().itertuples(index=False)}
    by_key = {(row[OBS_DATE], row[MARKET]): row for row in previous_rows}
    revise_from = date.fromisoformat(previous_cutoff).toordinal() - REVISION_WINDOW_DAYS
    stats = Counter()
    for row in download.rows:
        day, market = row[OBS_DATE], row[MARKET]
        day_iso = iso_day(day)
        new_values = [price_value(row[name]) for name in base.columns]
        if day_iso <= base.cutoff:
            if (market, day_iso) not in frozen_days:
                stats["frozen_late_rows"] += 1     # published after the snapshot; never added
                continue
            for crop, value in zip(base.crop_ids, new_values):
                stats["frozen_compared"] += 1
                stats["frozen_mismatch"] += value != frozen_points.get((crop, market, day_iso))
            continue
        old = by_key.get((day, market))
        if old is None:
            by_key[(day, market)] = row
            stats["added_rows"] += 1
            continue
        changed = sum(price_value(old[name]) != value for name, value in zip(base.columns, new_values))
        stats["previous_compared"] += len(base.columns)
        stats["previous_mismatch"] += changed
        if changed and date.fromisoformat(day_iso).toordinal() >= revise_from:
            by_key[(day, market)] = row
            stats["revised_values"] += changed
        elif changed:
            stats["ignored_old_revisions"] += changed
    for kind in ("frozen", "previous"):
        compared, mismatch = stats[f"{kind}_compared"], stats[f"{kind}_mismatch"]
        if compared and mismatch / compared > MAX_MISMATCH_RATE:
            raise Rejected("source_changed", f"{mismatch}/{compared} re-published {kind} values differ")
    rows = [by_key[key] for key in sorted(by_key)]
    if len(rows) < len(previous_rows):
        raise Rejected("rows_shrank", "merged history has fewer market days than the previous version")
    return rows, dict(stats)


# ---------- derived artifacts ----------

def build_history(base: FrozenBase, frozen_history: dict, rows: list) -> dict:
    """61-item history exactly as build_full_market_catalog stores it."""
    history = copy.deepcopy(frozen_history)
    for row in rows:
        day = iso_day(row[OBS_DATE])
        for crop, name in zip(base.crop_ids, base.columns):
            value = price_value(row[name])
            if value is not None:
                history[crop].setdefault(row[MARKET], []).append([day, value])
    return history


def check_jumps(base: FrozenBase, history: dict, rows: list, previous: "Version | None") -> dict:
    """Reject when many newly added values jump x5 against their recent median."""
    old_keys = {(r[OBS_DATE], r[MARKET]) for r in previous.rows} if previous else set()
    days_of: dict[tuple[str, str], list[str]] = {}
    checked = jumps = 0
    for row in rows:
        if (row[OBS_DATE], row[MARKET]) in old_keys:
            continue
        day = iso_day(row[OBS_DATE])
        for crop, name in zip(base.crop_ids, base.columns):
            value = price_value(row[name])
            if value is None:
                continue
            points = history[crop].get(row[MARKET], [])
            days = days_of.setdefault((crop, row[MARKET]), [p[0] for p in points])
            end = bisect_left(days, day)
            recent = sorted(p[1] for p in points[max(0, end - JUMP_WINDOW):end])
            if len(recent) < JUMP_MIN_POINTS:
                continue
            median = recent[len(recent) // 2]
            checked += 1
            jumps += not (median / JUMP_FACTOR <= value <= median * JUMP_FACTOR)
    if checked and jumps / checked > MAX_JUMP_RATE:
        raise Rejected("price_jump", f"{jumps}/{checked} new values moved more than x{JUMP_FACTOR:g}")
    return {"jump_checked": checked, "jump_outliers": jumps}


def build_frame(base: FrozenBase, rows: list) -> pd.DataFrame:
    """3-crop history exactly as models/package.py builds release 0.1.0's parquet."""
    from aiot_price.data.load import load_taichung_long
    from aiot_price.data.schema import CROP_MAPPINGS

    if not rows:
        return base.frame.copy()
    with tempfile.TemporaryDirectory(prefix="fmpa_rolling_") as folder:
        path = Path(folder) / "rows.json"
        path.write_bytes(canonical(rows))
        long_df, _ = load_taichung_long(path, crop_columns=[m.source_column for m in CROP_MAPPINGS.values()])
    long_df = long_df[~long_df["market_id"].str.contains(RETIRED_PREFIX, regex=False)].copy()
    long_df["crop_id"] = long_df["crop_raw"].map({m.source_column: cid for cid, m in CROP_MAPPINGS.items()})
    return pd.concat([base.frame, long_df[FRAME_COLUMNS]], ignore_index=True)


def build_catalog(base: FrozenBase, history: dict, rows: list, *, version: str, cutoff: str) -> dict:
    """The frozen catalog with only the cutoff and per-market statistics moved on."""
    zeros = Counter()
    for row in rows:
        for crop, name in zip(base.crop_ids, base.columns):
            zeros[crop] += str(row[name]).strip() == "0"
    catalog = copy.deepcopy(base.catalog)
    for entry in catalog["items"]:
        groups = history[entry["crop_id"]]
        stats = {}
        for market in base.markets:
            points = groups.get(market, [])
            stats[market] = {
                "observations": len(points),
                "latest_observed_date": points[-1][0] if points else None,
                "latest_public_market_mean": points[-1][1] if points else None,
            }
        entry["markets"] = stats
        entry["has_ever_had_public_price"] = any(s["observations"] for s in stats.values())
        entry["total_nonzero_observations"] = sum(s["observations"] for s in stats.values())
        entry["missing_zeros"] = base.index[entry["crop_id"]]["missing_zeros"] + zeros[entry["crop_id"]]
    catalog["source_observation_cutoff"] = cutoff
    catalog["public_history"] = {"schema": SCHEMA, "version": version, "cutoff": cutoff,
                                 "frozen_cutoff": base.cutoff}
    return catalog


def frozen_prefix(history: dict, cutoff: str) -> dict:
    """History cut back to the frozen cutoff; equals the frozen history iff it is untouched."""
    out = {}
    for crop, groups in history.items():
        kept = {}
        for market, points in groups.items():
            prefix = [p for p in points if p[0] <= cutoff]
            if prefix:
                kept[market] = prefix
        out[crop] = kept
    return out


# ---------- stored versions ----------

@dataclass(frozen=True)
class Version:
    version: str
    manifest_sha256: str
    manifest: dict
    rows: list
    catalog: dict
    history: dict
    index: dict
    parquet: bytes
    parquet_sha256: str
    cutoff: str
    download_rows: int


def _check_history(base: FrozenBase, history: dict, catalog: dict, cutoff: str) -> None:
    if list(history) != list(base.crop_ids):
        raise Rejected("bad_history", "history items differ from the frozen catalog")
    for crop, groups in history.items():
        for market, points in groups.items():
            if market not in base.markets or not points:
                raise Rejected("bad_history", "history has an unknown market or empty series")
            days = [p[0] for p in points]
            if days != sorted(set(days)) or days[-1] > cutoff:
                raise Rejected("bad_history", "history dates are not increasing within the cutoff")
            if any(not isinstance(p[1], float) or not 0 < p[1] <= MAX_PRICE for p in points):
                raise Rejected("bad_history", "history has a non-positive or implausible price")
    if sha256(canonical(frozen_prefix(history, base.cutoff))) != base.history_sha256:
        raise Rejected("frozen_prefix_changed", "history before the frozen cutoff differs from the snapshot")
    expected = build_catalog(base, history, [], version=catalog.get("public_history", {}).get("version", ""),
                             cutoff=cutoff)
    for got, want in zip(catalog["items"], expected["items"]):
        got = {k: v for k, v in got.items() if k != "missing_zeros"}
        want = {k: v for k, v in want.items() if k != "missing_zeros"}
        if got != want:
            raise Rejected("bad_catalog", f"catalog entry {want['crop_id']} disagrees with the history")
    frozen_top = {k: v for k, v in base.catalog.items() if k not in ("items", "source_observation_cutoff")}
    if (len(catalog["items"]) != len(expected["items"])
            or {k: v for k, v in catalog.items() if k in frozen_top} != frozen_top
            or catalog.get("source_observation_cutoff") != cutoff):
        raise Rejected("bad_catalog", "catalog header differs from the frozen catalog")


def _check_frame(base: FrozenBase, frame: pd.DataFrame, cutoff: str) -> None:
    if list(frame.columns) != FRAME_COLUMNS or len(frame) < len(base.frame):
        raise Rejected("bad_parquet", "3-crop history is shorter than the frozen one or has other columns")
    prefix = frame.iloc[:len(base.frame)].reset_index(drop=True)
    try:
        pd.testing.assert_frame_equal(prefix, base.frame, check_exact=True)
    except AssertionError:
        raise Rejected("frozen_prefix_changed", "3-crop history before the frozen cutoff differs") from None
    post = frame.iloc[len(base.frame):]
    frozen_ts = pd.Timestamp(base.cutoff)
    if (not post.empty and (
            (post["date"] <= frozen_ts).any()
            or not post["market_id"].isin(base.markets).all()
            or not post["crop_id"].isin(FROZEN_BY_COLUMN.values()).all()
            or (post["price"].dropna() <= 0).any())):
        raise Rejected("bad_parquet", "3-crop history has rows outside the rolling contract")
    if str(frame["date"].max().date()) != cutoff:
        raise Rejected("bad_parquet", "3-crop history cutoff differs from the manifest")


def load_version(root: Path, version: str, manifest_sha256: str, base: FrozenBase) -> Version:
    """Verify every byte and invariant of one stored version before it is served.

    Anything unexpected in stored data rejects that version; it never raises
    anything but Rejected, so a damaged folder cannot stop the service.
    """
    if not isinstance(version, str) or not VERSION_RE.fullmatch(version):
        raise Rejected("bad_pointer", "malformed version id")
    try:
        return _load_version(Path(root) / "versions" / version, version, manifest_sha256, base)
    except Rejected:
        raise
    except Exception as exc:
        raise Rejected("unreadable", f"{version}: {type(exc).__name__}") from None


def _load_version(folder: Path, version: str, manifest_sha256: str, base: FrozenBase) -> Version:
    manifest_bytes = (folder / "manifest.json").read_bytes()
    if sha256(manifest_bytes) != manifest_sha256:
        raise Rejected("manifest_hash", f"{version}: manifest hash mismatch")
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    if (manifest.get("schema") != SCHEMA or manifest.get("version") != version
            or manifest.get("frozen_base") != frozen_identity(base)
            or set(manifest.get("files", {})) != set(FILES)):
        raise Rejected("manifest_contract", f"{version}: manifest is not for this frozen snapshot")
    data = {}
    for name in FILES:
        content = (folder / name).read_bytes()
        if sha256(content) != manifest["files"][name]["sha256"]:
            raise Rejected("file_hash", f"{version}: {name} hash mismatch")
        data[name] = content
    cutoff = manifest["cutoff"]
    rows = json.loads(gzip.decompress(data["source_rows.json.gz"]).decode("utf-8"))
    history = json.loads(gzip.decompress(data["public_history.json.gz"]).decode("utf-8"))
    catalog = json.loads(data["catalog.json"].decode("utf-8"))
    frame = pd.read_parquet(io.BytesIO(data["public_history.parquet"]))
    last = iso_day(rows[-1][OBS_DATE]) if rows else base.cutoff
    if (len(rows) != manifest["counts"]["post_cutoff_market_days"]
            or sha256(canonical(rows)) != manifest["counts"]["rows_sha256"]
            or not version.endswith(manifest["counts"]["rows_sha256"][:12])
            or cutoff != last or cutoff < base.cutoff
            or (rows and iso_day(rows[0][OBS_DATE]) <= base.cutoff)
            or catalog.get("public_history", {}).get("version") != version):
        raise Rejected("manifest_contract", f"{version}: row counts, hashes or cutoff disagree")
    _check_history(base, history, catalog, cutoff)
    _check_frame(base, frame, cutoff)
    return Version(
        version=version, manifest_sha256=manifest_sha256, manifest=manifest, rows=rows,
        catalog=catalog, history=history,
        index={entry["crop_id"]: entry for entry in catalog["items"]},
        parquet=data["public_history.parquet"], parquet_sha256=manifest["files"]["public_history.parquet"]["sha256"],
        cutoff=cutoff, download_rows=manifest["source"]["active_market_days"],
    )


def read_pointer(root: Path) -> dict:
    try:
        pointer = json.loads((Path(root) / "CURRENT.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise Rejected("no_pointer", "no rolling version has been published") from None
    except (OSError, ValueError):
        raise Rejected("bad_pointer", "CURRENT.json is unreadable") from None
    if not isinstance(pointer, dict) or pointer.get("schema") != SCHEMA:
        raise Rejected("bad_pointer", "CURRENT.json has an unexpected schema")
    return pointer


def pointer_candidates(pointer: dict) -> list[tuple[str, str]]:
    entries = [pointer, *pointer.get("fallbacks", [])]
    return [(e.get("version"), e.get("manifest_sha256")) for e in entries if isinstance(e, dict)]


def select(root: Path, base: FrozenBase) -> tuple[Version | None, list[str]]:
    """Newest version that verifies: CURRENT first, then its listed fallbacks."""
    try:
        pointer = read_pointer(root)
    except Rejected as exc:
        return None, [str(exc)]
    errors = []
    for version, manifest_sha in pointer_candidates(pointer):
        try:
            return load_version(root, version, manifest_sha, base), errors
        except Rejected as exc:
            errors.append(str(exc))
    return None, errors


# ---------- publishing ----------

def _fsync_dir(path: Path) -> None:
    if not hasattr(os, "O_DIRECTORY"):
        return
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_synced(path: Path, data: bytes) -> None:
    with open(path, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o644)


def atomic_write(path: Path, data: bytes) -> None:
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", dir=path.parent)
    os.close(fd)
    try:
        _write_synced(Path(tmp), data)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    _fsync_dir(path.parent)


def publish(root: Path, base: FrozenBase, frozen_history: dict, previous: Version | None,
            download: Download, raw: bytes, *, retrieved_at: str,
            accept_shorter: bool = False) -> dict:
    """Validate, build, write and switch to a new version, or report it unchanged."""
    root = Path(root)
    rows, stats = merge(base, frozen_history, previous, download, accept_shorter=accept_shorter)
    rows_bytes = canonical(rows)
    rows_sha = sha256(rows_bytes)
    if previous and rows_sha == previous.manifest["counts"]["rows_sha256"]:
        return {"outcome": "unchanged", "version": previous.version, "cutoff": previous.cutoff,
                "download_last_day": download.last_day, **stats}
    history = build_history(base, frozen_history, rows)
    stats.update(check_jumps(base, history, rows, previous))
    cutoff = max(base.cutoff, iso_day(rows[-1][OBS_DATE])) if rows else base.cutoff
    version = cutoff.replace("-", "") + "-" + rows_sha[:12]
    catalog = build_catalog(base, history, rows, version=version, cutoff=cutoff)
    frame = build_frame(base, rows)
    buffer = io.BytesIO()
    frame.to_parquet(buffer, index=False)
    files = {
        "source_rows.json.gz": gzip_bytes(rows_bytes),
        "download.json.gz": gzip_bytes(raw),
        "public_history.parquet": buffer.getvalue(),
        "catalog.json": canonical(catalog),
        "public_history.json.gz": gzip_bytes(canonical(history)),
    }
    manifest = {
        "schema": SCHEMA,
        "version": version,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cutoff": cutoff,
        "frozen_base": frozen_identity(base),
        "source": {
            "dataset_id": DATASET_ID, "url": DOWNLOAD_URL, "retrieved_at": retrieved_at,
            "download_sha256": download.sha256, "download_bytes": download.size,
            "download_rows": download.total_rows, "retired_market_rows": download.retired_rows,
            "active_market_days": len(download.rows),
            "first_day": download.first_day, "last_day": download.last_day,
        },
        "counts": {
            "post_cutoff_market_days": len(rows), "rows_sha256": rows_sha,
            "history_points": sum(len(p) for g in history.values() for p in g.values()),
            "parquet_rows": len(frame),
        },
        "merge": stats,
        "accept_shorter_download": accept_shorter,
        "previous": None if previous is None else {
            "version": previous.version, "manifest_sha256": previous.manifest_sha256,
            "post_cutoff_market_days": len(previous.rows),
        },
        "files": {name: {"sha256": sha256(data), "bytes": len(data)} for name, data in files.items()},
    }
    versions = root / "versions"
    versions.mkdir(parents=True, exist_ok=True)
    final = versions / version
    if final.exists():
        # Same rows as a version that no longer verifies (it was not chosen as
        # previous): set it aside so the rebuilt one can take its place.
        os.rename(final, versions / f".damaged-{version}-{datetime.now(timezone.utc):%Y%m%dT%H%M%S}")
    staging = Path(tempfile.mkdtemp(prefix=".tmp-", dir=versions))
    try:
        for name, data in files.items():
            _write_synced(staging / name, data)
        manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
        _write_synced(staging / "manifest.json", manifest_bytes)
        staging.chmod(0o755)
        _fsync_dir(staging)
        os.rename(staging, final)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    _fsync_dir(versions)
    # The new version must pass the same check the server runs before it is pointed at.
    try:
        load_version(root, version, sha256(manifest_bytes), base)
    except Rejected:
        shutil.rmtree(final, ignore_errors=True)
        raise
    fallbacks = []
    if previous:
        fallbacks = [{"version": previous.version, "manifest_sha256": previous.manifest_sha256}]
        try:
            old = pointer_candidates(read_pointer(root))
        except Rejected:
            old = []
        # select() took the first entry that verified, so entries before
        # previous are known bad; keep only the older ones after it.
        names = [v for v, _ in old]
        tail = old[names.index(previous.version) + 1:] if previous.version in names else []
        fallbacks += [{"version": v, "manifest_sha256": s} for v, s in tail
                      if isinstance(v, str) and VERSION_RE.fullmatch(v) and (versions / v).is_dir()]
    pointer = {"schema": SCHEMA, "version": version, "manifest_sha256": sha256(manifest_bytes),
               "cutoff": cutoff, "fallbacks": fallbacks[:KEEP_VERSIONS - 1]}
    atomic_write(root / "CURRENT.json", json.dumps(pointer, ensure_ascii=False, indent=2).encode("utf-8"))
    prune(root, pointer)
    return {"outcome": "switched", "version": version, "cutoff": cutoff,
            "previous_version": previous.version if previous else None,
            "download_last_day": download.last_day, **stats}


def prune(root: Path, pointer: dict) -> list[str]:
    """Remove version folders the pointer no longer lists, and stale staging folders."""
    keep = {v for v, _ in pointer_candidates(pointer)}
    removed = []
    for folder in sorted((Path(root) / "versions").iterdir()):
        if folder.is_dir() and folder.name not in keep:
            shutil.rmtree(folder)
            removed.append(folder.name)
    return removed
