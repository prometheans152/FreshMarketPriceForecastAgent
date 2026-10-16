"""Isolated, loopback-only FMPA A/B form launcher."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
LOOPBACK = ("127.0.0.1", "::1", "localhost")


def isolated_environment(home: Path, release_dir: Path, records_dir: Path | None = None):
    """Initialize the manual runtime before the first API import."""
    home = home.resolve()
    home.mkdir(parents=True, exist_ok=True)
    paths = {
        "HOME": home, "USERPROFILE": home,
        "APPDATA": home / "AppData" / "Roaming",
        "LOCALAPPDATA": home / "AppData" / "Local",
        "XDG_CONFIG_HOME": home / "xdg" / "config",
        "XDG_DATA_HOME": home / "xdg" / "data",
        "XDG_CACHE_HOME": home / "xdg" / "cache",
        "HERMES_HOME": home / "hermes", "AIOT_HERMES_HOME": home / "aiot_hermes",
    }
    # Environment *names* are all that may be logged; values are never read.
    disabled = ("AIOT_GLM_", "AIOT_QWEN_", "AIOT_AGENT_", "AIOT_HERMES_",
                "HERMES_", "GLM_", "QWEN_", "ZAI_", "OPENAI_", "DASHSCOPE_")
    ignored = ("AIOT_LOCAL_HERMES_DEMO", "ANTHROPIC_API_KEY")
    removed = []
    for name in tuple(os.environ):
        if name.startswith(disabled) or name in ignored:
            os.environ.pop(name, None)
            removed.append(name)
    # Populate isolated paths only after inherited provider settings are removed;
    # otherwise HERMES_HOME itself would accidentally be stripped.
    for key, value in paths.items():
        os.environ[key] = str(value)
    os.environ["AIOT_RUNTIME_ISOLATED"] = "1"
    os.environ["AIOT_MANUAL_WEB"] = "1"
    os.environ["AIOT_RELEASE_DIR"] = str(release_dir.resolve())
    if records_dir is None:
        os.environ.pop("AIOT_RECORDS_DIR", None)
    else:
        os.environ["AIOT_RECORDS_DIR"] = str(records_dir.resolve())
    return tuple(sorted(removed))


def main(argv=None):
    parser = argparse.ArgumentParser(description="FMPA manual form; no LLM required")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--release-dir", type=Path, default=PROJECT_ROOT / "models" / "releases" / "0.1.0")
    parser.add_argument("--records-dir", type=Path, default=None)
    parser.add_argument("--home", type=Path, default=PROJECT_ROOT / "outputs" / "runtime_home" / "manual")
    args = parser.parse_args(argv)
    if args.host not in LOOPBACK:
        parser.error("Only loopback interfaces are allowed.")
    if not 0 < args.port < 65536:
        parser.error("Invalid port.")
    isolated_environment(args.home, args.release_dir, args.records_dir)
    from aiot_price.api.app import app
    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
