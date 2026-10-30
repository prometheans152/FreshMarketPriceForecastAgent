"""Rolling public history (D48): validation, versions, fallback and the served app.

Store tests run in this process on the repo modules. App tests run
rolling_probe.py / rolling_update.py in fresh interpreters on the sources
baked into the deployed v1.0.0 image, as test_v1_full_catalog.py does.

Needs local artifacts that are not in git; each test skips without them:
- the portable release folder the image was built from (FMPA_V1EXT_IMAGE_DIR);
- a saved real source download (FMPA_ROLLING_DOWNLOAD), here the 2026-10-30
  one with days up to 2026-10-29;
- the frozen source JSON data/raw/taichung/retail_prices_20261003.json (parity).
"""
from __future__ import annotations

import copy
import dataclasses
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
IMAGE_DIR = Path(os.environ.get(
    "FMPA_V1EXT_IMAGE_DIR",
    ROOT / "outputs/quality_runs/tw01_docker_portable_final_20261015_025240_Windows5800X/TW01_Docker_Portable_v1.0.0",
))
DOWNLOAD = Path(os.environ.get(
    "FMPA_ROLLING_DOWNLOAD",
    ROOT / "outputs/quality_runs/rolling_history_d48_20261030/download/taichung_20261030.json",
))
FROZEN_SOURCE = ROOT / "data/raw/taichung/retail_prices_20261003.json"
TODAY = date(2026, 10, 30)
TOKEN = "test_only_" + "r" * 48

pytestmark = pytest.mark.skipif(
    not (IMAGE_DIR / "catalog/catalog.json").is_file() or not DOWNLOAD.is_file(),
    reason="portable release or saved source download not present")

sys.path[:0] = [str(HERE), str(HERE.parent)]
import rolling_store as store  # noqa: E402


# ---------- fixtures ----------

@pytest.fixture(scope="module")
def frozen():
    os.environ["FMPA_EXTENDED_CATALOG_DIR"] = str(IMAGE_DIR / "catalog")
    import full_catalog_runtime

    bundle = full_catalog_runtime.data_bundle.__wrapped__()
    return store.load_frozen_base(IMAGE_DIR / "models/releases/0.1.0", bundle), bundle[1]


@pytest.fixture(scope="module")
def raw_rows():
    return json.loads(DOWNLOAD.read_bytes().decode("utf-8"))


def encode(rows) -> bytes:
    return json.dumps(rows, ensure_ascii=False).encode("utf-8")


def up_to(rows, last_day: str):
    return [r for r in rows if r[store.OBS_DATE] <= last_day]


def publish(frozen, root: Path, rows, *, accept_shorter=False):
    base, history = frozen
    raw = encode(rows) if not isinstance(rows, bytes) else rows
    previous, _ = store.select(root, base)
    download = store.parse_download(raw, base, TODAY)
    return store.publish(root, base, history, previous, download, raw,
                         retrieved_at="2026-10-30T00:00:00+00:00", accept_shorter=accept_shorter)


def snapshot(root: Path) -> dict:
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


@pytest.fixture()
def first(frozen, raw_rows, tmp_path):
    """A rolling folder whose current version covers source days up to 2026-10-20."""
    publish(frozen, tmp_path, up_to(raw_rows, "20261020"))
    return tmp_path


# ---------- the derivations reproduce the frozen artifacts ----------

def test_canonical_serialization_is_the_frozen_file(frozen):
    base, history = frozen
    plain = gzip.decompress((IMAGE_DIR / "catalog/public_history.json.gz").read_bytes())
    assert hashlib.sha256(plain).hexdigest() == base.history_sha256 == store.sha256(store.canonical(history))


def test_catalog_rebuild_without_new_rows_is_the_frozen_catalog(frozen):
    base, history = frozen
    rebuilt = store.build_catalog(base, history, [], version="x", cutoff=base.cutoff)
    assert rebuilt.pop("public_history")["frozen_cutoff"] == "2026-10-02"
    assert rebuilt == base.catalog


