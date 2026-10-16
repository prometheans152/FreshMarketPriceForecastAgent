"""Isolated manual service must reject cross-origin / DNS rebinding traffic.

Uses real Starlette TestClient in a fresh Python process so manual imports do
not pollute legacy agent pytest collection. No model/provider APIs or private
records are read. These network-facing controls are manual-mode only.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_manual_loopback_origin_and_host_fail_closed(tmp_path):
    script = r"""
import sys
from pathlib import Path
from fastapi.testclient import TestClient
from aiot_price.integrations.manual_web import isolated_environment
isolated_environment(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
from aiot_price.api.app import app

base='http://127.0.0.1:8766'
with TestClient(app, base_url=base, client=('127.0.0.1', 56010)) as client:
    good=[
      ({},'/agent/status',200),
      ({'Origin':base},'/agent/status',200),
      ({'Referer':base+'/index.html'},'/agent/status',200),
      ({'Origin':base,'Sec-Fetch-Site':'same-origin'},'/agent/status',200),
    ]
    bad=[
      ({'Origin':'https://attacker.example'},'/health','origin'),
      ({'Origin':'null'},'/health','null_origin'),
      ({'Origin':'http://127.0.0.1:9999'},'/health','different_port'),
      ({'Host':'attacker.example:8766'},'/health','host_rebinding'),
      ({'Sec-Fetch-Site':'cross-site'},'/health','cross_site_browser'),
      ({'Sec-Fetch-Site':'same-site'},'/health','same_site_not_origin'),
      ({'Referer':'https://attacker.example/steal'},'/health','cross_site_referer'),
    ]
    for headers,path,expected in good:
        r=client.get(path,headers=headers)
        assert r.status_code == expected,(path,headers,r.status_code,r.text[:200])
    for headers,path,tag in bad:
        r=client.get(path,headers=headers)
        assert r.status_code == 403,(tag,r.status_code,r.text[:200])
        assert r.json()['error']['code']=='manual_local_origin_only'
    post=client.post('/records',json={'request_id':'fake'},headers={
        'Origin':'https://attacker.example',
        'Content-Type':'text/plain',
    })
    assert post.status_code==403,post.text

with TestClient(app, base_url=base,client=('192.0.2.25',56010)) as outside:
    r=outside.get('/health')
    assert r.status_code==403,('remote_client',r.status_code,r.text[:200])
print('same_origin_good=4 cross_origin_denied=9')
"""
    env = {
        **os.environ,
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONPATH": str(PROJECT_ROOT / "src"),
        "AIOT_RUNTIME_ISOLATED": "1",
    }
    result = subprocess.run(
        [
            sys.executable, "-X", "utf8", "-c", script,
            str(tmp_path / "home"),
            str(PROJECT_ROOT / "models" / "releases" / "0.1.0"),
            str(tmp_path / "records"),
        ],
        cwd=PROJECT_ROOT, env=env, text=True, capture_output=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    assert 'same_origin_good=4 cross_origin_denied=9' in result.stdout
