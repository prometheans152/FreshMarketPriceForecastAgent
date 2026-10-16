"""Input bounds must reject before decode/parser/large error construction."""
from __future__ import annotations

import asyncio
import importlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from aiot_price.integrations.chatgpt_contracts import ContractError, validate_arguments


def _ingress():
    name = "aiot_price.integrations.bounded_stdio"
    assert importlib.util.find_spec(name) is not None, "MCP binary ingress guard is missing"
    return importlib.import_module(name)


def test_extra_key_error_does_not_echo_or_join_large_input():
    arguments = {"crop_id": "cabbage", "market_id": "中義市場"}
    arguments.update({"sensitive_extra_" + str(i): 0 for i in range(512)})
    with pytest.raises(ContractError) as exc:
        validate_arguments("get_market_quote", arguments)
    assert len(str(exc.value)) < 256
    assert "sensitive_extra" not in str(exc.value)


def test_long_extra_key_error_is_bounded():
    with pytest.raises(ContractError) as exc:
        validate_arguments("get_market_quote", {"crop_id": "cabbage", "market_id": "中義市場", "private_" + "x" * 4096: 0})
    assert len(str(exc.value)) < 256
    assert "private_" not in str(exc.value)


def test_non_string_argument_key_is_controlled_contract_error():
    with pytest.raises(ContractError):
        validate_arguments("get_market_quote", {"crop_id": "cabbage", "market_id": "中義市場", 7: 0})


def test_invalid_unicode_argument_key_is_controlled_contract_error():
    with pytest.raises(ContractError):
        validate_arguments("get_market_quote", {"crop_id": "cabbage", "market_id": "中義市場", "\ud800": 0})


def test_oversized_argument_mapping_is_rejected_before_iteration():
    class OversizedMapping(dict):
        def __iter__(self):
            raise AssertionError("Oversized argument keys must not be enumerated")
    with pytest.raises(ContractError):
        validate_arguments("post_forecast", OversizedMapping({str(i): 0 for i in range(512)}))


def _read_one(raw):
    return asyncio.run(_ingress().BoundedStdin(io.BytesIO(raw)).__anext__())


def _native_sdk_configuration():
    sdk_python = os.environ.get("FMPA_MCP_PYTHON", os.environ.get("TW01_MCP_PYTHON"))
    if not sdk_python:
        if os.environ.get("FMPA_ACCEPTANCE", os.environ.get("TW01_ACCEPTANCE")) == "1":
            pytest.fail("Native ingress acceptance requires FMPA_MCP_PYTHON; skipping would hide missing coverage.")
        pytest.skip("Set FMPA_MCP_PYTHON to the isolated official SDK Python for actual stdio ingress")
    return sdk_python


def test_byte_limit_is_checked_before_utf8_decode():
    guard = _ingress()
    with pytest.raises(guard.IngressLimitError, match="message_bytes"):
        _read_one(b"\xff" * 16385)


def test_reader_never_requests_or_retains_an_unbounded_line():
    guard = _ingress()
    class RecordingBinary(io.BytesIO):
        sizes = []
        def readline(self, size=-1):
            self.sizes.append(size)
            return super().readline(size)
    stream = RecordingBinary(b"x" * 65536)
    with pytest.raises(guard.IngressLimitError, match="message_bytes"):
        asyncio.run(guard.BoundedStdin(stream).__anext__())
    assert stream.sizes == [16385]
    assert stream.tell() == 16385


@pytest.mark.parametrize("raw,reason", [
    (b'[' * 17 + b'0' + b']' * 17 + b'\n', "json_depth"),
    (json.dumps({str(i): 0 for i in range(129)}).encode() + b'\n', "object_members"),
    (b'{"' + b'x' * 65 + b'":0}\n', "key_bytes"),
    (b'{"' + b'\\u0061' * 11 + b'":0}\n', "key_bytes"),
    (b'{"x":"\xff"}\n', "utf8"),
], ids=["depth", "members", "long_key", "escaped_key", "invalid_utf8"])
def test_resource_limit_cases_are_rejected(raw, reason):
    guard = _ingress()
    with pytest.raises(guard.IngressLimitError, match=reason):
        _read_one(raw)


