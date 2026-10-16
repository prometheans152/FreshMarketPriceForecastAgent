"""Install SHA-verified 61-column public-market website on the existing VPS.

Only the WEB overlay and /web/* Nginx locations change. The frozen
ForecastEngine release, its /v1/* Bearer API, Oracle secret files, old Windows
Web A/B/records, Cloudflare MCP files and instance settings remain unchanged.
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

NGINX = Path("/etc/nginx/sites-available/fresh-market-price-agent-tls.conf")
OVERRIDE = Path("/etc/systemd/system/fresh-market-price-agent-forecastengine.service.d/20-web-frontend.conf")
WEBSITE = Path("/var/www/fresh-market-price-agent-website")
BASE = Path("/opt/fresh-market-price-agent-forecastengine-web")
RELEASE = Path("/opt/fresh-market-price-agent-forecastengine/current/models/releases/0.1.0")
PUBLIC_CATALOG_ROUTE = b'''location = /web/catalog.json {
    alias /var/www/fresh-market-price-agent-website/catalog.json;
    default_type application/json;
    add_header Cache-Control "no-store" always;
    add_header X-Content-Type-Options nosniff always;
}
'''


def execute(*args):
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(
            f"{args[0]} action failed (exit {result.returncode})"
        )


def wait_http_ready(url: str, *, attempts: int = 20):
    # systemctl restart returns once the Python process is launched, BEFORE
    # uvicorn has finished imports, cgroup setup and the first model check.
    for _ in range(attempts):
        result = subprocess.run(
            ["curl", "--fail", "--silent", "--show-error",
             "--connect-timeout", "2", "--max-time", "7", url],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            return
        time.sleep(1)
    raise RuntimeError("New service did not become HTTP ready within bounded checks")


def sha(file: Path) -> str:
    return hashlib.sha256(file.read_bytes()).hexdigest()


def verify_readable(file: Path):
    if not file.is_file() or file.is_symlink():
        raise RuntimeError("Missing or unsafe staged file: " + file.name)
    if file.stat().st_size > 4_000_000:
        raise RuntimeError("Excessively large staged file: " + file.name)


def install(stage: Path, tag: str):
    stage = stage.resolve(strict=True)
    if not str(stage).startswith("/home/ubuntu/fresh-market-price-agent-full-catalog-stage-"):
        raise ValueError("Stage is not a dedicated approved FMPA upload location")
    if not tag.replace("_", "").replace("-", "").isalnum():
        raise ValueError("Invalid version ID")
    files = [
        "install_full_catalog.py",
        "oracle_web_site.py", "full_catalog_runtime.py",
        "nginx-web-public-snippet.conf",
        "catalog/manifest.json", "catalog/catalog.json",
        "catalog/public_history.json.gz",
        "site/index.html", "site/app.js", "site/style.css",
        "site/catalog.json",
    ]
    for file in files:
        verify_readable(stage / file)
    # Windows PowerShell 5.1 emits UTF-8 with BOM by default.
    checksums = json.loads((stage / "transfer_sha256.json").read_text(encoding="utf-8-sig"))
    if sorted(checksums) != sorted(files):
        raise ValueError("Staged file manifest does not cover every exact file")
    for file in files:
        if sha(stage / file) != checksums[file]:
            raise RuntimeError("Transfer file SHA256 mismatch: " + file)
    manifest = json.loads((stage / "catalog/manifest.json").read_text(encoding="utf-8"))
    expected = json.loads((RELEASE / "manifest.json").read_text(encoding="utf-8"))
    if (
        manifest["source_sha256"] != expected["source"]["json_sha256"]
        or manifest["item_count"] != 61
        or manifest["with_data"] != 60
        or manifest["catalog_sha256"] != sha(stage / "catalog/catalog.json")
        or manifest["history_sha256"] != sha(stage / "catalog/public_history.json.gz")
    ):
        raise RuntimeError("Catalog disagrees with frozen source manifest")

    deployed_catalog = BASE / ("full_catalog-" + tag)
    deployed_overlay = BASE / "site_overlays" / ("catalog-" + tag)
    destinations = {
        "index.html": WEBSITE / "index.html",
        "app.js": WEBSITE / "app.js",
        "style.css": WEBSITE / "style.css",
    }
    current_nginx = NGINX.read_bytes()
    old_snippet = (stage / "nginx-web-public-snippet.conf").read_bytes()
    if current_nginx.count(old_snippet) != 1:
        raise RuntimeError("Public website Nginx snippet does not match deployed version")
    if current_nginx.count(b"location = /v1/forecast {") != 1:
        raise RuntimeError("Origin API boundary absent")
    if current_nginx.count(b"location = /v1/market-quote {") != 1:
        raise RuntimeError("Origin quote API boundary absent")
    new_snippet = old_snippet.replace(
        b"location @fmpa_web_rate_limit_error {",
        PUBLIC_CATALOG_ROUTE + b"\nlocation @fmpa_web_rate_limit_error {",
        1,
    )
    if new_snippet.count(PUBLIC_CATALOG_ROUTE) != 1:
        raise RuntimeError("Public catalog endpoint insertion failed")
    original_service = OVERRIDE.read_text(encoding="utf-8")
    old_dir = "--app-dir /opt/fresh-market-price-agent-forecastengine-web/site_overlay"
    if original_service.count(old_dir) != 1 or any(
            p + "EXTENDED_CATALOG_DIR" in original_service for p in ("FMPA_", "TW01_")):
        raise RuntimeError("Systemd original Web overlay version mismatch")
    new_service = original_service.replace(old_dir, "--app-dir " + str(deployed_overlay))
    new_service += f"\nEnvironment=FMPA_EXTENDED_CATALOG_DIR={deployed_catalog}\n"
    saved = {
        NGINX: NGINX.with_name(NGINX.name + ".pre-catalog-" + tag),
        OVERRIDE: OVERRIDE.with_name(OVERRIDE.name + ".pre-catalog-" + tag),
        **{dest: dest.with_name(dest.name + ".pre-catalog-" + tag)
           for dest in destinations.values()},
    }
    new_public_catalog = WEBSITE / "catalog.json"
    if any(item.exists() or item.is_symlink() for item in (
        *saved.values(), deployed_catalog, deployed_overlay, new_public_catalog
    )):
        raise FileExistsError("Refuse overwrite of existing catalog release/backup")
    execute("systemctl", "is-active", "--quiet", "fresh-market-price-agent-forecastengine.service")
    execute("systemctl", "is-active", "--quiet", "nginx.service")
    # Scope is fixed; leave original frozen releases completely untouched.
    for source, backup in saved.items():
        shutil.copy2(source, backup)
    service_touched = False
    try:
        deployed_catalog.mkdir(parents=True, mode=0o755)
        deployed_overlay.mkdir(parents=True, mode=0o755)
        for name in ("manifest.json", "catalog.json", "public_history.json.gz"):
            shutil.copy2(stage / "catalog" / name, deployed_catalog / name)
            (deployed_catalog / name).chmod(0o644)
        for name in ("oracle_web_site.py", "full_catalog_runtime.py"):
            shutil.copy2(stage / name, deployed_overlay / name)
            (deployed_overlay / name).chmod(0o644)
        for name, target in destinations.items():
            shutil.copy2(stage / "site" / name, target)
            target.chmod(0o644)
        shutil.copy2(stage / "site/catalog.json", new_public_catalog)
        new_public_catalog.chmod(0o644)
        NGINX.write_bytes(current_nginx.replace(old_snippet, new_snippet, 1))
        NGINX.chmod(0o644)
        OVERRIDE.write_text(new_service, encoding="utf-8")
        OVERRIDE.chmod(0o644)
        service_touched = True
        execute("nginx", "-t")
        execute("systemctl", "daemon-reload")
        execute("systemctl", "restart", "fresh-market-price-agent-forecastengine.service")
        execute("systemctl", "is-active", "--quiet", "fresh-market-price-agent-forecastengine.service")
        # Check original origin live before touching public Nginx worker routes.
        wait_http_ready("http://127.0.0.1:8767/healthz")
        execute("systemctl", "reload", "nginx.service")
        wait_http_ready("https://161.33.19.220/web/catalog.json")
    except Exception:
        # Restore only this site's known original files. Keep the newly created
        # catalog dir in place for forensics, but make it INACTIVE.
        for destination, backup in saved.items():
            shutil.copy2(backup, destination)
        if new_public_catalog.is_file():
            new_public_catalog.unlink()
        if service_touched:
            execute("systemctl", "daemon-reload")
            execute("systemctl", "restart", "fresh-market-price-agent-forecastengine.service")
        execute("nginx", "-t")
        execute("systemctl", "reload", "nginx.service")
        raise
    print("EXPANDED_PUBLIC_WEB_INSTALLED=YES")
    print("PUBLIC_SOURCE_FIELDS=61")
    print("PUBLIC_FIELDS_WITH_PRICE=60")
    print("ORIGINAL_FROZEN_RF_HGB=3_UNCHANGED")
    print("NONTRAINED_HISTORY_BASELINE=57_WITH_PRICE")
    print("ORIGIN_BEARER_ROUTES_UNCHANGED=YES")
    print("NO_PRIVATE_RECORDS_COPIED=YES")
    print("WEB_NGINX_BACKUP=" + str(saved[NGINX]))
    print("WEB_SYSTEMD_BACKUP=" + str(saved[OVERRIDE]))
    print("PUBLIC_CATALOG_DIR=" + str(deployed_catalog))
    print("WEB_OVERLAY_DIR=" + str(deployed_overlay))


if __name__ == "__main__":
    args = argparse.ArgumentParser()
    args.add_argument("--stage", type=Path, required=True)
    args.add_argument("--tag", type=str, required=True)
    values = args.parse_args()
    if os.geteuid() != 0:
        raise SystemExit("Root required for scoped deployment")
    install(values.stage, values.tag)
