"""Atomically change ONLY the FMPA public website title/header/meta on Oracle.

Guarded by old/new SHA256, fixed deployed destination, unique rollback backup.
Does not touch the API, models, login, records, other Nginx settings or Git.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import tempfile
from pathlib import Path

DEST = Path("/var/www/fresh-market-price-agent-website/index.html")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--old-sha256", required=True)
    parser.add_argument("--new-sha256", required=True)
    parser.add_argument("--tag", required=True)
    args = parser.parse_args()

    if os.geteuid() != 0:
        parser.error("root required")
    if not args.tag.replace("_", "").replace("-", "").isalnum():
        parser.error("invalid backup tag")
    candidate = args.input.resolve(strict=True)
    if not str(candidate).startswith("/home/ubuntu/fresh-market-price-agent-web-title-stage-"):
        parser.error("candidate must be in the dedicated FMPA staging directory")
    if candidate.is_symlink() or not candidate.is_file():
        parser.error("candidate must be a regular file")
    if not DEST.is_file() or DEST.is_symlink():
        parser.error("deployed webpage missing or not a regular file")
    backup = DEST.with_name(DEST.name + ".pre-branding-" + args.tag)
    if backup.exists() or backup.is_symlink():
        parser.error("backup path already exists")

    old = DEST.read_bytes()
    new = candidate.read_bytes()
    if sha(old) != args.old_sha256.lower():
        parser.error("deployed webpage differs from approved baseline; no change")
    if sha(new) != args.new_sha256.lower():
        parser.error("candidate integrity mismatch; no change")
    if not 1024 < len(new) < 100_000:
        parser.error("unexpected candidate webpage size")
    page = new.decode("utf-8")
    if page.count("<title>菜市場現場價格預測</title>") != 1:
        parser.error("new browser title missing")
    if page.count("<h1>菜市場現場價格預測</h1>") != 1:
        parser.error("new visible page heading missing")
    for stable in ("predictForm", "hasLastWeek", "cropSearch",
                   "cropCategory", "recordsPanel", "marketPriceStatus"):
        if stable not in page:
            parser.error("expected existing website control absent: " + stable)

    shutil.copy2(DEST, backup)
    temp_path = None
    try:
        fd, name = tempfile.mkstemp(prefix=".fresh-market-price-agent-branding-", dir=DEST.parent)
        temp_path = Path(name)
        with os.fdopen(fd, "wb") as output:
            output.write(new)
        os.chmod(temp_path, 0o644)
        os.chown(temp_path, 0, 0)
        os.replace(temp_path, DEST)
        temp_path = None
        if sha(DEST.read_bytes()) != args.new_sha256.lower():
            raise RuntimeError("post-install content SHA256 failed")
    except Exception:
        shutil.copy2(backup, DEST)
        if temp_path and temp_path.exists():
            temp_path.unlink()
        raise

    print("FMPA_WEB_BRANDING_UPDATED=YES")
    print("VISIBLE_TITLE=菜市場現場價格預測")
    print("BROWSER_TITLE=菜市場現場價格預測")
    print("DEPLOYED_INDEX_SHA256=" + sha(DEST.read_bytes()))
    print("ROLLBACK_BACKUP=" + str(backup))
    print("API_AND_MODELS_UNCHANGED=YES")


if __name__ == "__main__":
    main()
