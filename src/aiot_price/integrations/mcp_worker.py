"""Single-invocation worker using original ML interpreter; JSON on private stdout.

No model API, no records endpoint, no HTTP listener, no arbitrary dispatch.
This child can always be killed by the transport at a 15-second deadline.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Internal numeric worker; not an MCP listener")
    parser.add_argument("--release-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    # Only read trusted transport-provided input, bounded before JSON parsing.
    payload_bytes = sys.stdin.buffer.read(8193)
    if len(payload_bytes) > 8192:
        print(json.dumps({"ok": False, "error": "工具輸入過大。"}, ensure_ascii=False))
        return 2
    try:
        from aiot_price.integrations.chatgpt_contracts import strict_json_loads
        payload = strict_json_loads(payload_bytes.decode("utf-8"))
        if not isinstance(payload, dict) or set(payload) != {"tool", "arguments"}:
            raise ValueError("worker 輸入格式不合法。")
        from aiot_price.integrations.chatgpt_adapter import execute_tool

        answer = execute_tool(payload["tool"], payload["arguments"], args.release_dir)
        print(json.dumps({"ok": True, "result": answer}, ensure_ascii=False, allow_nan=False))
        return 0
    except Exception as exc:
        # Never include environment variables, key contents, local private file data.
        from aiot_price.integrations.chatgpt_contracts import ContractError
        from aiot_price.integrations.chatgpt_adapter import ToolUnavailable

        msg = str(exc) if isinstance(exc, (ValueError, ContractError, ToolUnavailable)) else "模型工作程序無法完成查詢。"
        print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
        if not isinstance(exc, (ValueError, ContractError, ToolUnavailable)):
            print(f"worker unexpected error type={type(exc).__name__}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
