"""Install immutable TW01 Docker Compose release on the EXISTING Oracle VM.

The production Nginx/site/systemd services are NOT touched by this script.
The EXISTING origin credential is copied from its root-only Oracle env into
the root-only Docker secret, without printing or transporting its value.
The new self-hosted MCP gets an independent random secret.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

BASE = Path("/opt/tw01-docker")
ORIGIN_ENV = Path("/etc/tw01-forecastengine/origin.env")
ZIP_SHA256 = "dcd0c7b0362bfe823a22efe42e3caf55cf3d2cd4ad7cf1cc231074e5ad3e2336"
IMAGE_SHA256 = "841dc2d12b7fb5e0dd3bd9275faaf1d033f958c947b18e3b240624d1401331a2"
RELEASE_NAME = "TW01_Docker_Portable_v1.0.0"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def origin_token() -> str:
    if not ORIGIN_ENV.is_file() or ORIGIN_ENV.is_symlink():
        raise RuntimeError("Oracle original protected env missing")
    if (ORIGIN_ENV.stat().st_mode & 0o077) != 0:
        raise RuntimeError("Oracle original secret file permissions are unsafe")
    text = ORIGIN_ENV.read_text(encoding="utf-8")
    candidates = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("TW01_ORIGIN_API_TOKEN="):
            token = stripped.split("=", 1)[1].strip()
            if token.startswith(("'", '"')) and token[-1:] == token[:1]:
                token = token[1:-1]
            candidates.append(token)
    if len(candidates) != 1 or not (32 <= len(candidates[0]) <= 220):
        raise RuntimeError("Expected exactly one safe origin secret in original env")
    if any(c.isspace() or ord(c) < 33 or ord(c) > 126 for c in candidates[0]):
        raise RuntimeError("Malformed origin secret; refusing migration")
    return candidates[0]


def write_root_only(path: Path, value: str):
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as file:
        file.write(value + "\n")
        file.flush()
        os.fsync(file.fileno())
    os.chmod(path, 0o600)
    os.chown(path, 0, 0)


def safe_extract(zipped: Path, destination_parent: Path):
    expected_root = destination_parent / RELEASE_NAME
    if expected_root.exists():
        raise RuntimeError("Zip extraction root already exists")
    with zipfile.ZipFile(zipped) as archive:
        total = 0
        for entry in archive.infolist():
            parts = PurePosixPath(entry.filename).parts
            if (not parts or parts[0] != RELEASE_NAME
                    or ".." in parts or any(p in ("", ".", "..") for p in parts)):
                raise RuntimeError("Unsafe path inside portable zip")
            unix_type = stat.S_IFMT(entry.external_attr >> 16)
            if unix_type not in (0, stat.S_IFDIR, stat.S_IFREG):
                raise RuntimeError("Nonregular/linked ZIP member not allowed")
            total += entry.file_size
            if entry.file_size > 10_000_000 or total > 24_000_000:
                raise RuntimeError("Unexpected ZIP member size")
            target = destination_parent.joinpath(*parts)
            if entry.is_dir():
                target.mkdir(mode=0o755, parents=True, exist_ok=True)
                continue
            target.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
            with archive.open(entry) as source, target.open("xb") as output:
                shutil.copyfileobj(source, output)
            target.chmod(0o644)
    manifest_file = expected_root / "RELEASE_MANIFEST.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    rows = manifest.get("files_sha256")
    if (
        not isinstance(rows, dict) or len(rows) != 53
        or manifest.get("includes_tokens_or_private_keys") is not False
        or manifest.get("includes_private_records") is not False
        or manifest.get("additional_supervised_trained_crops") != 57
        or manifest.get("original_frozen_crops") != 3
    ):
        raise RuntimeError("Portable source release integrity mismatch")
    for relative, expected in rows.items():
        path = expected_root / relative
        if path.is_symlink() or not path.is_file() or sha(path) != expected:
            raise RuntimeError("Portable file SHA256 failed: " + relative)
    return expected_root


def main():
    args = argparse.ArgumentParser()
    args.add_argument("--stage", type=Path, required=True)
    args.add_argument("--tag", required=True)
    a = args.parse_args()
    if os.geteuid() != 0:
        args.error("Run as root on the already authorized Oracle VPS")
    if not a.tag.replace("_", "").replace("-", "").isalnum():
        args.error("Invalid release tag")
    stage = a.stage.resolve(strict=True)
    if not str(stage).startswith("/home/ubuntu/tw01-oracle-docker-stage-"):
        args.error("Refusing nonstandard staging path")
    public_zip = stage / (RELEASE_NAME + ".zip")
    archived_images = stage / "tw01_verified_linux_amd64_images.tar.gz"
    if sha(public_zip) != ZIP_SHA256 or sha(archived_images) != IMAGE_SHA256:
        raise RuntimeError("Windows-verified portable release or images SHA256 mismatch")

    stacks = BASE / "stacks"
    stacks.mkdir(mode=0o755, parents=True, exist_ok=True)
    target = stacks / a.tag
    if target.exists() or target.is_symlink():
        raise FileExistsError("Oracle Docker release tag already installed")
    with tempfile.TemporaryDirectory(prefix="tw01-docker-staging-", dir=stacks) as temp:
        extracted = safe_extract(public_zip, Path(temp))
        local = extracted
        secret_dir = local / ".secrets"
        if secret_dir.exists():
            raise RuntimeError("Portable release unexpectedly contains private secret directory")
        secret_dir.mkdir(mode=0o700)
        secret_dir.chmod(0o700)
        existing = origin_token()
        client = secrets.token_urlsafe(48)
        if client == existing:
            raise RuntimeError("MCP and origin tokens must be distinct")
        write_root_only(secret_dir / "origin_api_token", existing)
        write_root_only(secret_dir / "mcp_client_token", client)
        # Avoid printing either secret or its digest; both stay root-only on VPS.
        env_path = local / ".env"
        if env_path.exists():
            raise RuntimeError("Portable release contained an unsafe .env file")
        env_path.write_text(
            "TW01_BIND_ADDRESS=127.0.0.1\n"
            "TW01_HTTP_PORT=8080\n"
            "TW01_PUBLIC_ORIGIN=https://161.33.19.220\n"
            "TW01_MCP_AUTH_MODE=bearer\n",
            encoding="utf-8",
        )
        env_path.chmod(0o644)
        override = local / "compose.oracle.yaml"
        override.write_text(
            "services:\n"
            "  forecast:\n"
            "    mem_limit: 650m\n"
            "  mcp:\n"
            "    mem_limit: 180m\n"
            "  web:\n"
            "    mem_limit: 80m\n",
            encoding="utf-8",
        )
        override.chmod(0o644)
        # Move only after all hashes and secrets have been validated.
        os.rename(local, target)
    print("STAGED_DOCKER_RELEASE=VERIFIED")
    print("RELEASE_DIR=" + str(target))
    print("ZIP_SHA256_VERIFIED=YES")
    print("IMAGES_SHA256_VERIFIED=YES")
    print("ORIGINAL_ORIGIN_SECRET_PRESERVED=YES")
    print("NEW_INDEPENDENT_MCP_CLIENT_SECRET_CREATED=YES")
    print("ANY_SECRET_VALUE_PRINTED=NO")
    print("PUBLIC_BIND=127.0.0.1:8080")
    print("CSRF_CANONICAL_ORIGIN=https://161.33.19.220")
    print("PRODUCTION_NGINX_AND_SYSTEMD_UNMODIFIED=YES")


if __name__ == "__main__":
    main()
