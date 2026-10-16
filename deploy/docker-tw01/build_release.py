"""Build a self-contained, shareable TW01 Compose folder and secret-free ZIP.

Copies ONLY audited code, public quotes, trained weights, static UI and the
two exact MCP contracts. It never copies private/, any .env, keys, database,
user records, original remote credentials, node_modules, or a live Oracle
systemd/nginx config. It does not commit/push/deploy any external service.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = Path(__file__).resolve().parent
NAME = "TW01_Docker_Portable_v1.0.0"
FROZEN_SHA256 = {
    "manifest.json": "6f82dac547a72a692f8352a14ece77d7b94a53b85f7844dba0aa2eb291e15f5d",
    "fixtures.json": "235a7e23d2fa31c23cab26e878dbd842ab81d923e775aa93f6d0503b94e284c6",
    "model_h7.joblib": "ea98f31d91d27e18644c61736534483b443429e940cf474ee8a1adb9f7c5b327",
    "model_h14.joblib": "d88fd53d25f62e3737444609c2769f1ab9d547783ee2b0ff6a1128aa24dae92a",
    "public_history.parquet": "e53e34c49098e309544b902dbff29708cde2f969035dd13995e64deed2ba2e3c",
}
PYTHON_SOURCE = {
    "src/aiot_price/__init__.py",
    "src/aiot_price/data/__init__.py",
    "src/aiot_price/data/schema.py",
    "src/aiot_price/data/labels.py",
    "src/aiot_price/data/load.py",
    "src/aiot_price/features/build.py",
    "src/aiot_price/models/predict.py",
    "src/aiot_price/models/baselines.py",
    "src/aiot_price/models/train.py",
    "src/aiot_price/models/store_adapter.py",
    "src/aiot_price/agent/tools.py",
    "src/aiot_price/integrations/__init__.py",
    "src/aiot_price/integrations/chatgpt_adapter.py",
    "src/aiot_price/integrations/chatgpt_contracts.py",
}
ORIGIN_SOURCE = (
    "forecastengine_api.py", "oracle_web_site.py", "oracle_web_site_ml.py",
    "full_catalog_runtime.py", "pooled_ml_features.py", "pooled_ml_runtime.py",
)
MCP_SOURCE = ("contracts.js", "strict-json.js")
FORBIDDEN_NAMES = frozenset({
    ".env", "web-login.txt", "origin.env", ".ssh", "id_rsa",
    "private", "records", "node_modules", ".secrets", "credentials.json",
})


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def install_file(source: Path, target: Path):
    if not source.is_file() or source.is_symlink():
        raise FileNotFoundError("Required artifact missing or linked: " + str(source))
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise FileExistsError("Refusing overwrite within release: " + str(target))
    shutil.copyfile(source, target)


def portable_site_api(text: str):
    # Runtime Portability: the original deployment is intentionally scoped to
    # https://161.33.19.220. Docker must instead trust the *configured*
    # canonical local HTTPS/HTTP origin; keep anti-CSRF policy intact.
    required = [
        ("import asyncio\n", "import asyncio\nimport os\n"),
        (
            'origin = request.headers.get("origin", "")',
            'origin = request.headers.get("origin", "")\n'
            '    public_origin = os.environ.get("TW01_PUBLIC_ORIGIN", "http://localhost:8080").rstrip("/")\n'
            '    if not public_origin.startswith(("http://localhost:", "http://127.0.0.1:", "https://")):\n'
            '        return _failure(503, "not_ready", "請設定可信任的網站來源位址。")',
        ),
        (
            'origin != "https://161.33.19.220"',
            "origin != public_origin",
        ),
        (
            'referrer.startswith("https://161.33.19.220/web/")',
            'referrer.startswith(public_origin + "/web/")',
        ),
    ]
    for old, new in required:
        if text.count(old) != 1:
            raise RuntimeError("Upstream website origin code changed; cannot package blindly: " + old)
        text = text.replace(old, new, 1)
    return text


def build(destination: Path):
    if destination.exists():
        raise FileExistsError("Release folder already exists; use a new destination")
    catalog_dir = ROOT / "outputs/quality_runs/oracle_full_catalog_20261015_003810_Windows5800X/catalog"
    ml_dir = ROOT / "outputs/quality_runs/tw01_pooled_ml_training_20261015_013634_Windows5800X/ml_release"
    web_dir = ROOT / "outputs/quality_runs/tw01_pooled_ml_training_20261015_013634_Windows5800X/ml_site"
    old_frozen = ROOT / "models/releases/0.1.0"
    old_worker = ROOT / "deploy/cloudflare-workers-mcp"
    for file, expected in FROZEN_SHA256.items():
        if sha(old_frozen / file) != expected:
            raise RuntimeError("Frozen RF/HGB artifact changed: " + file)
    public_manifest = json.loads((catalog_dir / "manifest.json").read_text(encoding="utf-8"))
    ml_manifest = json.loads((ml_dir / "manifest.json").read_text(encoding="utf-8"))
    if (
        ml_manifest["model_version"] != "multi-crop-ml/1.0.0"
        or ml_manifest["source_sha256"] != public_manifest["source_sha256"]
        or len(ml_manifest["trained_crop_ids"]) != 57
        or sorted(m["horizon_days"] for m in ml_manifest["models"]) != [7, 14]
        or sha(catalog_dir / "catalog.json") != public_manifest["catalog_sha256"]
        or sha(catalog_dir / "public_history.json.gz") != public_manifest["history_sha256"]
    ):
        raise RuntimeError("New 57-crop ML/public model bundle not authentic")
    for model in ml_manifest["models"]:
        if sha(ml_dir / model["file"]) != model["sha256"]:
            raise RuntimeError("Pooled ML artifact hash mismatch")
    if sha(ml_dir / ml_manifest["evaluation_file"]) != ml_manifest["evaluation_sha256"]:
        raise RuntimeError("Pooled model evaluation report SHA256 mismatch")
    ui = (web_dir / "index.html").read_text(encoding="utf-8")
    if (
        "<title>菜市場現場價格預測</title>" not in ui
        or "predictForm" not in ui or "hasLastWeek" not in ui
        or "61" not in ui
    ):
        raise RuntimeError("Expected current version of fully trained ML website")

    shutil.copytree(SCRIPT / "stack", destination)
    for relative in sorted(PYTHON_SOURCE):
        install_file(ROOT / relative, destination / relative)
    origin_source = ROOT / "deploy/oracle-forecastengine"
    for name in ORIGIN_SOURCE:
        output = destination / "deploy/oracle-forecastengine" / name
        if name == "oracle_web_site.py":
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(portable_site_api(
                (origin_source / name).read_text(encoding="utf-8")
            ), encoding="utf-8")
        else:
            install_file(origin_source / name, output)
    for name in FROZEN_SHA256:
        install_file(old_frozen / name, destination / "models/releases/0.1.0" / name)
    for name in ("manifest.json", "evaluation.json", "pooled_h7.joblib", "pooled_h14.joblib"):
        install_file(ml_dir / name, destination / "models/pooled" / name)
    for name in ("manifest.json", "catalog.json", "public_history.json.gz"):
        install_file(catalog_dir / name, destination / "catalog" / name)
    for name in ("index.html", "app.js", "style.css", "catalog.json"):
        install_file(web_dir / name, destination / "web" / name)
    for name in MCP_SOURCE:
        install_file(old_worker / "src" / name, destination / "mcp/src" / name)
    for name in ("package.json", "package-lock.json"):
        install_file(old_worker / name, destination / "mcp" / name)

    manifest_files = {}
    for path in sorted(destination.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(destination).as_posix()
        if any(part in FORBIDDEN_NAMES for part in path.relative_to(destination).parts):
            raise RuntimeError("Unsafe file in release: " + relative)
        if relative.endswith((".key", ".pem", ".sqlite", ".db", ".env")):
            raise RuntimeError("Forbidden credential/record extension in release: " + relative)
        manifest_files[relative] = sha(path)
    receipt = {
        "distribution": NAME,
        "contents": "public_site_origin_api_two_tool_mcp_trained_models",
        "source_dataset": "data.gov.tw/84539",
        "source_sha256": public_manifest["source_sha256"],
        "source_observed_through": public_manifest["source_cutoff"],
        "public_source_items": 61,
        "published_positive_price_items": 60,
        "original_frozen_crops": 3,
        "additional_supervised_trained_crops": 57,
        "original_frozen_release": "0.1.0",
        "pooled_supervised_release": "multi-crop-ml/1.0.0",
        "shop_price_validation": "not available",
        "ml_better_than_flat_on_holdout": False,
        "includes_private_records": False,
        "includes_tokens_or_private_keys": False,
        "contains_cloudflare_vpc_binding": False,
        "total_file_count": len(manifest_files),
        "files_sha256": manifest_files,
    }
    (destination / "RELEASE_MANIFEST.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    checksum = destination / "SHA256SUMS.txt"
    checksum.write_text("".join(
        f"{hash_}  {name}\n" for name, hash_ in sorted(manifest_files.items())
    ), encoding="utf-8")
    return receipt


def zip_distribution(folder: Path, archive: Path):
    if archive.exists():
        raise FileExistsError("Refuse to overwrite an earlier ZIP")
    all_files = sorted(p for p in folder.rglob("*") if p.is_file())
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=7, allowZip64=True) as zipfile_out:
        for file in all_files:
            rel = file.relative_to(folder)
            if any(piece in (".env", ".secrets", "private", "records")
                   for piece in rel.parts):
                raise RuntimeError("Private file inclusion is forbidden")
            zipfile_out.write(file, arcname=folder.name + "/" + rel.as_posix())
    return len(all_files)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-parent", required=True, type=Path)
    args = parser.parse_args()
    parent = args.out_parent.resolve()
    parent.mkdir(parents=True, exist_ok=True)
    dest = parent / NAME
    receipt = build(dest)
    archive = parent / (NAME + ".zip")
    n = zip_distribution(dest, archive)
    print(json.dumps({
        "status": "PACKAGED", "directory": str(dest), "zip": str(archive),
        "zip_sha256": sha(archive), "zip_size": archive.stat().st_size,
        "files": n, "models": 4, "secrets_included": False,
    }, ensure_ascii=False, indent=2))