@pytest.mark.skipif(not FROZEN_SOURCE.is_file(), reason="frozen source JSON not present")
def test_derivations_reproduce_the_frozen_snapshot_from_its_source(frozen):
    """Same rules as build_full_market_catalog.py and models/package.py, on the full frozen year."""
    base, history = frozen
    raw = FROZEN_SOURCE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == base.training_source_sha256
    parsed = store.parse_download(raw, base, date(2026, 10, 3))   # the frozen source passes validation
    empty = {crop: {} for crop in base.crop_ids}
    assert store.build_history(base, empty, parsed.rows) == history
    frame = store.build_frame(dataclasses.replace(base, frame=base.frame.iloc[:0]), parsed.rows)
    key = ["market_id", "date", "crop_id"]
    pd.testing.assert_frame_equal(frame.sort_values(key).reset_index(drop=True),
                                  base.frame.sort_values(key).reset_index(drop=True), check_exact=True)


# ---------- publishing, versions and fallback ----------

def test_real_download_publishes_a_verified_version(frozen, raw_rows, tmp_path):
    base, _ = frozen
    result = publish(frozen, tmp_path, raw_rows)
    assert result["outcome"] == "switched" and result["cutoff"] == "2026-10-29"
    assert result["frozen_mismatch"] == 0 and result["frozen_compared"] > 200_000
    assert result["jump_outliers"] == 0 and result["added_rows"] > 300
    version, errors = store.select(tmp_path, base)
    assert version.version == result["version"] and errors == []
    assert version.manifest["frozen_base"]["training_source_sha256"].startswith("172dffc76e82")
    assert version.catalog["source_observation_cutoff"] == "2026-10-29"
    assert version.index["taichung_40"]["markets"]["第三市場"]["latest_observed_date"] > "2026-10-02"
    frame = pd.read_parquet(__import__("io").BytesIO(version.parquet))
    assert str(frame["date"].max().date()) == "2026-10-29" and len(frame) > len(base.frame)
    assert publish(frozen, tmp_path, raw_rows)["outcome"] == "unchanged"
    assert [p.name for p in (tmp_path / "versions").iterdir()] == [result["version"]]


def test_newer_download_switches_and_keeps_the_previous_as_fallback(frozen, raw_rows, first):
    base, _ = frozen
    old = store.read_pointer(first)
    result = publish(frozen, first, raw_rows)
    pointer = store.read_pointer(first)
    assert result["previous_version"] == old["version"] != pointer["version"]
    assert pointer["fallbacks"] == [{"version": old["version"], "manifest_sha256": old["manifest_sha256"]}]
    newest, _ = store.select(first, base)
    previous = store.load_version(first, old["version"], old["manifest_sha256"], base)
    assert len(newest.rows) > len(previous.rows) and newest.cutoff > previous.cutoff


def test_damaged_newest_version_falls_back_to_the_last_good_one(frozen, raw_rows, first):
    base, _ = frozen
    old = store.read_pointer(first)
    publish(frozen, first, raw_rows)
    newest = store.read_pointer(first)["version"]
    damaged = first / "versions" / newest / "public_history.json.gz"
    damaged.write_bytes(damaged.read_bytes()[:-10])
    version, errors = store.select(first, base)
    assert version.version == old["version"] and errors[0].startswith("file_hash")
    # Next run builds on the last good version and replaces the damaged one.
    result = publish(frozen, first, raw_rows)
    assert result["outcome"] == "switched" and result["previous_version"] == old["version"]
    assert store.select(first, base)[0].version == newest


def test_every_version_damaged_or_pointer_broken_serves_nothing(frozen, first):
    base, _ = frozen
    version = store.read_pointer(first)["version"]
    (first / "versions" / version / "catalog.json").write_text("{}", encoding="utf-8")
    assert store.select(first, base)[0] is None
    (first / "CURRENT.json").write_text("not json", encoding="utf-8")
    assert store.select(first, base) == (None, ["bad_pointer: CURRENT.json is unreadable"])


