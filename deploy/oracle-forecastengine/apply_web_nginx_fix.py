"""Scoped Nginx website route fix; preserve original Oracle origin routes."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

NGINX_TLS = Path("/etc/nginx/sites-available/fresh-market-price-agent-tls.conf")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--old-snippet", type=Path, required=True)
    p.add_argument("--new-snippet", type=Path, required=True)
    p.add_argument("--backup", type=Path, required=True)
    args = p.parse_args()
    if os.geteuid() != 0:
        p.error("Must be root")
    if args.backup.exists():
        p.error("Refuse existing backup overwrite")
    old = args.old_snippet.read_text(encoding="utf-8")
    new = args.new_snippet.read_text(encoding="utf-8")
    source = NGINX_TLS.read_text(encoding="utf-8")
    if source.count(old) != 1:
        raise RuntimeError("Original website snippet not found exactly once; no changes")
    assert source.count("location = /v1/forecast {") == 1
    assert source.count("location = /v1/market-quote {") == 1
    shutil.copy2(NGINX_TLS, args.backup)
    try:
        NGINX_TLS.write_text(source.replace(old, new, 1), encoding="utf-8")
        validation = subprocess.run(["nginx", "-t"], capture_output=True, text=True)
        if validation.returncode != 0:
            raise RuntimeError("nginx -t failed; restoring verified pre-fix site config")
        subprocess.run(["systemctl", "reload", "nginx.service"], check=True)
    except Exception:
        shutil.copy2(args.backup, NGINX_TLS)
        subprocess.run(["nginx", "-t"], check=True, capture_output=True)
        subprocess.run(["systemctl", "reload", "nginx.service"], check=True)
        raise
    print("NGINX_WEB_HTML_ALIAS_FIX_APPLIED=YES")
    print("NGINX_CONFIG_BACKUP=" + str(args.backup))


if __name__ == "__main__":
    main()
