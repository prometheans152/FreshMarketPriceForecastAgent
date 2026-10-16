"""Whitelisted, verifiable release packaging. Never copy private/, records, or web/."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from shutil import copyfile

from aiot_price.integrations.chatgpt_adapter import FROZEN_SHA256

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RAW_REL = "data/raw/taichung/retail_prices_20261003.json"
RAW_SHA256 = "172dffc76e8249026ac2ad89cc1a9f68bcfb686fd64a2820b38e949fe7e2e259"
CODE = [
    "src/aiot_price/__init__.py",
    "src/aiot_price/data/__init__.py",
    "src/aiot_price/data/schema.py",
    "src/aiot_price/data/labels.py",
    "src/aiot_price/features/build.py",
    "src/aiot_price/models/baselines.py",
    "src/aiot_price/models/train.py",
    "src/aiot_price/models/store_adapter.py",
    "src/aiot_price/models/predict.py",
    "src/aiot_price/agent/tools.py",
    "src/aiot_price/integrations/__init__.py",
    "src/aiot_price/integrations/chatgpt_contracts.py",
    "src/aiot_price/integrations/chatgpt_adapter.py",
]
SERVICE = [
    "deploy/oracle-forecastengine/forecastengine_api.py",
    "deploy/oracle-forecastengine/requirements-oracle.txt",
    "docs/deployment/FORECASTENGINE_API_V1.md",
]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build(dest: Path):
    dest = dest.resolve()
    if dest.exists():
        raise ValueError("輸出路徑已存在，禁止覆寫舊證據。")
    if dest.is_relative_to(ROOT) and not dest.is_relative_to(ROOT / "outputs" / "quality_runs"):
        raise ValueError("bundles 只能放入新的 quality_runs 目錄或獨立暫存位置。")
    rels = CODE + SERVICE + [RAW_REL]
    rels.extend(f"models/releases/0.1.0/{filename}" for filename in FROZEN_SHA256)
    checks = {f"models/releases/0.1.0/{name}": h for name, h in FROZEN_SHA256.items()}
    checks[RAW_REL] = RAW_SHA256
    # Complete source preflight before writing anything.
    for rel in rels:
        src = ROOT / rel
        if not src.is_file() or src.is_symlink():
            raise ValueError(f"缺失或非法的原始檔：{rel}")
        if rel in checks and digest(src) != checks[rel]:
            raise ValueError(f"凍結檔 hash 不符：{rel}")
    dest.mkdir(parents=True)
    files = []
    for rel in sorted(rels):
        original = ROOT / rel
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        copyfile(original, target)
        before = digest(original)
        after = digest(target)
        if before != after:
            raise RuntimeError(f"複製後 hash 不同：{rel}")
        files.append({"path": rel, "sha256": after, "bytes": target.stat().st_size})
    # No `private/`, untracked user files, saved records or other deployments.
    manifest = {"bundle_type": "TW01_FROZEN_ORACLE_A_ONLY", "files": files}
    (dest / "TRANSFER_SHA256.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = build(args.output)
    print(f"bundle validated: {len(result['files'])} whitelisted files")
    print(f"destination: {args.output.resolve()}")