def test_utf8_newline_frames_and_escaped_punctuation_are_preserved():
    guard = _ingress()
    raw = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "get_market_quote", "arguments": {"crop_id": "cabbage", "market_id": "中義市場"}, "padding": '[]{}:"\\'}} , ensure_ascii=False).encode() + b'\n'
    async def run():
        reader = guard.BoundedStdin(io.BytesIO(raw + b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n'))
        lines = [line async for line in reader]
        assert lines == [raw.decode("utf-8"), '{"jsonrpc":"2.0","method":"notifications/initialized"}\n']
    asyncio.run(run())


def test_depth_member_and_key_boundary_values_are_accepted():
    _read_one(b'[' * 16 + b'0' + b']' * 16 + b'\n')
    _read_one(json.dumps({str(i): 0 for i in range(128)}).encode() + b'\n')
    _read_one(b'{"' + b'x' * 64 + b'":0}\n')


def test_exact_byte_limit_is_accepted_and_next_byte_is_rejected():
    guard = _ingress()
    raw = b'{"padding":"' + b'x' * 16369 + b'"}\n'
    assert len(raw) == 16384
    assert _read_one(raw) == raw.decode()
    with pytest.raises(guard.IngressLimitError, match="message_bytes"):
        _read_one(raw[:-2] + b'x' + raw[-2:])


@pytest.mark.parametrize("raw,reason", [
    (b'{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"padding":"' + b'x' * 65536 + b'"}}\n', "message_bytes"),
    (json.dumps({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {str(i): 0 for i in range(129)}}).encode() + b'\n', "object_members"),
    (b'{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"' + b'x' * 65 + b'":0}}\n', "key_bytes"),
    (b'{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"x":' + b'[' * 64 + b'0' + b']' * 64 + b'}}\n', "json_depth"),
], ids=["oversized_bytes", "extra_members", "long_key", "deep_json"])
def test_native_production_ingress_rejects_before_request_dispatch(raw, reason, tmp_path):
    sdk_python = _native_sdk_configuration()
    root = Path(__file__).resolve().parents[2]
    home = tmp_path / "native_home"
    env = {key: os.environ[key] for key in ("SystemRoot", "WINDIR", "COMSPEC", "PATH", "PATHEXT", "TEMP", "TMP") if key in os.environ}
    env.update({"PYTHONPATH": str(root / "src"), "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8", "AIOT_RUNTIME_ISOLATED": "1"})
    for key, sub in (("HOME", ""), ("USERPROFILE", ""), ("APPDATA", "AppData/Roaming"), ("LOCALAPPDATA", "AppData/Local"),
                     ("XDG_CONFIG_HOME", "xdg/config"), ("XDG_DATA_HOME", "xdg/data"), ("XDG_CACHE_HOME", "xdg/cache"),
                     ("HERMES_HOME", "hermes"), ("AIOT_HERMES_HOME", "aiot_hermes")):
        env[key] = str(home / sub)
    command = [sdk_python, "-X", "utf8", "-m", "aiot_price.integrations.chatgpt_mcp",
               "--release-dir", str(root / "models/releases/0.1.0"), "--worker-python", sys.executable, "--home", str(home)]
    result = subprocess.run(command, input=raw, cwd=root, env=env, capture_output=True, timeout=10)
    # Windows kill-on-close may report exit 0; require the actual pre-parser
    # rejection and closed transport, never infer acceptance from that code.
    assert b"IngressLimitError" in result.stderr and reason.encode() in result.stderr
    assert len(result.stderr) < 65536
    assert not result.stdout, "Ingress breach must never reach a request response"


def test_native_acceptance_missing_sdk_fails_instead_of_skipping(monkeypatch):
    monkeypatch.delenv("FMPA_MCP_PYTHON", raising=False)
    monkeypatch.delenv("TW01_MCP_PYTHON", raising=False)
    monkeypatch.setenv("FMPA_ACCEPTANCE", "1")
    with pytest.raises(pytest.fail.Exception):
        try:
            _native_sdk_configuration()
        except pytest.skip.Exception as exc:
            raise AssertionError("Acceptance mode skipped required native ingress coverage") from exc


def test_native_optional_mode_missing_sdk_reports_skip(monkeypatch):
    monkeypatch.delenv("FMPA_MCP_PYTHON", raising=False)
    monkeypatch.delenv("TW01_MCP_PYTHON", raising=False)
    monkeypatch.delenv("FMPA_ACCEPTANCE", raising=False)
    monkeypatch.delenv("TW01_ACCEPTANCE", raising=False)
    with pytest.raises(pytest.skip.Exception):
        _native_sdk_configuration()
