"""Manual-only record listing must skip bad local JSON without touching files.

Original prediction_records.py remains frozen and legacy API unchanged.
This test uses an isolated temporary synthetic records directory.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_manual_corrupted_record_json_skipped_and_preserved(tmp_path):
    script = r"""
import hashlib,sys
from pathlib import Path
from fastapi.testclient import TestClient
from aiot_price.integrations.manual_web import isolated_environment
home,release,records = map(Path,sys.argv[1:4])
records.mkdir(parents=True,exist_ok=True)
samples={
    'prediction_null.json':b'null',
    'prediction_list.json':b'[]',
    'prediction_number.json':b'42',
    'prediction_invalid_utf8.json':b'\xff\xfe\xfd',
    'prediction_bad_request.json':b'{"request":"bad","response":{"results":[]}}',
    'prediction_bad_result.json':b'{"request":{},"response":{"results":[null]}}',
}
for key,value in samples.items():
    (records/key).write_bytes(value)
before={key:hashlib.sha256((records/key).read_bytes()).hexdigest() for key in samples}
isolated_environment(home,release,records)
from aiot_price.api.app import app
with TestClient(app) as client:
    listed=client.get('/records')
    assert listed.status_code==200,listed.text
    assert listed.json()['records']==[]
    assert listed.json()['skipped_bad_records']==len(samples)
    exported=client.get('/records/export')
    assert exported.status_code==200,exported.text
    assert exported.json()['records']==[]
after={key:hashlib.sha256((records/key).read_bytes()).hexdigest() for key in samples}
assert before==after,'unexpected modification to corrupted local files'
print('corrupted_records_skipped=6 original_files_preserved=True')
"""
    env = {
        **os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8",
        "PYTHONPATH": str(PROJECT_ROOT / "src"), "AIOT_RUNTIME_ISOLATED": "1",
    }
    p = subprocess.run(
        [
            sys.executable, "-X", "utf8", "-c", script,
            str(tmp_path / "home"),
            str(PROJECT_ROOT / "models" / "releases" / "0.1.0"),
            str(tmp_path / "records"),
        ],
        cwd=PROJECT_ROOT, env=env, text=True, encoding="utf-8",
        capture_output=True, timeout=25,
    )
    assert p.returncode == 0, p.stdout + "\n" + p.stderr
    assert "corrupted_records_skipped=6" in p.stdout
