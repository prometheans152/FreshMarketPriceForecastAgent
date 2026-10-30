"""Refresh the rolling public history from the Taichung source (D48).

Runs as a one-shot container from the host timer, as UID 10001, with the
rolling folder as its only writable mount. Downloads the fixed source URL,
validates it against the frozen snapshot and the last good version, and only
then publishes a new version and switches CURRENT.json. A rejected or failed
download changes nothing the server reads.

Exit codes: 0 switched or unchanged, 2 rejected by validation, 3 download
failed, 1 anything else. Every run also rewrites status.json and appends one
line to runs.jsonl in the rolling folder.
"""
from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import traceback
import urllib.request
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import rolling_store as store

TAIPEI = ZoneInfo("Asia/Taipei")
ALLOWED_PREFIX = "https://newdatacenter.taichung.gov.tw/"


def _env(name: str, default: str = "") -> str:
    """FMPA_* wins; legacy TW01_* is read only while the new name is absent."""
    return os.environ.get("FMPA_" + name, os.environ.get("TW01_" + name, default))


class DownloadFailed(Exception):
    pass


def download(url: str = store.DOWNLOAD_URL, timeout: float = 120.0) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "fresh-market-price-agent-rolling-history/1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=ssl.create_default_context()) as response:
            if response.status != 200 or not response.geturl().startswith(ALLOWED_PREFIX):
                raise DownloadFailed(f"HTTP {response.status} from an unexpected location")
            data = response.read(store.MAX_DOWNLOAD_BYTES + 1)
    except OSError as exc:
        raise DownloadFailed(type(exc).__name__) from None
    return data


@contextmanager
def _single_run(root: Path):
    """One updater at a time (systemd already serializes the timer runs)."""
    try:
        import fcntl
    except ImportError:          # Windows test runs
        yield
        return
    with open(root / ".update.lock", "w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise DownloadFailed("another update is running") from None
        yield


def _record(root: Path, result: dict) -> None:
    line = json.dumps(result, ensure_ascii=False, sort_keys=True)
    store.atomic_write(root / "status.json", (line + "\n").encode("utf-8"))
    with open(root / "runs.jsonl", "a", encoding="utf-8") as log:
        log.write(line + "\n")


def _frozen_loader():
    """The original, uncached frozen catalog check, also in a process rolling_runtime patched."""
    import full_catalog_runtime

    runtime = sys.modules.get("rolling_runtime")
    original = runtime._frozen_data_bundle if runtime else full_catalog_runtime.data_bundle
    return original.__wrapped__


def run(root: Path, *, source_file: Path | None, today: date, accept_shorter: bool) -> tuple[int, dict]:
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    result = {"checked_at": started, "today": today.isoformat()}
    try:
        with _single_run(root):
            # Original frozen checks first; they fail exactly as the server would.
            bundle = _frozen_loader()()
            base = store.load_frozen_base(Path(_env("RELEASE_DIR")), bundle)
            previous, skipped = store.select(root, base)
            result.update(current_version=previous.version if previous else None,
                          current_cutoff=previous.cutoff if previous else base.cutoff,
                          skipped_versions=skipped)
            raw = source_file.read_bytes() if source_file else download()
            parsed = store.parse_download(raw, base, today)
            outcome = store.publish(root, base, bundle[1], previous, parsed, raw,
                                    retrieved_at=started, accept_shorter=accept_shorter)
        result.update(outcome)
        code = 0
    except store.Rejected as exc:
        result.update(outcome="rejected", code=exc.code, message=str(exc))
        code = 2
    except DownloadFailed as exc:
        result.update(outcome="download_failed", message=str(exc))
        code = 3
    except Exception as exc:
        result.update(outcome="error", message=f"{type(exc).__name__}: {exc}")
        traceback.print_exc()
        code = 1
    _record(root, result)
    return code, result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=_env("ROLLING_DIR") or None,
                        help="rolling history folder (default $FMPA_ROLLING_DIR)")
    parser.add_argument("--source-file", type=Path,
                        help="use this saved download instead of fetching the source")
    parser.add_argument("--today", type=date.fromisoformat,
                        help="Taipei date used to reject future rows (default: today)")
    parser.add_argument("--accept-shorter-download", action="store_true",
                        help="the source window really shrank: accept it once (recorded in the manifest)")
    args = parser.parse_args(argv)
    if args.root is None or not args.root.is_dir():
        parser.error("--root or FMPA_ROLLING_DIR must name an existing folder")
    code, result = run(args.root, source_file=args.source_file,
                       today=args.today or datetime.now(TAIPEI).date(),
                       accept_shorter=args.accept_shorter_download)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
