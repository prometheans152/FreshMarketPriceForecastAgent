"""Enable an intentionally public, no-password web form with scoped rollback.

Run only on the verified Oracle host. Operates on FMPA's existing Nginx config,
not on the frozen model, origin Bearer token or Windows web/records. Fails
closed and restores the verified prechange Nginx config on any error.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
from pathlib import Path


SITE = Path("/etc/nginx/sites-available/fresh-market-price-agent-tls.conf")
RATE_LIMIT = Path("/etc/nginx/conf.d/fresh-market-price-agent-public-web-rate-limit.conf")
INDEX = Path("/var/www/fresh-market-price-agent-website/index.html")


def digest(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def cmd(*args: str):
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError("Command failed: " + " ".join(args) + " (exit=" + str(result.returncode) + ")")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--backup-tag", required=True)
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error("Must run as root on Oracle")
    if not args.backup_tag.replace("-", "").replace("_", "").isalnum():
        parser.error("Invalid backup tag")
    stage = args.stage.resolve(strict=True)
    if not str(stage).startswith("/home/ubuntu/fresh-market-price-agent-public-web-stage-"):
        parser.error("Not a verified FMPA staging directory")
    old = (stage / "nginx-web-snippet.conf").read_bytes()
    new = (stage / "nginx-web-public-snippet.conf").read_bytes()
    limiter = (stage / "fresh-market-price-agent-public-web-rate-limit.conf").read_bytes()
    page = (stage / "index-public.html").read_bytes()
    before = SITE.read_bytes()
    original_index = INDEX.read_bytes()
    if before.count(old) != 1:
        parser.error("Expected exact protected web configuration once; refuse ambiguous mutation")
    if before.count(b"location = /v1/forecast {") != 1:
        parser.error("Existing Bearer-origin route not found")
    if before.count(b"location = /v1/market-quote {") != 1:
        parser.error("Existing Bearer quote route not found")
    if not new.count(b"limit_req zone=fmpa_public_web_per_ip"):
        parser.error("Public web missing IP limit")
    if b"auth_basic" in new or b"fresh-market-price-agent-web-auth.conf" in new:
        parser.error("Web is not actually password-free")
    if b"web/forecast" not in new or b"/v1/forecast" not in before:
        parser.error("Missing expected service routes")
    if b"no-store" not in new:
        parser.error("Web privacy cache control missing")
    backup_site = SITE.with_name(SITE.name + ".pre-public-" + args.backup_tag)
    backup_page = INDEX.with_name(INDEX.name + ".pre-public-" + args.backup_tag)
    for item in (backup_site, backup_page, RATE_LIMIT):
        if item.exists() or item.is_symlink():
            parser.error("Existing backup or rate-limit config would be overwritten: " + str(item))
    # Verify only frontend wording changes; same 3 forms remain usable.
    if not all(token in page for token in (
        "predictForm".encode(), "hasLastWeek".encode(), "recordsPanel".encode()
    )):
        parser.error("Frontend lost important A/B UI controls")
    if not all(token in original_index for token in (
        "predictForm".encode(), "hasLastWeek".encode(), "recordsPanel".encode()
    )):
        parser.error("Existing frontend controls missing")
    # Existing long-lived Nginx Basic hash + password are deliberately untouched
    # for rollback, but not included by any active website routes.
    for svc in ("nginx.service", "fresh-market-price-agent-forecastengine.service"):
        cmd("systemctl", "is-active", "--quiet", svc)
    shutil.copy2(SITE, backup_site)
    shutil.copy2(INDEX, backup_page)
    try:
        RATE_LIMIT.write_bytes(limiter)
        os.chmod(RATE_LIMIT, 0o644)
        SITE.write_bytes(before.replace(old, new, 1))
        INDEX.write_bytes(page)
        os.chmod(INDEX, 0o644)
        cmd("nginx", "-t")
        cmd("systemctl", "reload", "nginx.service")
    except Exception:
        shutil.copy2(backup_site, SITE)
        shutil.copy2(backup_page, INDEX)
        RATE_LIMIT.unlink(missing_ok=True)
        cmd("nginx", "-t")
        cmd("systemctl", "reload", "nginx.service")
        raise
    print("PUBLIC_WEB_NO_PASSWORD=ENABLED")
    print("ORIGIN_BEARER_CONFIG_PRESERVED=YES")
    print("NGINX_PER_IP_LIMIT=12r/m;burst=6")
    print("SITE_BACKUP=" + str(backup_site))
    print("INDEX_BACKUP=" + str(backup_page))
    print("HTTPS_CONFIG_SHA256=" + digest(SITE.read_bytes()))
    print("PUBLIC_INDEX_SHA256=" + digest(INDEX.read_bytes()))


if __name__ == "__main__":
    main()
