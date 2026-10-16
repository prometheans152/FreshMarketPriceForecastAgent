"""Rollback ONLY the FMPA Oracle Docker cutover to the preserved systemd app.

This only operates on the exact scoped Nginx backup and FMPA systemd service.
It does not touch SSL/TLS certificates, Cloudflare Tunnel, source/model
releases, private records, or unrelated Docker containers.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

LIVE = Path("/etc/nginx/sites-available/fresh-market-price-agent-tls.conf")
UNIT = "fresh-market-price-agent-forecastengine.service"


def run(*args):
    subprocess.run(args, check=True, capture_output=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", required=True)
    parser.add_argument("--check-only", action="store_true",
                        help="Verify rollback files and current routes without modifying services")
    args = parser.parse_args()
    if os.geteuid() != 0 or not args.tag.replace("_", "").replace("-", "").isalnum():
        parser.error("root and a known version tag required")
    backup = LIVE.with_name(LIVE.name + ".pre-docker-" + args.tag)
    if not backup.is_file() or backup.is_symlink():
        raise RuntimeError("Approved original Nginx backup absent")
    old = backup.read_text(encoding="utf-8")
    deployed = LIVE.read_text(encoding="utf-8")
    if (
        old.count("proxy_pass http://127.0.0.1:8767;") != 3
        or old.count("proxy_pass http://127.0.0.1:8767/site/forecast;") != 1
        or "proxy_pass http://127.0.0.1:8080" not in deployed
    ):
        raise RuntimeError("Unexpected live vs backed-up config; refuse blind replacement")
    if args.check_only:
        print("ORIGINAL_NGINX_BACKUP_MATCHED=YES")
        print("CURRENT_FMPA_DOCKER_ROUTES_MATCHED=YES")
        print("SCOPED_ROLLBACK_READY=YES")
        print("MUTATIONS=NONE")
        return
    # Start original first, THEN return Nginx routing to it; no 502 gap.
    run("systemctl", "enable", "--now", UNIT)
    if subprocess.run(["systemctl", "is-active", "--quiet", UNIT]).returncode:
        raise RuntimeError("Original ForecastEngine cannot be restarted")
    shutil.copy2(backup, LIVE)
    run("nginx", "-t")
    run("systemctl", "reload", "nginx.service")
    print("SCOPED_NGINX_RESTORED_TO_ORIGINAL=YES")
    print("ORIGINAL_FORECAST_SYSTEMD_REENABLED=YES")
    print("HTTPS_CERTIFICATE_AND_CLOUDFLARE_UNTOUCHED=YES")
    print("DOCKER_STACK_LEFT_RUNNING_FOR_DIAGNOSIS=YES")


if __name__ == "__main__":
    main()