def _rehash(root: Path, version: str, edit) -> None:
    """Tamper with a version AND recompute every hash, as an insider could."""
    folder = root / "versions" / version
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    edit(folder, manifest)
    for name in store.FILES:
        manifest["files"][name]["sha256"] = store.sha256((folder / name).read_bytes())
    data = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
    (folder / "manifest.json").write_bytes(data)
    pointer = store.read_pointer(root)
    pointer["manifest_sha256"] = store.sha256(data)
    (root / "CURRENT.json").write_text(json.dumps(pointer), encoding="utf-8")


def test_frozen_period_cannot_be_rewritten_even_with_matching_hashes(frozen, first):
    base, _ = frozen
    version = store.read_pointer(first)["version"]

    def edit_history(folder, manifest):
        history = json.loads(gzip.decompress((folder / "public_history.json.gz").read_bytes()))
        history["taichung_40"]["第三市場"][0][1] += 1.0
        (folder / "public_history.json.gz").write_bytes(store.gzip_bytes(store.canonical(history)))

    _rehash(first, version, edit_history)
    assert store.select(first, base)[1][0].startswith("frozen_prefix_changed")


def test_frozen_crops_history_cannot_be_rewritten_even_with_matching_hashes(frozen, first):
    base, _ = frozen
    version = store.read_pointer(first)["version"]

    def edit_parquet(folder, manifest):
        frame = pd.read_parquet(folder / "public_history.parquet")
        assert frame.loc[0, "price"] != 999.0
        frame.loc[0, "price"] = 999.0
        frame.to_parquet(folder / "public_history.parquet", index=False)

    _rehash(first, version, edit_parquet)
    assert store.select(first, base)[1][0].startswith("frozen_prefix_changed")


def test_version_built_on_another_snapshot_is_rejected(frozen, first):
    base, _ = frozen
    version = store.read_pointer(first)["version"]
    _rehash(first, version, lambda folder, m: m["frozen_base"].update(cutoff="2026-10-01"))
    assert store.select(first, base)[1][0].startswith("manifest_contract")


def test_pointer_cannot_leave_the_versions_folder(frozen, first):
    base, _ = frozen
    pointer = store.read_pointer(first)
    pointer.update(version="../../etc", fallbacks=[])
    (first / "CURRENT.json").write_text(json.dumps(pointer), encoding="utf-8")
    assert store.select(first, base) == (None, ["bad_pointer: malformed version id"])


# ---------- negative controls: a bad download is rejected, nothing changes ----------

def _swap_columns(rows):
    out = copy.deepcopy(rows)
    a, b = "絲瓜", "花胡瓜"
    for row in out:
        row[a], row[b] = row[b], row[a]
    return out


def _times(rows, factor, after="20261020"):
    out = copy.deepcopy(rows)
    for row in out:
        if row[store.OBS_DATE] > after:
            for key in list(row)[2:]:
                row[key] = str(round(float(row[key]) * factor))
    return out


def _edit(rows, index, **changes):
    out = copy.deepcopy(rows)
    out[index].update(changes)
    return out


def _rename(rows):
    out = []
    for row in rows:
        row = dict(row)
        row["絲瓜(新)"] = row.pop("絲瓜")
        out.append(row)
    return out


