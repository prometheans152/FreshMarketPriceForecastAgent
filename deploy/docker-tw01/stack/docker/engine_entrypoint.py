"""Read root-only Docker secret then run app as unprivileged UID 10001.

The Docker service config never carries an API Token; only the running Python
process receives it, after which the process permanently drops privileges.
"""
import os
import sys
from pathlib import Path


def main():
    file = Path(os.environ.get("TW01_ORIGIN_TOKEN_FILE", "/run/secrets/origin_api_token"))
    if not file.is_file() or file.is_symlink() or file.stat().st_size > 4096:
        raise SystemExit("TW01 origin Docker secret missing or malformed")
    token = file.read_text(encoding="utf-8").strip()
    if len(token) < 32 or "\n" in token or "\r" in token:
        raise SystemExit("TW01 origin Docker secret is invalid")
    if os.geteuid() != 0:
        raise SystemExit("Docker secret bootstrap must start as root")
    env = dict(os.environ)
    env.pop("TW01_ORIGIN_TOKEN_FILE", None)
    env["TW01_ORIGIN_API_TOKEN"] = token
    os.setgroups([])
    os.setgid(10001)
    os.setuid(10001)
    args = [
        sys.executable, "-m", "uvicorn", "oracle_web_site_ml:app",
        "--app-dir", "/app/deploy/oracle-forecastengine",
        "--host", "0.0.0.0", "--port", "8767", "--workers", "1",
        "--no-access-log", "--log-level", "warning",
        "--timeout-keep-alive", "4",
    ]
    os.execve(sys.executable, args, env)


if __name__ == "__main__":
    main()
