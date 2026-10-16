"""Launch the existing TW01 UI on loopback with dedicated Hermes credentials.

Default: local, personal Hermes demonstration using the Coding Plan endpoint.
--general-api: ordinary product API usage; requires general API resources.
No account settings, Qwen configuration, or remote deployment are modified.
"""
from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
KEY_FILE = ROOT / "private/glm_zai/project.env"


def read_key_file(path: Path) -> dict[str, str]:
    if not path.is_file() or path.stat().st_size > 8192:
        raise ValueError("dedicated_key_file_missing_or_too_large")
    fields = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError("key_file_not_literal_assignment")
        name, value = (part.strip() for part in line.split("=", 1))
        if name not in {"AIOT_GLM_API_KEY", "AIOT_GLM_MODEL"} or name in fields:
            raise ValueError("key_file_unknown_or_duplicate_field")
        if any(char in value for char in ("$", "`", ";", "|", "&", '"', "'")):
            raise ValueError("key_file_shell_syntax_rejected")
        fields[name] = value
    key = fields.get("AIOT_GLM_API_KEY", "")
    if not key or key.lower().startswith(("your_", "your-", "replace_", "<", "請填", "貼上")):
        raise ValueError("dedicated_key_missing")
    return fields


def build_environment(key_file: Path, home: Path, source: dict[str, str], *, local_demo: bool = True, model: str = "glm-5.3-flash") -> dict[str, str]:
    fields = read_key_file(key_file)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}", model):
        raise ValueError("model_id_invalid")
    home = home.resolve()
    env = {}
    for name, value in source.items():
        upper = name.upper()
        credential = upper.endswith(("_API_KEY", "_TOKEN", "_SECRET", "_KEY")) or upper in {"AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"}
        override = upper.startswith(("HERMES_", "AIOT_AGENT_", "XDG_")) or upper.endswith("_BASE_URL") or upper in {
            "HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "HOMEDRIVE", "HOMEPATH",
            "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "SSLKEYLOGFILE",
            "OPENAI_ORG_ID", "OPENAI_PROJECT_ID", "AIOT_GLM_MODEL", "AIOT_LOCAL_HERMES_DEMO",
        }
        if not (credential or override):
            env[name] = value
    env.update({
        "AIOT_GLM_API_KEY": fields["AIOT_GLM_API_KEY"], "AIOT_GLM_MODEL": model,
        "AIOT_AGENT_PROFILE": "glm_zai_coding" if local_demo else "glm_zai",
        "AIOT_AGENT_FRAMEWORK": "hermes", "AIOT_LOCAL_HERMES_DEMO": "1" if local_demo else "0",
        "AIOT_RUNTIME_ISOLATED": "1",
        "AIOT_HERMES_HOME": str(home), "HERMES_HOME": str(home),
        "HOME": str(home), "USERPROFILE": str(home),
        "APPDATA": str(home / "appdata/roaming"), "LOCALAPPDATA": str(home / "appdata/local"),
        "HOMEDRIVE": home.drive, "HOMEPATH": str(home)[len(home.drive):],
        "XDG_CONFIG_HOME": str(home / "config"), "XDG_CONFIG_DIRS": str(home / "config"),
        "XDG_DATA_HOME": str(home / "data"), "XDG_DATA_DIRS": str(home / "data"),
        "XDG_CACHE_HOME": str(home / "cache"), "XDG_STATE_HOME": str(home / "state"),
        "XDG_RUNTIME_DIR": str(home / "runtime"),
        "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8",
    })
    return env


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--model", default="glm-5.3-flash")
    parser.add_argument("--general-api", action="store_true")
    parser.add_argument("--key-file", type=Path, default=KEY_FILE)
    parser.add_argument("--home", type=Path, default=ROOT / "private/hermes_web_home")
    args = parser.parse_args(argv)
    if not 1024 <= args.port <= 65535:
        parser.error("port must be between 1024 and 65535")
    try:
        env = build_environment(args.key_file, args.home, dict(os.environ), local_demo=not args.general_api, model=args.model)
    except (ValueError, OSError) as error:
        print("Hermes startup failed: " + (str(error) if isinstance(error, ValueError) else type(error).__name__))
        return 2
    os.environ.clear()
    os.environ.update(env)
    args.home.resolve().mkdir(parents=True, exist_ok=True)
    os.chdir(ROOT)
    # Import only after credential, HOME, dotenv and provider isolation.
    import uvicorn

    uvicorn.run("aiot_price.api.app:app", host="127.0.0.1", port=args.port, workers=1, access_log=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
