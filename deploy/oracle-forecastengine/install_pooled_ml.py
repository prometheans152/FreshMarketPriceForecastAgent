"""Safely activate new supervised ML for TW01's public 57-crop browser site.

No changes to the frozen RF/HGB 0.1.0 release, /v1 MCP Bearer API,
Nginx TLS/auth/rate limits, Windows original web, or private records.
Keep a scoped prior-site backup and automatically restore on failure.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path("/opt/tw01-forecastengine-web")
WEBSITE = Path("/var/www/tw01-website")
OVERRIDE = Path("/etc/systemd/system/tw01-forecastengine.service.d/20-web-frontend.conf")
FROZEN = Path("/opt/tw01-forecastengine/current/models/releases/0.1.0")
OLD_COMPONENTS = {
    "cabbage", "bok_choy", "sponge_gourd",
}
STATIC = ("index.html", "app.js", "style.css", "catalog.json")
OVERLAY = (
    "oracle_web_site.py", "oracle_web_site_ml.py",
    "full_catalog_runtime.py", "pooled_ml_features.py", "pooled_ml_runtime.py",
)
ML = ("manifest.json", "evaluation.json", "pooled_h7.joblib", "pooled_h14.joblib")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(*args):
    command = subprocess.run(args, capture_output=True, text=True)
    if command.returncode != 0:
        raise RuntimeError("Operation failed: " + args[0] + " exit=" + str(command.returncode))


def wait_until_ready():
    for _ in range(30):
        response = subprocess.run(
            ["curl", "--fail", "--silent", "--show-error",
             "--connect-timeout", "2", "--max-time", "8",
             "http://127.0.0.1:8767/healthz"],
            capture_output=True,
        )
        if response.returncode == 0:
            return
        time.sleep(1)
    raise RuntimeError("Model/web service did not become ready; rollback")


def http_smoke():
    import ssl
    import urllib.error
    import urllib.request

    base = "https://161.33.19.220"
    data = {
        "crop_id": "taichung_04", "market_id": "中義市場",
        "current_price": 32, "price_unit": "NTD_per_taiwan_jin",
        "observed_at": "2026-10-14T12:00:00+08:00",
        "mode": "without_last_week",
    }
    headers = {
        "Content-Type": "application/json",
        "Origin": base,
        "Referer": base + "/web/",
        "Sec-Fetch-Site": "same-origin",
    }
    req = urllib.request.Request(
        base + "/web/forecast", method="POST", headers=headers,
        data=json.dumps(data, ensure_ascii=False).encode("utf-8"),
    )
    with urllib.request.urlopen(
        req, timeout=28, context=ssl.create_default_context()
    ) as resp:
        result = json.loads(resp.read())
        if not (
            resp.status == 200
            and result.get("model_version") == "multi-crop-ml/1.0.0"
            and result.get("forecast_method") == "supervised_hgb_pooled"
            and [e["horizon_days"] for e in result["results"]] == [7, 14]
            and result.get("store_id") is None
        ):
            raise RuntimeError("Deployed ML model failed real HTTPS prediction")

    # Access to original MCP /v1/* still requires its dedicated Bearer token.
    unauthorized = urllib.request.Request(
        base + "/v1/forecast", method="POST",
        headers={"Content-Type": "application/json"},
        data=json.dumps({
            "crop_id": "cabbage", "market_id": "中義市場",
            "current_price": 32, "price_unit": "NTD_per_taiwan_jin",
            "observed_on": "2026-10-14",
        }, ensure_ascii=False).encode("utf-8"),
    )
    try:
        urllib.request.urlopen(
            unauthorized, timeout=18, context=ssl.create_default_context()
        )
        raise RuntimeError("Origin API unauthorized access unexpectedly permitted")
    except urllib.error.HTTPError as exc:
        if exc.code != 401:
            raise RuntimeError("Original MCP API auth semantics changed")


def install(stage: Path, tag: str):
    if os.geteuid() != 0:
        raise ValueError("Must be root on existing approved Oracle VPS")
    stage = stage.resolve(strict=True)
    if not str(stage).startswith("/home/ubuntu/tw01-pooled-ml-stage-"):
        raise ValueError("Unexpected staging location")
    if not tag.replace("_", "").replace("-", "").isalnum():
        raise ValueError("Invalid new immutable ML release tag")
    manifest_path = stage / "transfer_sha256.json"
    checksums = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    expected = (
        ["install_pooled_ml.py"]
        + ["overlay/" + n for n in OVERLAY]
        + ["ml_release/" + n for n in ML]
        + ["site/" + n for n in STATIC]
    )
    if sorted(checksums) != sorted(expected):
        raise RuntimeError("Transfer manifest is incomplete")
    for name in expected:
        file = stage / name
        if (not file.is_file() or file.is_symlink() or
                file.stat().st_size > 5_000_000 or
                sha(file) != checksums[name]):
            raise RuntimeError("Staging SHA256 check failed: " + name)

    ml_manifest = json.loads((stage / "ml_release/manifest.json").read_text(encoding="utf-8"))
    source_manifest = json.loads((FROZEN / "manifest.json").read_text(encoding="utf-8"))
    old_catalog_manifest = json.loads(
        (ROOT / "full_catalog-20261015_003810_r2/manifest.json").read_text(encoding="utf-8")
    )
    if not (
        ml_manifest["model_version"] == "multi-crop-ml/1.0.0"
        and ml_manifest["source_sha256"] == source_manifest["source"]["json_sha256"]
        and ml_manifest["source_sha256"] == old_catalog_manifest["source_sha256"]
        and len(ml_manifest["trained_crop_ids"]) == 57
        and set(ml_manifest["trained_crop_ids"]).isdisjoint(OLD_COMPONENTS)
        and [e["horizon_days"] for e in ml_manifest["models"]] == [7, 14]
        and all(sha(stage / "ml_release" / e["file"]) == e["sha256"]
                for e in ml_manifest["models"])
        and sha(stage / "ml_release/evaluation.json") == ml_manifest["evaluation_sha256"]
    ):
        raise RuntimeError("New release not compatible with original frozen source")
    public_catalog = json.loads((stage / "site/catalog.json").read_text(encoding="utf-8"))
    if not (
        len(public_catalog["items"]) == 61
        and public_catalog["source_sha256"] == ml_manifest["source_sha256"]
        and sum(e["method"] == "trained_pooled_hgb_ml_1.0.0"
                for e in public_catalog["items"]) == 57
        and sum(e["method"] == "frozen_rf_hgb_v0.1.0"
                for e in public_catalog["items"]) == 3
    ):
        raise RuntimeError("Public UI methods inconsistent with ML release")

    target_ml = ROOT / "ml_releases" / ("pooled-" + tag)
    target_overlay = ROOT / "site_overlays" / ("pooled-" + tag)
    saved = {path: path.with_name(path.name + ".pre-pooled-ml-" + tag)
             for path in [OVERRIDE, *(WEBSITE / n for n in STATIC)]}
    for p in [target_ml, target_overlay, *saved.values()]:
        if p.exists() or p.is_symlink():
            raise FileExistsError("Refusing overwrite of a previous live site or backup")
    previous = OVERRIDE.read_text(encoding="utf-8")
    old_application = (
        "uvicorn oracle_web_site:app --app-dir "
        "/opt/tw01-forecastengine-web/site_overlays/catalog-20261015_003810_r2"
    )
    if previous.count(old_application) != 1 or "TW01_POOLED_ML_DIR=" in previous:
        raise RuntimeError("Existing website systemd command differs from verified base")
    new = previous.replace(
        old_application,
        "uvicorn oracle_web_site_ml:app --app-dir " + str(target_overlay),
    )
    new += "\nEnvironment=TW01_POOLED_ML_DIR=" + str(target_ml) + "\n"
    run("systemctl", "is-active", "--quiet", "nginx.service")
    run("systemctl", "is-active", "--quiet", "tw01-forecastengine.service")
    for previous_file, backup_file in saved.items():
        shutil.copy2(previous_file, backup_file)

    service_changed = False
    try:
        target_ml.mkdir(parents=True)
        target_overlay.mkdir(parents=True)
        (ROOT / "ml_releases").chmod(0o755)
        (ROOT / "site_overlays").chmod(0o755)
        target_ml.chmod(0o755)
        target_overlay.chmod(0o755)
        for item in ML:
            destination = target_ml / item
            shutil.copy2(stage / "ml_release" / item, destination)
            destination.chmod(0o644)
        for item in OVERLAY:
            destination = target_overlay / item
            shutil.copy2(stage / "overlay" / item, destination)
            destination.chmod(0o644)
        for item in STATIC:
            destination = WEBSITE / item
            shutil.copy2(stage / "site" / item, destination)
            destination.chmod(0o644)
        OVERRIDE.write_text(new, encoding="utf-8")
        OVERRIDE.chmod(0o644)
        service_changed = True
        run("systemctl", "daemon-reload")
        run("systemctl", "restart", "tw01-forecastengine.service")
        wait_until_ready()
        http_smoke()
    except Exception:
        for live_file, backup in saved.items():
            shutil.copy2(backup, live_file)
        if service_changed:
            run("systemctl", "daemon-reload")
            run("systemctl", "restart", "tw01-forecastengine.service")
            wait_until_ready()
        raise
    print("NEW_TRAINED_POOLED_ML_DEPLOYED=TRUE")
    print("57_ADDITIONAL_CROPS_TRAINED_HGB_7_AND_14=TRUE")
    print("FROZEN_3_CROP_RF_HGB_0_1_0_PRESERVED=TRUE")
    print("PUBLIC_61_ITEM_CATALOG_PRESERVED=TRUE")
    print("ORIGINAL_BEARER_API_UNCHANGED=TRUE")
    print("LATEST_SOURCE_CUTOFF=2026-10-02")
    print("NEW_ML_RELEASE_PATH=" + str(target_ml))
    print("NEW_WEB_OVERLAY_PATH=" + str(target_overlay))
    print("SCOPED_ROLLBACK_SERVICE_FILE=" + str(saved[OVERRIDE]))
    print("HTTP_PUBLIC_POOLED_ML_A=PASS")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--tag", required=True)
    args = parser.parse_args()
    install(args.stage, args.tag)
