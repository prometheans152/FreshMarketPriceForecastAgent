"""Serve every forecast from the verified rolling public history (D48).

Wraps the /v1 full-catalog app (D47) without changing the image. Every frozen
check still runs as before: the 0.1.0 release is copied and SHA-256 verified
on each request, and the 61-item catalog and pooled models are verified
against the 2026-10-02 snapshot they were trained on. Only the model INPUTS,
the public price history, then come from the newest valid rolling version:

- 3 frozen crops: the verified private release snapshot gets the rolling
  public_history.parquet in place of its frozen copy;
- other catalog items: data_bundle() returns the rolling catalog and history,
  with the frozen manifest kept as the model-compatibility identity, so
  data_version still names the training snapshot.

A new version is verified off the request path (from /healthz, which Docker
polls every 30 s) and switched in only while no inference holds the single
inference lock, so one answer never mixes two versions. If no version
verifies, the frozen snapshot is served exactly as before D48.
"""
from __future__ import annotations

import hashlib
import logging
import os
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import forecastengine_api as api
import full_catalog_runtime as catalog_runtime
import oracle_web_site
import pooled_ml_runtime
from aiot_price.integrations import chatgpt_adapter

import rolling_store as store

log = logging.getLogger("fmpa.rolling")
ROOT = os.environ.get("FMPA_ROLLING_DIR", "")

_frozen_data_bundle = catalog_runtime.data_bundle
_frozen_snapshot = chatgpt_adapter.verified_release_snapshot
_frozen_ready = api._ready_metadata


@dataclass(frozen=True)
class Serving:
    bundle: tuple                 # (catalog, history, index, manifest) as data_bundle() returns
    parquet: bytes | None         # rolling 3-crop history; None serves the frozen copy
    parquet_sha256: str | None
    version: str | None
    manifest_sha256: str | None
    cutoff: str
    source: str                   # "rolling" or "frozen"


_state: Serving | None = None
_pending: Serving | None = None
_seen_pointer: bytes | None = None
_status: dict = {"checked_at": None, "errors": []}
_init_lock = threading.Lock()
_refresh_lock = threading.Lock()


@lru_cache(maxsize=1)
def _base() -> store.FrozenBase:
    return store.load_frozen_base(api.RELEASE, _frozen_data_bundle())


def _frozen_state() -> Serving:
    bundle = _frozen_data_bundle()
    return Serving(bundle, None, None, None, None, bundle[0]["source_observation_cutoff"], "frozen")


def _rolling_state(version: store.Version) -> Serving:
    return Serving((version.catalog, version.history, version.index, _base().manifest),
                   version.parquet, version.parquet_sha256, version.version,
                   version.manifest_sha256, version.cutoff, "rolling")


def _select() -> Serving | None:
    """Newest verified version, or None. Rolling problems never stop the service."""
    try:
        version, errors = store.select(Path(ROOT), _base())
    except Exception as exc:
        version, errors = None, [f"unexpected: {type(exc).__name__}"]
    _status["errors"] = errors[-5:]
    for error in errors:
        log.warning("rolling history version skipped: %s", error)
    return _rolling_state(version) if version else None


def _current() -> Serving:
    global _state, _seen_pointer
    state = _state
    if state is None:
        with _init_lock:
            if _state is None:
                # The original frozen check runs first and fails exactly as before.
                frozen = _frozen_state()
                chosen = None
                if ROOT:
                    _seen_pointer = _pointer_bytes()
                    chosen = _select()
                if chosen:
                    # The rolling history contains the frozen one; do not hold both.
                    _frozen_data_bundle.cache_clear()
                _state = chosen or frozen
                _status["checked_at"] = _now()
            state = _state
    return state


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _pointer_bytes() -> bytes | None:
    try:
        return (Path(ROOT) / "CURRENT.json").read_bytes()
    except OSError:
        return None


def refresh() -> None:
    """Pick up a newly published version; swap only while no inference runs."""
    global _state, _pending, _seen_pointer
    if not ROOT:
        return
    current = _current()
    with _refresh_lock:
        pointer = _pointer_bytes()
        if pointer != _seen_pointer:
            _seen_pointer = pointer
            candidate = _select()
            # A broken or missing pointer keeps the last good version.
            if candidate and candidate.manifest_sha256 != current.manifest_sha256:
                _pending = candidate
            elif candidate:
                _pending = None
        if _pending is not None and api._busy.acquire(blocking=False):
            try:
                _state, _pending = _pending, None
            finally:
                api._busy.release()
            log.warning("rolling history switched to %s (cutoff %s)", _state.version, _state.cutoff)
        _status["checked_at"] = _now()


def status() -> dict:
    state, pending = _current(), _pending
    return {
        "source": state.source,
        "version": state.version,
        "cutoff": state.cutoff,
        "frozen_training_cutoff": state.bundle[3]["source_cutoff"],
        "pending_version": pending.version if pending else None,
        "checked_at": _status["checked_at"],
        "errors": list(_status["errors"]),
    }


# ---------- the three patched entry points ----------

def data_bundle():
    return _current().bundle


@contextmanager
def rolling_release_snapshot(release_dir):
    state = _current()
    with _frozen_snapshot(release_dir) as snapshot:
        if state.parquet is not None:
            if hashlib.sha256(state.parquet).hexdigest() != state.parquet_sha256:
                raise chatgpt_adapter.ToolUnavailable("滾動公開歷史 release 複本 SHA-256 不符。")
            # Replaces the frozen copy only inside this private, verified snapshot.
            (Path(snapshot) / "public_history.parquet").write_bytes(state.parquet)
        yield snapshot


def _ready_metadata() -> dict:
    refresh()
    result = _frozen_ready()      # still verifies the frozen release bytes and loads the engine
    info = status()
    result["public_data_cutoff"] = info["cutoff"]
    result["public_history"] = info
    return result


catalog_runtime.data_bundle = data_bundle
pooled_ml_runtime.data_bundle = data_bundle
chatgpt_adapter.verified_release_snapshot = rolling_release_snapshot
oracle_web_site.verified_release_snapshot = rolling_release_snapshot
api._ready_metadata = _ready_metadata

# Imported after the patches so it binds the rolling data_bundle (and its
# import-time pooled-model check already sees the rolling state).
import v1_full_catalog  # noqa: E402

app = v1_full_catalog.app
