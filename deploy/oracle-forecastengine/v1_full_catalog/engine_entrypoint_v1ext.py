"""Read root-only Docker secret then run the /v1 full-catalog app as UID 10001.

Same as the image's docker/engine_entrypoint.py except that it serves
v1_full_catalog:app (which still includes every oracle_web_site_ml route) and
hands the token over under both the legacy TW01_ and the new FMPA_ name, so it
works with the v1.0.0 image and with later images.
"""
import os
import sys
from pathlib import Path


def main():
    file = Path(os.environ.get(
        "FMPA_ORIGIN_TOKEN_FILE",
        os.environ.get("TW01_ORIGIN_TOKEN_FILE", "/run/secrets/origin_api_token"),
    ))
    if not file.is_file() or file.is_symlink() or file.stat().st_size > 4096:
        raise SystemExit("Origin Docker secret missing or malformed")
    token = file.read_text(encoding="utf-8").strip()
    if len(token) < 32 or "\n" in token or "\r" in token:
        raise SystemExit("Origin Docker secret is invalid")
    if os.geteuid() != 0:
        raise SystemExit("Docker secret bootstrap must start as root")
    env = dict(os.environ)
    env.pop("FMPA_ORIGIN_TOKEN_FILE", None)
    env.pop("TW01_ORIGIN_TOKEN_FILE", None)
    env["FMPA_ORIGIN_API_TOKEN"] = token
    env["TW01_ORIGIN_API_TOKEN"] = token
    os.setgroups([])
    os.setgid(10001)
    os.setuid(10001)
    args = [
        sys.executable, "-m", "uvicorn", "v1_full_catalog:app",
        "--app-dir", "/app/ext",
        "--host", "0.0.0.0", "--port", "8767", "--workers", "1",
        "--no-access-log", "--log-level", "warning",
        "--timeout-keep-alive", "4",
    ]
    os.execve(sys.executable, args, env)


if __name__ == "__main__":
    main()
