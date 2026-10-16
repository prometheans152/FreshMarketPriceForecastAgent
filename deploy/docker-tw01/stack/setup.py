"""Portable first-run bootstrap. Secret values are NEVER printed or bundled."""
from __future__ import annotations

import argparse
import os
import secrets
import shutil
from pathlib import Path


def create_secret(path: Path):
    if path.exists():
        print("EXISTS:", path.name, "(unchanged)")
        return
    value = secrets.token_urlsafe(48).encode("ascii") + b"\n"
    handle = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(handle, "wb") as stream:
        stream.write(value)
    if os.name != "nt":
        path.chmod(0o600)
    print("CREATED:", path.name, "(value hidden)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force-rotate", action="store_true",
                        help="Reserved: use the explicit documented rotation procedure, not this flag")
    args = parser.parse_args()
    if args.force_rotate:
        parser.error("Refuse automatic credential rotation; coordinate MCP clients and restart")
    base = Path(__file__).resolve().parent
    os.chdir(base)
    secrets_dir = base / ".secrets"
    secrets_dir.mkdir(mode=0o700, exist_ok=True)
    if os.name != "nt":
        secrets_dir.chmod(0o700)
    create_secret(secrets_dir / "origin_api_token")
    create_secret(secrets_dir / "mcp_client_token")
    env = base / ".env"
    if not env.exists():
        shutil.copy2(base / ".env.example", env)
        print("CREATED: .env (nonsecret settings)")
    else:
        print("EXISTS: .env (unchanged)")
    if (secrets_dir / "origin_api_token").read_bytes() == (secrets_dir / "mcp_client_token").read_bytes():
        raise SystemExit("Refusing identical origin/MCP secrets")
    print("BOOTSTRAP_COMPLETE: docker compose up -d --build")


if __name__ == "__main__":
    main()