NEGATIVE = {
    "truncated": (lambda rows, raw: encode(rows[-100:]), "download_shrank"),
    "cut_bytes": (lambda rows, raw: raw[: len(raw) // 2], "download_not_json"),
    "empty": (lambda rows, raw: b"", "download_size"),
    "not_a_list": (lambda rows, raw: b'{"rows": []}', "download_shape"),
    "renamed_column": (lambda rows, raw: encode(_rename(rows)), "schema_changed"),
    "unknown_market": (lambda rows, raw: encode(_edit(rows, -1, **{store.MARKET: "新市場"})), "unknown_market"),
    "negative_price": (lambda rows, raw: encode(_edit(rows, -1, 絲瓜="-5")), "bad_price"),
    "text_price": (lambda rows, raw: encode(_edit(rows, -1, 絲瓜="abc")), "bad_price"),
    "huge_price": (lambda rows, raw: encode(_edit(rows, -1, 絲瓜="999999")), "bad_price"),
    "future_date": (lambda rows, raw: encode(_edit(rows, -1, **{store.OBS_DATE: "20261231"})), "bad_date"),
    "bad_date": (lambda rows, raw: encode(_edit(rows, -1, **{store.OBS_DATE: "20261332"})), "bad_date"),
    "conflicting_duplicate": (lambda rows, raw: encode(rows + [_edit(rows, -1, 絲瓜="77")[-1]]),
                              "conflicting_duplicate"),
    "older_than_current": (lambda rows, raw: encode(up_to(rows, "20261015")), "download_older"),
    "columns_swapped": (lambda rows, raw: encode(_swap_columns(rows)), "source_changed"),
    "unit_changed_x10": (lambda rows, raw: encode(_times(rows, 10)), "price_jump"),
    "old_days_rewritten": (lambda rows, raw: encode(_times(rows, 1.5, after="20261002")), "source_changed"),
}


@pytest.mark.parametrize("case", sorted(NEGATIVE))
def test_bad_download_is_rejected_and_the_last_good_version_kept(frozen, raw_rows, first, case):
    mutate, code = NEGATIVE[case]
    before = snapshot(first)
    with pytest.raises(store.Rejected) as caught:
        publish(frozen, first, mutate(raw_rows, DOWNLOAD.read_bytes()))
    assert caught.value.code == code
    assert snapshot(first) == before


def test_recent_revision_is_applied_and_counted(frozen, raw_rows, first):
    base, _ = frozen
    day = max(r[store.OBS_DATE] for r in up_to(raw_rows, "20261020"))
    index = max(i for i, r in enumerate(raw_rows)
                if r[store.OBS_DATE] == day and not r[store.MARKET].startswith(store.RETIRED_PREFIX))
    cabbage = "甘藍（平地高麗菜）"
    revised = _edit(raw_rows, index, **{cabbage: str(int(raw_rows[index][cabbage]) + 7)})
    result = publish(frozen, first, revised)
    assert result["revised_values"] == 1 and result["outcome"] == "switched"
    version, _ = store.select(first, base)
    stored = next(r for r in version.rows if (r[store.OBS_DATE], r[store.MARKET]) ==
                  (day, raw_rows[index][store.MARKET]))
    assert stored[cabbage] == revised[index][cabbage]


def test_shorter_source_window_needs_the_explicit_override(frozen, raw_rows, first):
    shorter = [r for r in raw_rows if r[store.OBS_DATE] >= "20260801"]
    with pytest.raises(store.Rejected, match="download_shrank"):
        publish(frozen, first, shorter)
    result = publish(frozen, first, shorter, accept_shorter=True)
    assert result["outcome"] == "switched"
    pointer = store.read_pointer(first)
    manifest = json.loads((first / "versions" / pointer["version"] / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["accept_shorter_download"] is True
    # Rows already accepted are never dropped, only the reference size moves.
    assert manifest["counts"]["post_cutoff_market_days"] >= manifest["previous"]["post_cutoff_market_days"]


# ---------- the served app on the deployed image sources ----------

def image_env(**extra) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("FMPA_", "TW01_", "PROBE_"))}
    env.update({
        "PYTHONPATH": os.pathsep.join([str(IMAGE_DIR / "src"), str(IMAGE_DIR / "deploy/oracle-forecastengine"),
                                       str(HERE.parent / "v1_full_catalog"), str(HERE)]),
        "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1",
        "TW01_ORIGIN_API_TOKEN": TOKEN,
        "TW01_RELEASE_DIR": str(IMAGE_DIR / "models/releases/0.1.0"),
        "TW01_EXTENDED_CATALOG_DIR": str(IMAGE_DIR / "catalog"),
        "TW01_POOLED_ML_DIR": str(IMAGE_DIR / "models/pooled"),
    })
    env.update(extra)
    return env


def run_updater(root: Path, source: Path, *extra) -> tuple[int, dict]:
    done = subprocess.run(
        [sys.executable, str(HERE / "rolling_update.py"), "--root", str(root), "--source-file", str(source),
         "--today", TODAY.isoformat(), *extra],
        env=image_env(), cwd=str(HERE), capture_output=True, text=True, encoding="utf-8", timeout=600)
    return done.returncode, json.loads(done.stdout.strip().splitlines()[-1])


def run_probe(app: str, root: Path | None = None, swap: Path | None = None) -> dict:
    extra = {"PROBE_APP": app, "PROBE_TOKEN": TOKEN, "PROBE_DAY": "2026-10-30",
             "PROBE_PARITY_DAY": "2026-10-03", "PROBE_TODAY": TODAY.isoformat()}
    if root is not None:
        extra["FMPA_ROLLING_DIR"] = str(root)
    if swap is not None:
        extra["PROBE_SWAP_SOURCE"] = str(swap)
    done = subprocess.run([sys.executable, str(HERE / "rolling_probe.py")], env=image_env(**extra),
                          cwd=str(HERE), capture_output=True, text=True, encoding="utf-8", timeout=900)
    assert done.returncode == 0, done.stderr[-3000:]
    return json.loads(done.stdout.strip().splitlines()[-1])


@pytest.fixture(scope="module")
def served(raw_rows, tmp_path_factory):
    """v1ext (D47, frozen) and rolling (D48) probes; rolling switches 10-20 -> 10-29 while running."""
    root = tmp_path_factory.mktemp("rolling")
    partial = root.parent / "download_upto_20261020.json"
    partial.write_bytes(encode(up_to(raw_rows, "20261020")))
    code, first_run = run_updater(root, partial)
    assert code == 0 and first_run["outcome"] == "switched", first_run
    return {"root": root, "first": first_run,
            "frozen": run_probe("v1ext"),
            "rolling": run_probe("rolling", root, swap=DOWNLOAD)}


def numbers(response: dict) -> list:
    body = response.get("body", response)
    raw = body.get("engine_result", body)
    return [(r["horizon_days"], r["target_date"], r["direction"], r["relative_change_estimate"],
             r["price_estimate"]) for r in raw["results"]]


def test_rolling_app_wires_every_route(served):
    assert served["rolling"]["patched"] == ["v1_full_catalog", "v1_full_catalog", "rolling_runtime"]
    assert served["frozen"]["patched"][:2] == ["v1_full_catalog", "v1_full_catalog"]


def test_switch_waits_for_the_inference_lock(served):
    r = served["rolling"]
    assert r["before_swap"]["cutoff"] == "2026-10-20" and r["before_swap"]["source"] == "rolling"
    assert r["swap_publish"]["code"] == 0 and r["swap_publish"]["cutoff"] == "2026-10-29"
    assert r["while_busy"]["cutoff"] == "2026-10-20" and r["while_busy"]["pending_version"] == r["swap_publish"]["version"]
    assert r["after_idle"]["cutoff"] == "2026-10-29" and r["after_idle"]["pending_version"] is None
    assert r["after_idle"]["version"] == r["swap_publish"]["version"]


def test_health_reports_the_rolling_history(served):
    health = served["rolling"]["health"]
    assert health["status"] == 200 and health["body"]["status"] == "ready"
    assert health["body"]["public_data_cutoff"] == "2026-10-20"           # before the in-run switch
    assert health["body"]["public_history"]["frozen_training_cutoff"] == "2026-10-02"
    assert health["body"]["data_version"] == served["frozen"]["health"]["body"]["data_version"] == "172dffc76e82"
    assert served["frozen"]["health"]["body"]["public_data_cutoff"] == "2026-10-02"


@pytest.mark.parametrize("case", ["forecast_frozen", "forecast_catalog", "forecast_catalog_2",
                                  "web_frozen", "web_catalog"])
def test_answers_before_the_frozen_cutoff_are_unchanged(served, case):
    """Features only look back from t-1, so at t=2026-10-03 the rolling history changes nothing."""
    rolled = numbers(served["rolling"]["parity"][case])
    assert len(rolled) == 2 and rolled == numbers(served["frozen"]["parity"][case])


@pytest.mark.parametrize("case", ["forecast_frozen", "forecast_catalog"])
def test_fresh_days_change_the_model_inputs(served, case):
    """第三市場 moved after 10-02, so its answers must differ from the frozen ones.

    (第五市場 quoted the same price for months; its features differ only in the
    weekday and the models return the same numbers, so it is not used here.)
    """
    assert numbers(served["rolling"]["day"][case]) != numbers(served["frozen"]["day"][case])


@pytest.mark.parametrize("case", ["forecast_frozen", "forecast_catalog", "forecast_catalog_2"])
def test_today_uses_the_fresh_history_and_keeps_the_v1_contract(served, case):
    rolled, frozen_ = served["rolling"]["day"][case], served["frozen"]["day"][case]
    assert rolled["status"] == 200 == frozen_["status"], rolled
    raw = rolled["body"]["engine_result"]
    assert raw["public_data_cutoff"] == "2026-10-29"
    assert frozen_["body"]["engine_result"]["public_data_cutoff"] == "2026-10-02"
    assert raw["data_version"] == frozen_["body"]["engine_result"]["data_version"]
    assert raw["model_version"] == frozen_["body"]["engine_result"]["model_version"]
    assert rolled["body"]["price_age_days_at_query"] == (
        date.fromisoformat(rolled["body"]["query_date"]) - date(2026, 10, 29)).days
    if "public_last_visible_quote_date" in raw:
        assert raw["public_last_visible_quote_date"] > "2026-10-02"
    assert not any("相差" in w or "距今" in w for w in raw["warnings"])


@pytest.mark.parametrize("case", ["web_frozen", "web_catalog"])
def test_website_uses_the_fresh_history(served, case):
    assert served["rolling"]["day"][case]["error"] is None
    assert served["rolling"]["day"][case]["public_data_cutoff"] == "2026-10-29"
    assert served["frozen"]["day"][case]["public_data_cutoff"] == "2026-10-02"


def test_quotes_move_past_the_frozen_cutoff(served):
    for case in ("quote_frozen", "quote_catalog"):
        raw = served["rolling"]["day"][case]["body"]["engine_result"]
        assert raw["public_data_cutoff"] == "2026-10-29" and raw["observed_date"] > "2026-10-02"
        assert served["frozen"]["day"][case]["body"]["engine_result"]["observed_date"] <= "2026-10-02"


def test_rejected_download_keeps_serving_the_current_version(served, raw_rows):
    root = served["root"]
    before = (root / "CURRENT.json").read_bytes()
    truncated = root.parent / "download_truncated.json"
    truncated.write_bytes(encode(raw_rows[-50:]))
    code, result = run_updater(root, truncated)
    assert code == 2 and result["outcome"] == "rejected" and result["code"] == "download_shrank"
    assert (root / "CURRENT.json").read_bytes() == before
    status = json.loads((root / "status.json").read_text(encoding="utf-8"))
    assert status["outcome"] == "rejected"
    code, result = run_updater(root, DOWNLOAD)
    assert code == 0 and result["outcome"] == "unchanged"


def test_damaged_versions_fall_back_at_startup(served, tmp_path):
    root = tmp_path / "rolling"
    shutil.copytree(served["root"], root)
    pointer = store.read_pointer(root)
    newest, older = pointer["version"], pointer["fallbacks"][0]["version"]
    (root / "versions" / newest / "public_history.parquet").write_bytes(b"PAR1 damaged")
    probe = run_probe("rolling", root)
    assert probe["health"]["body"]["public_history"]["version"] == older
    assert probe["health"]["body"]["public_history"]["errors"][0].startswith("file_hash")
    assert probe["day"]["forecast_frozen"]["status"] == 200
    assert probe["day"]["forecast_frozen"]["body"]["engine_result"]["public_data_cutoff"] == "2026-10-20"
    (root / "versions" / older / "manifest.json").write_bytes(b"{}")
    probe = run_probe("rolling", root)
    assert probe["health"]["body"]["public_history"]["source"] == "frozen"
    for case in ("forecast_frozen", "forecast_catalog"):
        assert probe["day"][case]["status"] == 200
        assert probe["day"][case]["body"]["engine_result"]["public_data_cutoff"] == "2026-10-02"
    assert numbers(probe["day"]["forecast_catalog"]) == numbers(served["frozen"]["day"]["forecast_catalog"])
