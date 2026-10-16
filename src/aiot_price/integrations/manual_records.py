"""Defensive reader for manual-only sandbox records.

The legacy prediction_records.py file is intentionally left unchanged. This
reader preserves every malformed file for manual inspection and reports the
number skipped, without exposing it in the active form or export.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

RECORD_ID = re.compile(r"[A-Za-z0-9_-]+\Z")


def load_manual_records(out_dir: str | Path, include_skipped_info: bool = False):
    folder = Path(out_dir)
    if not folder.exists():
        return ([], 0) if include_skipped_info else []
    records, skipped = [], 0
    for path in sorted(folder.glob("prediction_*.json")):
        # Never follow a link to an unrelated user file from the local store.
        record_id = path.stem.removeprefix("prediction_")
        if path.is_symlink() or not RECORD_ID.fullmatch(record_id):
            skipped += 1
            continue
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError, OSError):
            skipped += 1
            continue
        if not isinstance(record, dict):
            skipped += 1
            continue
        request = record.get("request")
        response = record.get("response")
        if not isinstance(request, dict) or not isinstance(response, dict):
            skipped += 1
            continue
        results = response.get("results")
        if not isinstance(results, list) or any(not isinstance(row, dict) for row in results):
            skipped += 1
            continue
        # Reproduce the legacy summary/export shape for valid entries, without
        # mutating or normalizing source JSON on disk.
        records.append({**record, "record_id": record_id})
    return (records, skipped) if include_skipped_info else records
